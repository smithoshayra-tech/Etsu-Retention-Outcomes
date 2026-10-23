#!/usr/bin/env bash
# Download the IPEDS complete data files used here (report years 2013-2023) and unzip them.
# The 2024 files (EF2024D, GR2024) did not resolve at this address when this was built.
# Needs network access to nces.ed.gov. Run from the utrgv-texas-peers folder.
set -euo pipefail
mkdir -p data_raw extract
BASE=https://nces.ed.gov/ipeds/datacenter/data
curl -fsS -o data_raw/HD2023.zip "$BASE/HD2023.zip"
for y in $(seq 2013 2023); do
  for f in EF${y}D GR${y}; do curl -fsS -o data_raw/${f}.zip "$BASE/${f}.zip"; done
done
for z in data_raw/*.zip; do n=$(basename "$z" .zip); mkdir -p "extract/$n"; unzip -oq "$z" -d "extract/$n"; done
echo "done"
