#!/usr/bin/env bash
# Run the gf180-rcosc PVT-corner simulation campaign (issue #12).
#
# 1. Regenerates design/netlist/*.spice from the xschem sources via
#    design/regen-netlist.sh, so the campaign always runs against the
#    committed schematics rather than a stale export.
# 2. Runs sim/pvt/pvt_sweep.py, which sweeps the full process x temperature
#    x supply factorial (pre-trim and post-trim) and writes a new,
#    UTC-stamped evidence directory under sim/pvt/.
#
# Evidence is APPEND-ONLY (CLAUDE.md): each invocation creates a fresh run id
# under sim/pvt/corners/<runid>/ and sim/pvt/results/<runid>/ and refuses to
# start if that run id already has content. A re-run never rewrites a prior
# run's raw logs, CSV, manifest, or summary.
#
# Usage:
#   sim/pvt/run-pvt-sweep.sh                # full campaign
#   sim/pvt/run-pvt-sweep.sh --jobs 8       # limit parallel ngspice processes
#   sim/pvt/run-pvt-sweep.sh --keep-build   # keep the generated per-run decks
#
# All arguments are forwarded to sim/pvt/pvt_sweep.py (see --help there).
#
# Requires: ngspice, xschem, python3, and a gf180mcuC PDK resolvable the same
# way design/regen-netlist.sh resolves it (PDK_ROOT, else `klt pdk find`).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

for tool in ngspice python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "ERROR: required tool '$tool' not found on PATH" >&2
    exit 1
  }
done

echo "== gf180-rcosc PVT campaign: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
"$REPO_ROOT/design/regen-netlist.sh"

exec python3 "$REPO_ROOT/sim/pvt/pvt_sweep.py" "$@"
