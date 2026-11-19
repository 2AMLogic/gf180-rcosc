# 0047: Row 4: no `w<K>r<P>` bank variant clears the `ss` span without a code-0xFF running-Iq rise; measured floor

- **Status**: proposed - measurement only. Changes no ratified row or window, no schematic, netlist or layout file; per-die basis
  ([0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md)) unchanged; no per-corner trim; [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched.
- **Date**: 2026-11-19
- **Decided by**: Loom Builder (issue #337), pending operator ratification

## Context

The operator ruling on #337 (2026-11-18) kept `w3r65` as one change but did not adopt it ([0045](0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md):
`ss` span 4.68 pt, 0xFF Iq +18..28 %). It asked for a lower-Iq variant, or the measured floor. Search space: the same one-change family, K x W on the 16 bank pass devices with the base resistor
`X$91` shortened to P % so the `ss` die stays centred at code 212. Basis: extraction of the rebuilt layout with the variant as netlist text (layout not re-extracted), as 0045.
Evidence: `sim/row4-iq-variant/` (README has commands).

## Evidence

Re-centring (`results/20261118T230500Z-ss-recentre/table.md`): `ss` at code 212 reads 48.39 (w2r80), 47.72 (w2.5r75), 48.37 (w1.5r90) MHz against the baseline 48.038 MHz at 212 (`sim/row45-rerun/results/20261112T203500Z-stage-extracted-l07/table.md`, `ss` ref row), so the baseline code stays.

| variant | `ss` span 27 C (-40 / 85 C), pt | 0xC0 Iq delta | 0xFF Iq delta | cells > 500 uA (0xC0+0xFF, of 54) | max Iq uA |
|---|---|---|---|---|---|
| baseline (0044/0045, 1x) | 6.09 (6.11 / 5.77) | - | 0 | 15 | 759.0 |
| w1.5r90 | 5.42 (5.44 / 5.22) | +0.23..+1.05 % | +4.76..+7.60 % | 16 | 802.6 |
| w2r80 | 5.08 (5.06 / 4.89) | +0.29..+1.80 % | +9.54..+14.88 % | 17 | 844.1 |
| **w2.5r75** | **4.84** (4.77 / 4.61) | +0.18..+2.01 % | **+12.09..+19.20 %** | 20 | 868.3 |
| w3r65 (0045) | 4.68 | +0.42..+2.74 % | +18.4..+28.1 % | 21 | 918.9 |

Iq deltas are against the rebuilt-layout extraction (L 0.7 um), `results/.../<v>-iq/table_vs_l07.md`. Cells above 500 uA are counted over the codes run (0xC0, 0xFF) - the same 54 cells (3 dice x 3 supplies x 3 temperatures) for every row, baseline included: 15 for the baseline (`sim/row45-rerun/results/20261113T064105Z-iq-extracted-l07`: 0xC0 3 + 0xFF 12) and 21 for `w3r65` (`sim/row4-w3r65/results/20261113T093000Z-iq`: 0xC0 3 + 0xFF 18). DR-0044/0045's four-code counts (baseline 16 of 108, `w3r65` 22 of 108, over all of 0x00/0x80/0xC0/0xFF) are a different, larger basis and are not row-comparable with the 54-cell figures above. The other codes are unchanged within 3 % in 0045.

The `ss` span and 0xFF Iq trade off monotonically along the family; no point has both. The DR-0044 band (-4.6..+0.2 % vs the L=1u control) is not met even by w1.5r90 (+4.8 % at 0xFF) while its span (5.42) is still 0.5 pt above 4.9.

## Measured floor (for the operator)

- Best `ss` span at no Iq regression: not reached in this family; baseline 6.09 pt at 0 %. The smallest step tried (1.5x) already costs +4.8..+7.6 % at 0xFF for 0.67 pt of span.
- Best 0xFF Iq at span <= 4.9: **w2.5r75, +12.09..+19.20 % (max 868.3 uA)**, `ss` span 4.84 pt. (w2r80 is 5.08 at 27 C, over the window.)

## Die population (ruling item 2)

Codes and the 0-of-1500 count below are DR-0032's baseline (1x) population, not a variant measurement: per-die calibration codes (500 dies per corner, 27 C / 3.3 V) `tt` 161-168, `ff` 73-83, `ss` 210-215. The variant dies were not re-calibrated; the only variant data behind this section is the nominal `ss` die scan at code 212 (`sim/row4-iq-variant/results/20261118T230500Z-ss-recentre`, one die, not a population).
- Dice calibrating at 0xFF (where the 18-28 % / 12-19 % rise was measured): **0 of 1500** in the baseline population, extrapolated to `w3r65` and w2.5r75 (their calibrated codes were not re-derived); none within 7 codes of a rail.
- The `ss` dice (500) calibrate at 0xD2-0xD7, above the 0xC0 point (<= +2.7 %) and below 0xFF; Iq was run at 0xC0 and 0xFF only, so the rise at 0xD2-0xD7 is **not measured** here (it lies between those two); `tt` and `ff` dice (1000) calibrate at or below 0xA8, where 0045 reports <= +3 % - baseline-sweep readings, extrapolated to the variants because their `tt` / `ff` codes were not re-derived (their stage cells were not run).
- Consequence: the 0xFF rise applies to the row-8 code sweep, not to any calibrated die. Whether row 8 is graded on the sweep or on the calibration code is the open question behind accepting the cost; a measurement at 0xD2-0xD7 on the `ss` die would settle it.

## Decision / open

Recorded, not adopted. No variant in the one-change family passes; per the ruling this returns to the operator with the floor above (`loom:operator` re-applied). Not done: schematic, netlist, layout, DRC, LVS, extraction; tt/ff stage cells for the variants; Iq at 0xD2-0xD7; 500-die Monte Carlo (#317). Tool gap: none new.
