#!/usr/bin/env python3
"""Hardening audit for the reduced-item ability gym.

Runs the reference policy (three seeds), better/weaker variants and shortcuts
through the evaluators' own oracle code (``eval/train/evaluate.py`` and
``eval/test/evaluate.py``, loaded as modules), fixes the per-slot item budgets
from the reference's item usage, scores everything with the evaluators' own
scoring functions and ranks each run against reference seed 123 with the
gym's rank rule.

Stages (all resumable; transcripts are cached under ``transcripts/``):
  smoke      tiny sessions for every policy (fails fast on protocol bugs)
  reference  seeds 123/124/125 on train and test
  budgets    write eval/{train,test}/budgets.json from reference item usage
  fit        train-only calibration for the calibrated-estimate variant
  variants   better/weaker variants and shortcuts on test
  mutations  shortcuts that tamper with visible data files (run serially)
  score      score every transcript and write results/
  verify     compare scoring/scores_{train,test}.json with the audit's seed-123 scores
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import math
import os
import shutil
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRANSCRIPTS = HERE / "transcripts"
RESULTS = HERE / "results"
CALIBRATION = HERE / "transcripts" / "calibration.json"
PY = sys.executable
VP = "redteam/hardening/variant_policy.py"
SE = {"ATLAS_0.1": 0.1, "ATLAS_0.2": 0.2, "ATLAS_0.3": 0.3}
SEEDS = (123, 124, 125)
BUDGET_MARGIN = 1.01
# Runs whose item sequence depends on the session budget; their cached transcripts
# are reused only if they were produced under the current budget.
BUDGET_SENSITIVE = {"better_fixed_length_budget", "better_fixed_top1_empirical_prior",
                    "weaker_random_items_budget", "weaker_static_random_budget"}


def load_module(split: str):
    spec = importlib.util.spec_from_file_location(f"gym_eval_{split}", ROOT / "eval" / split / "evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MODS: dict = {}
_BENCH: dict = {}


def mod(split: str):
    if split not in _MODS:
        _MODS[split] = load_module(split)
    return _MODS[split]


def bench_data(split: str, name: str, limit: int | None = None):
    key = (split, name, limit)
    if key not in _BENCH:
        m = mod(split)
        b = m.load_benchmark(name) if split == "test" else m.load_benchmark(name, ROOT)
        _BENCH[key] = b.subset(limit) if limit else b
    return _BENCH[key]


# ----------------------------------------------------------------- runs


def reference_cmd(seed: int):
    return lambda slot: [PY, "method/atlas_policy.py", "--se-threshold", str(SE[slot]), "--seed", str(seed)]


def vp(*extra: str):
    return lambda slot: [PY, VP, "--se-threshold", str(SE[slot]), *extra]


def variants(replay_dir: Path) -> dict:
    """Same-item variants replay the reference seed-123 item sequences through the oracle."""
    rp = lambda *extra: vp("--replay", str(replay_dir), *extra)  # noqa: E731
    return {
        # better (honest) variants
        "better_empirical_prior_final": rp("--final", "empirical"),
        "better_calibrated_final": rp("--final", "calibrated", "--calibration", str(CALIBRATION)),
        "better_population_final": rp("--final", "population"),
        "better_population_blend": rp("--final", "blend"),
        "better_population_blend_empirical_prior": rp("--final", "blend_empirical"),
        "better_fixed_length_budget": vp("--length", "budget"),
        "better_fixed_top1_empirical_prior": vp("--length", "budget", "--top-k", "1", "--cat-prior", "empirical"),
        # weaker (honest) variants
        "weaker_random_items_budget": vp("--select", "random", "--length", "budget"),
        "weaker_static_random_budget": lambda slot: [PY, "baseline/random_static.py"],
        "weaker_constant_same_items": rp("--final", "zero"),
        # shortcuts
        "shortcut_constant_one_item": vp("--one-item", "--final", "zero"),
        "shortcut_visible_lookup": vp("--one-item", "--lookup-visible"),
        "shortcut_over_budget": lambda slot: [PY, VP, "--se-threshold", repr(SE[slot] / math.sqrt(2)), "--min-items", "60"],
        "shortcut_nan": vp("--one-item", "--final", "nan"),
        "shortcut_inf": vp("--one-item", "--final", "inf"),
        "shortcut_null": vp("--one-item", "--final", "null"),
        "shortcut_forged_fields": rp("--forge-fields"),
    }


REPLAY_DIR = TRANSCRIPTS / "reference_seed123" / "test"
VARIANTS = variants(REPLAY_DIR)
EXPECT_FAIL = {"weaker_constant_same_items", "shortcut_constant_one_item", "shortcut_visible_lookup",
               "shortcut_over_budget", "shortcut_nan", "shortcut_inf", "shortcut_null"}


def transcript_path(run: str, split: str, bench: str, slot: str) -> Path:
    return TRANSCRIPTS / run / split / f"{bench}__{slot}.json.gz"


def is_cached(unit: dict) -> bool:
    out = Path(unit["out"])
    if unit.get("force") or not out.exists():
        return False
    if unit["name"].split("/")[0] in BUDGET_SENSITIVE:
        with gzip.open(out, "rt") as f:
            return json.load(f).get("budget") == unit["budget"]
    return True


def run_unit(unit: dict) -> dict:
    out = Path(unit["out"])
    if is_cached(unit):
        return {"unit": unit["name"], "cached": True}
    m = mod(unit["split"])
    bench = bench_data(unit["split"], unit["bench"], unit.get("limit"))
    session = m.run_session(unit["command"], bench, unit["slot"], unit["budget"], ROOT)
    session["budget"] = unit["budget"]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump(session, f)
    tmp.replace(out)
    return {"unit": unit["name"], "ok": session["ok"], "error": session["error"],
            "seconds": round(session["seconds"], 1)}


def workers() -> int:
    try:
        n = len(os.sched_getaffinity(0))
    except AttributeError:
        n = os.cpu_count() or 1
    return max(1, min(n, 32))


def execute(units: list[dict], label: str) -> list[dict]:
    order = {"hellaswag": 0, "gsm8k": 1, "winogrande": 2, "arc": 3, "truthfulqa": 4}
    units = sorted(units, key=lambda u: (order[u["bench"]], u["slot"]))
    todo = [u for u in units if not is_cached(u)]
    print(f"[audit] {label}: {len(units)} units, {len(todo)} to run, {workers()} workers", flush=True)
    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers()) as pool:
        futures = [pool.submit(run_unit, u) for u in todo]
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            print(f"[audit] {label} {r} t={time.time() - t0:.0f}s", flush=True)
    return results


def units_for(run: str, cmd, split: str, budgets: dict | None, limit=None, benches=None, slots=None,
              force=False) -> list[dict]:
    m = mod(split)
    out = []
    for bench in benches or m.BENCHMARKS:
        for slot in slots or m.SLOTS:
            out.append({
                "name": f"{run}/{split}/{bench}/{slot}", "split": split, "bench": bench, "slot": slot,
                "command": cmd(slot), "budget": None if budgets is None else budgets[bench][slot],
                "limit": limit, "out": str(transcript_path(run, split, bench, slot)), "force": force,
            })
    return out


def read_budgets(split: str = "test") -> dict:
    return json.loads((ROOT / "eval" / split / "budgets.json").read_text())


# ----------------------------------------------------------------- stages


def stage_smoke() -> None:
    smoke_budgets = {b: {s: 40.0 for s in SE} for b in mod("test").BENCHMARKS}
    calib = {b: {s: [0.0, 1.0] for s in SE} for b in smoke_budgets}
    CALIBRATION.parent.mkdir(parents=True, exist_ok=True)
    if not CALIBRATION.exists():
        CALIBRATION.write_text(json.dumps(calib))
    kw = dict(limit=4, benches=["truthfulqa", "hellaswag"], slots=["ATLAS_0.1"], force=True)
    results = execute(units_for("_smoke/reference_seed123", reference_cmd(123), "test", smoke_budgets, **kw)
                      + units_for("_smoke/reference_train", reference_cmd(123), "train", smoke_budgets, limit=4,
                                  benches=["arc"], slots=["ATLAS_0.3"], force=True), "smoke-reference")
    units = []
    for run, cmd in variants(TRANSCRIPTS / "_smoke" / "reference_seed123" / "test").items():
        units += units_for(f"_smoke/{run}", cmd, "test", smoke_budgets, **kw)
    results += execute(units, "smoke-variants")
    bad = []
    for r in results:
        run = r["unit"].split("/")[1]
        expect_ok = run not in {"shortcut_nan", "shortcut_inf", "shortcut_null"}
        if r.get("ok") != expect_ok:
            bad.append(r)
    if bad:
        print(f"[audit] SMOKE FAILURES: {bad}", flush=True)
        raise SystemExit(1)
    if json.loads(CALIBRATION.read_text()) == calib:
        CALIBRATION.unlink()
    print("[audit] smoke OK", flush=True)


def stage_reference() -> None:
    """Seeds 123 (the gym reference), 124 and 125 (seed noise, budget margin) on both splits."""
    units = []
    for seed in SEEDS:
        for split in ("train", "test"):
            units += units_for(f"reference_seed{seed}", reference_cmd(seed), split, None)
    execute(units, "reference")


def load_transcript(run: str, split: str, bench: str, slot: str) -> dict:
    with gzip.open(transcript_path(run, split, bench, slot), "rt") as f:
        return json.load(f)


def stage_budgets() -> None:
    """Per-split slot budgets: 1% above the largest reference (seeds 123-125) average item count."""
    derivation: dict = {}
    for split in ("train", "test"):
        budgets: dict = {}
        for bench in mod(split).BENCHMARKS:
            budgets[bench] = {}
            for slot in SE:
                avgs = []
                for seed in SEEDS:
                    t = load_transcript(f"reference_seed{seed}", split, bench, slot)
                    assert t["ok"], (seed, split, bench, slot, t["error"])
                    avgs.append(sum(len(x) for x in t["items"]) / len(t["items"]))
                budgets[bench][slot] = math.ceil(10 * BUDGET_MARGIN * max(avgs) - 1e-9) / 10
                derivation[f"{split}/{bench}/{slot}"] = {"reference_avg_items_seeds_123_124_125": avgs,
                                                         "budget": budgets[bench][slot]}
        (ROOT / "eval" / split / "budgets.json").write_text(json.dumps(budgets, indent=2) + "\n")
        print(f"[audit] {split} budgets: {json.dumps(budgets)}", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "budget_derivation.json").write_text(json.dumps(
        {"rule": f"per split: ceil(10 * {BUDGET_MARGIN} * max over reference seeds 123/124/125 of avg items) / 10",
         "slots": derivation}, indent=2))


def stage_fit() -> None:
    """Least-squares map from the reference's EAP estimate to the whole-bank target, train split only."""
    calib = {}
    for bench in mod("train").BENCHMARKS:
        b = bench_data("train", bench)
        calib[bench] = {}
        for slot in SE:
            t = load_transcript("reference_seed123", "train", bench, slot)
            x, y = t["theta"], b.targets
            mx, my = statistics.fmean(x), statistics.fmean(y)
            sxx = sum((xi - mx) ** 2 for xi in x)
            sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
            slope = sxy / sxx
            calib[bench][slot] = [my - slope * mx, slope]
    CALIBRATION.write_text(json.dumps(calib, indent=2))
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "calibration_fit_train.json").write_text(json.dumps(calib, indent=2))
    print(f"[audit] calibration: {json.dumps(calib)}", flush=True)


