# Hardening report

The red-team audit (`REDTEAM.md`) found that the old test did not reward better science: item
savings in raw units dominated the score, so a constant estimator with one recorded item beat the
reference by +62. Answers (whole-bank targets and full response matrices for every test identity)
sat in `data/`, the method's own item lists were trusted as the query count, and the comparator
artifacts could be edited. All of these are closed now. The test is a live query protocol against
evaluator-owned held-out data, at evaluator-fixed item budgets, with explicit failure rules. Honest
better variants now score above the reference by more than seed noise, and every major shortcut
scores as failed or ties.

Evidence: `redteam/hardening/results/` (`summary.md`, `summary.json`, one score file per run and
split, `budget_derivation.json`, `calibration_fit_train.json`, `verify.json`). Code:
`redteam/hardening/audit.py` and `variant_policy.py`. Replay: `bash redteam/hardening/run_audit.sh`.
Jobs `dd43d4df-4ca` and `a2e939f7-501`, both exit 0. The second job's live
`scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` reproduce the audit's seed-123 scores with
a maximum difference of 0.

## What changed

1. **Held-out answers live only in `eval/test/`.** All 18,780 released identities (4,635 TruthfulQA,
   4,680 WinoGrande, 3,467 HellaSwag, 4,195 GSM8K, 4,164 ARC) are split 50/50 by a name hash
   (`eval/test/build_test_data.py`). The held-out half (10,569 models) is stored as
   `eval/test/data/<b>_heldout.tsv.gz`: full-bank responses and whole-bank WLE targets, plus the
   evaluator's own item-bank copy. `data/calibrated_banks/*/irt_person_scores_WLE_SE.csv` and the
   downloaded matrices keep visible identities only. `scripts/download.sh` was also broken (upstream
   moved and replaced `data.zip`); it now pins upstream commit `e2f1975`, checks SHA-256 sums and
   drops held-out rows.
2. **Methods are queried, not trusted.** A method is a policy program declared in
   `checkpoints/**/manifest.json`. The evaluator starts it and serves item responses through a
   JSON-lines oracle on anonymized, shuffled instances. It counts every query itself and reads back
   only the ability estimate. Accuracy reconstruction, overlap and exposure are recomputed from the
   oracle log; Random100 is computed by the evaluator on the same instances. Nothing else the
   method writes (fields, files, score files) is read.
3. **Item count is a constraint, not a reward.** Each benchmark has three operating-point slots
   (`ATLAS_0.1/0.2/0.3`) with evaluator-fixed average-item budgets in `eval/{train,test}/budgets.json`.
   Each budget is 1% above the largest reference average item count over seeds 123-125, per split.
4. **Failure rules.** A slot is scored as failed, never as high, if any of these holds: protocol error,
   non-finite or |theta| > 10 estimate, a model left without an estimate, more than 500 queries for
   one model, average items over budget, ability MAE above 2x Random100, accuracy reconstruction worse
   than a constant guess, or no manifest claims the slot. A failed slot takes at least the error of a
   constant (median) guess on ability and accuracy, and 1.0 overlap and exposure.
5. **Scored metrics** (see the coefficient table below). `average_item_exposure_rate` is now taken
   over the items administered at least once. The paper's own Table 8 values need that denominator,
   for example HellaSwag 3.86% at 41 items; the old denominator, the whole bank, made exposure equal
   to test length / bank size, a second item-count reward.
6. **Reference reproduction** `method/atlas_policy.py` is the same ATLAS algorithm as before
   (start at theta = 0, first item near it, randomesque top-5 Fisher selection, EAP on a 241-point
   grid, SE stop with 30-500 items), ported to the protocol. Grid probabilities are precomputed.

## Do better results score higher?

The rank delta is the sum, over experiments, rows and metrics, of experiment weight x |coefficient| x
improvement in the better direction, relative to reference seed 123 on the hidden test.

- **Raw**: improvements in metric units.
- **Normalized**: each improvement divided by its standard deviation across the 14 audited runs that
  pass every slot (the honest-competition regime).
