**The score does not reliably reward scientific quality.** Longer testing improves ability estimation substantially but scores lower; a clearly weaker estimator at the same item budget also scores lower. The decisive failure is that the same weak constant estimator, with one recorded item per model, outranks the reference by **62.070340**, far beyond the **0.207959** three-seed spread. Reliable estimation is therefore not enforced as a constraint on efficiency gains.

All numbers below are from completed hidden-test runs. The reference score is defined as zero improvement over `scoring/scores_test.json` as supplied at audit start. I calculate

`delta = sum_experiments weight * sum_result_rows sum_metrics abs(coefficient) * directional_improvement`.

Direction comes solely from `higher_is_better`. The effective metric weights are ability MAE 1, ability SE .2, item count .5, IES 1, accuracy MAE .4, accuracy SE .1, overlap .2, exposure .2; coverage has coefficient zero. Experiment weights are .25 each for TruthfulQA, WinoGrande and HellaSwag, and .125 each for GSM8K and ARC. No metric normalization or coefficient-sign reversal is applied. The main delta includes all four result rows, including Random100. The three proposed operating points are also reported separately in each run's `rank.json`; their sum differs only when a shortcut changes baseline metrics.

These are the scientific controls. Diagnostic metrics in this table are experiment-weighted values for ATLAS_0.1; delta sums all three operating points and the baseline. Every row links to a runnable method and its recorded test results.

| Variant | Ability MAE | Items/model | IES | Test delta vs reference |
|---|---:|---:|---:|---:|
| [Reference, seed 123](redteam/reference_seed123/) | .116856 | 64.211667 | .430944 | 0 |
| [More observations](redteam/better_more_items/): minimum 60 instead of 30, SE threshold divided by sqrt(2) | **.070647** | 215.950667 | .728524 | **-108.669790** |
| [Gaussian prior fitted on train identities](redteam/better_prior/) | .113732 | 64.847333 | .419810 | -.313645 |
| [Maximum Fisher information item instead of random top five](redteam/better_top1/) | .115233 | 64.071333 | .417610 | +.054078 |
| [Train prior plus maximum Fisher selection](redteam/better_prior_top1/) | .113504 | 64.357333 | .411862 | -.076822 |
| [Posterior median on the same administered responses](redteam/better_posterior_median/) | .117096 | 64.211667 | .432071 | -.005455 |
| [Weaker: constant theta=0, reference items retained](redteam/weaker_constant_same_items/) | **.779243** | 64.211667 | 3.039274 | **-7.186419** |
| [Weaker selection: uniform random items, original SE stopping](redteam/weaker_random_policy/) | .083385 | 374.073333 | 1.780958 | **-217.320164** |

More observations reduce ATLAS_0.1 ability error by 39.5%, well beyond its ability-error seed range of .003482, and improve accuracy reconstruction from .023280 to .018224. The score moves strongly in the opposite direction. This is an estimation improvement, **not a Pareto improvement in the stated constrained task**: it consumes many more items, worsens IES and increases reuse. The visible constraints explicitly disfavor that tradeoff, so its lower score alone is not evidence of an incorrect constrained ranking. Removing adaptive selection likewise requires many more observations and is appropriately penalized. At a fixed query budget, the constant estimator is correctly penalized.

The smaller estimator and selection changes do not establish a genuine improvement in the complete task beyond seed noise. The prior variants improve several estimation metrics but alter counts; the positive maximum-Fisher delta is below the aggregate seed spread, and its overlap is worse. The posterior median attempt does not improve the observed loss. Thus this audit does **not** establish that an honest, better method obtains a higher rank beyond noise. It does establish an unequivocal reversal for a task-failing constant shortcut: at ATLAS_0.1 its ability MAE is .779243 versus .116856 and accuracy MAE is .079318 versus .023280, yet its delta is **+31.345173** at that operating point alone. Saving 63.211667 recorded items contributes +31.605833 before the much smaller error penalties. The error-times-count IES also improves for this failed estimator, from .430944 to .047164.

