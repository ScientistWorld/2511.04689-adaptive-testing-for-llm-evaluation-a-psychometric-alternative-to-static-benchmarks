#!/bin/bash
set -euo pipefail

cd /home/user

if [ "$#" -eq 0 ]; then
  mapfile -t manifests < <(find checkpoints -mindepth 2 -maxdepth 2 -name manifest.json | sort)
  if [ "${#manifests[@]}" -eq 0 ]; then
    echo "No checkpoint manifests found under checkpoints/*/manifest.json" >&2
    exit 1
  fi
  set -- "${manifests[@]}"
fi

python eval/train/evaluate.py --manifest "$@" --output scoring/scores_train.json