- **Paired**: the experiment-weighted per-model change in absolute ability error versus seed 123,
  on the same held-out models, with its standard error.

Seed noise is the largest |delta| among reference seeds 124 and 125: **0.0022 raw**, **0.184 normalized**.

| Variant (after) | Raw delta | Normalized | Paired ability-error change (SE) | Before (REDTEAM, old scale) |
|---|---:|---:|---|---|
| Population blend + empirical prior (same items) | **+0.0224** | **+0.699** | -0.0072 (0.0007) | (new) |
| Population blend: mean of the reference estimate and a visible-population nearest-pattern estimate (same items) | **+0.0214** | **+0.668** | -0.0068 (0.0007) | (new) |
| Empirical (visible-population) prior for the final EAP (same items) | **+0.0072** | **+0.294** | -0.0024 (0.0002) | "train prior": -0.314 |
| Reference seed 124 / 125 | +0.0022 / +0.0016 | +0.146 / +0.184 | -0.0006 / -0.0005 (0.0008) | spread 0.208 |
| Fixed-length test at the budget | -0.0029 | -0.175 | -0.0041 (0.0003) | (new) |
| Max-information (top-1) + empirical prior, fixed length | -0.0085 | -0.233 | -0.0035 (0.0007) | "max Fisher": +0.054 |
| Train-fitted linear calibration of the estimate | -0.0182 | -0.468 | +0.0060 (0.0002) | (new) |
| Visible-population estimate alone | -0.0549 | -2.172 | +0.0184 (0.0013) | (new) |
| **Weaker:** uniform random items at the budget | -0.4172 | -12.79 | +0.1516 (0.0018) | random policy: -217.3 |
| **Weaker:** static random subset at the budget (`baseline/`) | -1.2924 | -61.87 | +0.1546 (0.0018) | (new) |
| **Weaker:** constant theta = 0 on the reference's items | -2.6305 (all 15 slots failed) | -125.8 | +0.6766 | -7.19 |
| More observations (min 60 items, SE threshold / sqrt 2) | -2.5958 (all 15 slots over budget, failed) | -124.9 | -0.0342 | -108.7 |

- **Genuine improvements win.** Blending the reference estimate with an estimate learned from the
  visible population lowers ability error at identical item cost. It ranks 10x above raw seed noise
  and 3.8x above normalized noise. The empirical prior is a smaller but real gain (3.2x raw,
  1.6x normalized), and it holds on the visible split too: weighted ability MAE at ATLAS_0.1 is 0.1086
  vs the reference's 0.1112 there, against 0.1098 vs 0.1117 on the hidden test.
- **Trade-offs land near or below the reference.** The fixed-length and top-1 variants reach lower
  ability error (0.103 vs 0.112 at ATLAS_0.1) but concentrate item use: weighted overlap at ATLAS_0.1
  rises from 0.168 to 0.224-0.229, and exposure from 0.068 to 0.108-0.111. Fixed length lands within
  about one noise unit of the reference (raw -0.0029, normalized -0.175). Top-1, which drops
  exposure control, lands below (raw -0.0085, normalized -0.233). This matches the paper's design
  choice: randomesque selection exists to trade a little precision for exposure.
- **Weaker methods score lower.** The calibrated variant over-corrects a train-set bias and
  correctly scores lower; the weaker variants are far below.
- **Before:** better estimation with more items scored -108.7 and the constant estimator only -7.2,
  while the one-item constant scored +62. The test rewarded item savings, not estimation. The old
  "train prior" and "max Fisher" variants were within seed noise and are not the same
  implementations as the new ones.

## Major shortcuts: fix and score

Before is the REDTEAM delta under the old raw formula; after is the raw delta on the new hidden test.

