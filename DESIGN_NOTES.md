# Train/Test Evaluation Design Notes

## Checked

- Compared `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh`; train invokes `eval/train/evaluate.py` and writes `scoring/scores_train.json`, while test invokes `eval/test/evaluate.py` and writes `scoring/scores_test.json`.
- Checked that both scripts enumerate checkpoint manifests from disk instead of hardcoding a single method name.
- Checked for train/test cross-imports; the split evaluators do not import from each other or from `method/`.
- Checked that `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both split evaluation scripts.

## Changed

- Fixed a target-leak shortcut: both split evaluators now compute `ability_mae` against evaluator-owned WLE targets from `data/calibrated_banks/<benchmark>/irt_person_scores_WLE_SE.csv`, not the `Theta_WLE` column supplied in a method result CSV.
- Fixed an item-count shortcut: `avg_items` is now computed from the method's selected-item artifact, not the method-reported `Num_Items` field.
- Preserved selected-item sequences for item counts and convert to sets only for overlap/exposure metrics, so repeated item IDs cannot undercount actual item usage.
- Added evaluator-side artifact validation for duplicate result rows, missing slice result rows, missing selected-item rows, and selected item IDs outside the calibrated item bank.
- Added the required `description` field to every active metric in `scoring/reference.json` without changing paper-reported result values.

## Runtime Concerns For Runner Iteration

- The new full-slice coverage check is intentionally strict: each method manifest must provide exactly one result row for every model identity in the train/test slice. If existing generated artifacts are incomplete, the runner should regenerate artifacts rather than weakening the evaluator.
- The split is still a held-out model-identity split over the same calibrated benchmark banks. This is appropriate for detecting overfit to visible model identities, but it does not hide the underlying public item banks.
- The evaluator now ignores method-supplied `Theta_WLE` and `Num_Items` for scoring. Existing score values may shift on the next run if any artifact had inconsistencies between reported counts and selected-item files.
