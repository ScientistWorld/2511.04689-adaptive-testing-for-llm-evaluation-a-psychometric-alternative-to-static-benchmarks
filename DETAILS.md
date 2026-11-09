# Overview

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated
benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent
ability and repeatedly chooses high-information items targeted to that estimate.

This workspace packages a reproduction on the paper's released calibrated item banks and response
matrices for TruthfulQA, WinoGrande, HellaSwag, GSM8K and ARC. Methods are item-selection policies
queried through an evaluator-owned response oracle; at three evaluator-fixed item budgets per
benchmark they are scored on how closely their ability estimates match whole-bank abilities of
held-out models, how well raw accuracy can be reconstructed, and how concentrated their item use is.
The reproduced ATLAS recovers whole-bank ability with fewer than 100 items far better than a static
100-item random subset.

---

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

---

# Paper's Method

## Key Contribution

ATLAS reframes LLM benchmark evaluation as computerized adaptive testing over calibrated IRT item banks.

## Approach

The paper first calibrates benchmark items with a 3PL IRT model, estimating discrimination, difficulty, and guessing parameters. Large banks are calibrated in partitions and linked onto a shared scale with common-person mean-sigma linking, then full-bank model abilities are estimated with WLE.

At evaluation time, ATLAS starts each model at ability `theta = 0`. The first item is selected near that starting difficulty. Subsequent items are ranked by Fisher information at the current ability estimate, and the administered item is sampled from the top five candidates. After each binary response, ability is updated with EAP. Testing stops after at least 30 items once the estimated standard error is below the configured threshold (0.1, 0.2 or 0.3), or at 500 items.

## In this workspace

`method/atlas_policy.py` implements this loop as a policy for the evaluator's query protocol (N(0,1) prior, 241-point grid on [-6, 6], seed 123 + instance index for the randomesque draw). `scripts/method.sh` writes `checkpoints/atlas_python/manifest.json`, mapping slots `ATLAS_0.1/0.2/0.3` to SE thresholds 0.1/0.2/0.3. The slot budgets were set 1% above this policy's average item usage (seeds 123-125), so the reference stops by its own SE rule within budget.

## Main Claims

The primary claim is that adaptive, information-guided item selection recovers full-bank ability estimates with far fewer items than static benchmark subsets.

Secondary claims are that the latent ability score preserves raw-accuracy structure, differentiates models with similar or identical accuracy, and avoids overexposing the same items.

---

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

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

### [2026-06-06 21:35] - method_runs
- Job `5601fe49-efc` ran the implemented ATLAS adaptive testing loop and Random100 baseline on TruthfulQA, WinoGrande, and HellaSwag for 180 models.
- `python validate.py --compare` passed, and `scoring/scores.json` includes benefit and constraint metrics for the completed experiments.
- Expanded `scripts/method.sh` and `scripts/baseline.sh` so the next run covers GSM8K and ARC in addition to the three primary benchmarks.

### [2026-06-06 21:45] - core_claim
- Job `8d1fe4ff-0fd` ran ATLAS and Random100 on all five reference experiments for 180 models.
- The reproduced scores show ATLAS reducing administered items and information-efficiency score across the benchmark suite while retaining comparable or improved ability error relative to Random100.
- `scoring/scores.json`, `scoring/TARGETS.md`, and `scoring/EXPERIMENTS.md` now cover the same five experiments.

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:45] - method_runs
- Implemented and ran the ATLAS adaptive testing loop from calibrated 3PL item banks.
- Verified that method artifacts are produced and can be evaluated without importing from `method/`.

### [2026-06-06 21:46] - core_claim
- Reproduced the core ATLAS claim on reduced-scale benchmark runs: adaptive testing recovers full-bank ability with far fewer administered items than a static Random100 baseline.
- `python validate.py --compare` passed with reproduced scores in `scoring/scores.json`.

### [2026-06-06 22:00] - core_claim_plus
- Extended the same procedure to all five paper benchmarks: TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Results preserve the paper's accuracy-efficiency tradeoff across additional benchmark settings.

### [2026-06-06 22:20] - core_claim_plus
- Continuing audit verified that `method/atlas_runner.py` implements the paper's ATLAS loop rather than a surrogate: 3PL probabilities, Fisher-information item ranking, randomesque top-5 selection, EAP ability updates, and SE-based stopping.
- Fixed the evaluator's exposure metric to match the paper's average item exposure definition, regenerated `scoring/scores.json`, and reran `python validate.py --compare` successfully.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 6 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 6 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 6 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-07 00:27] - core_claim_plus
- Final verification confirmed the workspace structure, method/problem separation, download URL, train/test artifacts, and scoring files are suitable for gym use.
- Updated `reference.json` metric descriptions to match the corrected p-IRT accuracy and exposure-probability overlap formulas.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass after the verification update.

