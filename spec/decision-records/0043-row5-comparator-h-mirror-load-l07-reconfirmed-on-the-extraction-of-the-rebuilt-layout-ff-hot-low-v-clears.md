# 0043: Row 5: comparator-H mirror-load L 0.7 um re-confirmed on the extraction of the rebuilt layout; `ff` 85 C / 3.0 V clears

- **Status**: proposed - extends [0042](0042-row5-comparator-h-mirror-load-l07-layout-rebuilt-drc-clean-lvs-match-extraction-reconfirm-and-mismatch-open.md)
  and [0040](0040-row5-comparator-h-mirror-load-l07-reconfirmed-on-the-real-schematic-netlist-layout-lvs-iq-and-mismatch-open.md).
  Changes no ratified row or window, adds no per-corner trim and no temperature-dependent element ([0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #321), pending operator ratification

## Context

0040 cleared the lever on the schematic netlist but noted the +6.9 pt failure was a property of the *extracted* netlist; 0042 rebuilt the layout and left the extraction-based re-confirmation open.

## Evidence (all `klt sim` on the batch fleet via `--batch-set`, `--wait-for-capacity 600`; `sim/row45-rerun/results/`, append-only)

- **Extraction** `20261112T200335Z-extract-l07`: `sim/cmph-fix/gen_dut.py` (klayout-tools 0.4.0 in the throwaway venv, never the host `klt`) on the rebuilt `layout/cells/rcosc_top.gds`, same P3 transformation as DR-0028. `X$65` / `X$66` (MLOADA / MLOADB) read `L=0.7U` (they read `L=1U` in `sim/cmph-fix/`).
- **Per-die codes** re-derived by scan (`20261112T201500Z-calib-extracted-l07`, 14 requests, 27 C / 3.3 V): **tt 164, ff 79, ss 212** (48 MHz target: 47.91 / 47.97 / 48.04 MHz), the same codes as DR-0038's variant.
- **Stage re-run** (`20261112T203500Z-stage-extracted-l07`, 9 requests, `table.md`): error against the same die's 3.3 V / 27 C frequency.

| cell | extraction, L 0.7 um | limit |
|---|---|---|
| `ff` 85 C / 3.0 V (row 5, the failing cell) | **+1.66 pt** (was +6.9) | +8.8 |
| `ff` -40 C / 3.0 V | -4.40 pt | -10.8 |
| `tt` 85 C / 3.0 V | -0.28 pt | |
| `ss` 85 C / 3.0 V | -2.81 pt | |
| row 4 span at 27 C (3.6 V - 3.0 V): `ff` / `tt` / `ss` | 2.00 / 3.51 / 6.09 pt | 4.9 |

  This matches DR-0038's sim-only variant (+1.65 pt, `ss` span 6.09) and confirms DR-0040's reading that the failure was extraction-specific; the extraction delta (-5.2 pt) is larger than the schematic's (-2.92), cause still not isolated.
- The stage re-run here is **frequency only**: the DR-0028 probe net numbers do not apply to the re-extracted netlist (nets are renumbered), so `stage_attribution.py` was not run and `gen_row5_extracted.py` keeps only `f_ta` / `f_tb` / `fosc`. No stage attribution is claimed.

## Not done / open

- `ss` row 4 span 6.09 pt exceeds the 4.9 window; this is the pre-existing failure DR-0038 reports at base (about 6.1), attributed to the bank switches (0037), not this lever. Not re-baselined here.
- Trim range (row 2) and the ratified Iq sweep were run on the schematic netlist (0041), **not** on the extraction.
- Real local-mismatch Monte Carlo stays with #317 (steep one-sided slope, L 1.1 um = +10.4 pt per 0036): residual risk.
- Tool gap (generic): none new; `layout/run_checks.sh` pin mismatch as in 0042.

#321 stays open: the extraction-based `ff` hot / low-V cell now clears; the items above remain.
