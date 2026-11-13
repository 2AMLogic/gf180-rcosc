# 0045: Row 4: the DR-0037 `w3r65` bank candidate, measured on the extraction of the rebuilt layout: `ss` span clears (4.68 pt), but running Iq at code 0xFF rises 18-28 %

- **Status**: proposed - measurement only; closes the "not shown" list of [0037](0037-row4-ss-span-is-the-bank-switches-not-parasitic-c-dr0034-recalibration-confound.md). Changes no ratified row or window;
  per-die basis ([0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md)) unchanged; no per-corner trim; [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched.
  **No schematic, netlist or layout file is changed.** The operator ruling (below) is still open, so adoption is not started.
- **Date**: 2026-11-13
- **Decided by**: Loom Builder (issue #337), pending operator ratification

## Context

0037 held `w3r65` (16 bank pass devices at 3x W, base resistor `X$91` at 65 %) as a sim-only candidate on the old-layout extraction and listed what was not shown. This record measures those items on the
extraction of the rebuilt layout, the basis of [0043](0043-row5-comparator-h-mirror-load-l07-reconfirmed-on-the-extraction-of-the-rebuilt-layout-ff-hot-low-v-clears.md) /
[0044](0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md), by applying the candidate as netlist text (layout not re-extracted).
Evidence: `sim/row4-w3r65/` (README has the commands); all `klt sim --batch-set ... --backend batch --wait-for-capacity 600`.

## Evidence

Per-die codes re-derived by scan at 27 C / 3.3 V: **tt 167, ff 75, ss 212** (47.91 / 47.96 / 47.85 MHz targets 48; baseline 164 / 79 / 212).

Error against the same die's 3.3 V / 27 C frequency (`results/20261113T090000Z-stage/table.md`), pt, with the DR-0043 baseline:

| cell | `w3r65` | DR-0043 baseline | limit |
|---|---|---|---|
| row 4 span 27 C (3.6 V - 3.0 V), `ss` | **4.68** | 6.09 | 4.9 |
| row 4 span 27 C, `tt` / `ff` | 2.90 / 1.76 | 3.51 / 2.00 | 4.9 |
| row 4 span, worst over -40 / 27 / 85 C, `ss` | 4.68 (4.66 / 4.68 / 4.45) | 6.11 / 6.09 / 5.77 | 4.9 |
| row 5 `ff` 85 C / 3.0 V | +2.08 | +1.66 | +8.8 |
| row 5 `ff` -40 C / 3.0 V | -4.66 | -4.40 | -10.8 |
| `tt` 85 C / 3.0 V; `ss` 85 C / 3.0 V | +0.18; -1.58 | -0.28; -2.81 | |

The `ss` span cut is 1.41 pt. DR-0033's need was 0.61 pt (narrowest die), 1.18 (median), 1.79 (widest): the candidate covers the narrowest and median dies and not the widest (1.79 pt, i.e. 0.38 pt short). Whether the
widest die clears is a Monte Carlo question and stays with #317.

Trim range 0x00 / 0xFF at 3.3 V / 27 C (`results/20261113T080000Z-calib/ends_table.md`, MHz; baseline = 0044): `tt` 28.13 / 74.97 (28.61 / 76.38), `ff` 36.85 / 94.45 (37.57 / 96.92), `ss` 22.26 / 60.81 (22.62 / 61.37).
The row-2 window 28.8-67.2 MHz is covered at both ends exactly as at baseline (`tt` 0x00 is below 28.8, `tt` 0xFF above 67.2). The `ss` die's 0xE0 code reads 48.18 MHz against 49.75 at 0xD8 (block-boundary dip, DR-0014 pattern); not re-characterised here.

**Running Iq (row 8, 108 cells, `results/20261113T093000Z-iq`, `table_vs_l07.md`):**

| code | delta vs the rebuilt-layout extraction (L 0.7) | delta vs L=1u control |
|---|---|---|
| 0x00 | -0.14 .. +0.12 % | -0.58 .. +0.15 % |
| 0x80 | -0.46 .. +0.52 % | -0.77 .. +0.53 % |
| 0xC0 | +0.42 .. +2.74 % | +0.21 .. +2.66 % |
| **0xFF** | **+18.4 .. +28.1 %** | **+16.9 .. +28.3 %** |

Cells above 500 uA: 22 of 108 (baseline 16, L=1u control 17); maximum 918.9 uA (`ff`, 0xFF, 3.6 V, 85 C) against 759.0 uA (779.4 control). Shorter base R and 3x W lower the series resistance at high codes, so the charge current
rises with the code; at 0xFF it is a double-digit increase. The ratified limit is "< 500 uA running" (DR-0003 Row 4); the high-code cells above it already existed (0011, 0041, 0044) and this candidate widens that set.

## Acceptance against #337

- Criterion 1 (measurement): done, on 3 temperature points (the repo's PVT grid), not 5; no 5-point grid exists in `sim/pvt`.
- Criterion 2: `ss` span 4.68 <= 4.9 **met**; trim range **met** (no regression); running Iq **not met** at code 0xFF (+18-28 %, 6 more cells above 500 uA, max 918.9 uA), within +3 % at codes <= 0xC0.
- Criterion 3 (schematic, regen, layout, DRC, LVS, extraction re-run): **not started**, gated on the ruling.
- Criterion 4: windows unchanged, no per-corner trim, 0004 untouched.

## Decision / open

Do not adopt. Two decisions are needed from the operator before any design edit:

1. Does `w3r65` (3x W **and** base R at 65 %) count as one re-centred switch-sizing change (0037's question)?
2. The Iq cost: the candidate clears the `ss` span but raises 0xFF running Iq by 18-28 %. Either the "< 500 uA running" cells at the top code are accepted as already off-reference (0011 / 0044), or the candidate needs a variant (e.g. a smaller W step with base R re-centred) and a re-run. 2x W re-centred was already rejected (5.0-5.2 pt, 0037).

If the ruling is "no", the close-out is a record of the no-knob outcome; `ss` span then stays 6.09 pt on the extraction.

## Not done

Schematic / netlist / layout edits, DRC, LVS, extraction of the candidate (this is text-edited, old wiring parasitics), 500-die Monte Carlo (stays on #317), `klt yield` grading and signoff rows (#202). Tool gap: none new.
