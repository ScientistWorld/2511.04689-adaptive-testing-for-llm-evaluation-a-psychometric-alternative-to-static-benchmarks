#!/usr/bin/env python3
"""Static random-subset baseline policy.

Draws one fixed random subset of items per session (seeded), sized to the
slot's average-item budget (rounded down, at most the per-instance cap), asks
every instance the same subset in one batched query, and reports the EAP
ability (N(0, 1) prior, 241-point grid on [-6, 6]).  With a 100-item subset this
is the evaluator's Random100 comparison row.

Speaks the evaluator's JSON-lines protocol on stdin/stdout.
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

GRID = np.linspace(-6.0, 6.0, 241)


def read_item_bank(path: Path) -> dict:
    ids, a_vals, b_vals, c_vals, u_vals = [], [], [], [], []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            a = float(row["a1"])
            ids.append(row["X"])
            a_vals.append(a)
            b_vals.append(-float(row["d"]) / a)
            c_vals.append(float(row["g"]))
            u_vals.append(float(row.get("u") or 1.0))
    return {"item_ids": ids, "a": np.asarray(a_vals), "b": np.asarray(b_vals),
            "c": np.asarray(c_vals), "u": np.asarray(u_vals)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-items", type=int, default=None,
                        help="subset size (default: the slot budget, rounded down)")
    parser.add_argument("--seed", type=int, default=777)
    args = parser.parse_args()

    def recv():
        line = sys.stdin.readline()
        return json.loads(line) if line else None

    def send(obj):
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    session = recv()
    bank = read_item_bank(Path("data/calibrated_banks") / session["benchmark"] / "irt_item_parameters_combined.csv")
    n_items = len(bank["item_ids"])
    size = args.num_items if args.num_items is not None else int(math.floor(session["budget"]))
    size = max(1, min(size, n_items, int(session["max_items_per_instance"])))
    subset = random.Random(args.seed).sample(range(n_items), size)
    ids = [bank["item_ids"][j] for j in subset]

    z = np.clip(bank["a"][subset][None, :] * (GRID[:, None] - bank["b"][subset][None, :]), -40.0, 40.0)
    p = bank["c"][subset] + (bank["u"][subset] - bank["c"][subset]) / (1.0 + np.exp(-z))
    log_p = np.log(np.clip(p, 1e-9, 1.0))
    log_q = np.log(np.clip(1.0 - p, 1e-9, 1.0))
    prior = -0.5 * GRID * GRID

    while True:
        msg = recv()
        if msg is None or msg.get("type") == "end":
            break
        if msg.get("type") != "instance":
            continue
        send({"type": "query", "items": ids})
        y = np.asarray(recv()["scores"], dtype=np.float64)
        log_post = prior + log_p @ y + log_q @ (1.0 - y)
        w = np.exp(log_post - log_post.max())
        w /= w.sum()
        send({"type": "estimate", "theta": float(w @ GRID)})


if __name__ == "__main__":
    main()