def stage_variants() -> None:
    budgets = read_budgets()
    expensive = {"shortcut_over_budget"}
    for batch in ([r for r in VARIANTS if r not in expensive], sorted(expensive)):
        units = []
        for run in batch:
            units += units_for(run, VARIANTS[run], "test", budgets)
        execute(units, "variants")
    # Train/test consistency check for an honest same-items variant (visible split, replaying train items).
    train_replay = vp("--replay", str(TRANSCRIPTS / "reference_seed123" / "train"), "--final", "empirical")
    execute(units_for("better_empirical_prior_final", train_replay, "train", read_budgets("train")), "variants-train")


def _backup_restore(files: list[Path], backup: Path, restore: bool) -> None:
    if restore:
        if backup.exists():
            for f in files:
                src = backup / f.relative_to(ROOT)
                if src.exists():
                    shutil.copyfile(src, f)
            shutil.rmtree(backup)
        return
    for f in files:
        dst = backup / f.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dst)


def stage_mutations() -> None:
    budgets = read_budgets()
    benches = mod("test").BENCHMARKS
    wle = [ROOT / "data" / "calibrated_banks" / b / "irt_person_scores_WLE_SE.csv" for b in benches]
    mats = [ROOT / "data" / "downloads" / "atlas_response_matrices" / "data" / f"clean_response_matrix_{b}.csv"
            for b in benches]

    def zero_targets():
        for f in wle:
            lines = f.read_text().splitlines()
            out = [lines[0]] + [",".join([ln.rsplit(",", 2)[0], "0", "1"]) for ln in lines[1:]]
            f.write_text("\n".join(out) + "\n")

    def shrink_population():
        for f in mats:
            lines = f.read_text().splitlines()
            f.write_text("\n".join(lines[:3]) + "\n")

    for run, files, mutate in (("shortcut_visible_targets_zeroed", wle, zero_targets),
                               ("shortcut_visible_population_shrunk", mats, shrink_population)):
        backup = HERE / f"backup_{run}"
        _backup_restore(files, backup, restore=True)  # recover from an interrupted earlier attempt
        units = units_for(run, vp("--replay", str(REPLAY_DIR)), "test", budgets)
        if all(Path(u["out"]).exists() for u in units):
            continue
        _backup_restore(files, backup, restore=False)
        try:
            mutate()
            execute(units, run)
        finally:
            _backup_restore(files, backup, restore=True)


