#!/bin/bash
set -euo pipefail
cd /home/user
for variant in \
  reference_seed123 reference_seed124 reference_seed125 \
  better_prior better_top1 better_prior_top1 \
  shortcut_target_copy shortcut_constant_one_item shortcut_unreported_queries \
  shortcut_baseline_denominator shortcut_fixed_targets shortcut_test_size \
  shortcut_forged_fields shortcut_score_file shortcut_nan shortcut_infinity \
  shortcut_null shortcut_empty_selected \
  weaker_constant_same_items better_more_items weaker_random_policy
do
  if [ -f "redteam/$variant/status.json" ]; then
    echo "AUDIT: $variant already completed; preserving its test result"
    continue
  fi
  echo "AUDIT: $variant"
  bash "redteam/$variant/run.sh"
done
python redteam/summarize.py
