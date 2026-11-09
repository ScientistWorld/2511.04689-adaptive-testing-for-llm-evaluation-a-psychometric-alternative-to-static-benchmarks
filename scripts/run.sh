#!/bin/bash
set -euo pipefail

cd /home/user
echo "cpus: $(nproc)"

# 1) Hardening audit, part 1: smoke test of every policy, reference seeds,
#    evaluator budgets (eval/{train,test}/budgets.json) and the train-only fit
#    used by one variant. Resumable: transcripts cached in redteam/hardening/transcripts.
python redteam/hardening/audit.py smoke reference budgets fit

# 2) Reference pipeline from the final code: manifest -> visible split -> hidden test.
done_marker=redteam/hardening/transcripts/.final_pipeline_done_v2
if [ ! -e "$done_marker" ]; then
  rm -rf checkpoints/atlas_python checkpoints/random_static
  bash scripts/method.sh
  bash scripts/evaluate_train.sh
  cp scoring/scores_train.json scoring/scores.json
  bash scripts/evaluate_test.sh
  touch "$done_marker"
fi

# 3) Hardening audit, part 2: variants and shortcuts through the hidden test's oracle,
#    scoring/ranking, and a check that the live scores equal the audit's seed-123 scores.
python redteam/hardening/audit.py variants mutations score verify
python validate.py --compare || true