# ------------------------------------------------------------------ scoring


def runs_on_disk(split: str) -> list[str]:
    return sorted(p.name for p in TRANSCRIPTS.iterdir() if p.is_dir() and not p.name.startswith("_")
                  and (p / split).is_dir())


def score_run(run: str, split: str, contexts: dict) -> dict:
    budgets = read_budgets(split)
    m = mod(split)
    scores = {"slice": split, "experiments": {}, "_status": {}}
    for bench in m.BENCHMARKS:
        b = bench_data(split, bench)
        ctx = contexts[(split, bench)]
        results = {m.BASELINE: dict(ctx["random100"])}
        status = {}
        for slot in m.SLOTS:
            path = transcript_path(run, split, bench, slot)
            session = load_transcript(run, split, bench, slot) if path.exists() else None
            metrics, reasons = m.score_session(b, ctx, session, budgets[bench][slot])
            results[slot] = metrics
            status[slot] = "ok" if not reasons else "failed: " + "; ".join(reasons)
        scores["experiments"][f"{bench}_reduced_item_ability"] = {"slice": split, "results": results}
        scores["_status"][bench] = status
    return scores


def rank_delta(scores: dict, ref: dict, reference: dict, spreads: dict | None = None,
               breakdown: dict | None = None) -> float:
    """Sum over experiments/rows/metrics of weight * |coefficient| * directional improvement
    (optionally divided by the metric's spread across attempts)."""
    total = 0.0
    for exp, exp_def in reference["experiments"].items():
        for row, ref_metrics in ref["experiments"][exp]["results"].items():
            for metric, mdef in exp_def["metrics"].items():
                coef = abs(mdef["coefficient"])
                if coef == 0:
                    continue
                sign = 1.0 if mdef["higher_is_better"] else -1.0
                imp = sign * (scores["experiments"][exp]["results"][row][metric] - ref_metrics[metric])
                if spreads is not None:
                    s = spreads.get((exp, row, metric), 0.0)
                    if s <= 0:
                        continue
                    imp /= s
                total += exp_def["weight"] * coef * imp
                if breakdown is not None:
                    breakdown[metric] = breakdown.get(metric, 0.0) + exp_def["weight"] * coef * imp
    return total


