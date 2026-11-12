# sim/row4-ron - bank pass-gate Ron vs VDD at ss (issue #317, row 4)

Tests the DR-0033 hypothesis that the ss supply term (charge RC term +3.03 pt of the +6.13 pt span) is the bank
transmission-gate Ron rising as VDD falls. Schematic-level `rcosc_trim_bank`, ss corner, DC node levels vl/mid/vh
(VDD/3, VDD/2, 2VDD/3), 50 mV across the bank, 3 supplies x 3 temperatures, codes 0x00/55/80/AA/D4/FF. Append-only.

```
python3 -I sim/row4-ron/gen_ron_requests.py sim/row4-ron/results/<runid> [WSCALE]
cd sim/row4-ron/results/<runid> && klt sim --batch-set request_*.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art
python3 -I sim/row4-ron/ron_table.py sim/row4-ron/results/<runid> sim/row4-ron/results/<runid>/ron_table.md
```

- `results/20261112T081500Z/`: committed bank (`real`) and the ladder-only reference (`ideal`), `ron_table.md`.
- `results/20261112T083000Z-w{1.5,2,3}/`: `real` variant only, all pass-device widths scaled by WSCALE (candidate fix); the ideal
  reference is width-independent and is read from the first run.
