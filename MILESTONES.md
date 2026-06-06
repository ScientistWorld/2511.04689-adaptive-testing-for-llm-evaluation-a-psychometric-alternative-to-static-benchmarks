# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim`.