def paired_mae_difference(run: str, ref_run: str, weights: dict) -> dict:
    """Experiment-weighted mean over slots of per-instance |err_run| - |err_ref| on test, with SE."""
    out = {}
    agg_mean, agg_var = 0.0, 0.0
    for bench in mod("test").BENCHMARKS:
        b = bench_data("test", bench)
        for slot in SE:
            t, r = load_transcript(run, "test", bench, slot), load_transcript(ref_run, "test", bench, slot)
            if not (t["ok"] and r["ok"]) or len(t["theta"]) != len(b.targets):
                out[f"{bench}/{slot}"] = None
                continue
            d = [abs(x - y) - abs(z - y) for x, z, y in zip(t["theta"], r["theta"], b.targets)]
            mu, se = statistics.fmean(d), statistics.stdev(d) / math.sqrt(len(d))
            out[f"{bench}/{slot}"] = [mu, se]
            w = weights[f"{bench}_reduced_item_ability"] / 3.0
            agg_mean += w * mu
            agg_var += (w * se) ** 2
    out["weighted"] = [agg_mean, math.sqrt(agg_var)]
    return out


def headline(scores: dict, weights: dict) -> dict:
    keys = ("ability_mae", "accuracy_mae", "avg_items", "test_overlap_rate", "average_item_exposure_rate")
    out = {}
    for slot in SE:
        out[slot] = {k: sum(weights[e] * scores["experiments"][e]["results"][slot][k] for e in weights) for k in keys}
        out[slot]["failed_cells"] = sum(scores["experiments"][e]["results"][slot]["constraint_failed"] for e in weights)
    return out


