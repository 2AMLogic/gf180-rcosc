# sim/row4-nonron - isolating the non-Ron part of the ss supply span (issue #320, row 4)

Knock-out / swap experiments on the DR-0028 extracted netlist (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, edited as text by
`variant.py`; layout NOT re-extracted). Bench, probes and attribution reuse `sim/row45-attribution/` unchanged; ss only, 27 C,
3.0 / 3.3 / 3.6 V, code 212 unless stated. All runs on the batch fleet (`--wait-for-capacity 600`). Append-only.

```
python3 -I sim/row4-nonron/gen_knockout.py sim/row4-nonron/results/<runid>-<variant> <variant>   # variants: see variant.py
cd sim/row4-nonron/results/<runid>-<variant> && klt sim --batch-set request_*.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art
python3 -I sim/row4-nonron/gen_range.py <outdir> <variant> <code>   # tt/ff/ss 27 C 3.3 V endpoint requests
python3 -I sim/row4-nonron/knockout_table.py sim/row4-nonron/results/<runid> <out.md>   # <runid> is a prefix: reads <runid>-ctrl, -nojb, ... (see list below)
python3 -I sim/row4-nonron/ideal_table.py sim/row4-nonron/results/<runid> <out.md>   # reads <runid>-ctrl0, -ideal0, ...
python3 -I sim/row4-nonron/width_table.py <ctrl dir> sim/row4-nonron/results/<runid> <out.md> 2 4   # reads <runid>-w2, -w4
```

- Parasitic-C knock-outs (`knockout_table.py`, `<runid>` = the `T100000Z` stamp): `results/20261112T100000Z-ctrl`,
  `results/20261112T100000Z-nojb`, `results/20261112T100000Z-nojd`, `results/20261112T100000Z-nojall`,
  `results/20261112T100000Z-capx`; table in `results/20261112T100000Z-ctrl/knockout_table.md`.
- Committed vs ideal-switch bank at three codes (`ideal_table.py`): `results/20261112T110000Z-ctrl0`, `-ctrl255`,
  `-ideal0`, `-ideal212`, `-ideal255` (all under `results/`, same stamp prefix); table in
  `results/20261112T110000Z-ideal212/ideal_table.md`.
- Pass-device width at fixed code 212 (`width_table.py`): `results/20261112T120000Z-w2`, `results/20261112T120000Z-w4`,
  `results/20261112T120000Z-w8`; table in `results/20261112T120000Z-w2/width_table.md`. `w8` (W = 192 um) failed in ngspice
  (`ngspice_fatal`, outside the model's width bins) and is kept as the record of that.
- Width + base-resistor re-centring points (see DR-0036): `results/20261112T130000Z-w2r75`, `results/20261112T130000Z-w2r85`,
  `results/20261112T140000Z-w3r70`, `results/20261112T140000Z-w4r55`, `results/20261112T140000Z-w4r65`.
- The candidate's ss supply stage run and trim-range endpoints: `results/20261112T150000Z-w3r65`,
  `results/20261112T150000Z-range-w3r65-code0`, `results/20261112T150000Z-range-w3r65-code255`.
  The scripts print per-run numbers; the summary tables are in DR-0036.

Result and interpretation: `spec/decision-records/0036-*.md`.
