# Paper's Method

## Key Contribution

ATLAS reframes LLM benchmark evaluation as computerized adaptive testing over calibrated IRT item banks.

## Approach

The paper first calibrates benchmark items with a 3PL IRT model, estimating discrimination, difficulty, and guessing parameters. Large banks are calibrated in partitions and linked onto a shared scale with common-person mean-sigma linking, then full-bank model abilities are estimated with WLE.

At evaluation time, ATLAS starts each model at ability `theta = 0`. The first item is selected near that starting difficulty. Subsequent items are ranked by Fisher information at the current ability estimate, and the administered item is sampled from the top five candidates. After each binary response, ability is updated with EAP. Testing stops after at least 30 items once the estimated standard error is below the configured threshold (0.1, 0.2 or 0.3), or at 500 items.

## In this workspace

`method/atlas_policy.py` implements this loop as a policy for the evaluator's query protocol (N(0,1) prior, 241-point grid on [-6, 6], seed 123 + instance index for the randomesque draw). `scripts/method.sh` writes `checkpoints/atlas_python/manifest.json`, mapping slots `ATLAS_0.1/0.2/0.3` to SE thresholds 0.1/0.2/0.3. The slot budgets were set 1% above this policy's average item usage (seeds 123-125), so the reference stops by its own SE rule within budget.

## Main Claims

The primary claim is that adaptive, information-guided item selection recovers full-bank ability estimates with far fewer items than static benchmark subsets.

Secondary claims are that the latent ability score preserves raw-accuracy structure, differentiates models with similar or identical accuracy, and avoids overexposing the same items.
