#!/usr/bin/env bash
# Rebuild everything from the downloaded IPEDS files. Run from the project folder.
set -euo pipefail
ROOT="$(pwd)"
python3 -I src/01_build_db.py "$ROOT"
python3 -I - "$ROOT" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1] + "/outputs/ipeds_uvu.db")
con.executescript(open(sys.argv[1] + "/sql/01_views.sql").read())
con.commit()
PY
python3 -I src/02_simulate_funnel.py "$ROOT"
python3 -I src/04_adm_coverage.py "$ROOT"
python3 -I src/03_run_analysis.py "$ROOT" | tee outputs/run_log.txt
