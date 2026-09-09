#!/usr/bin/env bash
# Run the gf180-rcosc quiescent-current (Iq) sweep (issue #22, extended #24,
# extended to a full PVT-corner factorial by issue #35).
#
# 1. Regenerates design/netlist/*.spice from the xschem sources via
#    design/regen-netlist.sh, so the sweep always runs against the
#    committed schematics rather than a stale export.
# 2. Runs sim/iq/iq_sweep.py, which measures the block's supply current at
#    EVERY point of the full process x temperature x supply factorial
#    (7 process corners x 3 T x 3 VDD = 63 grid points, imported from
#    sim/pvt/pvt_sweep.py so the two campaigns' corner definitions cannot
#    drift) two ways -- the `.op` figure DR-0007 quoted and the running
#    average DR-0003 Row 4 actually names -- across several trim codes, for
#    the as-committed sizing (see sim/iq/iq_sweep.py's module docstring for
#    why the pre-#22 sizing comparison is not part of the corner grid).
#
# Evidence is APPEND-ONLY (CLAUDE.md): each invocation creates a fresh,
# UTC-stamped run id under sim/iq/corners/<runid>/ and sim/iq/results/<runid>/
# and refuses to start if that run id already has content.
#
# Usage:
#   sim/iq/run-iq-sweep.sh                       # full grid, codes 0x00 0x80 0xC0 0xFF
#   sim/iq/run-iq-sweep.sh --jobs 8
#   sim/iq/run-iq-sweep.sh --subset endpoints    # fast check: tt/ff/ss x 3T x 3V only
#   sim/iq/run-iq-sweep.sh --codes 0x00 0x40 0x80 0xC0 0xFF
#
# All arguments are forwarded to sim/iq/iq_sweep.py (see --help there). The
# full grid (252 points at the default 4 codes) took ~2.7-4.2 minutes at
# --jobs 6 on an 8-core host in this project's own evidence run -- see
# sim/README.md for committed run wall-clock figures. Per DR-0009's
# environment note, a host running multiple concurrent ngspice processes
# should set `set num_threads=1` in `~/.spiceinit` to avoid ngspice's
# default per-process OpenMP thread count oversubscribing the host.
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
