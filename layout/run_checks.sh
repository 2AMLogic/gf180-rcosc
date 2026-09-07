#!/usr/bin/env bash
# run_checks.sh -- rebuild layout/cells/*.gds and regenerate the committed
# DRC/extract/LVS evidence under layout/reports/ (issue #13).
#
#   layout/run_checks.sh
#
# PDK_ROOT is resolved automatically via `klt pdk find --pdk gf180mcuC` if
# not already set (same convention as design/regen-netlist.sh).
set -euo pipefail

LAYOUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$LAYOUT_DIR/.." && pwd)"
CELLS_DIR="$LAYOUT_DIR/cells"
LVS_REF_DIR="$LAYOUT_DIR/lvs_ref"
REPORTS_DIR="$LAYOUT_DIR/reports"

mkdir -p "$REPORTS_DIR"

echo "== regenerating design/netlist (source of truth for device geometry) =="
"$REPO_ROOT/design/regen-netlist.sh"

echo "== building layout/cells/*.gds from klt gen primitives =="
python3 "$LAYOUT_DIR/build_cells.py"

declare -A PINS=(
  [rcosc_bias]="vdd,vh,vl,vss,ibias"
  [rcosc_trim_bank]="p,m,t0,t1,t2,t3,t4,t5,t6,t7"
)
declare -A TOLERANCE=(
  [rcosc_bias]=""
  [rcosc_trim_bank]="0.001"
)

for cell in rcosc_bias rcosc_trim_bank; do
  gds="$CELLS_DIR/$cell.gds"
  ref="$LVS_REF_DIR/$cell.spice"
  extracted="$REPORTS_DIR/$cell.extracted.spice"

  echo "== $cell: DRC =="
  klt drc "$gds" --deck gf180mcu --format json > "$REPORTS_DIR/$cell.drc.json"
  python3 -c "
import json, sys
d = json.load(open('$REPORTS_DIR/$cell.drc.json'))
assert d['status'] == 'clean', f\"$cell DRC not clean: {d['violation_count']} violation(s)\"
print('$cell DRC: clean')
"

  echo "== $cell: extract =="
  klt extract "$gds" --deck gf180mcu --deck-option poly_res=1k \
    --pins "${PINS[$cell]}" --format json -o "$extracted" \
    > "$REPORTS_DIR/$cell.extract.json"

  echo "== $cell: LVS =="
  tolerance="${TOLERANCE[$cell]}"
  if [ -n "$tolerance" ]; then
    options_json="{\"parameter_tolerance\": $tolerance}"
  else
    options_json="{}"
  fi
  request=$(python3 -c "
import json
print(json.dumps({
    'layout': {'netlist': '$extracted', 'top': '$cell'},
    'reference': {'netlist': '$ref', 'top': '$cell', 'form': 'subckt-call', 'deck': 'gf180mcu'},
    'options': $options_json,
}))
")
  klt lvs "$request" --format json > "$REPORTS_DIR/$cell.lvs.json"
  python3 -c "
import json
d = json.load(open('$REPORTS_DIR/$cell.lvs.json'))
assert d['status'] == 'match', f\"$cell LVS not a match: {d.get('category_counts')}\"
print('$cell LVS: match', d.get('category_counts') or '(no tolerated deltas)')
"
done

echo "== all checks passed =="
