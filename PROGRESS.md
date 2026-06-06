# Progress

## What Works

- Paper analysis completed for the core ATLAS claim and appendix metrics.
- Released ATLAS code was cloned into `method/ATLAS` as reference source, with data assets separated out.
- `method/atlas_runner.py` implements ATLAS adaptive testing from calibrated 3PL banks.
- `baseline/random_static.py` implements a Random100 static subset baseline.
- `eval/evaluate_atlas.py` evaluates method artifacts without importing `method/`.
- `python validate.py --compare`, shell syntax checks, and Python parsing all pass.
- The current achieved milestone is `core_claim_plus`.
- Continuing audit corrected the exposure metric to match the paper's definition of average item exposure over the item bank.
- Continuing audit corrected Information Efficiency Score normalization so reproduced runs use the reproduced Random100 denominator when that baseline is present.
- Continuing audit confirmed the reproduction is trustworthy at `core_claim_plus` and changed script defaults to full-model evaluation, with `ATLAS_TEST_LENGTH` retained only as a scale-down override.

## Results

Job `5601fe49-efc` completed successfully on CPU for TruthfulQA, WinoGrande, and HellaSwag with 180 models, ATLAS thresholds 0.1, 0.2, and 0.3, plus Random100. Validation passed with comparison enabled.

The reproduced ATLAS runs show the core expected tradeoff on the three primary benchmarks: lower ability error than Random100 or comparable error with far fewer administered items. The constraint metrics are present in `scoring/scores.json`: `avg_items`, `information_efficiency_score`, `accuracy_mae`, `test_overlap_rate`, and `average_item_exposure_rate`.

Job `8d1fe4ff-0fd` completed the same procedure for all five reference benchmarks: TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC. It ran for 420 seconds on one CPU and passed `python validate.py --compare`.

## Current Run

- Submitting a normal CPU job for a full-model five-benchmark rerun using all available rows: TruthfulQA 4,635, WinoGrande 4,680, HellaSwag 3,467, GSM8K 4,195, and ARC 4,164. If successful, this should strengthen the reproduction beyond the previous 180-model bounded run.

## Remaining

- Higher milestones would require reproducing secondary analyses: refitting/calibrating item banks, model-fit RMSEA diagnostics, rank-reordering plots, and identical-accuracy case studies.

## Issues

- The original paper uses R `mirt`/`catR`; this reproduction uses the paper's released calibrated parameters and a Python implementation of the adaptive testing loop to avoid R runtime dependencies.
- Audit finding fixed: the previous evaluator reported `max_exposure_rate`, but the paper defines and reports average item exposure rate. `eval/evaluate_atlas.py`, `scoring/reference.json`, and target docs now use `average_item_exposure_rate`.
- Audit finding fixed: `scripts/download.sh` depends on `unzip`, so `environment/container.def` now installs it for fresh-container reproducibility.

## Deviations from Paper

- Current checked-in scores are from a subset of models (`ATLAS_TEST_LENGTH=180`) rather than the full held-out set. A full-model CPU rerun has been prepared; the procedure and algorithm are unchanged.
- Calibration is not recomputed in the initial run. The reproduction uses the paper's released calibrated item parameters and response matrices, then reproduces the adaptive testing and evaluation steps.
