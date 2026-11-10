#!/usr/bin/env bash
# Grade finished item-6 campaign runs with `klt yield` (pinned klt) and write
# the control summary into a NEW results directory.  Offline: reads committed
# `klt sim` reports, runs no simulator, copies no report (sources.txt records
# each report's path and sha256).
# Usage: sim/mc/grade.sh <new-gradeid> <results/runid dir> [<results/runid dir> ...]
#   reports are found by name (report_<case>.json) in the listed run dirs.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRADEID="${1:?usage: grade.sh <new-gradeid> <run dir> [<run dir> ...]}"; shift
OUT="$HERE/results/$GRADEID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
PIN="klayout-tools[yield]==0.8.0"
find_report() {  # case -> path of report_<case>.json in the first run dir that has it
  for d in "$@"; do [[ -f "$d/report_${CASE}.json" ]] && { echo "$d/report_${CASE}.json"; return; }; done
}
mkdir -p "$OUT"; cp "$HERE/limits_main.json" "$OUT/"
: > "$OUT/sources.txt"
for p in tt ff ss; do
  for kind in main inflated; do
    CASE="${kind}_${p}"; f="$(find_report "$@")"
    [[ -n "$f" ]] || { echo "missing report_${CASE}.json" >&2; exit 1; }
    echo "$(sha256sum "$f" | cut -d' ' -f1)  ${f#"$HERE/../../"}" >> "$OUT/sources.txt"
    eval "R_${kind}_${p}=$f"
  done
  m="R_main_${p}"; c="R_inflated_${p}"
  uvx --from "$PIN" klt yield-samples "${!m}" --negative-control "${!c}" \
    --description "same seed 20261008, sw_stat_mismatch=3: MOS and injected mismatch sigma 3x (DR-0022 s3)" \
    --format json > "$OUT/sampleset_${p}.json"
  # one klt yield report per (process, row set): row 2 = S1, row 4 = S2, row 5 = S3
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$OUT/limits_main.json" \
    --measurement s1_resid_abs_pct,s1_headroom --format json > "$OUT/yield_${p}_row2.json" || true
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$OUT/limits_main.json" \
    --measurement s2_margin_pct --format json > "$OUT/yield_${p}_row4.json" || true
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$OUT/limits_main.json" \
    --measurement s3_margin_pct --format json > "$OUT/yield_${p}_row5.json" || true
done
for c in zero_tt zero_ff zero_ss sens1_tt sens10_tt; do
  CASE="$c"; f="$(find_report "$@")"
  [[ -n "$f" ]] && echo "$(sha256sum "$f" | cut -d' ' -f1)  ${f#"$HERE/../../"}" >> "$OUT/sources.txt"
done
python3 -I "$HERE/analyze.py" "$OUT" "$@" > "$OUT/summary.md"
echo "wrote $OUT"
