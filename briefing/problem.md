# Problem Definition

## Research Question

How accurately can an evaluator recover a language model's whole-benchmark ability from a small,
fixed budget of item queries, when the items come from a calibrated item bank and the evaluator may
choose which items to ask each model?

## Why It Matters

Full benchmark evaluation is expensive and exposes entire item banks. A reduced evaluation is useful
only if it spends few item queries per model while still placing every model close to where the full
benchmark would place it, including models with similar raw accuracies, and without concentrating all
tests on the same small set of items.

## Setting

For five benchmarks (TruthfulQA, WinoGrande, HellaSwag, GSM8K, ARC) the gym provides calibrated
3PL item banks and, for about half of the released models (the visible population), complete binary
response matrices and whole-bank ability estimates. For any evaluated model, a method may query the
model's responses to items of its choice, up to an average item budget per model, and must report one
ability estimate per model. Three budgets per benchmark define three operating points.

## Success Criteria

A successful method, at each budget:

- reports abilities close to the whole-bank abilities of models it has never seen (primary);
- lets the full-bank raw accuracy be reconstructed from its queried responses and reported ability;
- spreads its queries over the bank instead of giving every model the same items;
- stays within the item budget and produces a valid estimate for every model.
