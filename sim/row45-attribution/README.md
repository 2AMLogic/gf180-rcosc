# sim/row45-attribution - rows 4 / 5 cause attribution (issue #236, DR-0031)

Analysis of existing evidence only; no simulation, no netlist. Append-only: new run ids only.

```
python3 -I sim/row45-attribution/attribute.py sim/item5/results/20261106T071555Z sim/row45-attribution/results/<runid>/attribution.md
```

`results/20261111T0000Z/attribution.md`: per-process split of the fixed-code (0xA4) error into process offset, supply term
and temperature term, plus the ideal-lever upper bound. Reads `sim/item5/report_rows.py` for the loader and ratified limits.

## Stage-level attribution (issue #314, DR-0033)

Simulation on the DR-0028 netlist (batch fleet). `gen_stage_requests.py` writes a probed copy of the DUT (probe pins only, no
device edited), 9 benches and 9 requests (3 processes x 3 supplies, each over -40 / 27 / 85 C, at the per-die code of DR-0032's
median die). `stage_attribution.py` splits each frequency error into the six oscillator stages (event gaps sum to the period) and
splits the charge stage into threshold-ratio / RC / cross terms. `test_stage_attribution.py` covers the sum-to-total checks
(`python3 -m pytest sim/row45-attribution`).

```
python3 -I sim/row45-attribution/gen_stage_requests.py sim/row45-attribution/results/<runid>
cd sim/row45-attribution/results/<runid> && klt sim --batch-set request_*.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art
python3 -I sim/row45-attribution/stage_attribution.py sim/row45-attribution/results/<runid> sim/row45-attribution/results/<runid>/stage_attribution.md
```

`results/20261112T070000Z/`: `stage_attribution.md` (all tables), `batch_report.json`, `art/` (per-request envelopes), `dut.txt`.
Event nets in the extracted netlist (read off the device terminals): vc `$24`, vh `$5`, vl `$6`, cmph_out `$29`, cmpl_out `$32`,
qbar `$33`, ibias `$35`, pb `$7`. Measurement names must differ case-insensitively (`ta`/`tA` silently shadow each other in ngspice).
