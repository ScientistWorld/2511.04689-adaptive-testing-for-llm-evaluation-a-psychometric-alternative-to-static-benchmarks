# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-06-02 00:00] - none
- Read the paper and identified ATLAS as a 3PL IRT computerized adaptive testing method for LLM benchmark evaluation.
- Cloned the released ATLAS repository, extracted calibrated item banks and response matrices, and implemented a Python ATLAS runner using Fisher-information randomesque selection, EAP updates, and SE-based stopping.
- Added an independent evaluator and Random100 baseline; lightweight validation passes.

### [2026-06-06 21:35] - method_runs
- Job `5601fe49-efc` ran the implemented ATLAS adaptive testing loop and Random100 baseline on TruthfulQA, WinoGrande, and HellaSwag for 180 models.
- `python validate.py --compare` passed, and `scoring/scores.json` includes benefit and constraint metrics for the completed experiments.
- Expanded `scripts/method.sh` and `scripts/baseline.sh` so the next run covers GSM8K and ARC in addition to the three primary benchmarks.

## Stop Justification
- Current validated milestone is `method_runs`; the next submitted job targets `core_claim` coverage across all five reference experiments.
