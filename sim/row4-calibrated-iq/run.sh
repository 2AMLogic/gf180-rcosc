#!/usr/bin/env bash
# Matched-die calibrated-code running-Iq campaign driver (issue #337, operator ruling q178).
# Every SPICE unit is a `klt sim` batch submission; this script never launches a local
# ngspice loop. Results go to NEW results/<runid>* dirs (append-only; a non-empty target
# is refused). If a submit ultimately fails, its exit code stays in exit-codes.txt and the
# case is NOT re-run locally.
#
# Usage: sim/row4-calibrated-iq/run.sh <runid> [pilot]
#   <runid>  UTC stamp, e.g. 20261119T220503Z
#   pilot    n=2 fleet pilots instead of the n=500 full population
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNID="${1:?usage: run.sh <runid> [pilot]}"
N=500; [[ "${2:-}" == "pilot" ]] && N=2
ROOT="$HERE/results"
KLT=(klt sim --backend batch --format json --max-units-per-job 15 --max-concurrent-jobs 10
     --capacity-retries 2 --wait-for-capacity 600)

gen() { python3 -I "$HERE/gen.py" "$@"; }

for V in w3r65 w2.5r75; do
  D="$ROOT/${RUNID}-cand-$V"
  [[ -e "$D" ]] && { echo "ERROR: $D exists" >&2; exit 1; }
  gen cand "$V" "$D" "$N"
  ( cd "$D" && for p in tt ff ss; do
      KLT_SIM_BACKEND=batch "${KLT[@]}" "request_$p.json" -o "art_$p" > "report_$p.json" 2> "stderr_$p.txt"
      echo "$p=$?" >> exit-codes.txt
    done )
done

# Control decks need the finished candidate reports (per-die seeds + calibrated codes).
# Sharding is REQUIRED: a 500-deck request as one batch job exceeds the fleet's 3600 s
# job cap (batch_job_timeout, see ...-ctl-w3r65/attempt1 files); 15 decks/job x 10
# concurrent jobs finishes a leg in ~20 min. Capacity-refused shards resume with --resume.
for V in w3r65 w2.5r75; do
  D="$ROOT/${RUNID}-ctl-$V"
  [[ -e "$D" ]] && { echo "ERROR: $D exists" >&2; exit 1; }
  gen ctl "$D" "$ROOT/${RUNID}-cand-$V" "$([[ $N == 2 ]] && echo 2 || true)"
  ( cd "$D" && for p in tt ff ss; do
      KLT_SIM_BACKEND=batch klt sim "request_decks_$p.json" --backend batch --format json \
        --max-units-per-job 15 --max-concurrent-jobs 10 --capacity-retries 2 \
        --wait-for-capacity 600 -o "art_decks_$p" > "report_decks_$p.json" 2> "stderr_$p.txt"
      echo "$p=$?" >> exit-codes.txt
      if ! python3 -c "import json,sys; sys.exit(0 if json.load(open('report_decks_$p.json')).get('status')=='pass' else 1)"; then
        KLT_SIM_BACKEND=batch klt sim "request_decks_$p.json" --backend batch --format json \
          --max-units-per-job 15 --max-concurrent-jobs 10 --capacity-retries 2 \
          --wait-for-capacity 600 --resume -o "art_decks_$p" > "report_decks_$p.json" 2> "stderr_$p.resume1.txt"
        echo "resume $p=$?" >> exit-codes.txt
      fi
    done )
done

# Analysis (offline):
#   tables.py check  results/<runid>-cand-<V> results/<runid>-ctl-<V>
#   tables.py <V>    results/<runid>-cand-<V> results/<runid>-ctl-<V> results/<runid>-analysis-<V>
