#!/usr/bin/env bash
# Item-6 Monte Carlo groundwork bench (issue #77): fixed-code reference,
# zero-mismatch control, and a 5-sample mismatch smoke run, each expressed as
# a `klt sim` request (so the multi-unit ones go to the batch fleet on a host
# that exports KLT_SIM_BACKEND=batch).  This script never launches a local
# ngspice loop.  Results go to a NEW sim/mc-groundwork/results/<runid>/
# (append-only; refuses to reuse a non-empty run directory).
#
# Usage: sim/mc-groundwork/run-groundwork.sh [--backend local|batch]
#   (--backend is forwarded to klt sim; default is the host's KLT_SIM_BACKEND)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ARGS=("$@")
python3 "$HERE/gen_bench.py"
RUNID="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HERE/results/$RUNID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
mkdir -p "$OUT"
cp "$HERE"/tb_*.spice "$HERE"/request_*.json "$OUT"/
cd "$OUT"
rc=0
for name in ref_codes control_nomm smoke_mm; do
  # absolute -o: a relative outdir makes klt sim never start ngspice (klayout-tools#2892)
  klt sim "request_${name}.json" --format json -o "$OUT/art_${name}" "${BACKEND_ARGS[@]}" \
    > "report_${name}.json" || rc=$?
done
echo "run id: $RUNID  (klt sim exit 3 = a declared limit failed; none are declared here)"
exit $rc
