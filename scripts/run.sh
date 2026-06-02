#!/bin/bash
set -euo pipefail

cd /home/user

export ATLAS_TEST_LENGTH=180

bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate.sh checkpoints/random_static/manifest.json checkpoints/atlas_python/manifest.json
python validate.py --compare