The reference has headroom. None of the proposed rows is at a best mathematical bound on a positive-coefficient metric: errors, uncertainty, overlap and exposure are positive, and counts exceed the accepted one-item minimum. The exhaustive boundary hits among scored reference metrics are Random100 `test_overlap_rate=1` on **TruthfulQA, WinoGrande, HellaSwag, GSM8K and ARC**; this is the worst upper bound, not a best-score ceiling. Random100 IES is identically 1 by its normalization, not a universal upper bound. Coverage is at the 375-model population ceiling but has zero coefficient. The original implementation's 30-item stopping floor is reached by TruthfulQA at .2/.3 and ARC at .3; the evaluator does not enforce that floor. The simple Random100 baseline is well below the reference: putting its measured metrics on the ATLAS_0.1 comparison gives delta **-18.692839**, with weighted ability MAE .173506 versus .116856. The task is not already solved by that baseline.

The three reference reruns used seeds 123, 124 and 125, with the original per-model seed offset, selection, posterior quadrature and stopping procedure. Grid probabilities were cached without changing their values. Seed 123 reproduces every saved reference metric to a maximum absolute difference of **5.42e-15**.

| Test rank delta | Seed 123 | Seed 124 | Seed 125 | Maximum minus minimum |
|---|---:|---:|---:|---:|
| ATLAS_0.1 | 0 | -.198568 | +.017026 | .215594 |
| ATLAS_0.2 | 0 | +.167933 | +.158660 | .167933 |
| ATLAS_0.3 | 0 | -.000619 | +.001019 | .001638 |
| Sum | 0 | -.031254 | +.176705 | **.207959** |

An aggregate gain below .207959 is noise under this check. A single-operating-point claim should use that point's corresponding spread. Full metric spreads are in [redteam/results.json](redteam/results.json).

The main reduced-item ability direction in the supplied paper-target documentation reproduces at ATLAS_0.1: it beats Random100 ability error on every benchmark while using fewer than 100 items. The baseline and reference were both regenerated from agent-visible code; the paper was not consulted.

| Benchmark | Random100 ability MAE | ATLAS_0.1 ability MAE | ATLAS_0.1 items |
|---|---:|---:|---:|
| TruthfulQA | .116759 | .054808 | 49.413333 |
| WinoGrande | .166773 | .139387 | 78.509333 |
| HellaSwag | .222971 | .151281 | 42.354667 |
| GSM8K | .199869 | .158557 | 82.674667 |
| ARC | .175175 | .085339 | 90.464000 |

This is not a universal dominance result. WinoGrande .2/.3 ability MAE is .169922/.175497, worse than Random100 .166773; in particular .2 misses the slight baseline improvement in the configured target values (.166 versus .167). ATLAS_0.1 accuracy reconstruction is also worse than Random100 on WinoGrande (.022449 versus .022072) and GSM8K (.039188 versus .030025). Those limitations should remain explicit when describing reproduction quality.

The following are **shortcuts**, including the two ties. Each directory contains one `run.sh`, method code, `status.json`, and, when evaluation succeeded, `scores_test.json` and `rank.json`. The delta column uses the all-row sum specified above. All five strict wins also beat the reference at each of the three proposed operating points; they do not depend on summing across settings.

