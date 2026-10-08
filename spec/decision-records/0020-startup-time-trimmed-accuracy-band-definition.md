# 0020: Startup-time row — "within trimmed accuracy" band definition left ambiguous, bench reports all readings

- **Status**: proposed (surfaced for ratification; the ratified bound is **not** changed)
- **Date**: 2026-10-08
- **Decided by**: Builder agent, issue #78 (needs human ratification of the primary band)

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

A human should ratify (or replace) the primary band and the time origin; this
record then becomes the definition. Until then the characterization report
states the verdict together with the band it holds at.

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
- The 63-point factorial was **not** obtainable on the Spot fleet at the time
  of this record (runner/client klt version mismatch, see
  `sim/startup/README.md`); only two single-corner local probes exist.
  Row 10 therefore reports partial evidence, not a factorial verdict.
- Not tested: slower supply ramps, per-corner calibrated trim codes, post-layout
  (PEX) startup, and mismatch-induced failure to start (a separate robustness
  check per DR-0019).
