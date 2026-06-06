#!/bin/bash
set -euo pipefail

cd /home/user

# CPU scheduler jobs are currently capped at one hour. This bounded default
# improves on the validated 750-model run while keeping the job runnable.
# Set ATLAS_TEST_LENGTH=full to run every available response-matrix row.
export ATLAS_TEST_LENGTH="${ATLAS_TEST_LENGTH:-1500}"
echo "ATLAS_TEST_LENGTH=${ATLAS_TEST_LENGTH}"

bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate.sh checkpoints/random_static/manifest.json checkpoints/atlas_python/manifest.json
python validate.py --compare
