#!/usr/bin/env bash
# Strip/trim per-unit artifacts from collected ctl trees before committing (README contract:
# unit.json + stderr.bin + a trimmed stdout.txt are the evidence; the deck and dut_control.spice
# are byte-identical to the request-side files and unit.json keeps the deck sha256). The raw
# ngspice stdout is ~210 kB per die (9 transient probes x full node tables, 3796 lines) and only
# the 18 printed measurement lines plus the circuit banner carry evidence, so units commit a
# trimmed stdout.txt (banner + `(iq|f)_<lab>[0] = value` lines); the n=2 pilot dirs keep their
# full stdout.bin to document the raw format.
set -euo pipefail
D="${1:?usage: strip-ctl-units.sh <ctl-run-dir>}"
for a in "$D"/art_decks_{tt,ff,ss}; do
  [[ -d "$a" ]] || continue
  find "$a" -mindepth 2 -maxdepth 2 -name 'dut_control.spice' -delete
  find "$a" -mindepth 2 -maxdepth 2 -name '*.spice' -delete
  find "$a" -mindepth 2 -maxdepth 2 -name '.klt-expanded-*.spice' -delete
  for u in "$a"/*/; do
    [[ -f "$u/stdout.bin" ]] || continue
    awk 'NR<=7 || /^(iq|f)_(n40_30|n40_33|n40_36|27_30|27_33|27_36|85_30|85_33|85_36)\[0\] = /' \
      "$u/stdout.bin" > "$u/stdout.txt"
    rm "$u/stdout.bin"
  done
done
echo "stripped $D"
