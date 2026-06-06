#!/bin/bash
set -euo pipefail

cd /home/user

manifests=()
if [ "$#" -eq 0 ]; then
  set -- checkpoints
fi

for target in "$@"; do
  if [ -d "$target" ]; then
    while IFS= read -r manifest; do
      manifests+=("$manifest")
    done < <(find "$target" -mindepth 1 -maxdepth 3 -name manifest.json | sort)
  elif [ -f "$target" ]; then
    manifests+=("$target")
  else
    echo "Checkpoint target not found: $target" >&2
    exit 1
  fi
done

if [ "${#manifests[@]}" -eq 0 ]; then
  echo "No checkpoint manifests found" >&2
  exit 1
fi

python eval/test/evaluate.py --manifest "${manifests[@]}" --output scoring/scores_test.json --train-scores scoring/scores_train.json
