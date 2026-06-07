#!/usr/bin/env python3
"""Evaluate ATLAS-style outputs without importing method code."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


RANDOM_ABILITY_MAE = {
    "winogrande": 0.167,
    "truthfulqa": 0.103,
    "hellaswag": 0.240,
    "gsm8k": 0.150,
    "arc": 0.183,
}


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def standard_error(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var) / math.sqrt(len(values))


def read_manifest(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def read_item_parameters(path: Path) -> list[dict[str, float | str]]:
    rows = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            a = float(row["a1"])
            rows.append(
                {
                    "item_id": row["X"],
                    "a": a,
                    "b": -float(row["d"]) / a,
                    "c": float(row["g"]),
                    "u": float(row.get("u", 1.0)),
                }
            )
    return rows


def read_ability_targets(path: Path) -> dict[str, float]:
    with path.open(newline="") as f:
        return {row["Model_Name"]: float(row["Theta_WLE"]) for row in csv.DictReader(f) if row["Theta_WLE"]}


def resolve_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def prob(theta: float, item: dict[str, float | str]) -> float:
    a = float(item["a"])
    b = float(item["b"])
    c = float(item["c"])
    u = float(item["u"])
    z = max(-40.0, min(40.0, a * (theta - b)))
    logistic = 1.0 / (1.0 + math.exp(-z))
    return c + (u - c) * logistic


def load_response_rows(path: Path) -> tuple[list[str], dict[str, dict[str, int]]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Missing header in {path}")
        model_col = reader.fieldnames[0]
        item_ids = reader.fieldnames[1:]
        rows = {}
        for row in reader:
            rows[row[model_col]] = {item: int(row[item]) for item in item_ids}
    return item_ids, rows


def read_results(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_selected(path: Path) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = defaultdict(list)
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            selected[row["model"]].append(row["item_id"])
    return selected


def average_item_exposure_rate(item_sets: list[set[str]], total_items: int) -> float:
    if not item_sets or total_items == 0:
        return 0.0
    exposure_counts = Counter(item for items in item_sets for item in items)
    total_models = len(item_sets)
    return sum(count / total_models for count in exposure_counts.values()) / total_items


def overlap_rate(item_sets: list[set[str]]) -> float:
    if len(item_sets) < 2:
        return 0.0
    avg_len = mean([float(len(items)) for items in item_sets])
    if avg_len <= 0:
        return 0.0
    exposure_counts = Counter(item for items in item_sets for item in items)
    model_count = len(item_sets)
    exposure_square_sum = sum((count / model_count) ** 2 for count in exposure_counts.values())
    return (model_count * exposure_square_sum) / (avg_len * (model_count - 1)) - (1.0 / (model_count - 1))


def evaluate_run(run: dict, workspace: Path) -> dict[str, float]:
    benchmark = run["benchmark"]
    result_path = resolve_path(workspace, run["results"])
    selected_path = resolve_path(workspace, run["selected_items"])
    params = read_item_parameters(workspace / "data" / "calibrated_banks" / benchmark / "irt_item_parameters_combined.csv")
    ability_targets = read_ability_targets(
        workspace / "data" / "calibrated_banks" / benchmark / "irt_person_scores_WLE_SE.csv"
    )
    param_by_id = {str(item["item_id"]): item for item in params}
    all_item_ids, response_rows = load_response_rows(
        workspace / "data" / "downloads" / "atlas_response_matrices" / "data" / f"clean_response_matrix_{benchmark}.csv"
    )
    results = read_results(result_path)
    if not results:
        raise ValueError(f"No result rows found for {run['method']} on {benchmark}")

    result_names = [row["Model_Name"] for row in results]
    duplicate_results = sorted(model for model, count in Counter(result_names).items() if count > 1)
    if duplicate_results:
        raise ValueError(f"Duplicate result rows for {run['method']} on {benchmark}: {duplicate_results[:5]}")

    result_models = {row["Model_Name"] for row in results}
    missing_responses = sorted(result_models - response_rows.keys())
    if missing_responses:
        raise ValueError(f"Missing response rows for {run['method']} on {benchmark}: {missing_responses[:5]}")
    missing_targets = sorted(result_models - ability_targets.keys())
    if missing_targets:
        raise ValueError(f"Missing calibrated WLE targets for {benchmark}: {missing_targets[:5]}")

    selected = read_selected(selected_path)
    missing_selected = sorted(result_models - selected.keys())
    if missing_selected:
        raise ValueError(f"Missing selected-item records for {run['method']} on {benchmark}: {missing_selected[:5]}")
    unexpected_selected = sorted(selected.keys() - result_models)
    if unexpected_selected:
        raise ValueError(f"Selected-item records without result rows for {run['method']} on {benchmark}: {unexpected_selected[:5]}")
    invalid_items = sorted({item for items in selected.values() for item in items if item not in param_by_id})
    if invalid_items:
        raise ValueError(f"Selected items not in calibrated bank for {benchmark}: {invalid_items[:5]}")

    abs_theta_errors = [abs(float(row["Theta_ATLAS"]) - ability_targets[row["Model_Name"]]) for row in results]
    avg_items = mean([float(len(selected[row["Model_Name"]])) for row in results])
    ability_mae = mean(abs_theta_errors)
    ability_se = standard_error(abs_theta_errors)
    ies = ability_mae * avg_items / (RANDOM_ABILITY_MAE[benchmark] * 100.0)

    acc_errors = []
    for row in results:
        model = row["Model_Name"]
        theta = float(row["Theta_ATLAS"])
        selected_items = {item for item in selected[model] if item in param_by_id}
        observed_total = sum(response_rows[model][item] for item in selected_items if item in response_rows[model])
        predicted_total = sum(
            prob(theta, param_by_id[item])
            for item in all_item_ids
            if item in param_by_id and item not in selected_items
        )
        expected_acc = (observed_total + predicted_total) / len(all_item_ids)
        raw_acc = mean(list(response_rows[model].values()))
        acc_errors.append(abs(expected_acc - raw_acc))

    item_sets = [set(selected[row["Model_Name"]]) for row in results]
    return {
        "ability_mae": ability_mae,
        "ability_se": ability_se,
        "avg_items": avg_items,
        "information_efficiency_score": ies,
        "accuracy_mae": mean(acc_errors),
        "accuracy_se": standard_error(acc_errors),
        "test_overlap_rate": overlap_rate(item_sets),
        "average_item_exposure_rate": average_item_exposure_rate(item_sets, len(param_by_id)),
        "models_evaluated": float(len(result_models)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, nargs="+", default=[Path("checkpoints/atlas_python/manifest.json")])
    parser.add_argument("--output", type=Path, default=Path("scoring/scores.json"))
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()

    scores = {"experiments": {}}
    for manifest_path in args.manifest:
        manifest = read_manifest(args.workspace / manifest_path)
        for run in manifest["runs"]:
            benchmark = run["benchmark"]
            exp_name = f"{benchmark}_adaptive_ability"
            scores["experiments"].setdefault(exp_name, {"results": {}})
            scores["experiments"][exp_name]["results"][run["method"]] = evaluate_run(run, args.workspace)
    for exp_name, experiment in scores["experiments"].items():
        random_metrics = experiment["results"].get("Random100")
        if not random_metrics:
            continue
        denominator = random_metrics["ability_mae"] * random_metrics["avg_items"]
        if denominator <= 0:
            continue
        for metrics in experiment["results"].values():
            metrics["information_efficiency_score"] = metrics["ability_mae"] * metrics["avg_items"] / denominator
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(scores, f, indent=2)


if __name__ == "__main__":
    main()
