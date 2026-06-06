#!/bin/bash
set -euo pipefail

cd /home/user

# Full five-benchmark CPU reproduction. Set ATLAS_TEST_LENGTH before
# invoking this script to run a bounded smoke test.

bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate.sh checkpoints/random_static/manifest.json checkpoints/atlas_python/manifest.json
python validate.py --compare
