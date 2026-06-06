# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim_plus`.
