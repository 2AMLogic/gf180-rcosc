#!/usr/bin/env bash
# Strip per-unit deck copies from collected ctl trees before committing (README contract:
# stdout.bin / stderr.bin / unit.json are the evidence; the deck and dut_control.spice are
# byte-identical to the request-side files and unit.json keeps the deck sha256).
set -euo pipefail
D="${1:?usage: strip-ctl-units.sh <ctl-run-dir>}"
for a in "$D"/art_decks_{tt,ff,ss}; do
  [[ -d "$a" ]] || continue
  find "$a" -mindepth 2 -maxdepth 2 -name 'dut_control.spice' -delete
  find "$a" -mindepth 2 -maxdepth 2 -name '*.spice' -delete
  find "$a" -mindepth 2 -maxdepth 2 -name '.klt-expanded-*.spice' -delete
done
echo "stripped $D"
