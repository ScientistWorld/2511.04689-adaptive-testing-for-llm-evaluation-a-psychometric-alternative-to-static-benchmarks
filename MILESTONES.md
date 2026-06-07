# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim_plus`.
