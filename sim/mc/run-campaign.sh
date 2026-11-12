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
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUT=""
if [[ "${1:-}" == "--dut" ]]; then DUT="${2:?--dut needs a netlist path}"; shift 2; fi
RUNID="${1:?usage: run-campaign.sh <runid> [case ...]}"; shift
CASES=("$@")
[[ ${#CASES[@]} -eq 0 ]] && CASES=(main_tt main_ff main_ss inflated_tt inflated_ff inflated_ss sens1_tt sens10_tt senszero_tt zero_ff zero_ss)
OUT="$HERE/results/$RUNID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
if [[ -n "$DUT" ]]; then
  [[ -f "$DUT" ]] || { echo "ERROR: DUT $DUT not found" >&2; exit 1; }
  mkdir -p "$OUT"
  python3 -I "$HERE/gen_campaign.py" --dut "$DUT" --out "$OUT"
  echo "$(sha256sum "$DUT" | cut -d' ' -f1)  $DUT" > "$OUT/dut.txt"
else
  python3 -I "$HERE/gen_campaign.py"
  mkdir -p "$OUT"
  cp "$HERE"/tb_*.spice "$HERE"/request_*.json "$HERE"/limits_*.json "$HERE"/mismatch-manifest.json "$OUT"/
fi
cd "$OUT"
rc=0
for c in "${CASES[@]}"; do
  # absolute -o (klayout-tools#2892); explicit batch backend; 25 units per job, <= 8 jobs in flight
  KLT_SIM_BACKEND=batch klt sim "request_${c}.json" --backend batch --format json \
    --max-units-per-job 25 --max-concurrent-jobs 8 --wait-for-capacity 600 \
    -o "$OUT/art_${c}" > "report_${c}.json" 2> "stderr_${c}.txt"
  r=$?
  echo "$c exit=$r" | tee -a exit-codes.txt
  [[ $r -ne 0 ]] && rc=$r
done
echo "run id: $RUNID  (klt sim exit 3 = a declared limit failed; none are declared in the requests)"
exit $rc
