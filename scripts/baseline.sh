#!/bin/bash
set -euo pipefail

cd /home/user

python baseline/random_static.py \
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc \
  --test-length "${ATLAS_TEST_LENGTH:-150}" \
  --num-items 100 \
  --output-dir checkpoints/random_static

bash scripts/evaluate.sh checkpoints/random_static/manifest.json
