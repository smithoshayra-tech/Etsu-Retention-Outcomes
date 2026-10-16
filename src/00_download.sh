#!/usr/bin/env bash
# Download IPEDS complete data files (2013-2023) and the data dictionaries.
# 2024 files (EF2024D, GR2024) did not resolve at $BASE/<name>.zip when this was built.
# Download them from the IPEDS Complete Data Files page (Year 2024) and unzip the CSVs to
# extract/EF2024D/ef2024d.csv and extract/GR2024/gr2024.csv before running run_all.sh.
# Needs network access to nces.ed.gov. Run from the project root.
set -euo pipefail
mkdir -p data_raw extract dict
BASE=https://nces.ed.gov/ipeds/datacenter/data
curl -fsS -o data_raw/HD2023.zip "$BASE/HD2023.zip"
for y in $(seq 2013 2023); do
  for f in EF${y}D GR${y}; do curl -fsS -o data_raw/${f}.zip "$BASE/${f}.zip"; done
done
for z in data_raw/*.zip; do n=$(basename "$z" .zip); mkdir -p "extract/$n"; unzip -oq "$z" -d "extract/$n"; done
for f in HD2023 EF2023D GR2023; do
  curl -fsS -o dict/${f}_Dict.zip "$BASE/${f}_Dict.zip"; mkdir -p dict/$f; unzip -oq dict/${f}_Dict.zip -d dict/$f
done
echo "done"
