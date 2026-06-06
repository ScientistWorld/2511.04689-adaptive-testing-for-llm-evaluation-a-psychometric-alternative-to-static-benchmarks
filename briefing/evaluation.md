# Evaluation

## Metrics

The primary metric is `ability_mae`, the mean absolute error between reduced-test ability estimates and full-bank reference ability estimates. Lower is better.

Efficiency is measured by `avg_items` and `information_efficiency_score`, where the latter combines estimation error and item count relative to a 100-item random baseline. Lower is better.

Accuracy preservation is measured by `accuracy_mae`, the absolute error between reconstructed accuracy from the reduced evaluation and raw full-bank accuracy. Lower is better.

Item-bank reuse constraints are measured by `test_overlap_rate` and `average_item_exposure_rate`. Lower values indicate less redundant testing and less concentration on a small group of items.

## Baselines and Targets

The main baseline is `Random100`, a non-adaptive 100-item subset. A strong solution should match or improve its ability error while using fewer items and maintaining reasonable accuracy reconstruction.

## Evaluation Protocol

Evaluation reads method outputs containing per-model reduced-test ability estimates, selected item sequences, and item counts. It compares those artifacts to the fixed full-bank references and response matrices in `data/`, then writes `scoring/scores.json`.