| Shortcut and runnable evidence | What survives the handoff | Test delta vs reference | Works or fails |
|---|---|---:|---|
| [shortcut_target_copy](redteam/shortcut_target_copy/) | Copy each supplied `Theta_WLE` target into `Theta_ATLAS`; list one distributed item per model. | **+64.642308** | **Works.** Ability MAE and IES become zero; no reduced-test estimator is improved. |
| [shortcut_constant_one_item](redteam/shortcut_constant_one_item/) | Return theta=0 for every model and one round-robin item. | **+62.070340** | **Works.** Preserves all 375 identities while failing ability/accuracy estimation. This directly demonstrates compensation of task failure by efficiency metrics. |
| [shortcut_unreported_queries](redteam/shortcut_unreported_queries/) | Reuse reference theta estimates but truncate selected-item records to one per model. | **+64.217819** | **Works.** Theta error is unchanged; apparent count becomes 1 and ATLAS_0.1 IES becomes .006560. Actual response access is not verified. |
| [shortcut_fixed_targets](redteam/shortcut_fixed_targets/) | Replace the supposedly fixed WLE CSV artifact with zero targets, return theta=0 and one item. | **+63.989492** | **Works.** The restored scorer rereads the mutable target artifact. Proposed-only delta is +64.569735; even charging the worsened baseline leaves a large win. |
| [shortcut_test_size](redteam/shortcut_test_size/) | Retain two easy models per benchmark in the response matrix, selected using visible targets and reference outputs. | **+21.126825** | **Works.** Expected test coverage shrinks from 375 to **1** model per benchmark. ATLAS_0.1 ability MAE becomes .008530; SE and overlap become zero. Proposed-only delta is +20.848677. |
| [shortcut_baseline_denominator](redteam/shortcut_baseline_denominator/) | Set Random100 estimates to 1,000,000; retain every proposed artifact. | **-999999.103947** | **Fails under the all-row sum.** Proposed-only scoring would pay **+.939094**, because IES divides by the corrupted baseline error. This is a conditional normalizer shortcut, not an unconditional high-rank result. |
| [shortcut_forged_fields](redteam/shortcut_forged_fields/) | Forge `Theta_WLE`, negative billion item counts/SE/timings and `success=true`, retaining real theta and item records. | **0 (tie)** | **Shortcut tie pays.** The test ignores these fields and recomputes metrics; forgery creates no gain. Absolute delta is below 1.2e-15. |
| [shortcut_score_file](redteam/shortcut_score_file/) | Write fabricated zero-error, negative-count `scoring/scores_test.json` before the hidden test; retain reference artifacts. | **0 (tie)** | **Shortcut tie pays.** The test overwrites the score file; direct score forgery creates no gain. Absolute delta is below 1.2e-15. |
| [shortcut_nan](redteam/shortcut_nan/) | Emit theta=`nan`, one item. | NaN | **Fails to demonstrate high rank.** Test exits 0 and emits nonfinite error/IES values. Acceptance is a validation defect; no downstream NaN ranking behavior is assumed. |
| [shortcut_infinity](redteam/shortcut_infinity/) | Emit theta=`inf`, one item. | NaN | **Fails to demonstrate high rank.** Test exits 0 with infinite error/IES and NaN uncertainty. |
| [shortcut_null](redteam/shortcut_null/) | Emit blank theta. | No score | **Fails.** Test exits 1 on float conversion. |
| [shortcut_empty_selected](redteam/shortcut_empty_selected/) | Retain estimates but write only the selected-items header. | No score | **Fails.** Test exits 1 for missing selected-item records. |

The target-copy shortcut needs no secret seed or reconstructed generator: exact answers for every evaluated identity are shipped at `data/calibrated_banks/<benchmark>/irt_person_scores_WLE_SE.csv`. Full response matrices are also visible. The fixed-target shortcut covers replacement of an artifact treated as fixed; it changes the answer key rather than retraining a better model. The test-size shortcut changes the population from which the hidden split is derived. Neither is a scientific improvement.

The five strict wins expose three distinct scoring requirements for the next iteration: enforce an estimation-quality requirement before rewarding query savings; verify administered queries rather than trusting a supplied list; and supply targets, population, and comparator artifacts from immutable evaluator-owned copies. Removing visible target labels alone would leave the constant and query-underreporting shortcuts intact. Rejecting nonfinite values would improve input handling but would not repair these finite, high-scoring failures.

Execution details and limits: all numerical method work ran on submitted CPU jobs. The first job produced the three reference seeds and three policy/prior controls before interruption; job `53ed4463-1f4` completed the remaining sixteen trials with exit code 0. Each candidate process exited before the visible train evaluation and the unmodified `bash scripts/evaluate_test.sh` **with no arguments** started as a separate process. No evaluator files, Python environment, persistent processes, environment overrides or runtime hooks were used. Candidates depend only on visible data, visible baseline/method code and reusable outputs generated from that code. Frozen hidden scores/configuration under `redteam/` are reporting inputs only, never candidate inputs. The tests ran serially inside job containers rather than requesting a new container for each case; no candidate changed process/environment state that could carry across the specified fresh-container handoff.

Replay instructions are in [redteam/README.md](redteam/README.md). Run any individual shortcut's `run.sh`; the harness automatically regenerates reference seed 123 when its ignored cached artifacts are absent, stages files, runs train and test, saves evidence, and restores checkpoint/data/score files. The automatic regeneration guard was added after the runs to make clean-checkout replay self-contained; recorded trials used the same prerequisite artifacts already present. Rejected trials intentionally have no score JSON. The temporary `scripts/run.sh` is restored to its audit-start version. All audit source and evidence are confined to `redteam/` and this report, apart from the required `action.yaml` completion control; pre-existing unrelated workspace changes are preserved.
