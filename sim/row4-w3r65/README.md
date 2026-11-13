# sim/row4-w3r65 - DR-0037 `w3r65` bank candidate, measurement increment (issue #337, row 4 `ss` span)

`gen.py` applies DR-0037's candidate (16 bank pass devices at 3x W, base resistor `X$91` at 65 % length, via `sim/row4-nonron/variant.py` `w3r65`) as
netlist text to the **extraction of the rebuilt layout** (`sim/row45-rerun/results/20261112T200335Z-extract-l07/`, the DR-0043 / DR-0044 basis). The
layout is NOT re-extracted for the candidate; no schematic, netlist or layout file is touched (the operator ruling in DR-0045 is still open).
All SPICE is `klt sim --batch-set request_*.json --backend batch --wait-for-capacity 600` on the batch fleet (klt 0.9.2.dev885). Append-only.

```
python3 -I sim/row4-w3r65/gen.py calib OUTDIR tt:0xA0,... ff:... ss:...   # per-die scan, 27 C / 3.3 V
python3 -I sim/row4-w3r65/gen.py stage OUTDIR tt=167,ff=75,ss=212          # 9 requests: 3 dies x 3 supplies x (-40, 27, 85 C)
python3 -I sim/row4-w3r65/gen.py iq OUTDIR                                 # running Iq, codes 0x00 0x80 0xC0 0xFF, 108 cells
python3 -I sim/row45-rerun/iq_table.py CAND_DIR CONTROL_DIR                # Iq delta table
```

- `results/20261113T080000Z-calib` (coarse scan plus 0x00 / 0xFF trim ends, 20 requests) and `results/20261113T083000Z-calib-fine` (12 requests):
  per-die codes nearest 48 MHz at 27 C / 3.3 V, **tt 0xA7 (167) 48.07 MHz, ff 0x4B (75) 47.96 MHz, ss 0xD4 (212) 47.85 MHz**.
  The `ss` scan is non-monotonic above 0xDC (0xE0 reads 48.18 MHz, a DR-0014 block-boundary dip); 0xD4 is the nearest-to-48 MHz code below it.
- `results/20261113T090000Z-stage` (`table.py` -> `table.md`): error against the same die's 3.3 V / 27 C frequency, as in DR-0043.
  The temperature axis is the repo's PVT grid (-40 / 27 / 85 C; `sim/pvt/pvt_sweep.py` `TEMPS_C`), three points, not five.
- `results/20261113T093000Z-iq` (`table_vs_l07.md`, `table_vs_l1.md`): same integrator bench as `gen_row5_iq_extracted.py`; controls are
  `sim/row45-rerun/results/20261113T064105Z-iq-extracted-l07` (the rebuilt-layout extraction, the correct baseline) and `...065500Z-iq-extracted-control-l1` (DR-0044's L=1u control).

Result and interpretation: `spec/decision-records/0045-*.md`.
