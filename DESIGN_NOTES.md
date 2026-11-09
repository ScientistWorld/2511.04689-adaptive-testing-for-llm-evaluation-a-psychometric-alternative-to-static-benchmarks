# Train/Test Evaluation Design Notes

Current design (after hardening; details in `HARDENING.md` and `briefing/evaluation.md`):

- `eval/train/evaluate.py` and `eval/test/evaluate.py` are independent copies of one protocol. Each runs every
  manifest-declared policy against a response oracle, counts queries itself, and scores ability MAE, p-IRT
  accuracy MAE, overlap and exposure, plus diagnostics. Neither imports `method/` or the other.
- Visible split: identities in `data/calibrated_banks/<b>/irt_person_scores_WLE_SE.csv` and the filtered
  matrices in `data/downloads/`. Hidden test: `eval/test/data/<b>_heldout.tsv.gz` (responses + whole-bank
  targets) and an item-bank copy, built by `eval/test/build_test_data.py`.
- Slot budgets: `eval/{train,test}/budgets.json`, 1% above the reference's maximum average item usage
  over seeds 123-125 on each split.
- Rows in every score file: evaluator-computed `Random100` plus the three slots. An unclaimed or failed slot
  gets failure values that are never better than a constant guess.
- `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` scan `checkpoints/` for manifests; no method name
  is hardcoded, and each slot must be claimed by exactly one manifest.
