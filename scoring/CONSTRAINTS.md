# Constraints

Methods are evaluated only through the evaluator's response oracle: a method sees a held-out model's
response to an item only by querying it, and every query counts toward the slot's average item budget.
Methods may learn from anything visible in `data/` (item banks, the visible response matrices and
whole-bank abilities), but must not read evaluator-owned files under `eval/test/`, the upstream release
of the full response matrices or person scores, or earlier git revisions of `data/` to obtain held-out
models' responses or abilities.

The item budgets, the 500-query cap per model, the held-out population, the whole-bank targets, the
item-bank copy used for scoring and the Random100 baseline are fixed by `eval/`. A method must not
change them, and must produce a valid estimate for every model in every slot it claims.

Item reuse is measured with the configured aggregate metrics: exposure-probability test overlap and
average exposure over the items used. Do not substitute pairwise Jaccard overlap or a worst-case
maximum exposure metric unless either is added as a separate, clearly named diagnostic.

Evaluation does not train: anything a policy needs must be computed beforehand from visible data and
saved under `checkpoints/`.