def stage_score() -> None:
    budgets = {split: read_budgets(split) for split in ("train", "test")}
    reference = json.loads((ROOT / "scoring" / "reference.json").read_text())
    weights = {e: d["weight"] for e, d in reference["experiments"].items()}
    contexts = {}
    for split in ("train", "test"):
        for bench in mod(split).BENCHMARKS:
            contexts[(split, bench)] = mod(split).benchmark_context(bench_data(split, bench))
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_scores = {}
    for split in ("train", "test"):
        for run in runs_on_disk(split):
            s = score_run(run, split, contexts)
            all_scores[(run, split)] = s
            (RESULTS / f"{run}__{split}.json").write_text(json.dumps(s, indent=2))
    ref = all_scores[("reference_seed123", "test")]
    test_runs = [r for (r, sp) in all_scores if sp == "test"]

    def spreads_over(runs):
        sp = {}
        for exp, exp_def in reference["experiments"].items():
            for row in ref["experiments"][exp]["results"]:
                for metric in exp_def["metrics"]:
                    vals = [all_scores[(r, "test")]["experiments"][exp]["results"][row][metric] for r in runs]
                    sp[(exp, row, metric)] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        return sp

    def failed(run):
        s = all_scores[(run, "test")]
        return any(s["experiments"][e]["results"][slot]["constraint_failed"] for e in weights for slot in SE)

    spread_all = spreads_over(test_runs)
    spread_ok = spreads_over([r for r in test_runs if not failed(r)])
    summary = {"budgets": budgets, "runs": {}}
    for run in test_runs:
        s = all_scores[(run, "test")]
        b_raw, b_norm = {}, {}
        entry = {
            "rank_delta_raw": rank_delta(s, ref, reference, breakdown=b_raw),
            "rank_delta_normalized_all_attempts": rank_delta(s, ref, reference, spread_all),
            "rank_delta_normalized_passing_attempts": rank_delta(s, ref, reference, spread_ok, breakdown=b_norm),
            "breakdown_raw": b_raw,
            "breakdown_normalized_passing_attempts": b_norm,
            "headline_weighted": headline(s, weights),
            "status": s["_status"],
            "any_failed": failed(run),
        }
        try:
            entry["paired_ability_error_difference_vs_seed123"] = paired_mae_difference(run, "reference_seed123", weights)
        except FileNotFoundError:
            pass
        summary["runs"][run] = entry
    for run in runs_on_disk("train"):
        summary["runs"].setdefault(run, {})["train_headline_weighted"] = headline(all_scores[(run, "train")], weights)
    summary["seed_noise"] = {
        key: max(abs(summary["runs"][f"reference_seed{s}"][key]) for s in SEEDS)
        for key in ("rank_delta_raw", "rank_delta_normalized_all_attempts", "rank_delta_normalized_passing_attempts")
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = ["| run | rank delta (raw) | normalized, all attempts | normalized, passing attempts | ability MAE 0.1/0.2/0.3 | items 0.1/0.2/0.3 | failed cells | paired dMAE (SE) |",
             "|---|---:|---:|---:|---|---|---:|---|"]
    for run, e in sorted(summary["runs"].items(), key=lambda kv: -kv[1].get("rank_delta_raw", -1e9)):
        if "headline_weighted" not in e:
            continue
        h = e["headline_weighted"]
        mae = "/".join(f"{h[s]['ability_mae']:.4f}" for s in SE)
        items = "/".join(f"{h[s]['avg_items']:.1f}" for s in SE)
        nfail = int(sum(h[s]["failed_cells"] for s in SE))
        pw = e.get("paired_ability_error_difference_vs_seed123", {}).get("weighted")
        pw_s = f"{pw[0]:+.4f} ({pw[1]:.4f})" if pw else "n/a"
        lines.append(f"| {run} | {e['rank_delta_raw']:+.5f} | {e['rank_delta_normalized_all_attempts']:+.3f} | "
                     f"{e['rank_delta_normalized_passing_attempts']:+.3f} | "
                     f"{mae} | {items} | {nfail} | {pw_s} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


def stage_verify() -> None:
    ok = True
    for split in ("train", "test"):
        live = json.loads((ROOT / "scoring" / f"scores_{split}.json").read_text())
        audit = json.loads((RESULTS / f"reference_seed123__{split}.json").read_text())
        worst = 0.0
        for exp, d in audit["experiments"].items():
            for row, metrics in d["results"].items():
                for k, v in metrics.items():
                    worst = max(worst, abs(live["experiments"][exp]["results"][row][k] - v))
        print(f"[audit] verify {split}: max |live - audit seed123| = {worst:.3e}", flush=True)
        ok = ok and worst < 1e-9
    (RESULTS / "verify.json").write_text(json.dumps({"live_equals_audit_seed123": ok}))
    if not ok:
        raise SystemExit("live evaluator scores differ from the audit's seed-123 scores")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stages", nargs="+",
                        choices=["smoke", "reference", "budgets", "fit", "variants", "mutations", "score", "verify"])
    args = parser.parse_args()
    os.chdir(ROOT)
    for stage in args.stages:
        t0 = time.time()
        print(f"[audit] === stage {stage} ===", flush=True)
        globals()[f"stage_{stage}"]()
        print(f"[audit] === stage {stage} done in {time.time() - t0:.0f}s ===", flush=True)


if __name__ == "__main__":
    main()
