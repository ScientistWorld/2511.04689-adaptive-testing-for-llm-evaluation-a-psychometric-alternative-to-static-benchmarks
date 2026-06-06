# Progress

## What Works

- Paper analysis completed for the core ATLAS claim and appendix metrics.
- Released ATLAS code was cloned into `method/ATLAS` as reference source, with data assets separated out.
- `method/atlas_runner.py` implements ATLAS adaptive testing from calibrated 3PL banks.
- `baseline/random_static.py` implements a Random100 static subset baseline.
- `eval/evaluate_atlas.py` evaluates method artifacts without importing `method/`.
- `python validate.py --compare`, shell syntax checks, and Python parsing all pass.

## Results

Job `5601fe49-efc` completed successfully on CPU for TruthfulQA, WinoGrande, and HellaSwag with 180 models, ATLAS thresholds 0.1, 0.2, and 0.3, plus Random100. Validation passed with comparison enabled.

The reproduced ATLAS runs show the core expected tradeoff on the three primary benchmarks: lower ability error than Random100 or comparable error with far fewer administered items. The constraint metrics are present in `scoring/scores.json`: `avg_items`, `information_efficiency_score`, `accuracy_mae`, `test_overlap_rate`, and `max_exposure_rate`.

Job `8d1fe4ff-0fd` completed the same procedure for all five reference benchmarks: TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC. It ran for 420 seconds on one CPU and passed `python validate.py --compare`.

## Remaining

- No further job is required for `core_claim`. A full-model rerun would extrapolate beyond the one-hour job limit from the 180-model five-benchmark runtime, so the final package keeps the validated bounded scale and records that deviation.

## Issues

- The original paper uses R `mirt`/`catR`; this reproduction uses the paper's released calibrated parameters and a Python implementation of the adaptive testing loop to avoid R runtime dependencies.

## Deviations from Paper

- Current jobs evaluate a subset of models (`ATLAS_TEST_LENGTH=180`) rather than the full held-out set to keep CPU validation jobs within the scheduler time limit. The procedure and algorithm are unchanged.
- Calibration is not recomputed in the initial run. The reproduction uses the paper's released calibrated item parameters and response matrices, then reproduces the adaptive testing and evaluation steps.
