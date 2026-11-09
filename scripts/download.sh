#!/bin/bash
set -euo pipefail

# Fetches the public ATLAS response matrices (Open LLM Leaderboard item
# responses) and keeps the rows of the *visible* model identities only, i.e.
# the identities listed in data/calibrated_banks/<benchmark>/irt_person_scores_WLE_SE.csv.
# Held-out identities are evaluator-owned (eval/test/) and are dropped here.
#
# Estimated download size: 16 MB; disk usage after filtering: ~37 MB.

cd /home/user

ZIP_URL="https://github.com/Peiyu-Georgia-Li/ATLAS/raw/e2f1975f21862603ff26717b19b7a9732686abe7/data.zip"
ZIP_SHA256="1125f9b64ef43e1ccc6deb1e5760cfb63124c5ab1db9b0e73a76772de026db63"
OUT_DIR=data/downloads/atlas_response_matrices/data
MARKER=data/downloads/atlas_response_matrices/.complete-visible-v2
BENCHMARKS=(truthfulqa winogrande hellaswag gsm8k arc)

mkdir -p data/downloads tmp

complete=true
[ -e "$MARKER" ] || complete=false
for b in "${BENCHMARKS[@]}"; do
  [ -s "$OUT_DIR/clean_response_matrix_${b}.csv" ] || complete=false
done
if [ "$complete" = true ]; then
  echo "[download] visible response matrices already present"
  exit 0
fi

work=tmp/atlas_download
rm -rf "$work" data/downloads/atlas_response_matrices
mkdir -p "$work" "$OUT_DIR"
curl -L --fail --retry 3 "$ZIP_URL" -o "$work/data.zip"
echo "${ZIP_SHA256}  $work/data.zip" | sha256sum -c -
unzip -q "$work/data.zip" -d "$work/unzipped"

python3 -I - "$work/unzipped/data" "$OUT_DIR" "${BENCHMARKS[@]}" <<'PY'
import csv, sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
expected = {
    "truthfulqa": "db72ba4c04f837d241bbe782c3f36e7370bc18dda94893798cd76dc00b83d6a1",
    "winogrande": "c7c22110b6acede504fa881b221a4d347f1676a17cece5108a1856a6935f7448",
    "hellaswag": "4e597f70e7799f0f27ec9647baa2c7a129239fa53164dea881bf214e3ad292ba",
    "gsm8k": "e1e3199be643ee6732fd745ad2d129d9c61809f4e4927c74b9fa2a9f1d36cfd0",
    "arc": "2fd77ceaa5e82c771df262362584338ec77fe7aa4db42e6889aa15213d604a12",
}
import hashlib
for bench in sys.argv[3:]:
    path = src / f"clean_response_matrix_{bench}.csv"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected[bench]:
        raise SystemExit(f"checksum mismatch for {path}")
    with open(f"data/calibrated_banks/{bench}/irt_person_scores_WLE_SE.csv", newline="") as f:
        visible = {row["Model_Name"] for row in csv.DictReader(f)}
    kept = 0
    with path.open(newline="") as fin, (out / path.name).open("w", newline="") as fout:
        header = fin.readline()
        fout.write(header)
        for line in fin:
            name = next(csv.reader([line]))[0]
            if name in visible:
                fout.write(line)
                kept += 1
    if kept != len(visible):
        raise SystemExit(f"{bench}: kept {kept} rows but {len(visible)} visible identities are listed")
    print(f"[download] {bench}: kept {kept} visible model rows")
PY

touch "$MARKER"
rm -rf "$work"
