#!/usr/bin/env bash
# run_checks.sh -- rebuild layout/cells/*.gds and regenerate the committed
# DRC/extract/LVS evidence under layout/reports/ (issues #13, #27).
#
#   layout/run_checks.sh
#
# Covers all four cells of the hierarchy: the two leaf blocks (rcosc_bias,
# rcosc_trim_bank), the comparator (rcosc_comparator) and the full composition
# (rcosc_top, which instantiates the other three as sub-cells).
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

# `build_cells.py` needs the `klayout` python module and `klayout_tools`
# importable (`klt`'s own runtime dependencies). Prefer a plain `python3` that
# already has them; otherwise fall back to the same `uv run` invocation
# build_cells.py's own docstring documents, so a host with `klt` installed as a
# tool (its dependencies isolated in the tool's venv, invisible to `python3`)
# still runs this script unattended.
if python3 -c "import klayout.db, klayout_tools.gen" >/dev/null 2>&1; then
  PYTHON=(python3)
else
  echo "== python3 has no klayout/klayout_tools -- falling back to uv run =="
  PYTHON=(uv run --with klayout --with klayout-tools python3)
fi

echo "== regenerating design/netlist (source of truth for device geometry) =="
"$REPO_ROOT/design/regen-netlist.sh"

echo "== building layout/cells/*.gds from klt gen primitives =="
"${PYTHON[@]}" "$LAYOUT_DIR/build_cells.py"

CELLS=(rcosc_bias rcosc_trim_bank rcosc_comparator rcosc_top)

declare -A PINS=(
  [rcosc_bias]="vdd,vh,vl,vss,ibias"
  [rcosc_trim_bank]="p,m,t0,t1,t2,t3,t4,t5,t6,t7"
  [rcosc_comparator]="vdd,vss,ibias,inp,inn,out"
  [rcosc_top]="vdd,vss,clk,t0,t1,t2,t3,t4,t5,t6,t7"
)

# Extraction deck flavour selections. `poly_res=1k` is this design's
# `ppolyf_u_1k` timing/trim/threshold resistor (DR-0003 sec 5.1/6.1);
# `mim_cap=cap_mim_1f0_m4m5_noshield` is the 1.0 fF/um^2 MiM density the
# schematic's `cap_mim_1f0fF` commits to. Both are one drawn geometry with
# several PDK-offered interpretations, so neither can be inferred from the
# layout -- the design has to say which one it means.
declare -A DECK_OPTIONS=(
  [rcosc_bias]="--deck-option poly_res=1k"
  [rcosc_trim_bank]="--deck-option poly_res=1k"
  [rcosc_comparator]="--deck-option poly_res=1k"
  [rcosc_top]="--deck-option poly_res=1k --deck-option mim_cap=cap_mim_1f0_m4m5_noshield"
)

# Per-cell `klt lvs` options, each disclosed in the report it produces:
#
#   parameter_tolerance  absorbs the sub-0.1% grid-rounding deltas the 1nm
#                        database unit introduces on the trim bank's short
#                        segments (every tolerated delta is listed with both
#                        original values in the JSON -- see layout/README.md)
#   combine_devices      folds the comparator's 8-finger MTAIL, which extracts
#                        (correctly) as 8 parallel W=2u nfets, back into the
#                        reference's single W=16u device. Scoped to "nfet"
#                        rather than blanket-true so it can never quietly merge
#                        a series resistor pair in the bias divider or trim
#                        bank. Load-bearing, not decorative: without it the
#                        comparator LVS reports 7 unmatched devices.
#   flatten_reference    the reference is written hierarchically (it reads like
#                        the schematic); `klt extract` always emits the layout
#                        side flat, so the reference is flattened to meet it.
declare -A LVS_OPTIONS=(
  [rcosc_bias]='{}'
  [rcosc_trim_bank]='{"parameter_tolerance": 0.001}'
  [rcosc_comparator]='{"combine_devices": ["nfet"]}'
  [rcosc_top]='{"combine_devices": ["nfet"], "flatten_reference": true, "parameter_tolerance": 0.001}'
)

for cell in "${CELLS[@]}"; do
  gds="$CELLS_DIR/$cell.gds"
  ref="$LVS_REF_DIR/$cell.spice"
  extracted="$REPORTS_DIR/$cell.extracted.spice"

  echo "== $cell: DRC =="
  klt drc "$gds" --deck gf180mcu --top "$cell" --format json > "$REPORTS_DIR/$cell.drc.json"
  python3 -c "
import json, sys
d = json.load(open('$REPORTS_DIR/$cell.drc.json'))
assert d['status'] == 'clean', f\"$cell DRC not clean: {d['violation_count']} violation(s)\"
print('$cell DRC: clean')
"

  echo "== $cell: extract =="
  # shellcheck disable=SC2086  # DECK_OPTIONS is a deliberate word-split flag list
  klt extract "$gds" --deck gf180mcu --top "$cell" ${DECK_OPTIONS[$cell]} \
    --pins "${PINS[$cell]}" --format json -o "$extracted" \
    > "$REPORTS_DIR/$cell.extract.json"

  echo "== $cell: LVS =="
  request=$(OPTIONS_JSON="${LVS_OPTIONS[$cell]}" python3 -c "
import json, os
print(json.dumps({
    'layout': {'netlist': '$extracted', 'top': '$cell'},
    'reference': {'netlist': '$ref', 'top': '$cell', 'form': 'subckt-call', 'deck': 'gf180mcu'},
    'options': json.loads(os.environ['OPTIONS_JSON']),
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
