#!/usr/bin/env python3
"""ATLAS adaptive-testing policy (paper Algorithm 1) for the gym's item oracle.

For each instance the policy starts at theta = 0, administers a first item whose
difficulty is near the starting ability, then repeatedly ranks the unadministered
items by 3PL Fisher information at the current estimate and samples the next
item uniformly from the top five (randomesque selection).  After every response
the ability is re-estimated by EAP (N(0, 1) prior, 241-point grid on [-6, 6]);
testing stops once at least ``min_items`` items were given and the posterior
standard error is at most the SE threshold, or at ``max_items``.

The policy talks the evaluator's JSON-lines protocol on stdin/stdout (see
``briefing/evaluation.md``).  The item bank is read from
``data/calibrated_banks/<benchmark>/irt_item_parameters_combined.csv``.
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
    return {
        "item_ids": ids,
        "a": np.asarray(a_vals, dtype=np.float64),
        "b": np.asarray(b_vals, dtype=np.float64),
        "c": np.asarray(c_vals, dtype=np.float64),
        "u": np.asarray(u_vals, dtype=np.float64),
    }


def probability(theta, bank: dict) -> np.ndarray:
    z = np.clip(bank["a"] * (np.asarray(theta)[..., None] - bank["b"]), -40.0, 40.0)
    logistic = 1.0 / (1.0 + np.exp(-z))
    return bank["c"] + (bank["u"] - bank["c"]) * logistic


def fisher_information(theta: float, bank: dict) -> np.ndarray:
    a, b, c, u = bank["a"], bank["b"], bank["c"], bank["u"]
    z = np.clip(a * (theta - b), -40.0, 40.0)
    logistic = 1.0 / (1.0 + np.exp(-z))
    p = c + (u - c) * logistic
    dp = (u - c) * a * logistic * (1.0 - logistic)
    return (dp * dp) / np.clip(p * (1.0 - p), 1e-9, None)


class AtlasCAT:
    """Sequential CAT state shared by the reference policy and its variants."""

    def __init__(self, bank: dict, prior_log: np.ndarray | None = None):
        self.bank = bank
        p_grid = probability(GRID, bank)  # (grid, items)
        self.log_p = np.log(np.clip(p_grid, 1e-9, 1.0))
        self.log_q = np.log(np.clip(1.0 - p_grid, 1e-9, 1.0))
        self.prior_log = -0.5 * GRID * GRID if prior_log is None else prior_log

    @staticmethod
    def posterior_moments(log_post: np.ndarray) -> tuple[float, float]:
        w = np.exp(log_post - np.max(log_post))
        w /= w.sum()
        theta = float(np.sum(w * GRID))
        var = float(np.sum(w * (GRID - theta) ** 2))
        return theta, math.sqrt(max(var, 0.0))

    def first_item(self, rng: random.Random, start_theta: float) -> int:
        b = self.bank["b"]
        candidates = np.flatnonzero(np.abs(b - start_theta) < 0.5)
        if len(candidates) == 0:
            return int(np.argmin(np.abs(b - start_theta)))
        return int(rng.choice(candidates.tolist()))

    def next_item(self, administered: list[int], theta: float, rng: random.Random, top_k: int = 5) -> int:
        info = fisher_information(theta, self.bank)
        if administered:
            info[administered] = -np.inf
        finite = np.flatnonzero(np.isfinite(info))
        if len(finite) == 0:
            raise RuntimeError("No unadministered items remain")
        top_count = min(top_k, len(finite))
        top = np.argpartition(info, -top_count)[-top_count:]
        top = top[np.argsort(info[top])[::-1]]
        return int(rng.choice(top.tolist()))

    def run(self, ask, seed: int, se_threshold: float, min_items: int, max_items: int,
            top_k: int = 5, fixed_length: int | None = None) -> dict:
        """Administer one adaptive test.  ``ask(item_index) -> 0/1``."""
        rng = random.Random(seed)
        log_post = self.prior_log.copy()
        administered: list[int] = []
        responses: list[int] = []
        theta, se = 0.0, float("inf")
        limit = max_items if fixed_length is None else min(fixed_length, max_items)
        for position in range(1, limit + 1):
            if position == 1:
                item = self.first_item(rng, theta)
            else:
                item = self.next_item(administered, theta, rng, top_k)
            y = int(ask(item))
            administered.append(item)
            responses.append(y)
            log_post = log_post + (self.log_p[:, item] if y else self.log_q[:, item])
            theta, se = self.posterior_moments(log_post)
            if fixed_length is None and position >= min_items and se <= se_threshold:
                break
        return {"theta": theta, "se": se, "items": administered, "responses": responses, "log_post": log_post}


class Protocol:
    """Minimal client for the evaluator's JSON-lines protocol."""

    def __init__(self):
        self.stdin = sys.stdin
        self.stdout = sys.stdout

    def recv(self) -> dict | None:
        line = self.stdin.readline()
        if not line:
            return None
        return json.loads(line)

    def send(self, obj: dict) -> None:
        self.stdout.write(json.dumps(obj) + "\n")
        self.stdout.flush()

    def ask_one(self, item_id: str) -> int:
        self.send({"type": "query", "item": item_id})
        reply = self.recv()
        if reply is None or reply.get("type") != "response":
            raise SystemExit("evaluator closed the session")
        return int(reply["scores"][0])


def bank_path(benchmark: str) -> Path:
    return Path("data") / "calibrated_banks" / benchmark / "irt_item_parameters_combined.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--se-threshold", type=float, required=True)
    parser.add_argument("--min-items", type=int, default=30)
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()

    proto = Protocol()
    session = proto.recv()
    if session is None or session.get("type") != "session":
        raise SystemExit("expected a session message")
    bank = read_item_bank(bank_path(session["benchmark"]))
    cat = AtlasCAT(bank)
    item_ids = bank["item_ids"]
    max_items = min(args.max_items, int(session.get("max_items_per_instance") or args.max_items))

    while True:
        msg = proto.recv()
        if msg is None or msg.get("type") == "end":
            break
        if msg.get("type") != "instance":
            continue
        result = cat.run(
            lambda item: proto.ask_one(item_ids[item]),
            seed=args.seed + int(msg["index"]),
            se_threshold=args.se_threshold,
            min_items=args.min_items,
            max_items=max_items,
        )
        proto.send({"type": "estimate", "theta": result["theta"]})


if __name__ == "__main__":
    main()
