#!/usr/bin/env bash
# Wave-2 fleet submission for the row-8 comparator-H screen (issue #458): every request whose
# report is still absent after the interrupted first wave, submitted per results dir with
#   klt sim --batch-set <pending> --backend batch --format json --wait-for-capacity 600
# (host rule: batch fleet only, capacity wait).  A pre-existing set-manifest.json (wave 1) is
# preserved as set-manifest-wave1.json before klt rewrites it.  Idempotent: requests that already
# have reports are skipped, so re-running the script resumes.  Progress -> wave2-driver.log.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/wave2-driver.log"
exec >>"$LOG" 2>&1
echo "=== wave2 driver start $(date -u +%FT%TZ) pid $$"
rc_all=0
for spec in \
    "t70/delay" "t70/startup" \
    "t55/iq" "t55/delay" "t55/startup" \
    "t40/iq" "t40/delay" "t40/startup" \
    "l06/iq" "l06/delay" "l06/startup" \
    "t70l06/iq" "t70l06/delay" "t70l06/startup" ; do
  d="$HERE/$spec"
  [ -d "$d" ] || { echo "!! no dir $spec"; continue; }
  pend=()
  for r in "$d"/request_*.json; do
    [ -f "${r%.json}/report.json" ] || pend+=("$(basename "$r")")
  done
  if [ "${#pend[@]}" -eq 0 ]; then echo "--- $spec: nothing pending"; continue; fi
  echo "--- $spec: submitting ${#pend[@]} request(s): ${pend[*]}"
  [ -f "$d/set-manifest.json" ] && [ ! -f "$d/set-manifest-wave1.json" ] && cp "$d/set-manifest.json" "$d/set-manifest-wave1.json"
  ( cd "$d" && klt sim --batch-set "${pend[@]}" --backend batch --format json \
      --wait-for-capacity 600 -o "$PWD" --report-out "$PWD/batch-set-wave2.json" \
      > "$PWD/batch-wave2.log" 2> "$PWD/batch-wave2.err" )
  rc=$?
  echo "$rc" > "$d/exit-code-wave2.txt"
  echo "--- $spec: klt exit $rc"
  [ "$rc" -ne 0 ] && rc_all=$rc
done
echo "=== wave2 driver done $(date -u +%FT%TZ) rc_all=$rc_all"
echo "DONE-$rc_all" > "$HERE/wave2-driver.done"
