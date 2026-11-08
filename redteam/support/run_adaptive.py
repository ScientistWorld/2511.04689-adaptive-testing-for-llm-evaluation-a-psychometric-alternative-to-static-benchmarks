#!/usr/bin/env python3
"""Run visible method code; cache its unchanged quadrature probabilities.

The cache changes no estimates, item policies, RNG calls, or stopping rules.
All numerical method work is executed on the submitted compute job.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cache_grid_probabilities(module):
    original = module.probability
    cache = {}

    def probability(theta, bank):
        if isinstance(theta, np.ndarray) and theta.ndim == 1:
            key = (id(bank), theta.tobytes())
            if key not in cache:
                # Keep the bank alive so Python cannot recycle its id.
                cache[key] = (bank, original(theta, bank))
            return cache[key][1]
        return original(theta, bank)

    module.probability = probability


def training_prior(benchmark):
    # This split is fully defined in the visible train evaluator.
    response = Path('data/downloads/atlas_response_matrices/data') / f'clean_response_matrix_{benchmark}.csv'
    with response.open(newline='') as f:
        reader = csv.reader(f)
        next(reader)
        names = []
        for row in reader:
            names.append(row[0])
            if len(names) == 750:
                break
    names.sort(key=lambda name: (hashlib.sha256(name.encode()).hexdigest(), name))
    training_names = set(names[::2])
    targets = Path('data/calibrated_banks') / benchmark / 'irt_person_scores_WLE_SE.csv'
    with targets.open(newline='') as f:
        values = [float(row['Theta_WLE']) for row in csv.DictReader(f) if row['Model_Name'] in training_names]
    return float(np.mean(values)), max(0.1, float(np.std(values, ddof=1)))


def incremental_eap(module):
    """The same discrete posterior, incremented one observed response at a time.

    Used only for the longer and random-policy variants. Reference reruns keep
    the original summation order for exact comparison with the frozen scores.
    """
    arrays = {}
    previous = {'selected': None, 'log_post': None, 'length': 0}

    def estimate(selected, responses, bank, grid, prior_log):
        key = id(bank)
        if key not in arrays:
            p = module.probability(grid, bank)
            arrays[key] = (bank, np.log(np.clip(p, 1e-9, 1.0)),
                           np.log(np.clip(1.0 - p, 1e-9, 1.0)))
        _, log_p, log_q = arrays[key]
        if previous['selected'] is selected and previous['length'] + 1 == len(selected):
            log_post = previous['log_post']
            item = selected[-1]
            log_post += log_p[:, item] if responses[-1] else log_q[:, item]
        else:
            log_post = prior_log.copy()
            for item, response in zip(selected, responses):
                log_post += log_p[:, item] if response else log_q[:, item]
        previous.update(selected=selected, log_post=log_post, length=len(selected))
        weights = np.exp(log_post - np.max(log_post))
        weights /= weights.sum()
        theta = float(np.sum(weights * grid))
        variance = float(np.sum(weights * (grid - theta) ** 2))
        return theta, float(np.sqrt(max(variance, 0.0)))

    module.eap_estimate = estimate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', required=True)
    parser.add_argument('--seed', type=int, default=123)
    args = parser.parse_args()
    module = load_module('visible_atlas', HERE / 'atlas_original.py')
    cache_grid_probabilities(module)
    if args.kind in ('better_more_items', 'weaker_random_policy'):
        incremental_eap(module)
    changes = {}
    if args.kind in ('better_prior', 'better_prior_top1'):
        original_read = module.read_item_bank
        original_run = module.run_one_model

        def read_item_bank(path):
            bank = original_read(path)
            mu, sigma = training_prior(path.parent.name)
            bank['training_prior'] = (mu, sigma)
            changes[path.parent.name] = {'train_prior_mean': mu, 'train_prior_sd': sigma}
            return bank

        def run_one_model(model_name, response_vector, bank, seed, se_threshold, min_items, max_items, grid, prior_log):
            mu, sigma = bank['training_prior']
            return original_run(model_name, response_vector, bank, seed, se_threshold, min_items, max_items,
                                grid, -0.5 * ((grid - mu) / sigma) ** 2)

        module.read_item_bank = read_item_bank
        module.run_one_model = run_one_model
    if args.kind in ('better_top1', 'better_prior_top1'):
        def choose_next_item(bank, administered, theta, rng):
            info = module.fisher_information(theta, bank)
            if administered:
                info[list(administered)] = -np.inf
            return int(np.argmax(info))
        module.choose_next_item = choose_next_item
    if args.kind == 'weaker_random_policy':
        def choose_next_item(bank, administered, theta, rng):
            # Rejection sampling remains uniform over unadministered items
            # without scanning the complete bank at every assessment step.
            while True:
                item = rng.randrange(len(bank['item_ids']))
                if item not in administered:
                    return item
        module.choose_next_item = choose_next_item
    extra = []
    if args.kind == 'better_more_items':
        # A real increase in assessment information, not an oracle estimate.
        original_run = module.run_one_model

        def run_one_model(model_name, response_vector, bank, seed, se_threshold, min_items, max_items, grid, prior_log):
            return original_run(model_name, response_vector, bank, seed, se_threshold / np.sqrt(2.0),
                                60, max_items, grid, prior_log)
        module.run_one_model = run_one_model
    sys.argv = ['atlas_runner.py', '--benchmarks', *module.BENCHMARKS,
                '--se-thresholds', '0.1', '0.2', '0.3', '--test-length', '750',
                '--seed', str(args.seed), '--output-dir', 'checkpoints/atlas_python', *extra]
    module.main()
    Path('checkpoints/method_training_metadata.json').write_text(json.dumps(changes, indent=2))


if __name__ == '__main__':
    main()
