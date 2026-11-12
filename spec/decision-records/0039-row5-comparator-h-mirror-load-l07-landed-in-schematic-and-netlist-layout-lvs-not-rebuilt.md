# 0039: Row 5: comparator-H mirror-load L 0.7 um is landed in the schematic and regenerated netlists; layout / LVS are not rebuilt

- **Status**: proposed - extends [0038](0038-row5-comparator-h-mirror-load-l07-clears-ff-hot-low-v-on-three-die-stage-rerun-schematic-not-yet-changed.md)
  (which left the schematic unchanged). Changes no ratified row or window, adds no per-corner trim and no temperature-dependent element
  ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0038 showed, on the DR-0028 P3 extraction with `X$65` / `X$66` (MLOADA / MLOADB) at L 0.7 um, `ff` 85 C / 3.0 V going +6.93 -> +1.65 pt
(limit +8.8) and left the schematic alone because the edit breaks `design/check-netlist-consistency.py` until the tracked bench copies and
provenance pins are refreshed (the DR-0028 precedent, commit `affc8a64`, did that together with a layout rebuild).

## Decision

Land the edit in the design sources, following the DR-0028 precedent for the bench copies:

- `design/rcosc_comparator.sch`: `MLOADA` / `MLOADB` `L=1u` -> `L=0.7u` (comparator H only; `rcosc_comparator_p.sch` has no MLOAD instance).
- `design/netlist/{rcosc_top,pvt_tb,smoke_test}.spice` regenerated with `design/regen-netlist.sh` (`klt netlist`).
- The five tracked `sim/**/rcosc_top_schematic.spice` bench copies get the same two lines; `sim/trim-transition/provenance.json` and
  `sim/waveform/provenance.json` `source_sha256` / `extracted_sha256` are re-pinned to the new netlist. These are tracked bench inputs, not
  `sim/*/results/*`; archived results keep the netlist they were simulated on (append-only check unaffected).
- `python3 design/check-netlist-consistency.py`: **OK** (was 22 problems with the schematic edit alone).

## Evidence and what it does not show

- `variant.first_stage(<P3 source>, load_l=0.7)` (the DR-0038 sim-only variant) differs from its source in exactly two lines, `X$65` and `X$66`
  `L=1U -> 0.7U`, W unchanged - the same two devices the schematic edit changes. So the DR-0038 numbers are for this change.
- **Not done:** no new SPICE was run for this record. The DR-0038 re-run is on the P3 *extraction* (layout parasitics, trim-ladder x0.70), not on the
  schematic netlist now committed, so "re-confirmed on the real regenerated netlist" is **not** established; the schematic netlist carries no
  such parasitics and would need its own per-die calibration scan.
- **Layout / LVS:** not rebuilt. `layout/cells/rcosc_comparator.gds`, `rcosc_top.gds`, `layout/lvs_ref/*` and `layout/reports/*` still describe L=1u;
  an LVS of the layout against the new schematic would mismatch on the two devices. `layout/run_checks.sh` needs klayout-tools 0.4.0 /
  klayout 0.30.12 (host `klt` is 0.9.2), and whether comparator H and L share a layout cell is unverified. Needs a rebuild increment.
- **Residual:** ratified Iq sweep (`sim/iq`) and real-model local-mismatch Monte Carlo not run (see 0038 "Not done"; Monte Carlo stays with #317).

#321 stays open: AC 1 (netlist change) and the netlist-consistency part of AC 4 are met; the real-netlist re-run, layout/LVS, Iq and Monte Carlo remain.
