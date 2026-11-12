# 0038: Row 5 `ff` hot / low-V skew: comparator-H mirror-load L 1.0 -> 0.7 um clears the cell in the 9-request stage re-run (+6.93 -> +1.65 pt), with margin to length mismatch; schematic and layout not yet edited

- **Status**: proposed - sim-only variant evidence; **no design change is made by this record** (committed schematics, netlists and
  layout unchanged). Changes no ratified row or window, keeps the per-die calibration basis of
  [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md), adds no per-corner trim and no temperature-dependent
  element ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched). Extends [0036](0036-row5-comparator-h-first-stage-is-the-supply-slope-lever-load-l-and-tail-screen.md).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0036 found the lever on one die (`ff` median, code 0x4E). This record runs the issue's deterministic 9-request stage re-run on the
DR-0028 netlist with `MLOADA` / `MLOADB` (X$65 / X$66) at L 0.7 um (`gen_row5_candidate.py`, `variant.first_stage`; bank switches NOT
doubled, so it is independent of the row-4 candidate), re-derives the per-die codes by calibration scan (nearest 48.000 MHz at
3.3 V / 27 C), and adds margin, trim-range and supply-current checks. All SPICE on the batch fleet (`klt sim --batch-set ... --wait-for-capacity 600`).
Netlist is the P3 extraction with the old wiring parasitics (layout not re-extracted), as in 0034-0036.

Evidence (`sim/row45-rerun/results/`): `20261112T130000Z-calib-ll07` + `20261112T133000Z-calib-ll07-lower` (scan), `20261112T140000Z-stage-ll07`
(9 requests, `stage_attribution.md`), `20261112T143000Z-calib-ll07-ends` (trim ends), `20261112T150000Z-iq-ll07`, `20261112T153000Z-mismatch-ll07` (`table.md`).

## Result

Per-die codes at L 0.7: **tt 164 (47.907 MHz), ff 79 (47.959), ss 212 (48.029)** (baseline 165 / 78 / 212). Change of `fosc` against the same die's
3.3 V / 27 C frequency, points (row 5 windows +8.8 hot / -10.8 cold; `stage_attribution.md` header still prints the old constants, as in 0034):

| die | cell | base (0033 run) | L 0.7 |
|---|---|---|---|
| ff | 3.0 V / 85 C (failing cell) | +6.93 | **+1.65** |
| ff | 3.0 V / -40 C | -4.86 | -4.39 |
| ff | 3.6 V / 85 C | +4.36 | +3.04 |
| ff | 3.6 V / -40 C | -2.69 | -2.25 |
| tt | 3.0 V / 85 C | +1.00 | -0.26 |
| tt | 3.0 V / -40 C | -4.26 | -4.26 |
| tt | 3.6 V / 85 C | +3.23 | +2.95 |
| ss | 3.0 V / 85 C | -2.31 | -2.81 |
| ss | 3.0 V / -40 C | -4.21 | -4.09 |
| ss | 3.6 V / 85 C | +3.13 | +2.96 |

Remaining cells of the 27 move by < 0.5 pt (see the evidence tables). The 2.2 pt needed at the failing cell is exceeded (5.3 pt gained); no cell
worsens by more than 0.5 pt (`ss` 3.0 V / 85 C, -2.81 vs limit -10.8).

- **Row 4 at `ff` (27 C supply span, 3.6 V minus 3.0 V):** 1.56 -> 1.96 pt (window 4.9). `tt` span 3.51 pt and `ss` 6.12 pt at L 0.7 (`ss` was 6.1 at base: row 4 at `ss` still fails the 4.9 window, its cause is the bank switches per 0037, untouched by this lever).
- **Trim range (row 2), 0x00 / 0xFF at 3.3 V / 27 C, MHz, baseline -> L 0.7:** tt 28.65 / 76.42 -> 28.61 / 76.37; ff 37.72 / 98.20 -> 37.56 / 96.94;
  ss 22.62 / 61.18 -> 22.61 / 61.34. Moves <= 1.3 %; the range still brackets 48 MHz with the same margin.
- **Row 8 (supply current), side check only:** mean `i(VDD)` over 900-1200 ns, `ff` 3.6 V code 0x4F, base -> L 0.7: -426.5 / -452.9 / -508.1 uA ->
  -427.6 / -452.9 / -504.1 uA at -40 / 27 / 85 C (<= 0.8 %). This is the oscillating mean, not the ratified Iq definition (`sim/iq`), which was not re-run.
- **Length mismatch, `ff` code 0x4F (`20261112T153000Z-mismatch-ll07/table.md`):** MLOADA / MLOADB at 0.7 / 0.7 +1.65; 0.8 / 0.7 +1.29; 0.6 / 0.7 +2.17;
  0.7 / 0.8 +2.48; 0.7 / 0.6 +0.69; 0.8 / 0.8 +2.40 pt hot (limit +8.8), -3.9 to -4.9 pt cold. Mismatch shifts the 3.3 V frequency by up to +/-2 %
  (absorbed by the per-die code). With 0036 (common L 0.6 +1.40, 0.8 +2.50, 0.9 +4.19, 1.1 +10.4) the shoulder is at about L 1.0-1.1; L 0.7 sits 0.3 um from it.

## Not done (so #321 stays open)

- **Schematic / layout edit.** `design/rcosc_comparator.sch` (MLOADA / MLOADB L=1u -> 0.7u; comparator H only - `rcosc_comparator_p.sch` has no MLOAD instance)
  was edited and `design/regen-netlist.sh` run, then **reverted in this PR**: it makes `design/check-netlist-consistency.py` fail on 22 problems, because
  the five tracked `sim/**/rcosc_top_schematic.spice` bench copies and their `provenance.json` `source_sha256` pins (trim-transition, waveform) would have to
  be rewritten to a netlist the archived results were not simulated on (the DR-0028 precedent also rebuilt the layout). The layout (two device
  lengths in one cell, GDS rebuild, DRC / LVS) is not rebuilt here, so a schematic-only change would also leave `layout/` LVS-mismatched.
  Needs an operator call on the provenance-pin policy and the layout rebuild, as one increment.
- Local-mismatch Monte Carlo on the real statistical models (500-die campaign stays on #317); the deterministic length-mismatch table above stands in.
- The ratified Iq sweep (`sim/iq`) and row 4 `ff` / row 2 at all corners; only the cells listed above were run.
