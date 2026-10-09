#!/usr/bin/env bash
# Rebuild every table and the report from already-scraped data. Usage: scripts/run_all.sh DATADIR TEMPLATE OUT_HTML
set -euo pipefail
D=${1:-data}; TPL=${2:-report/template.html}; OUT=${3:-index.html}
S=$(dirname "$0")
python3 -I "$S/build_dataset.py" "$D"
python3 -I "$S/meta_analysis.py" "$D" > /dev/null
python3 -I "$S/features.py" "$D" 300 > "$D/out/features.log"          # per-list resource vectors (all events)
python3 -I "$S/dimret.py" "$D" 40 500 > "$D/out/dimret.log"           # simulated uses at 1-4 copies
python3 "$S/regress.py" "$D" > "$D/out/regress.log"                   # fitted CE weights (needs statsmodels)
python3 -I "$S/ce_cv.py" "$D" > "$D/out/ce_cv.log"                    # out-of-sample test of hand-set vs fitted weights
python3 "$S/cardcount.py" "$D" 40 > "$D/out/cardcount.log"            # copy-count effects within archetypes
python3 -I "$S/models.py" "$D" CUR 250 all > "$D/out/models_CUR.log"
python3 -I "$S/models.py" "$D" CUR 250 day2 > "$D/out/models_CUR_day2.log"
python3 -I "$S/damage_model.py" "$D" CUR > "$D/out/damage_CUR.log"
python3 -I "$S/power.py" "$D" > "$D/out/power.log"                    # Card / Deck Power for every list
python3 -I "$S/power_eval.py" "$D" CUR > "$D/out/power_eval.log"      # Power tables + validation vs results
python3 -I "$S/rotation_analysis.py" "$D" CUR > "$D/out/rotation_CUR.log"
python3 -I "$S/rankings.py" "$D" CUR > /dev/null
python3 -I "$S/jp_analysis.py" "$D" CUR > "$D/out/jp.log"
python3 -I "$S/build_report.py" "$D" "$TPL" "$OUT"
