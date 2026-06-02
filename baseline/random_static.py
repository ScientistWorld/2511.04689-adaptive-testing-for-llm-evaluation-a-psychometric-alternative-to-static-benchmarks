#!/usr/bin/env python3
"""Random fixed-length subset baseline for ATLAS evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np


def read_item_bank(path: Path) -> dict[str, np.ndarray | list[str]]:
    item_ids, a_vals, b_vals, c_vals, u_vals = [], [], [], [], []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            a = float(row["a1"])
            item_ids.append(row["X"])
            a_vals.append(a)
            b_vals.append(-float(row["d"]) / a)
            c_vals.append(float(row["g"]))
            u_vals.append(float(row.get("u", 1.0)))
    return {
        "item_ids": item_ids,
        "a": np.asarray(a_vals, dtype=np.float64),
        "b": np.asarray(b_vals, dtype=np.float64),
        "c": np.asarray(c_vals, dtype=np.float64),
        "u": np.asarray(u_vals, dtype=np.float64),
    }


def load_responses(path: Path, item_ids: list[str], limit: int | None) -> list[dict[str, object]]:
    rows = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"No header in {path}")
        model_col = reader.fieldnames[0]
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break
            rows.append({"model": row[model_col], "responses": np.fromiter((int(row[item]) for item in item_ids), dtype=np.int8)})
    return rows


def load_reference_thetas(path: Path) -> dict[str, float]:
    with path.open(newline="") as f:
        return {row["Model_Name"]: float(row["Theta_WLE"]) for row in csv.DictReader(f)}


def probability(theta: float | np.ndarray, bank: dict[str, np.ndarray | list[str]]) -> np.ndarray:
    a = bank["a"]
    b = bank["b"]
    c = bank["c"]
    u = bank["u"]
    z = np.clip(np.asarray(a) * (np.asarray(theta)[..., None] - np.asarray(b)), -40.0, 40.0)
    logistic = 1.0 / (1.0 + np.exp(-z))
    return np.asarray(c) + (np.asarray(u) - np.asarray(c)) * logistic


def eap_estimate(
    selected: list[int],
    responses: list[int],
    bank: dict[str, np.ndarray | list[str]],
    grid: np.ndarray,
    prior_log: np.ndarray,
) -> tuple[float, float]:
    probs = probability(grid, bank)[:, selected]
    y = np.asarray(responses, dtype=np.float64)
    log_lik = (y * np.log(np.clip(probs, 1e-9, 1.0)) + (1.0 - y) * np.log(np.clip(1.0 - probs, 1e-9, 1.0))).sum(axis=1)
    log_post = prior_log + log_lik
    log_post -= np.max(log_post)
    weights = np.exp(log_post)
    weights /= weights.sum()
    theta = float(np.sum(weights * grid))
    var = float(np.sum(weights * (grid - theta) ** 2))
    return theta, float(np.sqrt(max(var, 0.0)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", nargs="+", default=["truthfulqa", "winogrande", "hellaswag"])
    parser.add_argument("--test-length", type=int, default=150)
    parser.add_argument("--num-items", type=int, default=100)
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints/random_static"))
    args = parser.parse_args()

    grid = np.linspace(-6.0, 6.0, 241)
    prior_log = -0.5 * grid * grid
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"method": "random_static", "runs": []}

    for benchmark in args.benchmarks:
        bank = read_item_bank(args.data_dir / "calibrated_banks" / benchmark / "irt_item_parameters_combined.csv")
        rows = load_responses(
            args.data_dir / "downloads" / "atlas_response_matrices" / "data" / f"clean_response_matrix_{benchmark}.csv",
            bank["item_ids"],
            args.test_length,
        )
        refs = load_reference_thetas(args.data_dir / "calibrated_banks" / benchmark / "irt_person_scores_WLE_SE.csv")
        bench_dir = args.output_dir / benchmark / "random100"
        bench_dir.mkdir(parents=True, exist_ok=True)
        rng = random.Random(args.seed)
        item_count = min(args.num_items, len(bank["item_ids"]))
        fixed_subset = rng.sample(range(len(bank["item_ids"])), item_count)
        results = []
        selected_rows = []
        for row in rows:
            responses = [int(row["responses"][idx]) for idx in fixed_subset]
            theta, se = eap_estimate(fixed_subset, responses, bank, grid, prior_log)
            model = str(row["model"])
            results.append(
                {
                    "Model_Name": model,
                    "Theta_ATLAS": theta,
                    "Theta_WLE": refs.get(model, ""),
                    "SE": se,
                    "Num_Items": item_count,
                    "Time_Taken_Sec": 0.0,
                }
            )
            for order, idx in enumerate(fixed_subset, 1):
                selected_rows.append(
                    {
                        "model": model,
                        "order": order,
                        "item_id": bank["item_ids"][idx],
                        "score": int(row["responses"][idx]),
                        "theta": "",
                        "se": "",
                    }
                )
        result_file = bench_dir / "irt_person_scores_ATLAS.csv"
        with result_file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Model_Name", "Theta_ATLAS", "Theta_WLE", "SE", "Num_Items", "Time_Taken_Sec"])
            writer.writeheader()
            writer.writerows(results)
        selected_file = bench_dir / "selected_items_all.csv"
        with selected_file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["model", "order", "item_id", "score", "theta", "se"])
            writer.writeheader()
            writer.writerows(selected_rows)
        manifest["runs"].append(
            {
                "benchmark": benchmark,
                "method": "Random100",
                "se_threshold": None,
                "results": str(result_file),
                "selected_items": str(selected_file),
            }
        )
    with (args.output_dir / "manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
