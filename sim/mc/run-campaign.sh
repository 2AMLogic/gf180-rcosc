#!/usr/bin/env bash
# Item-6 Monte Carlo campaign driver (issue #202; DR-0019, DR-0022).
# Every case is a `klt sim` Monte Carlo request submitted to the batch fleet
# (sharded); this script never launches a local ngspice loop.  If a submit
# fails, the failure is kept in the run directory and reported -- no case is
# re-run locally.  Results go to a NEW results/<runid>/ (append-only; refuses
# to reuse a non-empty run directory).  Grading (`klt yield`) is grade.sh.
#
# Usage: sim/mc/run-campaign.sh [--dut <netlist>] <runid> [case ...]
#   --dut    DUT netlist other than the default DR-0023 P3 one (issue #236). The benches
#            and requests are then generated straight into the new results/<runid>/ and
#            the top-level sim/mc/tb_*.spice / request_*.json are left untouched; the DUT
#            path and sha256 are recorded in <runid>/dut.txt.
#   <runid>  UTC stamp for the new results directory, e.g. 20261106T060000Z
#   case     any of: main_tt main_ff main_ss inflated_tt inflated_ff inflated_ss sens1_tt sens10_tt senszero_tt zero_ff zero_ss
#            (default: all of them, in that order)
#   --pilot N  issue #461 control pilot (needs --dut): N draws per corner, seeded-defect cases
#              ctrlr2_<p> / ctrlr45_<p>, finer-timing sensitivity arms, limits_pilot.json
#   --derive   issue #461 defect-magnitude derivation sweep (needs --dut), zero mismatch
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUT=""; PILOT=""; DERIVE=""
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --dut) DUT="${2:?--dut needs a netlist path}"; shift 2 ;;
    --pilot) PILOT="${2:?--pilot needs a draw count}"; shift 2 ;;
    --derive) DERIVE=1; shift ;;
    *) echo "ERROR: unknown option $1" >&2; exit 1 ;;
  esac
done
RUNID="${1:?usage: run-campaign.sh <runid> [case ...]}"; shift
CASES=("$@")
GEN_ARGS=()
[[ -n "$PILOT" ]] && GEN_ARGS+=(--pilot "$PILOT")
[[ -n "$DERIVE" ]] && GEN_ARGS+=(--derive)
if [[ -n "$PILOT" || -n "$DERIVE" ]]; then
  [[ -n "$DUT" ]] || { echo "ERROR: --pilot/--derive need an explicit --dut" >&2; exit 1; }
fi
[[ ${#CASES[@]} -eq 0 && -n "$DERIVE" ]] && CASES=(__all_derive__)
[[ ${#CASES[@]} -eq 0 && -n "$PILOT" ]] && CASES=(main_tt main_ff main_ss inflated_tt inflated_ff inflated_ss ctrlr2_tt ctrlr2_ff ctrlr2_ss ctrlr45_tt ctrlr45_ff ctrlr45_ss zero_tt zero_ff zero_ss sens1_tt sens10_tt senszero_tt sens1fine_tt sens10fine_tt senszerofine_tt)
[[ ${#CASES[@]} -eq 0 ]] && CASES=(main_tt main_ff main_ss inflated_tt inflated_ff inflated_ss sens1_tt sens10_tt senszero_tt zero_ff zero_ss)
OUT="$HERE/results/$RUNID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
if [[ -n "$DUT" ]]; then
  [[ -f "$DUT" ]] || { echo "ERROR: DUT $DUT not found" >&2; exit 1; }
  mkdir -p "$OUT"
  python3 -I "$HERE/gen_campaign.py" --dut "$DUT" --out "$OUT" "${GEN_ARGS[@]}"
  echo "$(sha256sum "$DUT" | cut -d' ' -f1)  $DUT" > "$OUT/dut.txt"
else
  python3 -I "$HERE/gen_campaign.py"
  mkdir -p "$OUT"
  cp "$HERE"/tb_*.spice "$HERE"/request_*.json "$HERE"/limits_*.json "$HERE"/mismatch-manifest.json "$OUT"/
fi
cd "$OUT"
rc=0
if [[ "${CASES[0]}" == "__all_derive__" ]]; then
  CASES=(); for f in request_derive_*.json; do f="${f#request_}"; CASES+=("${f%.json}"); done
fi
for c in "${CASES[@]}"; do
  # absolute -o (klayout-tools#2892); explicit batch backend; units per job sized so that
  # timeout_s x units + 120 stays under the 3600 s fleet ceiling (25 at 120 s, 7 at 480 s); <= 8 jobs in flight
  T="$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))['options']['timeout_s'])" "request_${c}.json")"
  UPJ=$(( (3600 - 120) / T )); [[ $UPJ -gt 25 ]] && UPJ=25
  KLT_SIM_BACKEND=batch klt sim "request_${c}.json" --backend batch --format json \
    --max-units-per-job "$UPJ" --max-concurrent-jobs 8 --wait-for-capacity 600 \
    -o "$OUT/art_${c}" > "report_${c}.json" 2> "stderr_${c}.txt"
  r=$?
  echo "$c exit=$r" | tee -a exit-codes.txt
  [[ $r -ne 0 ]] && rc=$r
done
echo "run id: $RUNID  (klt sim exit 3 = a declared limit failed; none are declared in the requests)"
exit $rc
