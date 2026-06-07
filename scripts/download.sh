#!/bin/bash
set -euo pipefail

# Estimated download size: 16 MB
# Estimated disk usage after extraction: 157 MB

cd /home/user

mkdir -p data/downloads tmp

if [ ! -e data/downloads/atlas_response_matrices/data/clean_response_matrix_winogrande.csv ]; then
  rm -rf tmp/ATLAS_data.zip data/downloads/atlas_response_matrices
  curl -L --fail https://github.com/Peiyu-Georgia-Li/ATLAS/raw/main/data.zip -o tmp/ATLAS_data.zip
  unzip -q tmp/ATLAS_data.zip -d data/downloads/atlas_response_matrices
  rm -f tmp/ATLAS_data.zip
fi
