# 0041: Row 5: comparator-H mirror-load L 0.7 um leaves trim range and running Iq unchanged on the real schematic netlist; layout / LVS and mismatch Monte Carlo stay open

- **Status**: proposed - extends [0040](0040-row5-comparator-h-mirror-load-l07-reconfirmed-on-the-real-schematic-netlist-layout-lvs-iq-and-mismatch-open.md).
  Changes no ratified row or window, adds no per-corner trim and no temperature-dependent element
  ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0040 left two SPICE items open on the real regenerated schematic netlist (`MLOADA` / `MLOADB` L 0.7 um): trim range (DR-0003 Row 2) and the running
supply current (DR-0003 Row 4, "< 500 uA running"; the issue text calls it row 8). Both are run here, each against a same-netlist control with the two loads at L=1u
(`CONTROL_L1=1`). All SPICE is `klt sim --batch-set ... --wait-for-capacity 600` on the batch fleet; results are append-only under `sim/row45-rerun/results/`.

## Evidence

**Trim range**, 0x00 / 0xFF at 3.3 V / 27 C, MHz (`20261112T193941Z-ends-schematic`, control `...-ends-schematic-control-l1`):

| die | 0x00, L 0.7 | 0x00, control | 0xFF, L 0.7 | 0xFF, control |
|---|---|---|---|---|
| tt | 26.595 | 26.639 | 85.425 | 85.202 |
| ff | 35.875 | 35.908 | 111.638 | 111.376 |
| ss | 20.651 | 20.647 | 67.543 | 67.335 |

Every end moves by 0.3 % or less (largest: tt 0x00 -0.17 %, ff 0xFF +0.24 %, ss 0xFF +0.31 %). Each die's range still brackets 48 MHz with the same margin as the control.

**Running Iq** (`20261112T194358Z-iq-schematic`, control `...-iq-schematic-control-l1`, `table.md`): `-i(VDD)` averaged over clk rising edges 5..25 (the `sim/iq` `iq_run`
window), codes 0x00 / 0x80 / 0xC0 / 0xFF x 3.0 / 3.3 / 3.6 V x tt / ff / ss x -40 / 27 / 85 C = 108 cells per set. L 0.7 against control: -0.73 % to +0.33 % in every cell.
`gen_row5_iq_schematic.py` measures the average by integrating -i(VDD) on a 1 nF capacitor between the two edges, because `klt sim` emits each `.meas` at deck level and an
`AVG` window cannot reference an earlier measurement.

- **Cells above 500 uA exist in both sets and are not caused by this change.** 9 of 108 cells exceed 500 uA at L 0.7 (8 at code 0xFF, 1 at 0xC0; the smallest exceedance is `tt` 85 C / 3.6 V / 0xFF at 504.3 uA);
  the control exceeds it in the same cells. Maximum 692.7 uA (`ff`, 0xFF, 3.6 V, 85 C) against 693.5 uA in the control. This matches the off-reference exceedance already recorded in
  [0011](0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md) (fast die, hot, high supply, high code). The high codes are far from the per-die operating codes (tt 0xA0, ff 0x55, ss 0xCB).
- This is the `ff`/`tt`/`ss` endpoint subset of the ratified 7-corner grid (no `fs` / `sf`), run as a `klt sim` request set rather than through the local `sim/iq` driver. It is a base-vs-variant
  delta on the schematic netlist, not a replacement for the committed `sim/iq` record, and it is not a verdict on Row 4.

## Not done / open

- **Layout / LVS:** unchanged from 0039/0040. `layout/cells/rcosc_comparator.gds`, `rcosc_top.gds`, `layout/lvs_ref/*` and `layout/reports/*` still describe L=1u; whether comparator H and L share a
  layout cell is not verified; `layout/run_checks.sh` needs klayout-tools 0.4.0 and the host `klt` is 0.9.2. No LVS pass is claimed. This record's SPICE items do not touch the layout.
- **The extraction-based `ff` hot/low-V cell** (the +6.9 pt failure was extraction-specific, 0040) is not re-confirmed: it depends on the layout rebuild.
- **Real local-mismatch Monte Carlo:** not run; stays with the #317 campaign. Residual risk: the steep one-sided slope (0036: L 1.1 um = +10.4 pt).
- Why the schematic delta (-2.92 pt) is smaller than the extraction delta (-5.28 pt) is still not isolated.

#321 stays open: trim range and the Iq delta are now met on the schematic netlist; layout / LVS, the layout-dependent re-confirmation and the Monte Carlo remain.
