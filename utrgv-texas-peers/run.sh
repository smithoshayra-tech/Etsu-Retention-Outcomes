#!/usr/bin/env bash
# Run from this folder. Needs network access to nces.ed.gov for the first step.
set -euo pipefail
cd "$(dirname "$0")"
bash src/00_download.sh
python3 -I src/01_build_db.py
python3 -I src/02_quality_checks.py
python3 -I src/03_compare.py
python3 src/04_chart.py
