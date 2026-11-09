# Evaluation

## What is measured

Each benchmark (TruthfulQA, WinoGrande, HellaSwag, GSM8K, ARC) has a calibrated item bank
(`data/calibrated_banks/<benchmark>/irt_item_parameters_combined.csv`) and a population of
language models whose binary responses to every item are known to the evaluator. For every
evaluated model, a method may ask for the model's responses to items of its choice, one or several
at a time, and must then report a single ability estimate. The estimate is compared with the
model's *whole-bank* ability: the WLE ability computed from its responses to the entire bank with
the calibrated 3PL parameters.

A method never reads a response it did not ask for: the evaluator owns the responses and answers
queries through a response oracle, and counts every query itself.

## Operating points (slots) and item budgets

Every benchmark has three operating-point slots, named `ATLAS_0.1`, `ATLAS_0.2` and `ATLAS_0.3`
after the paper's three precision levels. Each slot has an evaluator-fixed **average item budget**
per evaluated model (`eval/train/budgets.json` for the visible split; the hidden test has its own
fixed budgets of the same construction, within about 4% of the visible ones). Budgets are roughly
40-90 items for `ATLAS_0.1` and 30-40 items for `ATLAS_0.2`/`ATLAS_0.3`, always below the 100
items of the static Random100 baseline. The budget is an *average* over all models of the session:
a method may spend more items on some models and fewer on others. No model may receive more than
500 queries.

A method is compared with others at the same budget, so its job is to recover whole-bank ability as
accurately as possible within that cost.

## Scored metrics (per benchmark and slot)

| metric | direction | coefficient | meaning |
|---|---|---:|---|
| `ability_mae` | lower | 1.0 | mean absolute error between reported and whole-bank ability (primary) |
| `accuracy_mae` | lower | 0.4 | mean absolute error between p-IRT reconstructed accuracy and full-bank raw accuracy |
| `test_overlap_rate` | lower | 0.1 | expected share of common items between two models' tests (paper Eq. 7); 1.0 for a fixed form |
| `average_item_exposure_rate` | lower | 0.1 | mean fraction of models that saw each item used at least once (paper Eq. 5-6 over used items); 1.0 for a fixed form |

p-IRT accuracy is computed by the evaluator: observed responses on the queried items plus the
calibrated 3PL probabilities, at the reported ability, for every other bank item, divided by the bank
size.

Diagnostics (reported, coefficient 0): `avg_items` (the budget constraint), `information_efficiency_score`
(paper Eq. 4, ability MAE x items relative to Random100), `ability_se` and `accuracy_se` (standard
errors of the per-model absolute errors), `models_evaluated`, `constraint_failed`.

Experiment weights: TruthfulQA, WinoGrande, HellaSwag 0.25 each; GSM8K, ARC 0.125 each.

## Failure rules

A slot is scored as **failed** when any of the following holds:

- the policy crashes, times out (900 s without a message), writes anything that is not a protocol
  message on stdout, queries an unknown item, exceeds 500 queries for one model, or skips a model;
- a reported ability is not a finite number with |theta| <= 10;
- the average number of queries exceeds the slot budget;
- `ability_mae` is more than 2x the Random100 baseline's `ability_mae` on the same models;
- `accuracy_mae` is worse than predicting the median raw accuracy for every model;
- no manifest claims the slot.

A failed slot is scored as if nothing was measured: `ability_mae` and `accuracy_mae` take at least the
error of a constant guess (median target), and overlap and exposure are set to 1.0.

## Baselines

`Random100` is computed by the evaluator itself on the same models (one fixed 100-item random
subset, EAP ability with a standard-normal prior) and appears as a row in every score file. It is
identical for every method. `baseline/random_static.py` (run with `bash scripts/baseline.sh`) is a
static random subset sized to each slot's budget; it scores far below the reference.

## How a method is plugged in

A method is a **policy program** declared by a manifest found under `checkpoints/` (any
`checkpoints/**/manifest.json`, up to three levels deep):

```json
{"method": "my_method",
 "slots": {"ATLAS_0.1": {"command": ["python", "path/to/policy.py", "--flag", "x"]},
           "ATLAS_0.2": {"command": ["python", "path/to/policy.py", "--flag", "y"]},
           "ATLAS_0.3": {"command": ["python", "path/to/policy.py", "--flag", "z"]}}}
```

Each slot must be claimed by exactly one manifest. Anything the policy needs (fitted parameters,
caches) must be produced beforehand from visible data and saved on disk; evaluation does not train.

For every benchmark and slot the evaluator starts the command with the workspace as the working
directory and exchanges one JSON object per line on the policy's stdin/stdout (stdout is reserved for
protocol messages; log to stderr):

```
evaluator -> {"type": "session", "benchmark": "arc", "slot": "ATLAS_0.1", "budget": 82.1,
              "max_items_per_instance": 500, "num_instances": 2082, "num_items": 841}
evaluator -> {"type": "instance", "id": "q00000", "index": 0}
policy    -> {"type": "query", "item": "X17"}            or {"type": "query", "items": ["X17", "X40"]}
evaluator -> {"type": "response", "items": ["X17"], "scores": [1]}
   ... more queries ...
policy    -> {"type": "estimate", "theta": 0.53}         (ends this model; next instance follows)
evaluator -> {"type": "end"}
```

Item ids are the `X` column of the item-bank file. Instances are anonymous and arrive in a fixed
shuffled order.

## Splits

- **Visible split** (`scripts/evaluate_train.sh`): the model identities whose rows are in
  `data/downloads/atlas_response_matrices/data/clean_response_matrix_<benchmark>.csv` and whose
  whole-bank abilities are in `data/calibrated_banks/<benchmark>/irt_person_scores_WLE_SE.csv`
  (about half of all released models). Writes `scoring/scores_train.json`.
  `--benchmarks`, `--slots` and `--limit N` restrict a development run.
- **Hidden test** (`scripts/evaluate_test.sh`, no arguments): the other half of the released models,
  held only by the evaluator. Same protocol, metrics and failure rules. Writes `scoring/scores_test.json`.

The visible split is the population a method may learn from. Its instances are drawn from that same
population, so a method that uses the visible response matrix as a reference set gets an optimistic
visible-split score unless it holds out the models it is evaluated on.

The hidden test runs the reference method in about four minutes of policy time on one CPU (about
10,600 held-out models x 3 slots).
