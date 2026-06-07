#!/bin/bash
set -euo pipefail

# Estimated download size: 16 MB
# Estimated disk usage after extraction: 157 MB

cd /home/user

mkdir -p data/downloads tmp

required_response_files=(
  data/downloads/atlas_response_matrices/data/clean_response_matrix_truthfulqa.csv
  data/downloads/atlas_response_matrices/data/clean_response_matrix_winogrande.csv
  data/downloads/atlas_response_matrices/data/clean_response_matrix_hellaswag.csv
  data/downloads/atlas_response_matrices/data/clean_response_matrix_gsm8k.csv
  data/downloads/atlas_response_matrices/data/clean_response_matrix_arc.csv
)

download_complete=true
if [ ! -e data/downloads/atlas_response_matrices/.complete ]; then
  download_complete=false
else
  for required_file in "${required_response_files[@]}"; do
    if [ ! -s "$required_file" ]; then
      download_complete=false
      break
    fi
  done
fi

if [ "$download_complete" = false ]; then
  rm -rf tmp/ATLAS_data.zip tmp/atlas_response_matrices_new data/downloads/atlas_response_matrices
  mkdir -p tmp/atlas_response_matrices_new
  curl -L --fail https://github.com/Peiyu-Georgia-Li/ATLAS/raw/main/data.zip -o tmp/ATLAS_data.zip
  unzip -q tmp/ATLAS_data.zip -d tmp/atlas_response_matrices_new
  mv tmp/atlas_response_matrices_new data/downloads/atlas_response_matrices
  for required_file in "${required_response_files[@]}"; do
    test -s "$required_file"
  done
  touch data/downloads/atlas_response_matrices/.complete
  rm -f tmp/ATLAS_data.zip
fi
