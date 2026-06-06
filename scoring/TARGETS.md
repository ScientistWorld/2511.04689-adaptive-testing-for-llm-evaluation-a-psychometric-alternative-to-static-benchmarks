# Evaluation Targets

## Primary: truthfulqa_adaptive_ability

Reduced-item ability estimation on TruthfulQA.
- **Metric**: `ability_mae` (lower is better)

## Primary: winogrande_adaptive_ability

Reduced-item ability estimation on WinoGrande.
- **Metric**: `ability_mae` (lower is better)

## Primary: hellaswag_adaptive_ability

Reduced-item ability estimation on HellaSwag.
- **Metric**: `ability_mae` (lower is better)

## Secondary: gsm8k_adaptive_ability

Reduced-item ability estimation on GSM8K.
- **Metric**: `ability_mae` (lower is better)

## Secondary: arc_adaptive_ability

Reduced-item ability estimation on ARC.
- **Metric**: `ability_mae` (lower is better)

## Constraint: item_efficiency

Methods must reduce administered items rather than simply evaluating the full bank.
- **Metrics**: `avg_items` and `information_efficiency_score` (lower is better)

## Constraint: accuracy_preservation

Reduced evaluations should preserve the global raw-accuracy structure of the full benchmark.
- **Metric**: `accuracy_mae` (lower is better)

## Constraint: item_reuse

Methods should avoid concentrating all tests on the same small set of items.
- **Metrics**: `test_overlap_rate` and `average_item_exposure_rate` (lower is better)
