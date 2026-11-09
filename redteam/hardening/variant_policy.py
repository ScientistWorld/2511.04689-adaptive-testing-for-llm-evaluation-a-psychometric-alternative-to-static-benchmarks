#!/usr/bin/env python3
"""Configurable policy for the hardening audit (better/weaker variants, shortcuts).

Reuses the reference CAT from ``method/atlas_policy.py`` so that variants which
keep the reference's item sequence administer exactly the same items.  Only
visible data (``data/``) is read.

Knobs
  --length se|budget   SE stopping (reference rule) or a fixed length paced so
                       the session average equals the slot budget
  --select fisher|random
  --top-k K            randomesque pool size for Fisher selection (reference 5)
  --cat-prior normal|empirical   prior used while testing
  --final eap|empirical|calibrated|population|blend|zero|nan|inf|null
  --one-item           administer a single item, then estimate
  --lookup-visible     try to read the instance's target/responses from data/
  --forge-fields       add self-reported fields to the estimate message
  --replay DIR         re-administer the reference run's item sequence for each
                       instance (one batched query through the oracle) instead of
                       re-running the selection loop; responses come from the oracle
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "method"))
from atlas_policy import GRID, AtlasCAT, Protocol, bank_path, read_item_bank  # noqa: E402


def visible_targets(benchmark: str) -> dict[str, float]:
    path = Path("data/calibrated_banks") / benchmark / "irt_person_scores_WLE_SE.csv"
    with path.open(newline="") as f:
        return {row["Model_Name"]: float(row["Theta_WLE"]) for row in csv.DictReader(f)}


def empirical_prior_log(benchmark: str) -> np.ndarray:
    thetas = np.asarray(list(visible_targets(benchmark).values()))
    bw = 1.06 * thetas.std() * len(thetas) ** (-0.2)
    dens = np.exp(-0.5 * ((GRID[:, None] - thetas[None, :]) / bw) ** 2).sum(axis=1)
    dens /= dens.sum()
    return np.log(np.clip(dens, 1e-300, None))


def visible_population(benchmark: str, item_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    targets = visible_targets(benchmark)
    path = Path("data/downloads/atlas_response_matrices/data") / f"clean_response_matrix_{benchmark}.csv"
    rows, thetas = [], []
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        pos = {c: k for k, c in enumerate(header)}
        idx = [pos[i] for i in item_ids]
        for row in reader:
            if row[0] in targets:
                rows.append([row[j] == "1" for j in idx])
                thetas.append(targets[row[0]])
    return np.asarray(rows, dtype=bool), np.asarray(thetas)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--se-threshold", type=float, required=True)
    p.add_argument("--min-items", type=int, default=30)
    p.add_argument("--max-items", type=int, default=500)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--length", choices=["se", "budget"], default="se")
    p.add_argument("--select", choices=["fisher", "random"], default="fisher")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--cat-prior", choices=["normal", "empirical"], default="normal")
    p.add_argument("--final", default="eap",
                   choices=["eap", "empirical", "calibrated", "population", "blend", "zero", "nan", "inf", "null"])
    p.add_argument("--calibration", type=Path)
    p.add_argument("--population-eps", type=float, default=0.15)
    p.add_argument("--one-item", action="store_true")
    p.add_argument("--lookup-visible", action="store_true")
    p.add_argument("--forge-fields", action="store_true")
    p.add_argument("--replay", type=Path)
    args = p.parse_args()

    proto = Protocol()
    session = proto.recv()
    bench_name, slot = session["benchmark"], session["slot"]
    bank = read_item_bank(bank_path(bench_name))
    ids = bank["item_ids"]
    n_items = len(ids)
    prior_log = empirical_prior_log(bench_name) if args.cat_prior == "empirical" else None
    cat = AtlasCAT(bank, prior_log)
    emp_log = empirical_prior_log(bench_name) if args.final == "empirical" else None
    calib = None
    if args.final == "calibrated":
        calib = json.loads(args.calibration.read_text())[bench_name][slot]
    pop_resp = pop_theta = None
    if args.final in ("population", "blend"):
        pop_resp, pop_theta = visible_population(bench_name, ids)
    lookup_targets = visible_targets(bench_name) if args.lookup_visible else {}
    budget = session.get("budget")
    n_inst = int(session["num_instances"])
    max_items = min(args.max_items, int(session["max_items_per_instance"]))
    replay = None
    if args.replay is not None:
        import gzip
        with gzip.open(args.replay / f"{bench_name}__{slot}.json.gz", "rt") as f:
            replay = json.load(f)["items"]

    def paced_length(k: int) -> int:
        total = budget * n_inst
        return int(math.floor(total * (k + 1) / n_inst + 1e-9) - math.floor(total * k / n_inst + 1e-9))

    while True:
        msg = proto.recv()
        if msg is None or msg.get("type") == "end":
            break
        if msg.get("type") != "instance":
            continue
        k = int(msg["index"])
        seed = args.seed + k
        ask = lambda item: proto.ask_one(ids[item])  # noqa: E731

        if args.lookup_visible:
            # Shortcut attempt: copy a target / read responses for this instance from visible files.
            found = lookup_targets.get(msg.get("id"))
            if found is not None:
                proto.send({"type": "estimate", "theta": found})
                continue
        if replay is not None:
            items = replay[k]
            proto.send({"type": "query", "items": [ids[j] for j in items]})
            reply = proto.recv()
            ys = [int(v) for v in reply["scores"]]
            log_post = cat.prior_log + sum(cat.log_p[:, j] if y else cat.log_q[:, j] for j, y in zip(items, ys))
            theta, se = cat.posterior_moments(log_post)
            res = {"theta": theta, "se": se, "items": items, "responses": ys, "log_post": log_post}
        elif args.one_item:
            res = cat.run(ask, seed, args.se_threshold, 1, 1, fixed_length=1)
        elif args.select == "random":
            length = paced_length(k) if args.length == "budget" else max_items
            rng = random.Random(seed)
            items = rng.sample(range(n_items), min(length, n_items))
            log_post = cat.prior_log.copy()
            ys = []
            for j in items:
                y = ask(j)
                ys.append(y)
                log_post = log_post + (cat.log_p[:, j] if y else cat.log_q[:, j])
            theta, se = cat.posterior_moments(log_post)
            res = {"theta": theta, "se": se, "items": items, "responses": ys, "log_post": log_post}
        else:
            fixed = paced_length(k) if args.length == "budget" else None
            res = cat.run(ask, seed, args.se_threshold, args.min_items, max_items,
                          top_k=args.top_k, fixed_length=fixed)

        theta = res["theta"]
        if args.final == "empirical":
            log_lik = res["log_post"] - cat.prior_log
            theta, _ = cat.posterior_moments(log_lik + emp_log)
        elif args.final == "calibrated":
            theta = calib[0] + calib[1] * theta
        elif args.final in ("population", "blend"):
            items = res["items"]
            y = np.asarray([1 if r else 0 for r in res["responses"]], dtype=bool)
            match = (pop_resp[:, items] == y[None, :]).sum(axis=1)
            eps = args.population_eps
            logw = match * math.log(1 - eps) + (len(items) - match) * math.log(eps)
            w = np.exp(logw - logw.max())
            pop = float((w * pop_theta).sum() / w.sum())
            theta = pop if args.final == "population" else 0.5 * pop + 0.5 * theta
        elif args.final == "zero":
            theta = 0.0
        elif args.final == "nan":
            theta = float("nan")
        elif args.final == "inf":
            theta = float("inf")
        elif args.final == "null":
            theta = None
        message = {"type": "estimate", "theta": theta}
        if args.forge_fields:
            message.update({"se": -1.0, "num_items": 1, "ability_mae": 0.0, "Theta_WLE": theta, "success": True})
        proto.send(message)


if __name__ == "__main__":
    main()
