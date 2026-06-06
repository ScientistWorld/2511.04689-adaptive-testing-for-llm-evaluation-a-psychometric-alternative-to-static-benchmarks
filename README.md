# Overview

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent ability and repeatedly chooses high-information items targeted to that estimate.

This workspace packages a reproduction using the paper's released calibrated item banks and response matrices. The reproduced run targets the core claim across TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC: ATLAS should approximate full-bank ability with fewer items than a static 100-item random baseline.

---

# Problem Definition

## Research Question

How can an evaluator estimate the benchmark ability of many language models with far fewer administered items than a full static benchmark, while preserving reliable rankings and uncertainty-aware scores?

## Why It Matters

Full benchmark evaluation is expensive and exposes entire item banks. A useful reduced evaluation should save item queries without collapsing model distinctions, especially when multiple models have similar raw accuracies.

## Success Criteria

A successful solution produces latent ability estimates close to full-bank reference estimates, uses substantially fewer items per model than the full item bank and a 100-item random subset, preserves raw-accuracy structure, and avoids excessive reuse of the same items across evaluated models.

---

# Paper's Method

## Key Contribution

ATLAS reframes LLM benchmark evaluation as computerized adaptive testing over calibrated IRT item banks.

## Approach

The paper first calibrates benchmark items with a 3PL IRT model, estimating discrimination, difficulty, and guessing parameters. Large banks are calibrated in partitions and linked onto a shared scale with common-person mean-sigma linking, then full-bank model abilities are estimated with WLE.

At evaluation time, ATLAS starts each model at ability `theta = 0`. The first item is selected near that starting difficulty. Subsequent items are ranked by Fisher information at the current ability estimate, and the administered item is sampled from the top five candidates. After each binary response, ability is updated with EAP. Testing stops after at least 30 items once the estimated standard error is below the configured threshold, or at 500 items.

## Main Claims

The primary claim is that adaptive, information-guided item selection recovers full-bank ability estimates with far fewer items than static benchmark subsets.

Secondary claims are that the latent ability score preserves raw-accuracy structure, differentiates models with similar or identical accuracy, and avoids overexposing the same items.

---

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


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