### [2026-06-07 00:23] - core_claim_plus
- Corrected the evaluator's accuracy reconstruction to the paper's p-IRT estimator: observed selected-item responses plus IRT-predicted probabilities for unobserved items.
- Corrected `test_overlap_rate` to the paper's exposure-probability formula and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from the completed 750-model artifacts.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass with the corrected metrics.

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 13m | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-07 00:40] - core_claim_plus
- Final verification confirmed the workspace is ready for gym use at `core_claim_plus`.
- Renamed public experiment IDs from `*_adaptive_ability` to neutral `*_reduced_item_ability` labels and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from existing artifacts.
- `python validate.py --compare`, `bash -n scripts/*.sh`, Python bytecode compilation, train/test split checks, and download URL verification pass.

### [2026-06-07 00:35] - core_claim_plus
- Hardened the method-agnostic evaluator so it loads WLE targets from `data/`, rejects duplicate or incomplete artifacts, and computes item counts from selected-item records rather than trusting method-emitted summaries.
- Cleaned duplicated calibrated CSVs and unused scoring helper code out of `method/ATLAS`, leaving calibrated banks under `data/calibrated_banks`.
- Revalidated the completed 750-model artifacts with `python validate.py --compare`, shell syntax checks, and Python compilation after the scoring metadata and evaluator fixes.

### [2026-06-07 00:27] - core_claim_plus
- Final verification confirmed the workspace structure, method/problem separation, download URL, train/test artifacts, and scoring files are suitable for gym use.
- Updated `reference.json` metric descriptions to match the corrected p-IRT accuracy and exposure-probability overlap formulas.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass after the verification update.

### [2026-06-07 00:23] - core_claim_plus
- Corrected the evaluator's accuracy reconstruction to the paper's p-IRT estimator: observed selected-item responses plus IRT-predicted probabilities for unobserved items.
- Corrected `test_overlap_rate` to the paper's exposure-probability formula and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from the completed 750-model artifacts.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass with the corrected metrics.

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 49m | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-07 00:40] - core_claim_plus
- Final verification confirmed the workspace is ready for gym use at `core_claim_plus`.
- Renamed public experiment IDs from `*_adaptive_ability` to neutral `*_reduced_item_ability` labels and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from existing artifacts.
- `python validate.py --compare`, `bash -n scripts/*.sh`, Python bytecode compilation, train/test split checks, and download URL verification pass.

### [2026-06-07 00:35] - core_claim_plus
- Hardened the method-agnostic evaluator so it loads WLE targets from `data/`, rejects duplicate or incomplete artifacts, and computes item counts from selected-item records rather than trusting method-emitted summaries.
- Cleaned duplicated calibrated CSVs and unused scoring helper code out of `method/ATLAS`, leaving calibrated banks under `data/calibrated_banks`.
- Revalidated the completed 750-model artifacts with `python validate.py --compare`, shell syntax checks, and Python compilation after the scoring metadata and evaluator fixes.

### [2026-06-07 00:27] - core_claim_plus
- Final verification confirmed the workspace structure, method/problem separation, download URL, train/test artifacts, and scoring files are suitable for gym use.
- Updated `reference.json` metric descriptions to match the corrected p-IRT accuracy and exposure-probability overlap formulas.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass after the verification update.

