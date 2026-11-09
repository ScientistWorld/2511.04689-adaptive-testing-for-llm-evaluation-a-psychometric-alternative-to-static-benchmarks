#!/bin/bash
set -euo pipefail

cd /home/user

# Reproduction score on the visible split (same evaluator as evaluate_train.sh),
# written to scoring/scores.json.
python eval/train/evaluate.py "$@" --output scoring/scores.json
