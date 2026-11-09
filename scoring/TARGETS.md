# Evaluation Targets

Each target is scored per operating-point slot (`ATLAS_0.1`, `ATLAS_0.2`, `ATLAS_0.3`, each with an
evaluator-fixed average item budget) on the held-out models.

## Primary: truthfulqa_reduced_item_ability

Recover whole-bank ability on TruthfulQA within the slot budgets.
- **Metric**: `ability_mae` (lower is better, coefficient 1.0)

## Primary: winogrande_reduced_item_ability

Recover whole-bank ability on WinoGrande within the slot budgets.
- **Metric**: `ability_mae` (lower is better, coefficient 1.0)

## Primary: hellaswag_reduced_item_ability

Recover whole-bank ability on HellaSwag within the slot budgets.
- **Metric**: `ability_mae` (lower is better, coefficient 1.0)

## Secondary: gsm8k_reduced_item_ability

Recover whole-bank ability on GSM8K within the slot budgets (experiment weight 0.125).
- **Metric**: `ability_mae` (lower is better, coefficient 1.0)

## Secondary: arc_reduced_item_ability

Recover whole-bank ability on ARC within the slot budgets (experiment weight 0.125).
- **Metric**: `ability_mae` (lower is better, coefficient 1.0)

## Constraint: item_budget

The average number of item queries per model, counted by the evaluator, must not exceed the slot
budget. A slot over budget is scored as failed.
- **Metric**: `avg_items` (diagnostic; enforced as a hard limit)

## Constraint: measurement_validity

Every held-out model receives a finite ability estimate (|theta| <= 10), `ability_mae` stays within 2x
the evaluator's Random100 baseline, and accuracy reconstruction beats a constant guess. Otherwise the
slot is scored as failed.
- **Metric**: `constraint_failed` (diagnostic; failure is reflected in all scored metrics)

## Constraint: accuracy_preservation

Reduced evaluations should preserve the full-bank raw-accuracy structure.
- **Metric**: `accuracy_mae` (lower is better, coefficient 0.4)

## Constraint: item_concentration

Tests should not concentrate on the same small set of items.
- **Metrics**: `test_overlap_rate` and `average_item_exposure_rate` (lower is better, coefficient 0.1 each)