| Shortcut | Before | Fix | After |
|---|---:|---|---|
| Copy the shipped `Theta_WLE` targets | +64.64 | Held-out targets exist only in `eval/test/data`; the visible file lists visible identities only; instances are anonymous | `shortcut_visible_lookup`: no match, falls back to a 1-item estimate. All 15 slots failed, **-2.596** |
| Constant theta, one item | +62.07 | Failure rules (MAE > 2x Random100) and items as a budget, not a reward | **-2.632**, all slots failed |
| Report reference thetas but list one item (unreported queries) | +64.22 | Responses are available only by querying the evaluator's oracle, which counts every query; no item list is read | Impossible by construction; the only way to have responses is to query (`shortcut_visible_lookup` above) |
| Replace the target CSV in `data/` | +63.99 | Scoring uses `eval/test/data` targets and item bank | `shortcut_visible_targets_zeroed`: **0.0000** (tie) |
| Shrink the response matrix in `data/` (test size) | +21.13 | Held-out population and size fixed in `eval/test/data` | `shortcut_visible_population_shrunk`: **0.0000** (tie) |
| Corrupt the Random100 artifact (IES denominator) | -999999 (+0.94 conditional) | Random100 computed by the evaluator; a manifest claim on `Random100` is ignored; IES not scored | No artifact to corrupt; the Random100 row is identical across all 22 audited test runs |
| NaN / inf estimates | accepted, NaN score | Non-finite or abs(theta) > 10 is a protocol error, so the slot fails | **-2.596** each, all slots failed |
| Blank (null) estimate | evaluator crash | Same | **-2.596**, all slots failed |
| Forged self-reported fields / `success=true` | 0 (tie) | Only `theta` is read | **0.0000** (tie) |
| Pre-written `scoring/scores_test.json` | 0 (tie) | Overwritten by the evaluator (unchanged) | not rerun; still a tie |
| Over-budget estimation (more observations) | -108.7 | Budget is a hard limit | **-2.596**, all slots failed |
| Empty item record | evaluator crash | No item records exist; a zero-query policy is scored by its estimate | covered by the constant and lookup cases |

## Shortcuts and risks left open

- **Reading evaluator files at test time.** The policy runs in the same container as
  `eval/test/data/`; a policy that opens those files, the public upstream release (all responses),
  or pre-hardening git revisions of `data/calibrated_banks/*/irt_person_scores_WLE_SE.csv` (all
  targets) gets the answers. This cannot be closed inside the evaluator without sandboxing. It is
  forbidden in `scoring/CONSTRAINTS.md` and left to the shortcut grader.
- **Budget slack.** Budgets sit up to 1% plus seed variation above the reference's own usage. A
  method that always fills the budget gets up to ~1.5% more items (the fixed-length variant used
  63.1 vs 62.2 at ATLAS_0.1). Its measured effect is within noise.
- **Population matching is allowed.** Estimators that use the visible response matrix (for example
  nearest response patterns) are legitimate and are the clearest source of headroom. Near-duplicate
  leaderboard models make them strong. Their visible-split score is optimistic, because an
  instance's own row is in the visible matrix; `briefing/evaluation.md` warns about this.
- **Hard failure rule for weak-but-honest methods.** The 2x Random100 rule fails the static
  random subset at TruthfulQA's 30-item slots. Such methods rank far below the reference either way.
- **Wall-clock.** Only a 900 s per-message inactivity timeout is enforced. The reference needs about
  4 minutes of policy time for the hidden test on one CPU; very slow policies make the test long.
- **Old red-team bundle.** The scripts in `redteam/` (other than `redteam/hardening/`) use the
  old artifact interface and no longer run against the new evaluator; they are kept as the before
  evidence.

## Reference score before and after

The rank delta of the reference against itself is 0 by definition. Experiment-weighted metrics on the
hidden test:

| Row | Before (375 test models from the first 750 rows) | After (10,569 held-out models) |
|---|---|---|
| Random100 | ability MAE 0.1735, accuracy MAE 0.0235 | ability MAE 0.1716, accuracy MAE 0.0228 |
| ATLAS_0.1 | ability MAE 0.1169, 64.2 items, overlap 0.166 | ability MAE 0.1117, 62.2 items, overlap 0.168, exposure 0.068 |
| ATLAS_0.2 | ability MAE 0.1342, 33.5 items | ability MAE 0.1326, 33.8 items |
| ATLAS_0.3 | ability MAE 0.1370, 31.7 items | ability MAE 0.1348, 31.3 items |

