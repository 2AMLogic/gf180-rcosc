#!/usr/bin/env bash
# Grade finished item-6 campaign runs with `klt yield` (pinned klt) and write
# the control summary into a NEW results directory.  Offline: reads committed
# `klt sim` reports, runs no simulator, copies no report (sources.txt records
# each report's path and sha256).
# Usage: sim/mc/grade.sh [--limits <file>] [--zero-ref <spec>] <new-gradeid> <results/runid dir> [...]
#   reports are found by name (report_<case>.json) in the listed run dirs.
#   --limits    limits file for `klt yield` (default limits_main.json).  The issue-#461 pilot
#               passes limits_pilot.json: same limits, only the sample floor is the pilot N.
#   --zero-ref  deterministic reference for the zero-mismatch control, "tt=164:47.91,ff=79:47.97,ss=212:48.04"
#               (code:MHz per process); default is the DR-0023 P3 grid built into analyze.py.
#   When report_ctrlr2_<p>.json / report_ctrlr4_<p>.json / report_ctrlr5_<p>.json exist (the --pilot campaign), each is
#   paired with the nominal through `yield-samples --negative-control` as a SEPARATE grade
#   (sampleset_<p>_ctrlr{2,4,5}.json, yield_<p>_row{2,4,5}_def.json); the 3x grades keep
#   their existing paths.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIMITS="$HERE/limits_main.json"; ZREF=""
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --limits) LIMITS="${2:?--limits needs a file}"; shift 2 ;;
    --zero-ref) ZREF="${2:?--zero-ref needs a spec}"; shift 2 ;;
    *) echo "ERROR: unknown option $1" >&2; exit 1 ;;
  esac
done
GRADEID="${1:?usage: grade.sh <new-gradeid> <run dir> [<run dir> ...]}"; shift
OUT="$HERE/results/$GRADEID"
[[ -e "$OUT" ]] && { echo "ERROR: $OUT exists" >&2; exit 1; }
PIN="klayout-tools[yield]==0.8.0"
find_report() {  # case -> path of report_<case>.json in the first run dir that has it
  for d in "$@"; do [[ -f "$d/report_${CASE}.json" ]] && { echo "$d/report_${CASE}.json"; return; }; done
}
mkdir -p "$OUT"; cp "$LIMITS" "$OUT/"; LIM="$OUT/$(basename "$LIMITS")"
[[ -n "$ZREF" ]] && echo "$ZREF" > "$OUT/zero_ref.txt"
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
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$LIM" \
    --measurement s1_resid_abs_pct,s1_headroom --format json > "$OUT/yield_${p}_row2.json" || true
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$LIM" \
    --measurement s2_margin_pct --format json > "$OUT/yield_${p}_row4.json" || true
  uvx --from "$PIN" klt yield "$OUT/sampleset_${p}.json" --limits "$LIM" \
    --measurement s3_margin_pct --format json > "$OUT/yield_${p}_row5.json" || true
  # issue #461: seeded-defect companions, each paired with the same nominal as its own grade
  for kind in ctrlr2 ctrlr4 ctrlr5; do
    CASE="${kind}_${p}"; f="$(find_report "$@")"; [[ -n "$f" ]] || continue
    echo "$(sha256sum "$f" | cut -d' ' -f1)  ${f#"$HERE/../../"}" >> "$OUT/sources.txt"
    uvx --from "$PIN" klt yield-samples "${!m}" --negative-control "$f" \
      --description "seeded defect (${kind}), same seed 20261008 and draw identities, same probes and grading expressions (DR-0051)" \
      --format json > "$OUT/sampleset_${p}_${kind}.json"
    case "$kind" in
      ctrlr2) meas=s1_resid_abs_pct,s1_headroom; row=2 ;;
      ctrlr4) meas=s2_margin_pct; row=4 ;;
      ctrlr5) meas=s3_margin_pct; row=5 ;;
    esac
    uvx --from "$PIN" klt yield "$OUT/sampleset_${p}_${kind}.json" --limits "$LIM" \
      --measurement "$meas" --format json > "$OUT/yield_${p}_row${row}_def.json" || true
  done
done
for c in zero_tt zero_ff zero_ss sens1_tt sens10_tt senszero_tt sens1fine_tt sens10fine_tt senszerofine_tt; do
  CASE="$c"; f="$(find_report "$@")"
  [[ -n "$f" ]] && echo "$(sha256sum "$f" | cut -d' ' -f1)  ${f#"$HERE/../../"}" >> "$OUT/sources.txt"
done
python3 -I "$HERE/analyze.py" "$OUT" "$@" > "$OUT/summary.md"
echo "wrote $OUT"
