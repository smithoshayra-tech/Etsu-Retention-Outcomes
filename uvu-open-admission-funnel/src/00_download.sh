#!/usr/bin/env bash
# Download the public IPEDS files used by this project (NCES Data Center).
# Run from the project folder. Files land in raw/ and data/.
set -euo pipefail
BASE=https://nces.ed.gov/ipeds/datacenter/data
mkdir -p raw data
for f in ADM2014 ADM2015 ADM2016 ADM2017 ADM2018 ADM2019 ADM2020 ADM2021 ADM2022 ADM2023 HD2023 EF2022C; do
  curl -sS -o "raw/$f.zip" "$BASE/$f.zip"
  mkdir -p "data/$f"
  unzip -o -q "raw/$f.zip" -d "data/$f"
done
echo "downloaded"
