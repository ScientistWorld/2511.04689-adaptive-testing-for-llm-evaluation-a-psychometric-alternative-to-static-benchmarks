#!/usr/bin/env python3
"""Visible (train) evaluator for reduced-item ability estimation.

Same protocol, budgets, gates and metrics as the hidden test, run over the
*visible* model identities: responses from
``data/downloads/atlas_response_matrices/data/clean_response_matrix_<b>.csv``,
whole-bank ability targets from
``data/calibrated_banks/<b>/irt_person_scores_WLE_SE.csv`` and the item bank
from ``data/calibrated_banks/<b>/irt_item_parameters_combined.csv``.  Budgets
are read from ``eval/train/budgets.json``.  ``--benchmarks``, ``--slots`` and
``--limit`` are development conveniences; the hidden test always scores every
benchmark, slot and held-out instance.

Each method is a *policy program* declared in a ``manifest.json``::

    {"method": "...",
     "slots": {"ATLAS_0.1": {"command": ["python", "path/to/policy.py", ...]},
               "ATLAS_0.2": {...}, "ATLAS_0.3": {...}}}

For every benchmark and claimed slot the evaluator starts the command (cwd =
workspace) and talks JSON lines over stdin/stdout:

    evaluator -> {"type": "session", "benchmark", "slot", "budget",
                  "max_items_per_instance", "num_instances", "num_items"}
    evaluator -> {"type": "instance", "id", "index"}
    policy    -> {"type": "query", "item": "<item id>"}   (or "items": [...])
    evaluator -> {"type": "response", "items": [...], "scores": [0/1, ...]}
    policy    -> {"type": "estimate", "theta": <float>}   (ends the instance)
    evaluator -> {"type": "end"}

Every scored number is recomputed here from the queried items and the reported
abilities; nothing else the method writes is read.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import random
import select
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

try:  # numpy is installed in the gym container; the pure-Python path is a fallback.
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


SLICE_NAME = "train"
HERE = Path(__file__).resolve().parent
WORKSPACE_DATA = Path("data")
BUDGET_FILE = HERE / "budgets.json"

BENCHMARKS = ("truthfulqa", "winogrande", "hellaswag", "gsm8k", "arc")
SLOTS = ("ATLAS_0.1", "ATLAS_0.2", "ATLAS_0.3")
BASELINE = "Random100"
BASELINE_ITEMS = 100
BASELINE_SEED = 777
ORDER_SEED = "atlas-gym-instance-order-v2"
MAX_ITEMS_PER_INSTANCE = 500
THETA_LIMIT = 10.0
PRECISION_GATE = 2.0  # ability MAE above 2 x Random100's ability MAE is a failed measurement
RESPONSE_TIMEOUT_S = 900.0
GRID = [-6.0 + 0.05 * k for k in range(241)]


class ProtocolError(RuntimeError):
    pass


# --------------------------------------------------------------------------- data


class Benchmark:
    def __init__(self, name: str, item_ids: list[str], a: list[float], b: list[float], c: list[float],
                 u: list[float], models: list[str], targets: list[float], responses: list[bytes]):
        self.name = name
        self.item_ids = item_ids
        self.index_of = {item: k for k, item in enumerate(item_ids)}
        self.a, self.b, self.c, self.u = a, b, c, u
        self.models = models
        self.targets = targets
        self.responses = responses
        self.raw_accuracy = [sum(row) / len(item_ids) for row in responses]
        if np is not None:
            self.a_np = np.asarray(a, dtype=np.float64)
            self.b_np = np.asarray(b, dtype=np.float64)
            self.c_np = np.asarray(c, dtype=np.float64)
            self.u_np = np.asarray(u, dtype=np.float64)

    @property
    def n_items(self) -> int:
        return len(self.item_ids)

    def subset(self, limit: int) -> "Benchmark":
        return Benchmark(self.name, self.item_ids, self.a, self.b, self.c, self.u,
                         self.models[:limit], self.targets[:limit], self.responses[:limit])


_BITS = bytes.maketrans(b"01", b"\x00\x01")


def read_items(path: Path) -> tuple[list[str], list[float], list[float], list[float], list[float]]:
    import csv

    ids, a_vals, b_vals, c_vals, u_vals = [], [], [], [], []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            a = float(row["a1"])
            ids.append(row["X"])
            a_vals.append(a)
            b_vals.append(-float(row["d"]) / a)
            c_vals.append(float(row["g"]))
            u_vals.append(float(row.get("u") or 1.0))
    return ids, a_vals, b_vals, c_vals, u_vals


def load_benchmark(name: str, workspace: Path = Path(".")) -> Benchmark:
    import csv

    bank_dir = workspace / WORKSPACE_DATA / "calibrated_banks" / name
    ids, a, b, c, u = read_items(bank_dir / "irt_item_parameters_combined.csv")
    with (bank_dir / "irt_person_scores_WLE_SE.csv").open(newline="") as f:
        targets = {}
        for row in csv.DictReader(f):
            try:
                value = float(row["Theta_WLE"])
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                targets[row["Model_Name"]] = value
    matrix = workspace / WORKSPACE_DATA / "downloads" / "atlas_response_matrices" / "data" / f"clean_response_matrix_{name}.csv"
    rows = []
    seen = set()
    with matrix.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        position = {col: k for k, col in enumerate(header)}
        idx = [position[item] for item in ids]
        for row in reader:
            model = row[0]
            if model not in targets or model in seen:
                continue
            seen.add(model)
            bits = "".join(row[j] for j in idx).encode("ascii")
            rows.append((model, targets[model], bits.translate(_BITS)))
    rows.sort(key=lambda r: r[0])
    random.Random(f"{ORDER_SEED}:{name}:{SLICE_NAME}").shuffle(rows)
    return Benchmark(name, ids, a, b, c, u, [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows])


def load_budgets() -> dict[str, dict[str, float]]:
    if not BUDGET_FILE.exists():
        raise SystemExit(f"Missing evaluator budget file {BUDGET_FILE}")
    with BUDGET_FILE.open() as f:
        budgets = json.load(f)
    for bench in BENCHMARKS:
        for slot in SLOTS:
            value = budgets[bench][slot]
            if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
                raise SystemExit(f"Invalid budget for {bench}/{slot}: {value!r}")
    return budgets


# ------------------------------------------------------------------ IRT helpers


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def standard_error(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values) / math.sqrt(len(values))


def item_probabilities(theta: float, bench: Benchmark):
    if np is not None:
        z = np.clip(bench.a_np * (theta - bench.b_np), -40.0, 40.0)
        return bench.c_np + (bench.u_np - bench.c_np) / (1.0 + np.exp(-z))
    out = []
    for a, b, c, u in zip(bench.a, bench.b, bench.c, bench.u):
        z = max(-40.0, min(40.0, a * (theta - b)))
        out.append(c + (u - c) / (1.0 + math.exp(-z)))
    return out


def pirt_accuracy(theta: float, administered: set[int], row: bytes, bench: Benchmark) -> float:
    """p-IRT: observed responses on administered items + 3PL predictions elsewhere."""
    probs = item_probabilities(theta, bench)
    if np is not None:
        predicted = float(probs.sum())
        if administered:
            idx = np.fromiter(administered, dtype=np.int64)
            predicted -= float(probs[idx].sum())
    else:
        predicted = sum(probs) - sum(probs[j] for j in administered)
    observed = sum(row[j] for j in administered)
    return (observed + predicted) / bench.n_items


def eap_fixed_subset(bench: Benchmark, subset: list[int]) -> list[float]:
    """EAP ability (N(0,1) prior, 241-point grid on [-6, 6]) from a fixed item subset."""
    if np is not None:
        grid = np.asarray(GRID)
        a, b, c, u = bench.a_np[subset], bench.b_np[subset], bench.c_np[subset], bench.u_np[subset]
        z = np.clip(a[None, :] * (grid[:, None] - b[None, :]), -40.0, 40.0)
        p = c + (u - c) / (1.0 + np.exp(-z))
        log_p = np.log(np.clip(p, 1e-9, 1.0))
        log_q = np.log(np.clip(1.0 - p, 1e-9, 1.0))
        y = np.asarray([[row[j] for j in subset] for row in bench.responses], dtype=np.float64)
        log_post = y @ log_p.T + (1.0 - y) @ log_q.T - 0.5 * grid[None, :] ** 2
        log_post -= log_post.max(axis=1, keepdims=True)
        w = np.exp(log_post)
        w /= w.sum(axis=1, keepdims=True)
        return [float(v) for v in w @ grid]
    thetas = []
    probs = []
    for t in GRID:
        row = []
        for j in subset:
            z = max(-40.0, min(40.0, bench.a[j] * (t - bench.b[j])))
            p = bench.c[j] + (bench.u[j] - bench.c[j]) / (1.0 + math.exp(-z))
            row.append((math.log(min(max(p, 1e-9), 1.0)), math.log(min(max(1.0 - p, 1e-9), 1.0))))
        probs.append(row)
    for resp in bench.responses:
        log_post = []
        for g, t in enumerate(GRID):
            s = -0.5 * t * t
            for k, j in enumerate(subset):
                s += probs[g][k][0] if resp[j] else probs[g][k][1]
            log_post.append(s)
        top = max(log_post)
        w = [math.exp(v - top) for v in log_post]
        total = sum(w)
        thetas.append(sum(wi * t for wi, t in zip(w, GRID)) / total)
    return thetas


def overlap_rate(item_sets: list[set[int]]) -> float:
    """Paper Eq. (7): expected share of common items between two test forms."""
    n = len(item_sets)
    if n < 2:
        return 0.0
    avg_len = mean([float(len(s)) for s in item_sets])
    if avg_len <= 0:
        return 0.0
    counts = Counter(item for s in item_sets for item in s)
    square_sum = sum((count / n) ** 2 for count in counts.values())
    return (n * square_sum) / (avg_len * (n - 1)) - 1.0 / (n - 1)


def exposure_rate(item_sets: list[set[int]]) -> float:
    """Paper Eq. (5)-(6) averaged over the items actually administered to someone."""
    counts = Counter(item for s in item_sets for item in s)
    if not counts:
        return 0.0
    n = len(item_sets)
    return sum(count / n for count in counts.values()) / len(counts)


# ------------------------------------------------------------- baseline/context


def benchmark_context(bench: Benchmark) -> dict[str, Any]:
    """Evaluator-owned comparison points for one benchmark slice."""
    subset = random.Random(BASELINE_SEED).sample(range(bench.n_items), min(BASELINE_ITEMS, bench.n_items))
    thetas = eap_fixed_subset(bench, subset)
    items = [list(subset) for _ in bench.models]
    r100 = compute_metrics(bench, thetas, items)
    r100["information_efficiency_score"] = 1.0
    r100["constraint_failed"] = 0.0
    med_theta = statistics.median(bench.targets)
    zero_err = [abs(t - med_theta) for t in bench.targets]
    med_acc = statistics.median(bench.raw_accuracy)
    zero_acc = [abs(x - med_acc) for x in bench.raw_accuracy]
    return {
        "random100": r100,
        "r100_mae": r100["ability_mae"],
        "zero_ability_mae": mean(zero_err),
        "zero_ability_se": standard_error(zero_err),
        "zero_accuracy_mae": mean(zero_acc),
        "zero_accuracy_se": standard_error(zero_acc),
    }


def compute_metrics(bench: Benchmark, thetas: list[float], items: list[list[int]]) -> dict[str, float]:
    sets = [set(x) for x in items]
    abs_err = [abs(t - y) for t, y in zip(thetas, bench.targets)]
    acc_err = [abs(pirt_accuracy(t, s, row, bench) - raw)
               for t, s, row, raw in zip(thetas, sets, bench.responses, bench.raw_accuracy)]
    return {
        "ability_mae": mean(abs_err),
        "ability_se": standard_error(abs_err),
        "avg_items": mean([float(len(x)) for x in items]),
        "accuracy_mae": mean(acc_err),
        "accuracy_se": standard_error(acc_err),
        "test_overlap_rate": overlap_rate(sets),
        "average_item_exposure_rate": exposure_rate(sets),
        "models_evaluated": float(len(thetas)),
    }


# ------------------------------------------------------------------ protocol


class PolicyProcess:
    def __init__(self, command: list[str], workspace: Path):
        try:
            self.proc = subprocess.Popen(command, cwd=workspace, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, bufsize=0)
        except OSError as exc:
            raise ProtocolError(f"cannot start policy: {exc}") from exc
        self.fd = self.proc.stdout.fileno()
        self.buf = bytearray()

    def send(self, obj: dict[str, Any]) -> None:
        data = memoryview((json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8"))
        try:
            while data:
                written = self.proc.stdin.write(data)
                data = data[written:]
        except (BrokenPipeError, OSError) as exc:
            raise ProtocolError("policy closed its input") from exc

    def recv(self) -> dict[str, Any]:
        while True:
            newline = self.buf.find(b"\n")
            if newline >= 0:
                line = bytes(self.buf[:newline])
                del self.buf[: newline + 1]
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except ValueError as exc:
                    raise ProtocolError(f"non-JSON line on policy stdout: {line[:80]!r}") from exc
                if not isinstance(msg, dict):
                    raise ProtocolError("policy message is not a JSON object")
                return msg
            ready, _, _ = select.select([self.fd], [], [], RESPONSE_TIMEOUT_S)
            if not ready:
                raise ProtocolError(f"no policy message within {RESPONSE_TIMEOUT_S:.0f}s")
            chunk = os.read(self.fd, 1 << 16)
            if not chunk:
                raise ProtocolError("policy exited before finishing the session")
            self.buf += chunk

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


def resolve_command(command: Any) -> list[str]:
    if not (isinstance(command, list) and command and all(isinstance(x, str) for x in command)):
        raise ProtocolError("manifest command must be a non-empty list of strings")
    command = list(command)
    if command[0] in ("python", "python3"):
        command[0] = sys.executable
    return command


def run_session(command: list[str], bench: Benchmark, slot: str, budget: float | None,
                workspace: Path) -> dict[str, Any]:
    """Run one policy over every instance of one benchmark; return its transcript."""
    start = time.time()
    thetas: list[float] = []
    items: list[list[int]] = []
    error = None
    policy = None
    try:
        policy = PolicyProcess(resolve_command(command), workspace)
        policy.send({
            "type": "session",
            "benchmark": bench.name,
            "slot": slot,
            "budget": budget,
            "max_items_per_instance": MAX_ITEMS_PER_INSTANCE,
            "num_instances": len(bench.models),
            "num_items": bench.n_items,
        })
        index_of = bench.index_of
        for k, row in enumerate(bench.responses):
            policy.send({"type": "instance", "id": f"q{k:05d}", "index": k})
            asked: list[int] = []
            while True:
                msg = policy.recv()
                kind = msg.get("type")
                if kind == "query":
                    if "items" in msg:
                        requested = msg["items"]
                        if not isinstance(requested, list):
                            raise ProtocolError("query 'items' must be a list")
                    else:
                        requested = [msg.get("item")]
                    idx = []
                    for item in requested:
                        if not isinstance(item, str) or item not in index_of:
                            raise ProtocolError(f"query for unknown item {item!r}")
                        idx.append(index_of[item])
                    if len(asked) + len(idx) > MAX_ITEMS_PER_INSTANCE:
                        raise ProtocolError(f"more than {MAX_ITEMS_PER_INSTANCE} queries for one instance")
                    asked.extend(idx)
                    policy.send({"type": "response", "items": requested, "scores": [row[j] for j in idx]})
                elif kind == "estimate":
                    theta = msg.get("theta")
                    if isinstance(theta, bool) or not isinstance(theta, (int, float)):
                        raise ProtocolError(f"estimate theta is not a number: {theta!r}")
                    theta = float(theta)
                    if not math.isfinite(theta) or abs(theta) > THETA_LIMIT:
                        raise ProtocolError(f"impossible ability estimate {theta!r}")
                    thetas.append(theta)
                    items.append(asked)
                    break
                else:
                    raise ProtocolError(f"unexpected policy message type {kind!r}")
        policy.send({"type": "end"})
    except ProtocolError as exc:
        error = str(exc)
    finally:
        if policy is not None:
            policy.close()
    return {"ok": error is None, "error": error, "theta": thetas, "items": items,
            "seconds": time.time() - start}


# ------------------------------------------------------------------- scoring


def failure_metrics(ctx: dict[str, Any], observed: dict[str, float] | None, avg_items: float,
                    completed: int) -> dict[str, float]:
    """Scores for a failed run: never better than measuring nothing."""

    def worst(key: str, floor: float) -> float:
        if observed is not None and math.isfinite(observed.get(key, float("nan"))):
            return max(floor, observed[key])
        return floor

    fail_mae = max(ctx["zero_ability_mae"], PRECISION_GATE * ctx["r100_mae"])
    ability_mae = worst("ability_mae", fail_mae)
    return {
        "ability_mae": ability_mae,
        "ability_se": worst("ability_se", ctx["zero_ability_se"]),
        "avg_items": avg_items,
        "information_efficiency_score": ability_mae / ctx["r100_mae"] * max(avg_items, BASELINE_ITEMS) / 100.0,
        "accuracy_mae": worst("accuracy_mae", ctx["zero_accuracy_mae"]),
        "accuracy_se": worst("accuracy_se", ctx["zero_accuracy_se"]),
        "test_overlap_rate": 1.0,
        "average_item_exposure_rate": 1.0,
        "models_evaluated": float(completed),
        "constraint_failed": 1.0,
    }


def score_session(bench: Benchmark, ctx: dict[str, Any], session: dict[str, Any] | None,
                  budget: float | None) -> tuple[dict[str, float], list[str]]:
    """Score a transcript; return (metrics, failure reasons)."""
    n = len(bench.models)
    if session is None:
        return failure_metrics(ctx, None, 0.0, 0), ["no manifest claims this slot"]
    total_queries = sum(len(x) for x in session["items"])
    if not session["ok"] or len(session["theta"]) != n:
        reason = session.get("error") or "incomplete session"
        return failure_metrics(ctx, None, total_queries / n, len(session["theta"])), [reason]
    metrics = compute_metrics(bench, session["theta"], session["items"])
    metrics["information_efficiency_score"] = (
        metrics["ability_mae"] * metrics["avg_items"] / (ctx["r100_mae"] * BASELINE_ITEMS)
    )
    reasons = []
    if budget is not None and metrics["avg_items"] > budget + 1e-9:
        reasons.append(f"average items {metrics['avg_items']:.3f} exceeds the slot budget {budget}")
    if metrics["ability_mae"] > PRECISION_GATE * ctx["r100_mae"]:
        reasons.append(
            f"ability MAE {metrics['ability_mae']:.4f} exceeds {PRECISION_GATE:g} x Random100 ({ctx['r100_mae']:.4f})"
        )
    if metrics["accuracy_mae"] > ctx["zero_accuracy_mae"]:
        reasons.append(
            f"accuracy MAE {metrics['accuracy_mae']:.4f} is worse than a constant guess ({ctx['zero_accuracy_mae']:.4f})"
        )
    if reasons:
        return failure_metrics(ctx, metrics, metrics["avg_items"], n), reasons
    metrics["constraint_failed"] = 0.0
    return metrics, []


# --------------------------------------------------------------- manifests


def discover_manifests(targets: list[str], workspace: Path) -> list[Path]:
    found: list[Path] = []
    for target in targets:
        path = Path(target)
        path = path if path.is_absolute() else workspace / path
        if path.is_dir():
            for pattern in ("*/manifest.json", "*/*/manifest.json", "*/*/*/manifest.json"):
                found.extend(sorted(p for p in path.glob(pattern) if p.is_file()))
        elif path.is_file():
            found.append(path)
        else:
            print(f"[eval] manifest target not found: {target}", file=sys.stderr)
    unique: list[Path] = []
    for p in found:
        if p.resolve() not in {q.resolve() for q in unique}:
            unique.append(p)
    return unique


def collect_claims(manifests: list[Path]) -> dict[str, tuple[Path, list[str]]]:
    claims: dict[str, tuple[Path, list[str]]] = {}
    for path in manifests:
        try:
            with path.open() as f:
                manifest = json.load(f)
        except (OSError, ValueError) as exc:
            print(f"[eval] skipping unreadable manifest {path}: {exc}", file=sys.stderr)
            continue
        slots = manifest.get("slots") if isinstance(manifest, dict) else None
        if not isinstance(slots, dict):
            print(f"[eval] skipping {path}: no 'slots' mapping (old artifact-style manifest?)", file=sys.stderr)
            continue
        for slot, spec in slots.items():
            if slot not in SLOTS:
                print(f"[eval] {path}: ignoring claim for '{slot}' (evaluator-owned or unknown slot)", file=sys.stderr)
                continue
            if slot in claims:
                raise SystemExit(
                    f"Slot {slot} is claimed by both {claims[slot][0]} and {path}; keep exactly one manifest per slot."
                )
            command = spec.get("command") if isinstance(spec, dict) else None
            claims[slot] = (path, command)
    return claims


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("targets", nargs="*", default=["checkpoints"],
                        help="manifest files or directories to scan (default: checkpoints)")
    parser.add_argument("--output", type=Path, default=Path("scoring/scores_train.json"))
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--benchmarks", nargs="+", choices=BENCHMARKS, default=list(BENCHMARKS))
    parser.add_argument("--slots", nargs="+", choices=SLOTS, default=list(SLOTS))
    parser.add_argument("--limit", type=int, default=None, help="score only the first N instances per benchmark")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    budgets = load_budgets()
    manifests = discover_manifests(args.targets, workspace)
    claims = collect_claims(manifests)
    print(f"[eval:{SLICE_NAME}] manifests: {[str(p) for p in manifests]}", flush=True)
    print(f"[eval:{SLICE_NAME}] claimed slots: {sorted(claims)}", flush=True)

    scores: dict[str, Any] = {"slice": SLICE_NAME, "experiments": {}}
    diagnostics: dict[str, Any] = {"budgets": budgets, "status": {}}
    for bench_name in args.benchmarks:
        bench = load_benchmark(bench_name, workspace)
        if args.limit:
            bench = bench.subset(args.limit)
        ctx = benchmark_context(bench)
        results: dict[str, Any] = {BASELINE: dict(ctx["random100"])}
        status: dict[str, Any] = {}
        for slot in args.slots:
            budget = budgets[bench_name][slot]
            session = None
            if slot in claims:
                path, command = claims[slot]
                print(f"[eval:{SLICE_NAME}] {bench_name} {slot} <- {path} (budget {budget})", flush=True)
                try:
                    command = resolve_command(command)
                    session = run_session(command, bench, slot, budget, workspace)
                except ProtocolError as exc:
                    session = {"ok": False, "error": str(exc), "theta": [], "items": [], "seconds": 0.0}
            metrics, reasons = score_session(bench, ctx, session, budget)
            results[slot] = metrics
            status[slot] = "ok" if not reasons else "failed: " + "; ".join(reasons)
            print(f"[eval:{SLICE_NAME}] {bench_name} {slot}: ability_mae={metrics['ability_mae']:.4f} "
                  f"avg_items={metrics['avg_items']:.2f} {status[slot]}", flush=True)
        scores["experiments"][f"{bench_name}_reduced_item_ability"] = {"slice": SLICE_NAME, "results": results}
        diagnostics["status"][bench_name] = status
    scores["_diagnostics"] = diagnostics

    output = args.output if args.output.is_absolute() else workspace / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        json.dump(scores, f, indent=2)
    print(f"[eval:{SLICE_NAME}] wrote {output}", flush=True)


if __name__ == "__main__":
    main()
