#!/usr/bin/env python3
"""Rank with weighted raw directional improvements, using coefficient magnitude.

Keep baseline and each proposed operating point separate to make aggregation
explicit. The proposed aggregate sums the three reference operating points.
"""
import json
import math
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
REFERENCE = json.loads((AUDIT / 'reference_scores_test.json').read_text())
CONFIG = json.loads((AUDIT / 'rank_reference.json').read_text())
METHODS = ['ATLAS_0.1', 'ATLAS_0.2', 'ATLAS_0.3']


def summarize(scores):
    by_method = {}
    for method in [*METHODS, 'Random100']:
        contributions = {}
        averages = {}
        total_weight = 0.0
        for exp_name, ref_exp in REFERENCE['experiments'].items():
            if exp_name not in scores.get('experiments', {}):
                continue
            result = scores['experiments'][exp_name]['results'].get(method)
            if result is None:
                continue
            settings = CONFIG['experiments'][exp_name]
            weight = settings['weight']
            total_weight += weight
            for metric, definition in settings['metrics'].items():
                value = result[metric]
                ref_value = ref_exp['results'][method][metric]
                coefficient = abs(definition['coefficient'])
                direction = 1.0 if definition['higher_is_better'] else -1.0
                if coefficient:
                    delta = weight * coefficient * direction * (value - ref_value)
                    contributions[metric] = contributions.get(metric, 0.0) + delta
                averages[metric] = averages.get(metric, 0.0) + weight * value
        if total_weight:
            by_method[method] = {'rank_delta': sum(contributions.values()),
                                 'rank_contributions': contributions, 'weighted_metrics': averages}
    return {'by_method': by_method,
            'proposed_sum_delta': sum(by_method[m]['rank_delta'] for m in METHODS if m in by_method),
            'all_rows_sum_delta': sum(v['rank_delta'] for v in by_method.values())}


def main():
    report = {'rank_definition': 'sum_experiments weight * sum_metrics abs(coefficient) * directional raw improvement',
              'operating_points': METHODS, 'reference_bounds': [], 'runs': {}}
    for experiment, exp in REFERENCE['experiments'].items():
        for method, metrics in exp['results'].items():
            for metric, definition in CONFIG['experiments'][experiment]['metrics'].items():
                if not abs(definition['coefficient']):
                    continue
                value = metrics[metric]
                if value == 0 and not definition['higher_is_better']:
                    report['reference_bounds'].append([experiment, method, metric, value, 'lower bound'])
                elif metric == 'test_overlap_rate' and value == 1:
                    report['reference_bounds'].append([experiment, method, metric, value, 'upper/worst bound'])
    for directory in sorted(AUDIT.iterdir()):
        if not directory.is_dir() or not (directory / 'status.json').exists():
            continue
        status = json.loads((directory / 'status.json').read_text())
        result = {'status': status}
        if (directory / 'scores_test.json').exists() and status.get('test_exit') == 0:
            result.update(summarize(json.loads((directory / 'scores_test.json').read_text())))
            (directory / 'rank.json').write_text(json.dumps(result, indent=2) + '\n')
        report['runs'][directory.name] = result
    seeds = [report['runs'][f'reference_seed{seed}'] for seed in (123, 124, 125)
             if f'reference_seed{seed}' in report['runs']]
    if len(seeds) == 3 and all('proposed_sum_delta' in seed for seed in seeds):
        values = [seed['proposed_sum_delta'] for seed in seeds]
        report['seed_spread'] = {'proposed_sum_deltas': values, 'range': max(values) - min(values), 'by_method': {}}
        for method in METHODS:
            deltas = [seed['by_method'][method]['rank_delta'] for seed in seeds]
            metrics = {key: [seed['by_method'][method]['weighted_metrics'][key] for seed in seeds]
                       for key in seeds[0]['by_method'][method]['weighted_metrics']}
            report['seed_spread']['by_method'][method] = {'rank_deltas': deltas, 'range': max(deltas) - min(deltas),
                                                        'weighted_metric_values': metrics}
    ref_rerun = AUDIT / 'reference_seed123/scores_test.json'
    if ref_rerun.exists():
        rerun = json.loads(ref_rerun.read_text())
        max_diff = 0.0
        for experiment, exp in REFERENCE['experiments'].items():
            for method, metrics in exp['results'].items():
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        max_diff = max(max_diff, abs(value - rerun['experiments'][experiment]['results'][method][key]))
        report['seed123_max_metric_difference_from_saved_reference'] = max_diff
    (AUDIT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: run.get('proposed_sum_delta', run['status']) for name, run in report['runs'].items()}, indent=2))
    if 'seed_spread' in report:
        print('SEED SPREAD:', json.dumps(report['seed_spread']))


if __name__ == '__main__':
    main()
