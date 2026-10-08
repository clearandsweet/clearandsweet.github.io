#!/usr/bin/env bash
# Rebuild every table and the report from already-scraped data. Usage: scripts/run_all.sh DATADIR TEMPLATE OUT_HTML
set -euo pipefail
D=${1:-data}; TPL=${2:-$(dirname "$0")/report_template.html}; OUT=${3:-index.html}
S=$(dirname "$0")
python3 -I "$S/build_dataset.py" "$D"
python3 -I "$S/meta_analysis.py" "$D" > /dev/null
python3 -I "$S/models.py" "$D" CUR 250 all > "$D/out/models_CUR.log"
python3 -I "$S/models.py" "$D" CUR 250 day2 > "$D/out/models_CUR_day2.log"
python3 -I "$S/damage_model.py" "$D" CUR > "$D/out/damage_CUR.log"
python3 -I "$S/rotation_analysis.py" "$D" CUR > "$D/out/rotation_CUR.log"
python3 -I "$S/rankings.py" "$D" CUR > /dev/null
python3 -I "$S/jp_analysis.py" "$D" CUR > "$D/out/jp.log"
python3 -I "$S/build_report.py" "$D" "$TPL" "$OUT"
