#!/bin/bash
set -euo pipefail

cd /home/user

# Visible split: same protocol, budgets, gates and metrics as the hidden test,
# over the visible model identities in data/. Scans checkpoints/ for
# manifest.json files unless manifest files/directories are given.
# Development options (forwarded): --benchmarks, --slots, --limit N.
python eval/train/evaluate.py "$@" --output scoring/scores_train.json
