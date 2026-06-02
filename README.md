# Overview

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent ability and repeatedly chooses high-information items targeted to that estimate.

This workspace packages a reproduction using the paper's released calibrated item banks and response matrices. The initial run targets the core claim on TruthfulQA, WinoGrande, and HellaSwag: ATLAS should approximate full-bank ability with fewer items than a static 100-item random baseline.

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

Item-bank reuse constraints are measured by `test_overlap_rate` and `max_exposure_rate`. Lower values indicate less redundant testing and less concentration on a small group of items.

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


---

# Reproduction Milestones

**Current: none**

## Stop Justification
- Completed at milestone `none`.
