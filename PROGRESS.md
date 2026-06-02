# Progress

## What Works

- Paper analysis completed for the core ATLAS claim and appendix metrics.
- Released ATLAS code was cloned into `method/ATLAS` as reference source, with data assets separated out.
- `method/atlas_runner.py` implements ATLAS adaptive testing from calibrated 3PL banks.
- `baseline/random_static.py` implements a Random100 static subset baseline.
- `eval/evaluate_atlas.py` evaluates method artifacts without importing `method/`.
- `python validate.py --reference-only`, shell syntax checks, and Python parsing all pass.

## Results

No reproduced scores yet. A CPU job is being submitted to run TruthfulQA, WinoGrande, and HellaSwag with ATLAS thresholds 0.1, 0.2, and 0.3 plus Random100.

## Remaining

- Run the first end-to-end job and inspect `scoring/scores.json`.
- If the core three-benchmark results support the paper's claim, update milestone to `core_claim`.
- Expand to GSM8K and ARC if budget/time allow.

## Issues

- The original paper uses R `mirt`/`catR`; this reproduction uses the paper's released calibrated parameters and a Python implementation of the adaptive testing loop to avoid R runtime dependencies.

## Deviations from Paper

- The first job evaluates a subset of models (`ATLAS_TEST_LENGTH=180`) rather than the full held-out set to keep the initial validation job small. The procedure and algorithm are unchanged.
- Calibration is not recomputed in the initial run. The reproduction uses the paper's released calibrated item parameters and response matrices, then reproduces the adaptive testing and evaluation steps.
