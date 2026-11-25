# #460 F2.50@tt full 256-code x 3-corner curve (COMPLETE: 768/768 batch reports, all valid)

Full dense trim curve of the least-bad screened sizing
`s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256`
(the range-true ratio-rule pole) at the three dense-campaign corners, on the
P3 extraction with netlist-text re-sizing only. Companion of the screen
`../20261122T0550Z-screen/`; the reading of these numbers is DR-0048.

| path | what |
|---|---|
| `bench/` | frozen 768-request set (provenance.json with per-request sha256, per-corner DUT copies) |
| `manifest.json` | execution manifest (git sha, klt 0.9.0, ngspice 47 uniform, PDK stamp `f6eeac7d...`, solver settings) |
| `jobs/`, `reports/`, `ledger.jsonl` | batch-fleet execution (`run_set.py`, single-variant `--batch-set` groups after the cross-wiring incident in the screen run) |
| `analysis/` | `sim/trim-dense/analyze.py` output: `results.json`, `steps.csv`, `summary.md` - all 3 curves OK, `run_errors` empty (the analyzer verifies every report's netlist sha and engine) |

## Headline (DR-0048 quotes these)

| corner | f ends MHz | mean step (x nominal) | outside half-LSB | worst dev | non-positive | carries |
|---|---|---|---|---|---|---|
| tt 27 C 3.3 V | 27.067 / 53.151 | 0.3779 % (1.20x) | 65/255 | 13.6 LSB | 15 | all 4 negative |
| ss -40 C 3.0 V | 20.121 / 40.401 | 0.3953 % (1.26x) | 56/255 | 14.9 LSB | 13 | all 4 negative |
| ff 85 C 3.6 V | 37.488 / 71.626 | 0.3571 % (1.14x) | 69/255 | 14.4 LSB | 19 | all 4 negative |

Reproduce:

```
python3 -I sim/row2-trimsize/gen_full.py --sizing s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256 --out <fresh>/bench
python3 -I sim/row2-trimsize/run_set.py --bench-dir <fresh>/bench --out-dir <fresh>          # batch fleet
python3 -I sim/trim-dense/analyze.py --bench-dir <fresh>/bench --reports-dir <fresh>/reports \
  --manifest <fresh>/manifest.json --outdir <fresh>/analysis
```

Execution window: 2026-11-22T06:51-08:38 UTC (ledger.jsonl), ngspice 47 on
every report; a spot resubmission of `tt c00` reproduced its frequency to the
digit (27,066,921.2 Hz). The directory-stamp minute is nominal.
