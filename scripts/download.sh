#!/bin/bash
set -euo pipefail

# Estimated download size: 16 MB
# Estimated disk usage after extraction: 157 MB

cd /home/user

mkdir -p data/downloads tmp

if [ ! -e data/downloads/atlas_response_matrices/data/clean_response_matrix_winogrande.csv ]; then
  rm -rf tmp/ATLAS_download tmp/ATLAS_download.zip data/downloads/atlas_response_matrices
  git clone --depth 1 https://github.com/Peiyu-Georgia-Li/ATLAS.git tmp/ATLAS_download
  unzip -q tmp/ATLAS_download/data.zip -d data/downloads/atlas_response_matrices
  rm -rf tmp/ATLAS_download
fi
