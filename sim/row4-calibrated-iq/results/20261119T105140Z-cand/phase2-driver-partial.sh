#!/usr/bin/env bash
# Phase-2 partial driver: submits ONLY the ctrl deck-sets whose phase-1 member is
# complete (w3r65_ff, w3r65_ss, w2.5r75_tt as of 2026-11-20T02:35Z), so control
# decks drain while the remaining phase-1 members resume. The full
# phase2-driver.sh run afterwards re-lists all six members; --resume harvests
# whatever this partial run already collected (decks regenerate byte-identically).
set -u
cd /home/ubuntu/GitHub/gf180-rcosc/.loom/worktrees/issue-337/sim/row4-calibrated-iq/results/20261119T105140Z-cand
REQS=$(ls ctrl-*/dreq_*.json | sort)
echo "phase-2 partial: $(echo "$REQS" | wc -l) deck-list requests" > phase2-partial.log
MAX=16
for i in $(seq 1 "$MAX"); do
  LOG="phase2-submit.p$i.log"
  echo "=== cycle $i $(date -u +%H:%M:%SZ)" >> phase2-partial.log
  klt sim --batch-set $REQS --backend batch --wait-for-capacity 600 --resume \
      --max-units-per-job 10 --max-in-flight 6 --max-concurrent-jobs 12 \
      -o phase2 > "$LOG" 2>&1 || true
  st=$(python3 -c "
import json
try:
    e=json.load(open('phase2/set-envelope.json'))
    print(e.get('status'))
except Exception:
    print('none')")
  echo "cycle $i envelope=$st" >> phase2-partial.log
  if [ "$st" = "pass" ]; then
    echo "cycle $i COMPLETE" >> phase2-partial.log
    exit 0
  fi
  sleep 20
done
echo "phase2 partial: MAX cycles reached" >> phase2-partial.log
exit 1
