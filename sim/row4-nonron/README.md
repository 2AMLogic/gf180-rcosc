# sim/row4-nonron - isolating the non-Ron part of the ss supply span (issue #320, row 4)

Knock-out / swap experiments on the DR-0028 extracted netlist (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, edited as text by
`variant.py`; layout NOT re-extracted). Bench, probes and attribution reuse `sim/row45-attribution/` unchanged; ss only, 27 C,
3.0 / 3.3 / 3.6 V, code 212 unless stated. All runs on the batch fleet (`--wait-for-capacity 600`). Append-only.

```
python3 -I sim/row4-nonron/gen_knockout.py sim/row4-nonron/results/<runid>-<variant> <variant>   # variants: see variant.py
cd sim/row4-nonron/results/<runid>-<variant> && klt sim --batch-set request_*.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art
python3 -I sim/row4-nonron/gen_range.py <outdir> <variant> <code>   # tt/ff/ss 27 C 3.3 V endpoint requests
python3 -I sim/row4-nonron/knockout_table.py sim/row4-nonron/results/20261112T100000Z <out.md>
python3 -I sim/row4-nonron/ideal_table.py sim/row4-nonron/results/20261112T110000Z <out.md>
python3 -I sim/row4-nonron/width_table.py <ctrl dir> sim/row4-nonron/results/20261112T120000Z <out.md> 2 4
```

- `20261112T100000Z-{ctrl,nojb,nojd,nojall,capx}`: parasitic-C knock-outs; `-ctrl/knockout_table.md`.
- `20261112T110000Z-{ctrl0,ctrl255,ideal0,ideal212,ideal255}`: committed vs ideal-switch bank at three codes; `-ideal212/ideal_table.md`.
- `20261112T120000Z-{w2,w4,w8}`: pass-device width at fixed code 212; `-w2/width_table.md`. `-w8` (W = 192 um) failed in ngspice
  (`ngspice_fatal`, outside the model's width bins) and is kept as the record of that.
- `20261112T130000Z-w2r{75,85}`, `20261112T140000Z-{w3r70,w4r55,w4r65}`: width + base-resistor re-centring points (see DR-0036).
- `20261112T150000Z-w3r65` and `-range-w3r65-code{0,255}`: the candidate's ss supply stage run and trim-range endpoints.
  The scripts print per-run numbers; the summary tables are in DR-0036.

Result and interpretation: `spec/decision-records/0036-*.md`.