### [2026-06-07 00:23] - core_claim_plus
- Corrected the evaluator's accuracy reconstruction to the paper's p-IRT estimator: observed selected-item responses plus IRT-predicted probabilities for unobserved items.
- Corrected `test_overlap_rate` to the paper's exposure-probability formula and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from the completed 750-model artifacts.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass with the corrected metrics.

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim_plus` | **Status**: cancelled
- **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-07 00:40] - core_claim_plus
- Final verification confirmed the workspace is ready for gym use at `core_claim_plus`.
- Renamed public experiment IDs from `*_adaptive_ability` to neutral `*_reduced_item_ability` labels and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from existing artifacts.
- `python validate.py --compare`, `bash -n scripts/*.sh`, Python bytecode compilation, train/test split checks, and download URL verification pass.

### [2026-06-07 00:35] - core_claim_plus
- Hardened the method-agnostic evaluator so it loads WLE targets from `data/`, rejects duplicate or incomplete artifacts, and computes item counts from selected-item records rather than trusting method-emitted summaries.
- Cleaned duplicated calibrated CSVs and unused scoring helper code out of `method/ATLAS`, leaving calibrated banks under `data/calibrated_banks`.
- Revalidated the completed 750-model artifacts with `python validate.py --compare`, shell syntax checks, and Python compilation after the scoring metadata and evaluator fixes.

### [2026-06-07 00:27] - core_claim_plus
- Final verification confirmed the workspace structure, method/problem separation, download URL, train/test artifacts, and scoring files are suitable for gym use.
- Updated `reference.json` metric descriptions to match the corrected p-IRT accuracy and exposure-probability overlap formulas.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass after the verification update.

### [2026-06-07 00:23] - core_claim_plus
- Corrected the evaluator's accuracy reconstruction to the paper's p-IRT estimator: observed selected-item responses plus IRT-predicted probabilities for unobserved items.
- Corrected `test_overlap_rate` to the paper's exposure-probability formula and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from the completed 750-model artifacts.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass with the corrected metrics.

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 45m | **GPU**: 0.0h
- **Jobs**: 9 total (7 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-11-09 02:00] - core_claim_plus
- Hardened the gym (see `HARDENING.md`). Held-out answers now live only in `eval/test/data/`, as a 50/50 name-hash split of every released identity (10,569 held-out models). Methods are policies queried through an evaluator-owned response oracle, at evaluator-fixed per-slot item budgets, with explicit failure rules. Random100, the item bank and the targets used for scoring are evaluator-owned. `download.sh` is pinned to upstream commit e2f1975 with checksums.
- The reference ATLAS was rerun from the final code through the hidden test. At ATLAS_0.1, with fewer than 100 items, it beats Random100 ability MAE on all five benchmarks (weighted 0.112 vs 0.172). Live scores equal the audit's seed-123 scores exactly.
- All major red-team shortcuts now fail or tie, and honest better variants beat the reference beyond seed noise.

### [2026-06-07 00:40] - core_claim_plus
- Final verification confirmed the workspace is ready for gym use at `core_claim_plus`.
- Renamed public experiment IDs from `*_adaptive_ability` to neutral `*_reduced_item_ability` labels and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from existing artifacts.
- `python validate.py --compare`, `bash -n scripts/*.sh`, Python bytecode compilation, train/test split checks, and download URL verification pass.

### [2026-06-07 00:35] - core_claim_plus
- Hardened the method-agnostic evaluator so it loads WLE targets from `data/`, rejects duplicate or incomplete artifacts, and computes item counts from selected-item records rather than trusting method-emitted summaries.
- Cleaned duplicated calibrated CSVs and unused scoring helper code out of `method/ATLAS`, leaving calibrated banks under `data/calibrated_banks`.
- Revalidated the completed 750-model artifacts with `python validate.py --compare`, shell syntax checks, and Python compilation after the scoring metadata and evaluator fixes.

### [2026-06-07 00:27] - core_claim_plus
- Final verification confirmed the workspace structure, method/problem separation, download URL, train/test artifacts, and scoring files are suitable for gym use.
- Updated `reference.json` metric descriptions to match the corrected p-IRT accuracy and exposure-probability overlap formulas.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass after the verification update.

### [2026-06-07 00:23] - core_claim_plus
- Corrected the evaluator's accuracy reconstruction to the paper's p-IRT estimator: observed selected-item responses plus IRT-predicted probabilities for unobserved items.
- Corrected `test_overlap_rate` to the paper's exposure-probability formula and regenerated `scores.json`, `scores_train.json`, and `scores_test.json` from the completed 750-model artifacts.
- `python validate.py --compare`, shell syntax checks, and Python compilation pass with the corrected metrics.

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

### [2026-06-06 22:24] - core_claim_plus
- Cancelled the full-model CPU rerun after the scheduler exposed a one-hour timeout for the job; it completed only Random100 and left incomplete scores, which were restored to the last complete validated results.
- Added output cleanup and progress logging to the job scripts to avoid stale partial artifacts after cancellations.
- Submitting a larger bounded five-benchmark rerun with 750 models per benchmark, keeping the ATLAS algorithm unchanged while fitting the observed CPU job limit.

### [2026-06-06 22:48] - core_claim_plus
- Job `a26f6ee5-684` completed successfully in about 21 minutes with 750 models per benchmark and passed `python validate.py --compare`.
- Updated `scoring/scores.json` with the 750-model ATLAS and Random100 results across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC.
- Submitting one more bounded CPU rerun at 1,500 models per benchmark to improve statistical coverage while staying within the observed scheduler limit.

### [2026-06-06 23:31] - core_claim_plus
- Cancelled the 1,500-model rerun after it was still mid-ATLAS at 40 minutes and unlikely to finish before the one-hour CPU timeout.
- Restored `scoring/scores.json` to the complete validated 750-model results from job `a26f6ee5-684`.
- Set the reusable job default back to 750 models per benchmark, the largest validated scale completed in this continuation.

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
