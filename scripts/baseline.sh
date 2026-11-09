#!/bin/bash
set -euo pipefail

cd /home/user

# Static random subset at each slot's item budget, scored on the visible split.
# (The Random100 row in every score file is computed by the evaluator itself.)
mkdir -p checkpoints
python eval/train/evaluate.py baseline/manifest.json "$@" --output checkpoints/baseline_random_static_scores_train.json
