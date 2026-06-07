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
- Continuing audit corrected accuracy reconstruction to the paper's p-IRT estimator and corrected test overlap to the paper's exposure-probability formula.
- Continuing audit confirmed the reproduction is trustworthy at `core_claim_plus`.
- Job scripts now clean their own output directories before reruns and print benchmark-level progress.
- `scripts/run.sh` now refreshes the standard `scoring/scores.json` file in addition to the train/test split score files.
- `eval/evaluate_atlas.py` now owns the calibrated WLE targets from `data/`, rejects duplicate or incomplete method artifacts, and computes item counts from selected-item records.
- Duplicated calibrated CSVs and an unused scoring helper were removed from `method/ATLAS`; calibrated banks remain in `data/calibrated_banks`.
- `scripts/download.sh` now uses an all-benchmark completeness check and `.complete` sentinel for the ATLAS response matrices.

## Results

Job `5601fe49-efc` completed successfully on CPU for TruthfulQA, WinoGrande, and HellaSwag with 180 models, ATLAS thresholds 0.1, 0.2, and 0.3, plus Random100. Validation passed with comparison enabled.

The reproduced ATLAS runs show the core expected tradeoff on the three primary benchmarks: lower ability error than Random100 or comparable error with far fewer administered items. The constraint metrics are present in `scoring/scores.json`: `avg_items`, `information_efficiency_score`, `accuracy_mae`, `test_overlap_rate`, and `average_item_exposure_rate`.

Job `8d1fe4ff-0fd` completed the same procedure for all five reference benchmarks: TruthfulQA, WinoGrande, HellaSwag, GSM8K, and ARC. It ran for 420 seconds on one CPU and passed `python validate.py --compare`.

Job `a26f6ee5-684` completed successfully with 750 models per benchmark across the same five benchmarks and passed `python validate.py --compare`. The reproduced scores remain close to the paper's reported ability-error and item-efficiency tradeoffs, with ATLAS using substantially fewer items than Random100 while maintaining competitive accuracy MAE and lower test overlap.

On 2026-06-07, the existing 750-model artifacts were rescored with the corrected p-IRT accuracy reconstruction and exposure-formula overlap metrics. Validation still passes, and the reproduced overlap rates now match the scale of the paper's Table 8 definition.

On 2026-06-07, the existing 750-model artifacts were rescored again with a hardened evaluator that reads target abilities independently from `data/` and validates result/selected-item completeness. The reproduced scores remained numerically unchanged, and `python validate.py --compare` passed.

## Current Run

- Full-model CPU job `a6eac4c0-0ea` was cancelled after the logs showed the scheduler timeout was one hour. It completed Random100 only and produced incomplete scores; `scoring/scores.json` has been restored to the previous complete 180-model ATLAS + Random100 result.
- A 1,500-model CPU rerun was attempted but cancelled at 40 minutes while still mid-ATLAS; it was unlikely to complete before the one-hour timeout. The partial Random100-only scores were discarded, and `scoring/scores.json` was restored to the complete 750-model result.
- No further job is queued. The validated package is complete at `core_claim_plus`.

## Remaining

- Higher milestones would require reproducing secondary analyses: refitting/calibrating item banks, model-fit RMSEA diagnostics, rank-reordering plots, and identical-accuracy case studies.

## Issues

- The original paper uses R `mirt`/`catR`; this reproduction uses the paper's released calibrated parameters and a Python implementation of the adaptive testing loop to avoid R runtime dependencies.
- Audit finding fixed: the previous evaluator reported `max_exposure_rate`, but the paper defines and reports average item exposure rate. `eval/evaluate_atlas.py`, `scoring/reference.json`, and target docs now use `average_item_exposure_rate`.
- Audit finding fixed: `scripts/download.sh` depends on `unzip`, so `environment/container.def` now installs it for fresh-container reproducibility.
- Audit finding fixed: `accuracy_mae` now uses the paper's p-IRT combination of observed reduced-test responses and predicted probabilities on unobserved items, rather than a pure TCC average.
- Audit finding fixed: `test_overlap_rate` now uses the Hsu et al. exposure-probability formula reported in the paper, rather than pairwise Jaccard overlap.
- Audit finding fixed: the main evaluator no longer trusts method-emitted `Theta_WLE` labels and now checks duplicate rows, missing selected items, and invalid selected item IDs.
- Audit finding fixed: duplicated data artifacts under `method/ATLAS` were removed so calibrated banks live only under `data/`.
- Audit finding fixed: `scripts/run.sh` passes explicit manifests to split evaluators, preventing stale checkpoint manifests from being scored by default.
- Audit finding fixed: `scripts/download.sh` repairs partial response-matrix extraction instead of using only one CSV as a sentinel.

## Deviations from Paper

- Current checked-in scores are from a subset of models (`ATLAS_TEST_LENGTH=750`) rather than the full held-out set. Full-model and 1,500-model CPU runs exceeded the observed one-hour scheduler limit; the procedure and algorithm are unchanged.
- Calibration is not recomputed in the initial run. The reproduction uses the paper's released calibrated item parameters and response matrices, then reproduces the adaptive testing and evaluation steps.
