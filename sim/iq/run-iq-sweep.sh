#!/usr/bin/env bash
# Run the gf180-rcosc quiescent-current (Iq) sweep (issue #22).
#
# 1. Regenerates design/netlist/*.spice from the xschem sources via
#    design/regen-netlist.sh, so the sweep always runs against the
#    committed schematics rather than a stale export.
# 2. Runs sim/iq/iq_sweep.py, which measures the block's supply current at
#    the reference corner (tt / 27 C / 3.3 V) two ways -- the `.op` figure
#    DR-0007 quoted and the running average DR-0003 Row 4 actually names --
#    across several trim codes, for both the as-committed sizing and the
#    pre-#22 sizing it replaced.
#
# Evidence is APPEND-ONLY (CLAUDE.md): each invocation creates a fresh,
# UTC-stamped run id under sim/iq/corners/<runid>/ and sim/iq/results/<runid>/
# and refuses to start if that run id already has content.
#
# Usage:
#   sim/iq/run-iq-sweep.sh                       # default codes 0x00 0x80 0xFF
#   sim/iq/run-iq-sweep.sh --jobs 8
#   sim/iq/run-iq-sweep.sh --codes 0x00 0x40 0x80 0xC0 0xFF
#
# All arguments are forwarded to sim/iq/iq_sweep.py (see --help there).
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

echo "== gf180-rcosc Iq sweep: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
"$REPO_ROOT/design/regen-netlist.sh"

exec python3 "$REPO_ROOT/sim/iq/iq_sweep.py" "$@"
