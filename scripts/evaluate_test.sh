#!/bin/bash
set -euo pipefail

cd /home/user

# Hidden test: runs every method on disk (each checkpoints/**/manifest.json
# claims operating-point slots with a policy command) against the
# evaluator-owned response oracle of the held-out identities in eval/test/.
# Optional arguments: manifest files or directories to scan instead.
python eval/test/evaluate.py "$@" --output scoring/scores_test.json
