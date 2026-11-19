# sim/row4-iq-variant - lower-Iq bank variant search (issue #337, operator ruling 2026-11-18)

Sim-only search for a variant of DR-0037's `w3r65` (16 bank pass devices at K x W, base resistor `X$91` at P % length) that holds row 4 `ss` span <= 4.9 pt and
brings code-0xFF running Iq back to the DR-0044 band. Same DUT as `sim/row4-w3r65/` (extraction of the rebuilt layout, variant applied as netlist text, layout NOT
re-extracted); no `design/*` file touched. All SPICE `klt sim --batch-set ... --backend batch --wait-for-capacity 600`. Append-only.

```
python3 -I sim/row4-iq-variant/gen.py NAME calib|stage|iq OUTDIR ...   # NAME = w<K>r<P>, K decimal (row4-nonron/variant.py takes only integer K)
python3 -I sim/row4-iq-variant/tables.py RESULTDIR                     # ss span + Iq delta tables
```

- `results/20261118T230500Z-ss-recentre`: ss die scan, codes 0xC8/0xD0/0xD4/0xD8 for six (K,P) guesses (`table.md`). Baseline: the `ss` die at code 0xD4 (212)
  reads 48.038 MHz on the rebuilt-layout extraction (`sim/row45-rerun/results/20261112T203500Z-stage-extracted-l07/table.md`, `ss` ref row). At code 212 the six
  variants read 47.67 (w2r85), 47.72 (w2.5r75), 48.37 (w1.5r90), 48.39 (w2r80), 48.47 (w2.5r70), 49.07 MHz (w1.5r85): the first four land within 47.67-48.39 MHz
  of the baseline and re-centre without a code change; w2.5r70 / w1.5r85 do not. Reading the split as "within one code step of 48.038 MHz" (each variant's own
  0xC8->0xD8 slope: accepted 0.78-0.98 codes, rejected 1.03 / 2.81) reproduces it, but that rule is a reconstruction - the criterion actually applied is not recorded.
- `results/20261118T233000Z-ss-stage-iq`: for w2r80, w2.5r75, w1.5r90 - three of the four re-centring variants; w2r85 was not carried and the reason is not
  recorded. `<v>-stage` = `ss` die at code 212, 3 supplies x (-40, 27, 85 C), `table.md`;
  `<v>-iq` = running Iq at codes 0xC0 and 0xFF, 3 dies x 3 supplies x 3 temperatures (54 cells per variant), `table_vs_l07.md` against
  `sim/row45-rerun/results/20261113T064105Z-iq-extracted-l07`. tt / ff stage cells were not run (their re-centred codes were not derived; `ss` is the failing cell).

Result and interpretation: `spec/decision-records/0047-*.md`.
