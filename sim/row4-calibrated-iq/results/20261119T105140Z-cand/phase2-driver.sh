#!/usr/bin/env bash
# Phase-2 (matched control decks) driver for the calibrated-Iq campaign (issue #337).
# Generates the six ctrl deck-sets from the completed phase-1 reports, then loops
# batch-set resume until the phase-2 envelope passes.
set -eu
cd /home/ubuntu/GitHub/gf180-rcosc/.loom/worktrees/issue-337/sim/row4-calibrated-iq/results/20261119T105140Z-cand
GEN=../../gen.py

for name in w3r65 w2.5r75; do
  for proc in tt ff ss; do
    if [ ! -d "ctrl-$name-$proc" ]; then
      python3 -I "$GEN" ctrl "ctrl-$name-$proc" "$name" "$proc" \
        "phase1/request_${name}_${proc}/report.json" 25
    fi
  done
done

REQS=$(ls ctrl-*/dreq_*.json | sort)
echo "phase-2: $(echo "$REQS" | wc -l) deck-list requests" > phase2-driver.log

MAX=16
for i in $(seq 1 "$MAX"); do
  LOG="phase2-submit.a$i.log"
  echo "=== cycle $i $(date -u +%H:%M:%SZ)" >> phase2-driver.log
  klt sim --batch-set $REQS --backend batch --wait-for-capacity 600 --resume \
      --max-units-per-job 10 --max-in-flight 6 --max-concurrent-jobs 12 \
      -o phase2 > "$LOG" 2>&1 || true
  rc=$?
  st=$(python3 -c "
import json
try:
    e=json.load(open('phase2/set-envelope.json'))
    print(e.get('status'))
except Exception:
    print('none')")
  echo "cycle $i rc=$rc envelope=$st" >> phase2-driver.log
  if [ "$st" = "pass" ]; then
    echo "cycle $i COMPLETE" >> phase2-driver.log
    exit 0
  fi
  sleep 20
done
echo "phase2 driver: MAX cycles reached" >> phase2-driver.log
exit 1
