# sim/row45-attribution - rows 4 / 5 cause attribution (issue #236, DR-0031)

Analysis of existing evidence only; no simulation, no netlist. Append-only: new run ids only.

```
python3 -I sim/row45-attribution/attribute.py sim/item5/results/20261106T071555Z sim/row45-attribution/results/<runid>/attribution.md
```

`results/20261111T0000Z/attribution.md`: per-process split of the fixed-code (0xA4) error into process offset, supply term
and temperature term, plus the ideal-lever upper bound. Reads `sim/item5/report_rows.py` for the loader and ratified limits.
