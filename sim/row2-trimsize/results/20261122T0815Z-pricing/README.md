# #460 row-2 pricing of the F2.50@tt candidate (COMPLETE: 34 batch reports on the rebuilt-layout extraction)

Row-4 / row-5 / row-8 pricing for the least-bad screened sizing
`s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256`
(applied as netlist text to the **rebuilt-layout extraction**
`sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice`,
the DR-0044/0045/0047 basis, so the numbers are directly comparable with the
committed baselines). Layout NOT re-extracted; no design file touched.
Quoted in DR-0048 step 4. The candidate FAILS row 2 (see the screen README);
this pricing prices the sizing class, it does not propose adoption.

| dir | mode | requests | what |
|---|---|---|---|
| `calib-coarse/` | calib | 9 | 3 codes x 3 processes, locates 48 MHz |
| `calib-fine/` | calib | 19 | per-process scans: **tt 0xC8 (47.83 MHz), ff 0x70 (47.67), ss nearest 0xF8 (42.66 — 48 MHz NOT reachable at ss)** |
| `stage/` | stage | 9 | row-4 supply span at the per-process calibration codes (DR-0032 basis) |
| `iq/` | iq | 6 | row-8 running Iq at the tt calibration code 0xC8 and at 0xFF, 54 cells (DR-0046 basis) |
| `pricing-calib.md`, `pricing-stage.md`, `pricing-iq.md` | - | - | `pricing_table.py` outputs |

## Headline numbers (vs the DR-0047 54-cell / span baselines)

- **Row 5 / calibration:** the collapsed span (screen: 1.58x at tt on P3) is
  worse on the rebuild: `ss` tops out at 42.66 MHz at 0xF8 — **48 MHz is not
  reachable at ss at any code**, so the candidate cannot even be calibrated on
  a slow die. This alone disqualifies the sizing on the L07 basis.
- **Row 4 (`ss` 27 C supply span):** 5.81 pt (baseline 6.09, `w3r65` 4.68;
  window 4.9 — **not met**, same side as the baseline).
- **Row 8 (running Iq, 54 cells):** max 638.6 uA at 0xFF, 9/54 cells over
  500 uA (baseline 759.0 uA, 15/54) — the re-sized ladder's larger closed
  segments reduce the 0xFF switch current; no regression, no clearance of the
  > 500 uA cells either.

## Reproduce

```
python3 -I sim/row2-trimsize/gen_pricing.py calib <fresh>/calib-coarse s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256 tt:0x40,0x80,0xC0 ff:0x40,0x80,0xC0 ss:0x40,0x80,0xC0
python3 -I sim/row2-trimsize/run_set.py --bench-dir <fresh>/calib-coarse --out-dir <fresh>/calib-coarse   # batch fleet
python3 -I sim/row2-trimsize/pricing_table.py --reports <fresh>/calib-coarse/reports --mode calib
# likewise calib-fine / stage / iq
```

Execution window: 2026-11-22T06:5x-07:0x UTC (ledger.jsonl), ngspice 47, the
directory-stamp minute is nominal. The first `iq` submission round failed on a
request-schema bug (double-wrapped `corners.process`) and was regenerated after
fixing `gen_pricing.py`; the failed round left no reports and is not part of
the evidence.
