#!/usr/bin/env python3
"""Run ATLAS adaptive testing from calibrated 3PL item banks.

This is a Python reproduction of the paper's adaptive testing loop:
start at theta=0, select items by Fisher information with randomesque top-5
sampling, update ability with EAP after each response, and stop after a
minimum length once the posterior standard error is below the requested
threshold.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

import numpy as np


BENCHMARKS = ("truthfulqa", "winogrande", "hellaswag", "gsm8k", "arc")


def read_item_bank(path: Path) -> dict[str, np.ndarray | list[str]]:
    item_ids: list[str] = []
    a_vals: list[float] = []
    b_vals: list[float] = []
    c_vals: list[float] = []
    u_vals: list[float] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            a = float(row["a1"])
            d = float(row["d"])
            item_ids.append(row["X"])
            a_vals.append(a)
            b_vals.append(-d / a)
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
    rows: list[dict[str, object]] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"No header in {path}")
        model_col = reader.fieldnames[0]
        missing = [item for item in item_ids if item not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path} is missing {len(missing)} calibrated item columns")
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break
            responses = np.fromiter((int(row[item]) for item in item_ids), dtype=np.int8)
            rows.append({"model": row[model_col], "responses": responses})
    return rows


def load_reference_thetas(path: Path) -> dict[str, float]:
    refs: dict[str, float] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            refs[row["Model_Name"]] = float(row["Theta_WLE"])
    return refs


def probability(theta: float | np.ndarray, bank: dict[str, np.ndarray | list[str]]) -> np.ndarray:
    a = bank["a"]
    b = bank["b"]
    c = bank["c"]
    u = bank["u"]
    z = np.clip(np.asarray(a) * (np.asarray(theta)[..., None] - np.asarray(b)), -40.0, 40.0)
    logistic = 1.0 / (1.0 + np.exp(-z))
    return np.asarray(c) + (np.asarray(u) - np.asarray(c)) * logistic


def fisher_information(theta: float, bank: dict[str, np.ndarray | list[str]]) -> np.ndarray:
    p = probability(theta, bank).reshape(-1)
    a = np.asarray(bank["a"])
    b = np.asarray(bank["b"])
    c = np.asarray(bank["c"])
    u = np.asarray(bank["u"])
    z = np.clip(a * (theta - b), -40.0, 40.0)
    logistic = 1.0 / (1.0 + np.exp(-z))
    dp = (u - c) * a * logistic * (1.0 - logistic)
    return (dp * dp) / np.clip(p * (1.0 - p), 1e-9, None)


def eap_estimate(
    selected: list[int],
    responses: list[int],
    bank: dict[str, np.ndarray | list[str]],
    grid: np.ndarray,
    prior_log: np.ndarray,
) -> tuple[float, float]:
    if not selected:
        return 0.0, float("inf")
    probs = probability(grid, bank)[:, selected]
    y = np.asarray(responses, dtype=np.float64)
    log_lik = (y * np.log(np.clip(probs, 1e-9, 1.0)) + (1.0 - y) * np.log(np.clip(1.0 - probs, 1e-9, 1.0))).sum(axis=1)
    log_post = prior_log + log_lik
    log_post -= np.max(log_post)
    weights = np.exp(log_post)
    weights /= weights.sum()
    theta = float(np.sum(weights * grid))
    var = float(np.sum(weights * (grid - theta) ** 2))
    return theta, math.sqrt(max(var, 0.0))


def choose_first_item(bank: dict[str, np.ndarray | list[str]], rng: random.Random, start_theta: float) -> int:
    b = np.asarray(bank["b"])
    candidates = np.flatnonzero(np.abs(b - start_theta) < 0.5)
    if len(candidates) == 0:
        return int(np.argmin(np.abs(b - start_theta)))
    return int(rng.choice(candidates.tolist()))


def choose_next_item(bank: dict[str, np.ndarray | list[str]], administered: set[int], theta: float, rng: random.Random) -> int:
    info = fisher_information(theta, bank)
    if administered:
        info[list(administered)] = -np.inf
    finite = np.flatnonzero(np.isfinite(info))
    if len(finite) == 0:
        raise RuntimeError("No unadministered items remain")
    top_count = min(5, len(finite))
    top = np.argpartition(info, -top_count)[-top_count:]
    top = top[np.argsort(info[top])[::-1]]
    return int(rng.choice(top.tolist()))


def run_one_model(
    model_name: str,
    response_vector: np.ndarray,
    bank: dict[str, np.ndarray | list[str]],
    seed: int,
    se_threshold: float,
    min_items: int,
    max_items: int,
    grid: np.ndarray,
    prior_log: np.ndarray,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rng = random.Random(seed)
    selected: list[int] = []
    selected_set: set[int] = set()
    responses: list[int] = []
    theta = 0.0
    se = float("inf")
    trajectory: list[dict[str, object]] = []
    start = time.perf_counter()
    item_ids = bank["item_ids"]

    for position in range(1, max_items + 1):
        if position == 1:
            item_index = choose_first_item(bank, rng, theta)
        else:
            item_index = choose_next_item(bank, selected_set, theta, rng)
        selected.append(item_index)
        selected_set.add(item_index)
        response = int(response_vector[item_index])
        responses.append(response)
        theta, se = eap_estimate(selected, responses, bank, grid, prior_log)
        trajectory.append(
            {
                "model": model_name,
                "order": position,
                "item_id": item_ids[item_index],
                "score": response,
                "theta": theta,
                "se": se,
            }
        )
        if position >= min_items and se <= se_threshold:
            break

    result = {
        "Model_Name": model_name,
        "Theta_ATLAS": theta,
        "SE": se,
        "Num_Items": len(selected),
        "Time_Taken_Sec": time.perf_counter() - start,
    }
    return result, trajectory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", nargs="+", choices=BENCHMARKS, default=["truthfulqa", "winogrande", "hellaswag"])
    parser.add_argument("--se-thresholds", nargs="+", type=float, default=[0.1, 0.2, 0.3])
    parser.add_argument("--test-length", type=int, default=None)
    parser.add_argument("--min-items", type=int, default=30)
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints/atlas_python"))
    args = parser.parse_args()

    grid = np.linspace(-6.0, 6.0, 241)
    prior_log = -0.5 * grid * grid
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {"method": "ATLAS", "runs": []}
    for benchmark in args.benchmarks:
        print(f"[ATLAS] loading {benchmark}", flush=True)
        bank_path = args.data_dir / "calibrated_banks" / benchmark / "irt_item_parameters_combined.csv"
        response_path = args.data_dir / "downloads" / "atlas_response_matrices" / "data" / f"clean_response_matrix_{benchmark}.csv"
        ref_path = args.data_dir / "calibrated_banks" / benchmark / "irt_person_scores_WLE_SE.csv"
        bank = read_item_bank(bank_path)
        rows = load_responses(response_path, bank["item_ids"], args.test_length)
        refs = load_reference_thetas(ref_path)
        for se_threshold in args.se_thresholds:
            print(f"[ATLAS] starting {benchmark} threshold={se_threshold:g} models={len(rows)}", flush=True)
            bench_dir = args.output_dir / benchmark / f"atlas_{se_threshold:g}"
            selected_dir = bench_dir / "selected_items"
            selected_dir.mkdir(parents=True, exist_ok=True)
            results: list[dict[str, object]] = []
            all_trajectory: list[dict[str, object]] = []
            for row_index, row in enumerate(rows):
                result, trajectory = run_one_model(
                    str(row["model"]),
                    row["responses"],
                    bank,
                    args.seed + row_index,
                    se_threshold,
                    args.min_items,
                    args.max_items,
                    grid,
                    prior_log,
                )
                result["Theta_WLE"] = refs.get(str(row["model"]), "")
                results.append(result)
                all_trajectory.extend(trajectory)
                safe_name = str(row["model"]).replace("/", "_").replace("\\", "_").replace(" ", "_")
                with (selected_dir / f"{safe_name}_items.csv").open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["model", "order", "item_id", "score", "theta", "se"])
                    writer.writeheader()
                    writer.writerows(trajectory)
            result_file = bench_dir / "irt_person_scores_ATLAS.csv"
            with result_file.open("w", newline="") as f:
                fieldnames = ["Model_Name", "Theta_ATLAS", "Theta_WLE", "SE", "Num_Items", "Time_Taken_Sec"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            with (bench_dir / "selected_items_all.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["model", "order", "item_id", "score", "theta", "se"])
                writer.writeheader()
                writer.writerows(all_trajectory)
            manifest["runs"].append(
                {
                    "benchmark": benchmark,
                    "method": f"ATLAS_{se_threshold:g}",
                    "se_threshold": se_threshold,
                    "results": str(result_file),
                    "selected_items": str(bench_dir / "selected_items_all.csv"),
                }
            )
            print(f"[ATLAS] finished {benchmark} threshold={se_threshold:g}: {len(rows)} models", flush=True)
    with (args.output_dir / "manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
