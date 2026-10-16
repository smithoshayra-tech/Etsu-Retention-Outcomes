#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -I src/01_build_db.py
python3 -I src/02_quality_checks.py
python3 -I src/03_dq_log.py
python3 -I src/04_model.py
python3 -I src/05_export_dashboard.py
python3 -I src/06_charts.py
python3 -I src/07_build_readme.py
