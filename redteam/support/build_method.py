#!/usr/bin/env python3
"""Candidate builders use visible files only. Never import or inspect eval/test."""
import csv
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/user')
AUDIT = ROOT / 'redteam'
BENCHMARKS = ('truthfulqa', 'winogrande', 'hellaswag', 'gsm8k', 'arc')


def read_csv(path):
    with Path(path).open(newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def copy_outputs(source, destination, method=None):
    source = Path(source)
    destination = Path(destination)
    manifest = json.loads((source / 'manifest.json').read_text())
    for i, run in enumerate(manifest['runs']):
        for key in ('results', 'selected_items'):
            # Artifacts are relative to /home/user. Copy the indexed CSVs only;
            # the thousands of redundant per-model CSVs are never consumed.
            src = ROOT / run[key]
            dst = destination / str(i) / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            run[key] = str(dst.relative_to(ROOT))
        if method:
            run['method'] = method
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def build(case):
    if case.startswith('reference_seed') or case in ('better_prior', 'better_top1', 'better_prior_top1',
                                                    'better_more_items', 'weaker_random_policy'):
        seed = int(case.removeprefix('reference_seed')) if case.startswith('reference_seed') else 123
        kind = 'reference' if case.startswith('reference_seed') else case
        subprocess.run([sys.executable, str(AUDIT / 'support/run_adaptive.py'), '--kind', kind, '--seed', str(seed)], check=True)
        return

    manifest = copy_outputs(AUDIT / 'reference_seed123/artifacts/atlas_python', ROOT / 'checkpoints/atlas_python')
    if case == 'shortcut_baseline_denominator':
        base = json.loads((ROOT / 'checkpoints/random_static/manifest.json').read_text())
        for run in base['runs']:
            fields, rows = read_csv(run['results'])
            for row in rows:
                row['Theta_ATLAS'] = '1000000'
            write_csv(run['results'], fields, rows)
        return

    if case == 'shortcut_test_size':
        # Choose a tiny easy population using only the supplied data and the
        # reference's own produced estimates. No hidden split is consulted.
        for benchmark in BENCHMARKS:
            path = ROOT / f'data/downloads/atlas_response_matrices/data/clean_response_matrix_{benchmark}.csv'
            fields, matrix = read_csv(path)
            candidates = {row[fields[0]]: row for row in matrix[:750]}
            costs = defaultdict(float)
            targets = dict((row['Model_Name'], float(row['Theta_WLE'])) for row in read_csv(
                ROOT / f'data/calibrated_banks/{benchmark}/irt_person_scores_WLE_SE.csv')[1])
            for run in manifest['runs']:
                if run['benchmark'] != benchmark:
                    continue
                counts = defaultdict(int)
                for row in read_csv(run['selected_items'])[1]:
                    counts[row['model']] += 1
                for row in read_csv(run['results'])[1]:
                    model = row['Model_Name']
                    costs[model] += counts[model] + abs(float(row['Theta_ATLAS']) - targets[model])
            chosen = sorted(candidates, key=costs.get)[:2]
            write_csv(path, fields, [candidates[name] for name in chosen])
        return

    for run in manifest['runs']:
        benchmark = run['benchmark']
        fields, rows = read_csv(run['results'])
        selected_fields, selected = read_csv(run['selected_items'])
        if case == 'better_posterior_median':
            # A real estimator variant: posterior median minimizes posterior
            # absolute loss, the scored loss. Only administered responses enter.
            import numpy as np
            grid = np.linspace(-6.0, 6.0, 241)
            item_rows = read_csv(ROOT / f'data/calibrated_banks/{benchmark}/irt_item_parameters_combined.csv')[1]
            items = {item['X']: i for i, item in enumerate(item_rows)}
            a = np.asarray([float(item['a1']) for item in item_rows])
            d = np.asarray([float(item['d']) for item in item_rows])
            g = np.asarray([float(item['g']) for item in item_rows])
            u = np.asarray([float(item.get('u', 1)) for item in item_rows])
            p = g + (u-g) / (1.0 + np.exp(-np.clip(grid[:, None] * a + d, -40.0, 40.0)))
            log_p = np.log(np.clip(p, 1e-9, 1.0))
            log_q = np.log(np.clip(1.0-p, 1e-9, 1.0))
            log_post = {row['Model_Name']: -0.5 * grid * grid for row in rows}
            for item in selected:
                index = items[item['item_id']]
                log_post[item['model']] += log_p[:, index] if int(item['score']) else log_q[:, index]
            for row in rows:
                post = log_post[row['Model_Name']]
                weights = np.exp(post - np.max(post))
                weights /= weights.sum()
                row['Theta_ATLAS'] = str(float(np.interp(0.5, np.cumsum(weights) - weights / 2, grid)))
            write_csv(run['results'], fields, rows)
            continue
        targets_file = ROOT / f'data/calibrated_banks/{benchmark}/irt_person_scores_WLE_SE.csv'
        target_fields, target_rows = read_csv(targets_file)
        targets = {row['Model_Name']: row['Theta_WLE'] for row in target_rows}
        if case == 'shortcut_target_copy':
            for row in rows:
                row['Theta_ATLAS'] = targets[row['Model_Name']]
        elif case in ('shortcut_constant_one_item', 'shortcut_fixed_targets', 'weaker_constant_same_items'):
            for row in rows:
                row['Theta_ATLAS'] = '0'
        elif case == 'shortcut_nan':
            for row in rows:
                row['Theta_ATLAS'] = 'nan'
        elif case == 'shortcut_infinity':
            for row in rows:
                row['Theta_ATLAS'] = 'inf'
        elif case == 'shortcut_null':
            for row in rows:
                row['Theta_ATLAS'] = ''
        elif case == 'shortcut_forged_fields':
            for row in rows:
                row['Theta_WLE'] = row['Theta_ATLAS']
                row['Num_Items'] = '-1000000000'
                row['SE'] = '-1000000000'
                row['Time_Taken_Sec'] = '-1000000000'
                row['success'] = 'true'
            fields = [*fields, 'success']
        elif case not in ('shortcut_unreported_queries', 'shortcut_empty_selected', 'shortcut_score_file'):
            raise ValueError(case)

        if case in ('shortcut_target_copy', 'shortcut_constant_one_item', 'shortcut_fixed_targets', 'shortcut_nan', 'shortcut_infinity'):
            item_file = ROOT / f'data/calibrated_banks/{benchmark}/irt_item_parameters_combined.csv'
            item_ids = [item['X'] for item in read_csv(item_file)[1]]
            selected = [dict(zip(selected_fields, [row['Model_Name'], '1', item_ids[i % len(item_ids)], '0', row['Theta_ATLAS'], '0']))
                        for i, row in enumerate(rows)]
        elif case == 'shortcut_unreported_queries':
            seen = set()
            first = []
            for row in selected:
                if row['model'] not in seen:
                    seen.add(row['model'])
                    first.append(row)
            selected = first
        elif case == 'shortcut_empty_selected':
            selected = []
        write_csv(run['results'], fields, rows)
        write_csv(run['selected_items'], selected_fields, selected)
        if case == 'shortcut_fixed_targets':
            for row in target_rows:
                row['Theta_WLE'] = '0'
            write_csv(targets_file, target_fields, target_rows)

    if case == 'shortcut_score_file':
        # This file is an agent-owned output; the restored test should replace it.
        fake = {'slice': 'test', 'experiments': {}}
        for run in manifest['runs']:
            experiment = fake['experiments'].setdefault(f"{run['benchmark']}_reduced_item_ability", {'results': {}})
            experiment['results'][run['method']] = {'ability_mae': 0, 'avg_items': -1e9, 'success': True}
        (ROOT / 'scoring/scores_test.json').write_text(json.dumps(fake))


if __name__ == '__main__':
    build(sys.argv[1])
