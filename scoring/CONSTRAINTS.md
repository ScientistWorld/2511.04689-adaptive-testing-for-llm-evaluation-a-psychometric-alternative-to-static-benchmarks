# Constraints

Future methods must use the same response matrices, calibrated item banks, model set, and full-bank reference abilities provided in `data/`.

Evaluation must read produced reduced-test artifacts. It must not recompute a hidden full-bank score as the method output, and it must not use full-bank responses beyond the administered items when estimating reduced-test ability.

Reported improvements must preserve or improve item efficiency. A method that lowers error by administering substantially more items should be treated as weaker unless its information-efficiency score also improves.

Item reuse should be measured with the paper's aggregate diversity metrics: pairwise test overlap and average item exposure across the calibrated bank. Do not substitute a worst-case maximum exposure metric unless it is added as a separate, clearly named diagnostic.
