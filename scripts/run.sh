#!/bin/bash
set -euo pipefail

cd /home/user

# Reference reproduction end to end. ATLAS needs no training: method.sh writes
# the manifest mapping the three operating-point slots to the policy, and the
# evaluators run it against their response oracles (visible split, then the
# hidden test). About 5 minutes of CPU per split.
rm -rf checkpoints/atlas_python checkpoints/random_static
bash scripts/method.sh
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
bash scripts/evaluate_test.sh
python validate.py --compare

# The hardening audit (reference seeds, budgets, variants, shortcuts) is
# replayed with: bash redteam/hardening/run_audit.sh
