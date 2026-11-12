# 0040: Row 5: comparator-H mirror-load L 0.7 um is re-confirmed on the real schematic netlist (-2.92 pt at `ff` 85 C / 3.0 V); layout / LVS, ratified Iq and mismatch Monte Carlo stay open

- **Status**: proposed - extends [0039](0039-row5-comparator-h-mirror-load-l07-landed-in-schematic-and-netlist-layout-lvs-not-rebuilt.md)
  and [0038](0038-row5-comparator-h-mirror-load-l07-clears-ff-hot-low-v-on-three-die-stage-rerun-schematic-not-yet-changed.md).
  Changes no ratified row or window, adds no per-corner trim and no temperature-dependent element
  ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0039 landed `MLOADA` / `MLOADB` L 0.7 um in `design/rcosc_comparator.sch` and the regenerated netlists but ran no SPICE: 0038's numbers are on the DR-0028
P3 *extraction*, and the schematic netlist has no layout parasitics, so its per-die codes do not transfer. This record is that re-run.

## Evidence (all `klt sim` on the batch fleet, `--wait-for-capacity 600`; `sim/row45-rerun/results/`, append-only)

Method as 0033 / 0038 (`gen_row5_schematic.py`, which reuses `gen_calib_requests.py` and `gen_stage_requests.py`; DUT = the `rcosc_top`
hierarchy of `design/netlist/pvt_tb.spice`, probes added only as 1 mOhm taps). Per-die code = the code whose 3.3 V / 27 C frequency is nearest 48.0 MHz:

| die | code | f at 3.3 V / 27 C, L 0.7 um | same code, control L 1.0 um |
|---|---|---|---|
| tt | 0xA0 (160) | 48.008 MHz | 47.986 MHz |
| ff | 0x55 (85) | 47.992 MHz | 48.096 MHz |
| ss | 0xCB (203) | 47.967 MHz | 47.841 MHz |

Scans: `20261112T170000Z-calib-schematic-coarse` (22 of 24 returned, see "Not done"), `T180000Z-calib-schematic-fine`, `T183000Z-calib-schematic-ss`;
control (the same DUT with the two loads at L=1u, `CONTROL_L1=1`): `T200000Z-...-control-l1`, `T203000Z-...-control-l1-lower`. The control's best codes equal the candidate's,
so both stage runs are at identical codes: `T190000Z-stage-schematic` (candidate) and `T210000Z-stage-schematic-control-l1` (control). The
`stage_attribution.md` headers still print the script's old constants (tt 165, ff 78, ss 212); the codes simulated are in the table above.

Measured eps (periods), percentage points against each die's own 3.3 V / 27 C frequency:

| cell | control L 1.0 | L 0.7 | limit |
|---|---|---|---|
| **`ff` 85 C / 3.0 V** | +5.72 | **+2.80** (-2.92) | +8.8 |
| `ff` -40 C / 3.0 V | -5.91 | -5.12 | -10.8 |
| `tt` 85 C / 3.0 V | +2.52 | +1.84 | |
| `tt` -40 C / 3.0 V | -5.88 | -5.81 | |
| `ss` 85 C / 3.0 V | +0.54 | +0.16 | |
| `ss` -40 C / 3.0 V | -5.30 | -5.59 | |
| row 4 span `tt` 27 C | +1.89 | +2.02 | 4.9 |
| row 4 span `ff` 27 C | +0.93 | +1.40 | 4.9 |
| row 4 span `ss` 27 C | +3.46 | +3.31 | 4.9 |

- The expected reduction (2.3-2.8 pt, about 2.2 needed) is reproduced: -2.92 pt on the same netlist. It is smaller than 0038's +6.93 -> +1.65 (-5.28) on the
  extraction; the cause of that difference (parasitics, the extraction's trim-ladder scaling) is not isolated here. No cell regresses past its window; the largest worsening is `ff` row 4 span +0.47 and `ss` -40 C -0.29 pt.
- **The schematic control is already inside the window (+5.72 vs +8.8)**: the +6.9 pt failure is a property of the extracted netlist, not of the schematic. This
  record therefore confirms the lever direction and size on the schematic netlist; it does not replace 0038's extraction-based cell result.

## Not done / open

- **Trim range (row 2) and the ratified Iq sweep (`sim/iq`, row 8)** on the new netlist: not run here.
- **Layout / LVS:** unchanged from 0039 (layout still describes L=1u; `layout/run_checks.sh` needs klayout-tools 0.4.0; comparator H / L layout-cell sharing unverified).
- **Real local-mismatch Monte Carlo:** not run; stays with the #317 campaign. The steep one-sided slope (0036: L 1.1 um = +10.4 pt) is the residual risk.
- Coarse scan jobs `request_tt_c90` / `request_tt_cF0` (`klt-sim-78b085eb601f`, `klt-sim-8a94be163648`) had not returned after three attach attempts
  (~15 min) and the fleet has no cancel; they are not used by any number above.

#321 stays open: AC 1, AC 2 (schematic netlist) and the SPICE part of AC 3 for rows 4 / 5 are met; trim range, Iq, layout/LVS and Monte Carlo remain.
