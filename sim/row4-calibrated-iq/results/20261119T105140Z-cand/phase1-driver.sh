#!/usr/bin/env bash
# Resume-loop driver for the phase-1 batch-set (issue #337 calibrated-Iq campaign), v2.
# Per cycle, submits ONLY members whose report.json is not yet 500/500 pass:
# a cleanly-completed member retains no checkpoint, so re-submitting it would
# re-run all 500 units (seen live: cycle-1 re-ran w3r65_ff after it completed).
set -u
cd /home/ubuntu/GitHub/gf180-rcosc/.loom/worktrees/issue-337/sim/row4-calibrated-iq/results/20261119T105140Z-cand
MAX=18
for i in $(seq 1 "$MAX"); do
  REQ_LIST=$(python3 - <<'EOF'
import glob, json, os
names = ["w3r65_tt", "w3r65_ff", "w3r65_ss", "w2.5r75_tt", "w2.5r75_ff", "w2.5r75_ss"]
out = []
for n in names:
    rj = f"phase1/request_{n}/report.json"
    if not os.path.exists(rj):
        out.append(f"request_{n}.json")
        continue
    r = json.load(open(rj))
    passes = sum(1 for c in r.get("corners", []) if c.get("status") == "pass")
    if passes < 500:
        out.append(f"request_{n}.json")
print(" ".join(out))
EOF
)
  if [ -z "$REQ_LIST" ]; then
    echo "cycle $i: all members complete" >> phase1-driver.log
    echo "COMPLETE" >> phase1-driver.log
    exit 0
  fi
  LOG="phase1-submit.a5c$i.log"
  echo "=== cycle $i $(date -u +%H:%M:%SZ) members: $REQ_LIST" >> phase1-driver.log
  klt sim --batch-set $REQ_LIST --backend batch --wait-for-capacity 600 --resume \
      --max-units-per-job 10 --max-in-flight 6 --max-concurrent-jobs 12 \
      -o phase1 > "$LOG" 2>&1 || true
  st=$(python3 -c "
import json
try:
    e=json.load(open('phase1/set-envelope.json'))
    print(e.get('status'))
except Exception:
    print('none')")
  echo "cycle $i envelope=$st" >> phase1-driver.log
  sleep 20
done
echo "driver: MAX cycles reached" >> phase1-driver.log
exit 1
