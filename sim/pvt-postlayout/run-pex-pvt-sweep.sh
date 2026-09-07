#!/usr/bin/env bash
# Run the gf180-rcosc post-layout (PEX-extracted) PVT re-verification
# subset (issue #28).
#
# 1. Regenerates design/netlist/*.spice from the xschem sources via
#    design/regen-netlist.sh, so this always compares against the
#    committed schematic, not a stale export.
# 2. Runs `klt extract --parasitics` against the full-hierarchy
#    layout/cells/rcosc_top.gds (issue #27) to get a parasitic-annotated
#    netlist.
# 3. Runs sim/pvt-postlayout/pex_pvt_sweep.py, which re-simulates the
#    process={tt,ff,ss} x temperature={-40,+27,+85}C x
#    VDD={3.0,3.3,3.6}V corner-endpoint subset (27 points) against both
#    the schematic and the extracted netlist, at the fixed post-#24
#    (DR-0009) single-code post-trim methodology's own calibration code,
#    and reports the per-point delta.
#
# Evidence is APPEND-ONLY (CLAUDE.md): each invocation creates a fresh run
# id under sim/pvt-postlayout/corners/<runid>/ and
# sim/pvt-postlayout/results/<runid>/ and refuses to start if that run id
# already has content.
#
# Usage:
#   sim/pvt-postlayout/run-pex-pvt-sweep.sh                # full subset
#   sim/pvt-postlayout/run-pex-pvt-sweep.sh --jobs 8        # limit parallel ngspice processes
#   sim/pvt-postlayout/run-pex-pvt-sweep.sh --keep-build    # keep generated per-run decks
#
# All arguments are forwarded to sim/pvt-postlayout/pex_pvt_sweep.py (see
# --help there).
#
# Requires: ngspice, xschem, klt (>= the build this issue's PR documents
# the exact `klt extract`/`klt pex` flag surface against), python3, and a
# gf180mcuC PDK resolvable the same way design/regen-netlist.sh resolves
# it (PDK_ROOT, else `klt pdk find`).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

for tool in ngspice python3 klt; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "ERROR: required tool '$tool' not found on PATH" >&2
    exit 1
  }
done

echo "== gf180-rcosc post-layout PEX PVT campaign: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

exec python3 "$REPO_ROOT/sim/pvt-postlayout/pex_pvt_sweep.py" "$@"
