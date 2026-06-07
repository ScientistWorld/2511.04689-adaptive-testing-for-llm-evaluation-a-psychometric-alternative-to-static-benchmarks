#!/bin/bash
set -euo pipefail

cd /home/user

# CPU scheduler jobs are currently capped at one hour. This bounded default
# matches the completed five-benchmark reproduction scale and gives the split
# evaluators 375 visible plus 375 held-out model identities per benchmark.
export ATLAS_TEST_LENGTH="${ATLAS_TEST_LENGTH:-750}"
export ATLAS_EVAL_MODEL_LIMIT="${ATLAS_EVAL_MODEL_LIMIT:-$ATLAS_TEST_LENGTH}"
echo "ATLAS_TEST_LENGTH=${ATLAS_TEST_LENGTH}"
echo "ATLAS_EVAL_MODEL_LIMIT=${ATLAS_EVAL_MODEL_LIMIT}"

baseline_args=(
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc
  --num-items 100
  --output-dir checkpoints/random_static
)
method_args=(
  --benchmarks truthfulqa winogrande hellaswag gsm8k arc
  --se-thresholds 0.1 0.2 0.3
  --output-dir checkpoints/atlas_python
)
if [ "$ATLAS_TEST_LENGTH" != "full" ]; then
  baseline_args+=(--test-length "$ATLAS_TEST_LENGTH")
  method_args+=(--test-length "$ATLAS_TEST_LENGTH")
fi

rm -rf checkpoints/random_static checkpoints/atlas_python
python baseline/random_static.py "${baseline_args[@]}"
python method/atlas_runner.py "${method_args[@]}"

bash scripts/evaluate.sh checkpoints/random_static/manifest.json checkpoints/atlas_python/manifest.json
bash scripts/evaluate_train.sh checkpoints
bash scripts/evaluate_test.sh checkpoints
