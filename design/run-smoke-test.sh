#!/usr/bin/env bash
# Run the rcosc functional/DC smoke test (issue #6) -- NOT a PVT-corner or
# accuracy claim (see design/README.md and the issue's non-goals).
#
# 1. Regenerates design/netlist/*.spice + pdk_include.spice via
#    design/regen-netlist.sh.
# 2. Runs design/netlist/smoke_test.spice through ngspice in batch mode:
#    an .op sanity check (bias/threshold node voltages) plus a short
#    transient run at a fixed trim code (0x80) that measures two
#    consecutive rising-edge times on the free-running 'clk' output.
#
# Output is appended to design/netlist/smoke_test.log (append-only
# evidence per CLAUDE.md) -- re-running this script adds a new dated
# section rather than overwriting prior runs.
#
# Usage: design/run-smoke-test.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NETLIST_DIR="$REPO_ROOT/design/netlist"
LOG="$NETLIST_DIR/smoke_test.log"

"$REPO_ROOT/design/regen-netlist.sh"

{
  echo "===================================================================="
  echo "gf180-rcosc smoke test run: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ngspice: $(ngspice -v 2>&1 | sed -n '2p')"
  echo "Trim code under test: 0x80 (t7=1, t0..t6=0) -- see design/smoke_test.sch"
  echo "NOT a PVT-corner or accuracy claim -- functional/DC sanity only."
  echo "===================================================================="
} | tee -a "$LOG"

(cd "$NETLIST_DIR" && ngspice -b smoke_test.spice) 2>&1 | tee -a "$LOG"

echo "-- smoke test complete --" | tee -a "$LOG"
