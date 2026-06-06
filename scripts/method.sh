#!/bin/bash
set -euo pipefail

cd /home/user

python method/atlas_runner.py \
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc \
  --se-thresholds 0.1 0.2 0.3 \
  --test-length "${ATLAS_TEST_LENGTH:-150}" \
  --output-dir checkpoints/atlas_python

bash scripts/evaluate.sh checkpoints/atlas_python/manifest.json
