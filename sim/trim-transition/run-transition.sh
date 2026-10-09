#!/usr/bin/env bash
# Live trim-transition bench (issue #103): regenerate the nine requests and run
# each through `klt sim` (multi-corner -> batch fleet on a host that exports
# KLT_SIM_BACKEND=batch).  Never launches a local ngspice loop.  Output goes to
# a NEW sim/trim-transition/results/<runid>/ (append-only; refuses to reuse one).
# Usage: sim/trim-transition/run-transition.sh [--backend local|batch]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ARGS=("$@")
python3 -I "$HERE/prepare.py"
RUNID="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HERE/results/$RUNID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
mkdir -p "$OUT"
cp "$HERE"/tb_*.spice "$HERE"/request_*.json "$HERE"/schedule_*.json "$HERE"/provenance.json \
   "$HERE"/rcosc_top_schematic.spice "$OUT"/
cd "$OUT"
rc=0
for req in request_v*.json; do
  tag="${req#request_}"; tag="${tag%.json}"
  # absolute -o (klayout-tools#2892); the report is kept even if a submit fails
  klt sim "$req" --format json -o "$OUT/art_${tag}" "${BACKEND_ARGS[@]}" \
    > "report_${tag}.json" 2> "stderr_${tag}.log" || { echo "klt sim failed for $tag (exit $?)" >&2; rc=1; }
done
echo "run id: $RUNID"
exit $rc
