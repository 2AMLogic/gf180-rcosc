# 0020: Startup-time row — "within trimmed accuracy" band definition left ambiguous, bench reports all readings

- **Status**: ratified 2026-10-16 (operator ruling, batch 8 Q3 option 1: relative startup settling); the ratified 10 µs bound is **not** changed
- **Date**: 2026-10-08
- **Decided by**: Builder agent, issue #78 (proposal); ratified by the operator 2026-10-16 (issue #82)

## Context

The ratified row reads "Startup time ≤ 10 µs to within trimmed accuracy"
(README target-spec table, DR-0002/DR-0003). Issue #78 adds the first bench
for it (`sim/startup/`). The phrase "trimmed accuracy" is ambiguous in two
independent ways, and the ratified record does not resolve either:

1. **Which band.** The README carries more than one post-trim accuracy
   figure: ±1.1% (DR-0003's original at-calibration-point figure, still the
   figure in characterization report rows 5-6), −2.9%/+2.0% (DR-0017, the
   at-calibration-point worst case after the comparator respin), and
   +8.8%/−10.8% (DR-0017, full −40…+85 °C range). "Within trimmed accuracy"
   could mean any of them. They differ by an order of magnitude in
   strictness.
2. **Relative to what.** The band could be centred on the ratified 48.000 MHz
   target or on the corner's own settled frequency. The 48 MHz target is not
   reachable at most corners (DR-0005/DR-0006: trim-range shortfall), so an
   absolute-48 MHz reading would make the row fail for a reason that has
   nothing to do with startup, and would double-count rows 2, 5 and 6.
   *(Annotation, 2026-11-08: the trim-range-shortfall rationale is stale,
   since later records calibrate inner-range, per the operator triage of
   2026-10-16 on #82. The double-counting argument still carries the decision
   on its own.)*

Two further bench assumptions are not in the ratified spec at all: the
supply-ramp rate and the trim code held during startup.

## Decision

Nothing in the ratified spec is changed or relaxed. The bench makes these
*measurement* choices, each reported openly and none of them silently picking
the lenient reading:

- **Band centre**: the corner's own settled frequency (mean period over the
  last 2 µs of a 20 µs run, which must itself be steady to ±0.5%). This
  isolates startup transient from absolute accuracy, which rows 5-6 already
  grade. The settled frequency is reported per corner next to 48 MHz.
- **Band width**: settle time is reported for **all three** readings (±1.1%,
  ±2.9%, ±10.8%). The **primary verdict uses ±1.1%**, the strictest
  ratified figure; the row is called a pass only if it passes there. A
  pass at only a looser band is recorded as such, not as a pass.
- **Time origin**: start of the supply ramp (t = 0), so ramp time counts
  against the 10 µs budget (conservative; ST's `tsu(HSI48)` is measured from
  enable). First-edge time and VDD-90% time are recorded too.
- **Supply ramp**: linear 0 → VDD in 1 µs, trim pins following VDD, trim code
  0xA3 (post-#60 calibration code) held. A slower ramp, or a per-corner
  calibrated code, are untested assumptions (see Consequences).
- **Period sampling**: 8-cycle mean period, because single-edge times from
  the transient solver carry ~0.2 ns numerical noise (~0.7% of a cycle),
  comparable to the ±1.1% band.
- **Non-start**: fewer than 20 clk edges in the run, or fewer than 20 in the
  last 2 µs, is reported as `NON-START` and counts as a failure.

The operator ratified this definition on 2026-10-16 (issue #82): relative
settling to each corner's final mean period, +/-1.1% primary band over
8-cycle windows, <= 10 µs from the start of the 1 µs ramp, fixed trim
`0xA3`, with all diagnostic bands and the steady-tail / non-start checks
retained. A relative-settling pass can hold while the clock is stably
off-target; it is not a claim of target-accurate or USB-ready availability.

## Alternatives considered

- **Pick ±10.8% (full-range band) as the "trimmed accuracy"** — rejected:
  the most lenient reading would make the row easiest to pass; choosing it
  silently is exactly what the issue forbids.
- **Absolute ±1.1% of 48 MHz** — rejected as the primary: unreachable at
  most corners for reasons owned by rows 2/5/6 (DR-0005/0006), so it
  measures trim range rather than startup.
- **Time origin at ramp end** — rejected as primary (less conservative);
  available from the committed edge times.

## Consequences

- Row 10 of the characterization report states its band and origin.
- The 63-point factorial ran on the batch fleet (runner v11, 2026-11-06,
  `sim/startup/results/20261106T052948Z/`): **61/63 PASS, 2 FAIL**
  (`ff`/-40 °C at 3.3 V and 3.6 V fail the settled-tail steadiness check).
  This is a **simulated** result (ngspice-46 transient on a pre-layout
  schematic netlist, gf180mcuC, open_pdks `f6eeac7`); nothing in this record
  is a silicon measurement.
- **Which design that run grades.** `20261106T052948Z` grades the
  **pre-re-centre schematic at trim `0xA3`**, i.e. before DR-0023 (settled P3
  netlist, calibration code `0xA9`) and DR-0028 (comparator-H output-stage
  fix). It is kept as append-only history of that design. It is not the
  startup status of the current design.
- **Current-design startup evidence** (`main`, EE/market-key reconciliation):
  `sim/startup-settled/results/20261106T061500Z/` (settled P3 netlist, `0xA9`,
  DR-0020 analysis): 61/63 start, `fs`/-40 °C at 3.3 V and 3.6 V NON-START
  (a real design failure, #227); and
  `sim/startup-settled/results/20261106T0735Z/` (same netlist with the DR-0028
  comparator-H fix): 63/63 pass the primary band, worst settle 1.54 µs, 0
  NON-START. The two `ff`/-40 °C tail failures above do not reproduce on the
  current design (tail deviation 0.04-0.05% there). Row 10 of the
  characterization report records both, labelled by design revision.
- **Cause of the two `ff`/-40 °C FAILs (not root-caused).** The EE key found a
  slow µs-scale period drift on the pre-re-centre netlist (not edge jitter),
  absent on the DR-0028 stage. That is consistent with the old comparator-H
  output stage; this record does not claim a diagnosis.
- **Open question for the operator: the fixed trim code.** The 2026-10-16
  ruling names `0xA3`, which was the calibration code of the pre-re-centre
  schematic. The current design's tt/27 °C/3.3 V calibration code is `0xA9`
  (DR-0023); DR-0029 (Proposed) would move it to `0xA4`. The settled-netlist
  startup runs above use `0xA9`, so they do not literally conform to "`0xA3`".
  Candidate wording for a ruling: "the design's tt/27 °C/3.3 V calibration
  code, held fixed (not recalibrated per corner); `0xA3` for the run cited
  for the pre-re-centre design". This record deliberately **states both
  codes and picks neither**; the ruling is requested separately and the
  definition's trim-code clause is unchanged until it is given.
- Not tested: slower supply ramps, per-corner calibrated trim codes, post-layout
  (PEX) startup, and mismatch-induced failure to start (a separate robustness
  check per DR-0019).
