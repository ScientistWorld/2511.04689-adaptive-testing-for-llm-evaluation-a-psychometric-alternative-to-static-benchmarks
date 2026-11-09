#!/bin/bash
set -euo pipefail

# Replays the hardening audit on a compute node (8 CPUs: ~10 minutes; resumable).
# Note: the `budgets` stage rewrites eval/{train,test}/budgets.json from the
# reference runs; with unchanged code it reproduces the committed values.
cd /home/user
python redteam/hardening/audit.py smoke reference budgets fit
bash scripts/method.sh
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
bash scripts/evaluate_test.sh
python redteam/hardening/audit.py variants mutations score verify
