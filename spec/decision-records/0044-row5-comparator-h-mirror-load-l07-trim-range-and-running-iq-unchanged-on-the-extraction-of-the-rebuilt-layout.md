# 0044: Row 5: comparator-H mirror-load L 0.7 um leaves trim range and running Iq unchanged on the extraction of the rebuilt layout

- **Status**: proposed - extends [0043](0043-row5-comparator-h-mirror-load-l07-reconfirmed-on-the-extraction-of-the-rebuilt-layout-ff-hot-low-v-clears.md)
  and [0041](0041-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-schematic-netlist-layout-lvs-open.md).
  Changes no ratified row or window, adds no per-corner trim and no temperature-dependent element ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched).
- **Date**: 2026-11-13
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0043 left trim range (DR-0003 Row 2) and the running supply current (DR-0003 Row 4 "< 500 uA running"; the issue text calls it row 8) measured only on the schematic netlist (0041).
Both are run here on the extraction of the rebuilt layout (`results/20261112T200335Z-extract-l07`, MLOADA / MLOADB L=0.7U), against a same-recipe control: the P3 extraction of the previous layout
(`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, L=1U). Generators: `gen_row5_extracted.py calib` and the new `gen_row5_iq_extracted.py` (`CONTROL_L1=1` selects the control).
All SPICE is `klt sim --batch-set ... --wait-for-capacity 600` on the batch fleet; results are append-only under `sim/row45-rerun/results/`.

## Evidence

**Trim range**, 0x00 / 0xFF at 3.3 V / 27 C, MHz (`20261113T064105Z-ends-extracted-l07`, control `20261113T065500Z-ends-extracted-control-l1`):

| die | 0x00, L 0.7 | 0x00, control | 0xFF, L 0.7 | 0xFF, control |
|---|---|---|---|---|
| tt | 28.611 | 28.652 | 76.381 | 76.391 |
| ff | 37.571 | 37.717 | 96.921 | 98.203 |
| ss | 22.617 | 22.616 | 61.368 | 61.200 |

Every end moves by 1.3 % or less (largest: ff 0xFF -1.30 %). Each die's range still brackets 48 MHz.

**Running Iq** (`20261113T064105Z-iq-extracted-l07`, control `20261113T065500Z-iq-extracted-control-l1`, `table.md`): same integrator method and 20-period window as 0041,
codes 0x00 / 0x80 / 0xC0 / 0xFF x 3.0 / 3.3 / 3.6 V x tt / ff / ss x -40 / 27 / 85 C = 108 cells per set. L 0.7 against control: **-4.57 % to +0.18 %**; the lever does not raise the current anywhere.

- **Cells above 500 uA exist in both sets and are not caused by this change.** 16 of 108 cells exceed 500 uA at L 0.7 (control: 17); maximum 759.0 uA (`ff`, 0xFF, 3.6 V, 85 C) against 779.4 uA in the control.
  Same off-reference pattern as [0011](0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md) and 0041 (fast die, hot, high supply, high code). The extraction reads higher than the schematic
  (e.g. 759 vs 693 uA at that cell) because of parasitics, in both sets.
- This is the `ff`/`tt`/`ss` subset of the ratified 7-corner grid (no `fs` / `sf`), a base-vs-variant delta, not a replacement for the committed `sim/iq` record and not a verdict on Row 4.

## Acceptance status for #321

Row 5 `ff` 85 C / 3.0 V +1.66 pt on the extraction (0043); `ff` -40 C, `ss`/`tt` hot and row 4 on the extraction (0043); trim range and Iq on the extraction (this DR); netlist-consistency (0039); layout rebuilt, DRC clean, LVS match (0042).

## Not done / open

- Real local-mismatch Monte Carlo stays with the #317 campaign. Residual risk: steep one-sided slope (0036: L 1.1 um = +10.4 pt; deterministic +/-0.1 um in 0038 gave +0.69 to +2.48 pt hot).
- `ss` row 4 span (6.09 pt vs 4.9) is the pre-existing bank-switch failure (0037), not this lever.
- Why the extraction delta (-5.2 pt) exceeds the schematic's (-2.92 pt) is still not isolated.
