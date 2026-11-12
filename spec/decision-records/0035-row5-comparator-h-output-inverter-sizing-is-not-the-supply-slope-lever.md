# 0035: Row 5 `ff` hot / low-V skew: resizing the comparator-H output inverter does not move it (15 variants, none below +6.87 pt; target <= +4.6)

- **Status**: proposed - a refuted candidate lever only. Changes no ratified row, window or value, keeps the per-die calibration
  basis of [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md), adds no per-corner trim, leaves
  [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched. **No design change is proposed by this record and none is
  merged**: the committed schematics and netlists are unchanged.
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

[0033](0033-rows-4-5-stage-attribution-and-candidate-levers.md) put +6.27 pt of the `ff` 85 C / 3.0 V error (+6.88 pt median die,
worst die +11.04 % against +8.8 %, so about 2.2 pt to remove) on comparator H, whose delay falls from 1.84 ns (3.3 V / 27 C) to
0.61 ns, 2.84 pt of it the supply step. Candidate 2 there proposed a supply-slope change of the comparator-H output stage (the
MBUFN / MBUFP ratio) for an expected 2.3-2.8 pt. #321 asks for that change.

## Method (`sim/row45-rerun/`, batch fleet, nothing run locally)

`variant.py::comparator_h_buffer` resizes the two devices of the comparator-H output inverter in the flat extracted DR-0028 netlist
(`X$21` = MBUFN, `X$67` = MBUFP; with the committed sizes it returns the netlist byte-for-byte, AS/AD/PS/PD re-derived by the
extractor's rule otherwise). `gen_screen.py` writes, per variant, a 3.3 V / 27 C reference request and a 3.0 V request at -40 / 85 C
on the `ff` median die at its DR-0032 code 0x4E; `screen_table.py` reports the change against the same variant's 3.3 V / 27 C
frequency (the DR-0033 basis). The control reproduces DR-0033 (+6.91 vs +6.88 pt, -4.85 vs -4.88 pt).

Evidence: `sim/row45-rerun/results/20261112T100000Z-screen-cmph/` (set a) and
`sim/row45-rerun/results/20261112T101500Z-screen-cmph/` (set b).

## Result (`ff`, 3.0 V, change vs 3.3 V / 27 C at the same code, points; W/L in um)

| variant (MBUFN W / MBUFP W / L N / L P) | f(3.3 V, 27 C) MHz | 85 C | -40 C |
|---|---|---|---|
| base 1 / 4 / 0.5 / 0.5 | 47.956 | +6.91 | -4.85 |
| P 3 | 47.427 | +7.08 | -4.73 |
| P 2.5 | 46.784 | +7.60 | -4.55 |
| P 2 | 45.134 | +9.80 | -4.51 |
| P 6 | 48.243 | +7.01 | -4.95 |
| P 8 | 48.292 | +7.17 | -5.07 |
| N 0.7 | 48.261 | +7.00 | -4.99 |
| N 1.5 | 47.323 | +7.04 | -4.73 |
| N 2 (the pre-DR-0028 size) | 46.268 | +8.19 | -4.70 |
| N 0.7 / P 3 | 47.913 | +6.97 | -4.86 |
| N 1.5 / P 8 | 47.983 | +6.88 | -5.02 |
| L N 0.7 | 48.085 | +6.94 | -4.94 |
| L N 1.0 | 48.141 | +7.00 | -4.99 |
| L P 0.7 | 46.766 | +6.87 | -4.55 |

(The two sets share the `base` row; both runs gave the same numbers.)

**No variant reduces the failing cell by more than 0.04 pt** (best +6.87 against +6.91), against the 2.3-2.8 pt expected and 2.2 pt
needed. Lowering the inverter trip (narrower P, wider N) makes the cell worse, raising it (wider P, narrower N) is flat to slightly
worse: the 0.61 ns hot / low-V delay is not set by where the output inverter trips. The attribution's "output stage" reading of
comparator H was the stage as a whole; its collapse must come from the first stage (pair / mirror load / tail current against
supply and temperature), which this issue did not scope.

## Decision

Do **not** adopt any buffer-sizing change. Row 5's `ff` hot / low-V cell stays at the DR-0032 / DR-0033 figures. The screen is the
deliverable: the MBUFN / MBUFP lever named in 0033 candidate 2 is refuted at the whole-oscillator level.

## Not done in this record (open, tracked on #317 / #321)

- Acceptance criteria 1-4 of #321 are **not met**: there is no netlist change, so the 9-request calibrated stage re-run, the
  regression checks at `ff` -40 C, `ss` / `tt` hot, row 4 at `ff` and trim range, and the netlist-consistency / layout / LVS statement
  have nothing to evaluate. The -40 C column above (-4.5 to -5.1 pt, limit -10.8) is the only regression data, screen-grade only.
- Other `tt` / `ss` cells were not screened (no candidate reached the point of needing them).
- Next measurement: split comparator H's 0.61 ns into pair, mirror-load and buffer parts (probe `dp` / `dn`), then screen the
  first-stage devices (load L, pair W, tail ratio, which also touches row 8 current). Any such lever must stay a supply-slope change;
  a temperature-dependent element engages 0004 and the 2026-11-10 ruling.
- Rejected as before: relaxing windows, per-corner trim, active TC compensation (0004).
