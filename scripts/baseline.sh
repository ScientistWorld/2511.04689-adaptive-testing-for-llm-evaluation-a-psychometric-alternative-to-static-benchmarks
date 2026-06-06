#!/bin/bash
set -euo pipefail

cd /home/user

args=(
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc
  --num-items 100
  --output-dir checkpoints/random_static
)

if [ "${ATLAS_TEST_LENGTH:-}" != "" ]; then
  args+=(--test-length "$ATLAS_TEST_LENGTH")
fi

python baseline/random_static.py "${args[@]}"

bash scripts/evaluate.sh checkpoints/random_static/manifest.json
