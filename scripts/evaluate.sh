#!/bin/bash
set -euo pipefail

cd /home/user

if [ "$#" -eq 0 ]; then
  set -- checkpoints/atlas_python/manifest.json checkpoints/random_static/manifest.json
fi

python eval/evaluate_atlas.py --manifest "$@" --output scoring/scores.json
