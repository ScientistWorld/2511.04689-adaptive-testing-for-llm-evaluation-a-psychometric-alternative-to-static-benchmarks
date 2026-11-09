# Experiments

All five experiments share one protocol (see `briefing/evaluation.md`): a method queries
held-out models' item responses through the evaluator's oracle, within an evaluator-fixed average
item budget for each of three operating-point slots, and reports one ability per model. Each experiment
establishes, for one benchmark, how well a reduced evaluation at those budgets recovers what the full
benchmark would say about a model it has never seen.

## truthfulqa_reduced_item_ability

Whether a few dozen TruthfulQA item queries per model recover each model's whole-bank ability
(primary) and its full-bank raw accuracy, without concentrating every test on the same items. Compared
against a static 100-item random subset computed by the evaluator on the same models.

## winogrande_reduced_item_ability

The same question on WinoGrande, where whole-bank ability is hardest to recover from a short test and
a 100-item random subset is a strong competitor at the tighter budgets.

## hellaswag_reduced_item_ability

The same question on HellaSwag, the largest bank (5,600 items), where a short test must find the
informative items in a large pool.

## gsm8k_reduced_item_ability

The same question on GSM8K (appendix benchmark, half weight). Accuracy reconstruction from a short
test is hardest here.

## arc_reduced_item_ability

The same question on ARC (appendix benchmark, half weight).
