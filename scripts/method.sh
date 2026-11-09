#!/bin/bash
set -euo pipefail

cd /home/user

# ATLAS needs no training: the calibrated item bank is given, and the adaptive
# test runs inside the evaluators' sessions. This writes the manifest that maps
# each operating-point slot to the policy command (paper SE thresholds
# 0.1 / 0.2 / 0.3, 30-500 items, randomesque top-5, EAP).
rm -rf checkpoints/atlas_python
mkdir -p checkpoints/atlas_python
cat > checkpoints/atlas_python/manifest.json <<'JSON'
{
  "method": "ATLAS",
  "slots": {
    "ATLAS_0.1": {"command": ["python", "method/atlas_policy.py", "--se-threshold", "0.1"]},
    "ATLAS_0.2": {"command": ["python", "method/atlas_policy.py", "--se-threshold", "0.2"]},
    "ATLAS_0.3": {"command": ["python", "method/atlas_policy.py", "--se-threshold", "0.3"]}
  }
}
JSON
echo "wrote checkpoints/atlas_python/manifest.json"
