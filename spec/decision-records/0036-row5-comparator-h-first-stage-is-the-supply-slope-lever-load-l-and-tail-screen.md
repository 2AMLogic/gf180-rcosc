# 0036: Row 5 `ff` hot / low-V skew: the comparator-H first stage is the lever (mirror-load L 1 -> 0.7 um or tail x0.7 takes +6.91 to +1.7 pt); screen only, nothing adopted

- **Status**: proposed - screen-grade evidence on one die; **no design change is made by this record** (committed schematics and
  netlists unchanged). Changes no ratified row or window, keeps the per-die calibration basis of
  [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md), adds no per-corner trim and no temperature-dependent
  element ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched). Extends [0035](0035-row5-comparator-h-output-inverter-sizing-is-not-the-supply-slope-lever.md).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0035 refuted the comparator-H output inverter and named the first stage (pair / mirror load / tail) as the remaining suspect. This
record screens those devices the same way: `variant.first_stage` (pair X$19/X$20, mirror load X$65/X$66 = MLOADA/MLOADB, tail =
fingers X$39..X$46 = MTAIL W=16 nf=8), `gen_screen.py OUTDIR c|d`, `screen_table.py`. `ff` median die, code 0x4E, change of `fosc`
against the same variant's 3.3 V / 27 C frequency (DR-0033 basis), AS/AD/PS/PD re-derived. Batch fleet only. Control reproduces
DR-0033 (+6.91 / -4.85 pt). Evidence: `sim/row45-rerun/results/20261112T110000Z-screen-cmph-first/` (set c) and
`.../20261112T112000Z-screen-cmph-first/` (set d), each with `table.md`.

## Result (`ff`, 3.0 V, points; limit +8.8 hot / -10.8 cold; target on this die <= +4.6)

| variant | f(3.3 V, 27 C) MHz | 85 C | -40 C |
|---|---|---|---|
| base (load L 1.0, pair W 4, tail x1) | 47.956 | +6.91 | -4.85 |
| pair W 3 / 6 / 8 | 48.010 / 47.699 / 47.389 | +6.66 / +7.41 / +7.86 | -4.94 / -4.80 / -4.77 |
| load L 1.5 | 51.420 | +23.43 | -10.21 |
| load L 1.1 | 48.114 | +10.40 | -5.16 |
| load L 0.9 | 47.863 | +4.19 | -4.68 |
| load L 0.8 | 47.816 | +2.50 | -4.59 |
| load L 0.7 | 47.789 | +1.69 | -4.54 |
| load L 0.6 | 47.753 | +1.40 | -4.48 |
| load L 0.5 | 47.705 | +1.24 | -4.42 |
| tail x1.5 | 52.285 | +20.54 | -9.65 |
| tail x0.85 | 47.533 | +3.20 | -4.72 |
| tail x0.7 | 47.100 | +1.69 | -4.65 |
| tail x0.55 | 46.626 | +1.24 | -4.76 |

## Reading

- The pair width is not the lever (+/-0.7 pt). Mirror-load length and tail current are: both move the cell by 5 pt or more, in the
  needed direction, and both **floor at about +1.2 pt** (L 0.5 and tail x0.55 land on the same +1.24), the signature of comparator H
  ceasing to be the limiting delay. The expected 2.3-2.8 pt is exceeded; the 2.2 pt needed is met by L <= 0.9 or tail <= x0.85.
- The response is **steep and one-sided near the present design**: L 1.0 -> 1.1 adds 3.5 pt, L 1.5 reaches +23 pt (limit +8.8). The
  base sits on the shoulder, which is also why it is the failing cell. A choice must carry margin for device-length tolerance and
  mismatch, not the single-die optimum; L 0.7 is on the flat part (0.6-0.5 buy 0.3-0.45 pt more).
- Cold side improves (-4.4 to -4.8 pt, limit -10.8). The 3.3 V / 27 C frequency moves by < 1.7 % at the same code (per-die
  calibration absorbs it).
- Cost differences: load L touches only comparator H (no bias current, so row 8 unaffected on its face; layout: two devices change
  length, a cell edit). Tail x0.7 lowers comparator-H bias current (row 8 current and the comparator-H headroom/offset need a check)
  and touches the 8-finger MTAIL / MBIASD 8:1 ratio that DR-0009 re-derived.
- Both are supply-slope changes (no temperature-dependent element).

## Decision

Adopt nothing yet. The lever is found; the evidence is one die at one corner. Recommended candidate for the next increment: **MLOADA /
MLOADB L 1.0 -> 0.7 um** (comparator H only). Not done, so #321 acceptance criteria 1-4 stay open:

- schematic edit (`design/rcosc_comparator.sch` / `_p.sch`, confirm instance sharing with comparator L), `design/regen-netlist.sh`,
  netlist-consistency, layout / LVS statement;
- the deterministic 9-request stage re-run with per-die codes re-derived by calibration scan;
- `ff` -40 C, `ss` / `tt` hot, row 4 at `ff`, trim range (row 2), row 8 current; mismatch / Monte Carlo margin on the steep slope;
- the 500-die campaign stays on #317.