The reproduced claim keeps the paper's direction on the hidden test. At ATLAS_0.1, with fewer than
100 items, ability MAE beats Random100 on every benchmark:

| Benchmark | ATLAS_0.1 MAE | Items | Random100 MAE |
|---|---:|---:|---:|
| TruthfulQA | 0.057 | 47.7 | 0.116 |
| WinoGrande | 0.126 | 82.5 | 0.184 |
| HellaSwag | 0.149 | 40.2 | 0.220 |
| GSM8K | 0.149 | 72.3 | 0.158 |
| ARC | 0.081 | 84.4 | 0.176 |

The ATLAS-minus-Random100 gap (about 0.06 in weighted MAE) is about 75x the paired seed noise
(0.0008). Two shortfalls appear in both the paper and the reproduction:

- **GSM8K at ATLAS_0.2/0.3:** ability MAE 0.172 and 0.176 vs Random100's 0.158 (paper: 0.177 and
  0.173 vs 0.150).
- **GSM8K accuracy reconstruction:** 0.040-0.044 vs Random100's 0.030 (paper: 0.039-0.044 vs 0.026).

## Headroom check

No scored metric of the reference sits at a bound on the hidden test:

- ability MAE: 0.057-0.176 (bound 0);
- accuracy MAE: 0.016-0.044;
- overlap: 0.12-0.22;
- exposure: 0.03-0.10.

Random100's overlap and exposure are 1.0 by construction, which is the worst bound, not a ceiling.
Headroom is demonstrated, not just available: three honest variants beat the reference beyond raw
and normalized seed noise, with the best at -0.0072 paired ability error, about 6.5% of the
reference MAE. The paper's own shortfalls listed above (GSM8K at the tight slots and in accuracy
reconstruction, WinoGrande at the tight slots) are inside the scored experiments, so no additional
experiment was needed.

## Coefficients and weights

Experiment weights are unchanged: 0.25 each for TruthfulQA, WinoGrande and HellaSwag (the paper's
main table) and 0.125 each for GSM8K and ARC (appendix). Paper-reported results in
`scoring/reference.json` are unchanged.

| Metric | Old coefficient | New | Why |
|---|---:|---:|---|
| `ability_mae` | 1.0 | 1.0 | The paper's primary quantity |
| `accuracy_mae` | 0.4 | 0.4 | Paper Table 3 (main text) |
| `avg_items` | 0.5 | 0 (hard budget) | Rewarding fewer items let task failure outrank estimation (+62 shortcut); the paper compares methods at their item cost, which the budgets fix |
| `information_efficiency_score` | 1.0 | 0 (diagnostic) | The MAE x items product rewards near-empty tests (constant estimator IES 0.047 vs reference 0.431); redundant once items are fixed |
| `ability_se`, `accuracy_se` | 0.2, 0.1 | 0 (diagnostic) | The paper's "+/-" columns are the uncertainty of the MAE, not a target. Scored, they mostly added seed noise: in round 1 they contributed about 0.10 of seed 125's 0.29 normalized delta, and normalized seed noise fell to 0.18 after this change and the concentration change below |
| `test_overlap_rate`, `average_item_exposure_rate` | 0.2, 0.2 | 0.1, 0.1 | With the corrected exposure denominator both measure item concentration (paper Table 8, appendix). Together they weighed 0.4 against 1.0 for ability error, so concentration outweighed real accuracy gains; 0.2 in total keeps exposure control rewarded without dominating |
| `constraint_failed`, `models_evaluated` | -, 0 | 0 (diagnostic) | Failure is already reflected in the scored metrics |

## What I could not fix

- **Test size cannot grow further.** The test already uses half of every released identity. A 2%
  ability-error improvement (the empirical prior) clears raw seed noise 3.2x but normalized noise
  only 1.6x, because accuracy MAE varies little across honest methods and so is noisy after
  normalization.
- **The public upstream data and this repository's history** contain the held-out responses and
  targets. See "Shortcuts and risks left open".
- **Train and test budgets differ** by up to 4% because each is matched to the reference's usage on
  its own population.
