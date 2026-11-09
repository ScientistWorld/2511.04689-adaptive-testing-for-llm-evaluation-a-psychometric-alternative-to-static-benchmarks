#!/usr/bin/env python3
"""Build the evaluator-owned held-out data for the hidden test.

This script is the only code that can regenerate the hidden test answers, so
it lives in ``eval/test/``.  It splits every model identity of each benchmark
into a visible half and a held-out half, writes the held-out half (full-bank
responses and whole-bank WLE ability targets) under ``eval/test/data/``, and
rewrites the visible ability-target file so it lists visible identities only.

Inputs
------
``--responses-dir``  directory with the public ``clean_response_matrix_<b>.csv``
                     files (upstream ATLAS commit e2f1975, ``data.zip``).
``--wle-dir``        directory with the full-population
                     ``<b>/irt_person_scores_WLE_SE.csv`` files.  These are the
                     whole-bank WLE estimates shipped by this gym before the
                     split (``git show dfc4fd1:data/calibrated_banks/<b>/...``).
``--bank-dir``       calibrated item banks (``data/calibrated_banks``).

Split rule: identities present in both the response matrix and the WLE file
are sorted by (sha256(name), name); odd positions are held out.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import math
import shutil
from pathlib import Path

BENCHMARKS = ("truthfulqa", "winogrande", "hellaswag", "gsm8k", "arc")


def sort_key(name: str) -> tuple[str, str]:
    return hashlib.sha256(name.encode("utf-8")).hexdigest(), name


def read_bank_ids(path: Path) -> list[str]:
    with path.open(newline="") as f:
        return [row["X"] for row in csv.DictReader(f)]


def read_wle(path: Path) -> tuple[str, list[tuple[str, str, float]]]:
    """Return the raw header line and (name, raw_line, theta) rows."""
    rows = []
    with path.open(newline="") as f:
        lines = f.read().splitlines()
    header = lines[0]
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = next(csv.reader([line]))
        name, theta = fields[0], fields[1]
        try:
            value = float(theta)
        except ValueError:
            continue
        if math.isfinite(value):
            rows.append((name, line, value))
    return header, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--wle-dir", type=Path, required=True)
    parser.add_argument("--bank-dir", type=Path, default=Path("data/calibrated_banks"))
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--visible-wle-dir", type=Path, default=Path("data/calibrated_banks"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for bench in BENCHMARKS:
        bank_path = args.bank_dir / bench / "irt_item_parameters_combined.csv"
        item_ids = read_bank_ids(bank_path)
        header, wle_rows = read_wle(args.wle_dir / bench / "irt_person_scores_WLE_SE.csv")
        wle_by_name: dict[str, tuple[str, float]] = {}
        duplicate_wle = 0
        for name, line, theta in wle_rows:
            if name in wle_by_name:
                duplicate_wle += 1
                continue
            wle_by_name[name] = (line, theta)

        responses: dict[str, str] = {}
        duplicate_resp = 0
        with (args.responses_dir / f"clean_response_matrix_{bench}.csv").open(newline="") as f:
            reader = csv.reader(f)
            columns = next(reader)
            position = {col: i for i, col in enumerate(columns)}
            missing = [item for item in item_ids if item not in position]
            if missing:
                raise SystemExit(f"{bench}: {len(missing)} bank items missing from the response matrix")
            idx = [position[item] for item in item_ids]
            for row in reader:
                name = row[0]
                bits = "".join("1" if row[j] == "1" else "0" for j in idx)
                if any(row[j] not in ("0", "1") for j in idx):
                    raise SystemExit(f"{bench}: non-binary response for {name}")
                if name in responses:
                    duplicate_resp += 1
                    continue
                responses[name] = bits

        eligible = sorted(set(responses) & set(wle_by_name), key=sort_key)
        held_out = {name for k, name in enumerate(eligible) if k % 2 == 1}
        visible = [name for name in eligible if name not in held_out]

        shutil.copyfile(bank_path, args.out_dir / f"{bench}_items.csv")
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as gz:
            gz.write(b"model\ttheta_wle\tresponses\n")
            for name in sorted(held_out):
                theta = wle_by_name[name][1]
                gz.write(f"{name}\t{theta!r}\t{responses[name]}\n".encode("utf-8"))
        (args.out_dir / f"{bench}_heldout.tsv.gz").write_bytes(buffer.getvalue())

        # Visible target file: original row order, one row per visible identity.
        visible_set = set(visible)
        seen: set[str] = set()
        ordered = [header]
        for name, line, _ in wle_rows:
            if name in visible_set and name not in seen:
                ordered.append(line)
                seen.add(name)
        (args.visible_wle_dir / bench).mkdir(parents=True, exist_ok=True)
        (args.visible_wle_dir / bench / "irt_person_scores_WLE_SE.csv").write_text("\n".join(ordered) + "\n")
        print(
            f"{bench}: items={len(item_ids)} eligible={len(eligible)} visible={len(visible)} "
            f"held_out={len(held_out)} dup_wle={duplicate_wle} dup_responses={duplicate_resp} "
            f"resp_only={len(set(responses) - set(wle_by_name))} wle_only={len(set(wle_by_name) - set(responses))}"
        )


if __name__ == "__main__":
    main()
