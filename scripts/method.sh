#!/bin/bash
set -euo pipefail

cd /home/user

args=(
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc
  --se-thresholds 0.1 0.2 0.3
  --output-dir checkpoints/atlas_python
)

if [ "${ATLAS_TEST_LENGTH:-}" != "" ]; then
  if [ "$ATLAS_TEST_LENGTH" != "full" ]; then
    args+=(--test-length "$ATLAS_TEST_LENGTH")
  fi
fi

rm -rf checkpoints/atlas_python
python method/atlas_runner.py "${args[@]}"

bash scripts/evaluate.sh checkpoints/atlas_python/manifest.json
