# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-06 21:54] - core_claim_plus
- Implemented and validated the ATLAS adaptive testing loop using calibrated 3PL item banks: theta initialization at 0, Fisher-information top-5 randomesque item selection, EAP updates, and SE-based stopping with 30/500 item bounds.
- Ran Random100 and ATLAS thresholds 0.1, 0.2, and 0.3 on TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC with 180 held-out models per benchmark.
- `python validate.py --compare` passes, with reproduced ability MAE and item-efficiency trends supporting the paper's core claim across all five benchmarks at the bounded scale.

### [2026-06-06 21:59] - core_claim_plus
- Continuing audit confirmed the implementation is the paper's ATLAS adaptive testing algorithm, not a surrogate, and that evaluation remains separated from `method/`.
- Updated reusable scripts so the default reproduction uses the full available response matrices; `ATLAS_TEST_LENGTH` is now an explicit scale-down override.
- Submitting a full five-benchmark CPU rerun to replace the bounded 180-model scores if it completes within the scheduler limit.

## Stop Justification
- Completed at milestone `core_claim_plus`. Higher milestones would require reproducing calibration/model-fit diagnostics and qualitative rank-reordering case studies beyond the current adaptive-testing result set.
