# 0049: Row 8: comparator-H tail W x0.85 clears 500 uA at every calibrated-code cell with near-zero collateral; no variant in the screened family clears a 0xFF basis

- **Status**: proposed - simulation-only screen. Adopts nothing: no schematic, netlist-of-record
  or layout file changes, no ratified row, window or Iq metric basis touched
  ([0009](0009-running-iq-metric-basis-and-partial-trim-range-recovery.md) unchanged); picks no
  trim-code basis for row 8 (that ruling stays with the operator on #337).
- **Date**: 2026-11-21
- **Decided by**: Loom Builder (issue #458), pending operator ratification

## Context

Row 8 (running Iq < 500 uA) fails at the fast corners: 559.4 uA on the item-5 campaign's fixed
window and 505.4 uA on the DR-0009 charge-integral basis at `ff` / 85 C / 3.6 V at the calibration
code, 759.0 uA at `0xFF` (DR-0044). [0046](0046-row8-running-iq-stage-attribution.md) attributed
the code-flat, temperature-driven share to comparator-H and named its sizing (tail W factor /
mirror-load L, the [0036](0036-row5-comparator-h-first-stage-is-the-supply-slope-lever-load-l-and-tail-screen.md) family) as the
lever. This record screens that lever and prices it on the rows it can hurt. The row-4 bank
question (#337) moves only the code-driven term and is explicitly not answered here: every figure
is reported at both the per-corner calibrated code and `0xFF`, whichever basis the operator rules.

## Decision (the screen's result)

**`tail_k=0.85` (comparator-H tail fingers X$39..X$46 at W x0.85, mirror loads untouched) is the
candidate**: it meets the strict 500 uA limit at **every one of the 27 calibrated-code cells**
(worst 474.5 uA at `ff` / 85 C / 3.6 V, -30.9 uA vs control, 0/27 cells at or over 500; control
1/27, worst 505.4) at the price of:

- **Row 4** (already failing on control, DR-0043): worst span 6.10 pt vs control 6.09 pt
  (+0.01 pt; the ss leg -3.36 / +2.74 vs -3.37 / +2.72) - no measurable harm.
- **Row 5**: pass; worst cold -4.44 % (ff/3V, control -4.40), worst hot +3.07 % (ss/3.6V, control
  +3.05), and the row-5 gate cell `ff` / 85 C / 3.0 V **improves** to +1.29 % (control +1.65).
- **Row 10**: zero lost-clock cells; **startup** (fs / -40 C, 3.3 and 3.6 V, DR-0020 10 us bound)
  passes at 0.92 / 0.91 us (control 0.93 / 0.91).
- **Comparator-H delay** at the limiting cell (ff, 3.0 V, 85 C): 1.96 ns vs 1.75 ns (+0.21 ns;
  2.16 ns at -40 C / 3.0 V, 1.96 ns at 85 C / 3.6 V).
- **Calibration codes unchanged** from control (`tt 0xA4 / ff 0x4F / ss 0xD4`): no re-centre, no
  trim-range shift (scan frequencies 47.594 / 47.689 / 47.655 MHz; worst calibration residue
  across the family 0.49 MHz).

`tail_k=0.70` also clears (worst 445.4 uA, -59.9 uA) but costs +0.59 pt of row-4 span (6.68 pt),
+0.40 ns of delay and a one-step re-centre on every axis (`0xA8 / 0x53 / 0xD8`) for 29 uA more
margin - dominated by x0.85 unless the margin is wanted.

**Negative result on a `0xFF` basis:** no variant in the screened family comes close - worst
`0xFF` cells are 632.4..758.0 uA (`tail x0.40` best, 6/27 cells over; control 759.0, 12/27). At
`0xFF` the current is bank-dominated (DR-0046: trim bank 252.8 uA at the same cell), so the
comparator-H lever **cannot** close a `0xFF`-basis row 8 at any sizing that still starts and holds
row 5; that basis needs the bank lever (#337's chain), not this one. The mirror-load lever alone
(`load_l=0.60`) is dead for row 8: 505.2 uA worst at the calibrated codes (-0.2 uA vs control).

## Alternatives considered

- **`tail_k=0.70 / 0.55 / 0.40`** - deeper steps clear row 8 with more margin (445.4 / 417.1 /
  390.3 uA) but monotonically buy it with row-4 span (+0.59 / +0.62 / +1.22 pt on an
  already-failing row) and delay (+0.40 / +0.61 / +0.88 ns); x0.55/x0.40 also re-centre two steps.
- **`load_l=0.60`** - no row-8 gain at calibrated codes; kept only as the delay-cheap control on
  the load axis (+0.09 ns).
- **`tail_k=0.70 + load_l=0.60`** - same calibrated-code Iq as x0.70 alone (445.3 uA), same row-4
  cost (6.65 pt), no advantage on either axis.

## Consequences

**Adoption (a separate issue) would need:** resizing the eight tail fingers X$39..X$46 to W x0.85
in the schematic and layout (one region, no other device moves - this campaign's `dut_check`
asserts exactly that diff), LVS re-verify and re-extraction, then re-running the rows 4/5/8/10
benches on the new extraction. No re-centre for x0.85; a ratified x0.70 would re-centre the
calibration code one step on every axis. The DR-0036 hot-accuracy price scale applies to the
mirror-load axis, not the tail factor screened here; row 5 above is the measured price.

**Combination with the #337 bank variants (DR-0045, DR-0047, DR-0048):** screened **separately**.
This campaign holds the trim bank at the DR-0044 control state (`dut_check`: bank switches
untouched); DR-0045/0047/0048 held comparator-H at control. No combined-comparator-H + bank
operating point was measured, so the combined row-8 figure is **unknown** - deliberately not
predicted by adding independently measured deltas (out of scope, #458). Whichever bank variant
#337 adopts, the comparator-H x0.85 candidate's -31 uA at the calibrated-code worst cell is the
term this lever contributes; a combined screen on the adopted bank is the natural follow-up
campaign once #337 rules.

**Metric basis:** all figures are the DR-0009 charge integral over clk rising edges 5..25 on the
DR-0044 extraction (sha256 `01e06dae...d16a1`, identical control DUT). Item-5's fixed-window
559.4 uA is a different basis (DR-0046) and is not compared here. The control's 27 `0xFF` cells
reproduce DR-0044's committed figures to -0.01..+0.01 % (back-to-back gate, n=27).

**Evidence:** `sim/row45-rerun/results/20261120T211042Z-row8-cmph-iq-screen/` (append-only):
variant DUTs + sha256 table, calibration scans, 27-cell calibrated-code and 27-cell `0xFF` Iq
grids, t_cmp_h probes, fs/-40 C startup waveforms per variant, `table.md` (all tables above),
`klt sim --batch-set --backend batch --wait-for-capacity 600` receipts for every unit. Fleet
note: five wave-2 jobs from the interrupted first pass were accepted but never launched
(`klt-sim-f786be451eaf`, `-95b0932e498b`, `-c2d8ea7a9ec0`, `-210725089089`, `-ebb9f7985311`;
pending, no status.json after 6 h) and were replaced by fresh submissions; one completed job
(`klt-sim-5d95a9e76329`) was collected by `--attach`. Every request's report is present and
`pass` (208/208).

**Next lever if a `0xFF` basis is ruled:** the trim bank (#337 chain, DR-0047's family was
already exhausted on the row-4 side without an Iq rise - a bank redesign, #460 scope, or a
ladder-series-R increase is the remaining direction), not comparator sizing.
