# 0051: Item 6: seeded-defect negative controls per statistical row set, and the 0x7E->0x7F sensitivity miss resolved by timing resolution

- **Status**: proposed - harness and evidence plan only. Joins the pending ratification of
  [0019](0019-statistical-vs-deterministic-spec-rows-and-monte-carlo-evidence-plan.md)-family records (DR-0019 section 2 and DR-0022
  section 3 are `proposed` and are not edited here). No ratified row, window, target yield (99 %),
  confidence (95 %) or production sample count (500) changes; no design file changes.
- **Date**: 2026-11-23
- **Decided by**: Loom Builder (issue #461), pending operator ratification

## Context

Item 6 stays `negative_control_not_detected` even for a passing design because the DR-0019 section 2
control (sw_stat_mismatch = 3, a 3x mismatch-inflated run) leaves the yield at its nominal value in a
cell with margin (detected in 2 of 12 measurement cells in DR-0030, 2 of 12 in DR-0032). A 3x draw of a
design with margin is not known-bad; `klt yield`'s contract asks for a known-bad variant of the same
testbench. Separately the 0x7E->0x7F sensitivity check missed its 7-13 band (4.99x for 10x) and was
attributed, untested, to `tran 200p`.

## Decision

**Add a seeded physical defect per row set, in addition to (never replacing) the 3x and zero controls.**
Each is written into the generated control deck before the per-die calibration, with the same seed,
draw identities, probes and grading expressions as the nominal (a test asserts the control block is
byte-identical), so a measurement stuck at its nominal value makes the control miss.

| row set | defect (component, polarity, magnitude) | expected failing observable |
|---|---|---|
| 2 | trim-ladder base segment `X$91` drawn 4.0x too long (+36 um): the calibration runs onto a rail | `s1_resid_abs_pct`, `s1_headroom` |
| 4 | resistor 70 kohm + diode-connected `nfet_03v3` from vdd to the timing-capacitor plate (adds supply-dependent charge current; not proportional to vdd) | `s2_margin_pct` |
| 5 | reverse-biased junction leak plate->vss, `IS = 1e-8 A`, `XTI=3`, `EG=1.11` (rises ~2 decades 27->85 C; the 27 C calibration trims out its static part) | `s3_margin_pct` |

Magnitudes were derived on the deterministic zero-mismatch bench before any pilot draw
(`sim/mc/results/20261123T174327Z-ctrl-derivation/README.md`, five rounds including the rejected
candidates). **The row-4 magnitude did not meet its pre-fixed rule** (`s2_margin_pct <= -1.0` at tt and ff
on the deterministic draw): no bench-level supply-dependent defect on this DUT reached it without
exhausting the trim range (50 kohm pins ff at code 0). 70 kohm, the strongest candidate with all corners in
range, was carried and is reported as it falls.

**Detection is only the pinned grader's per-measurement verdict** (`klt yield-samples --negative-control`,
`klayout-tools[yield]==0.8.0`: lower empirical yield with non-overlapping exact CIs). A cell whose nominal
pass fraction has an exact upper bound below 0.99 is `nominal_fails`: listed, deferred to #317, never counted.

**The sensitivity miss is a timing-resolution limit of the 200 ps step.** On matched draws, `tran 50p`
puts the 0x7E->0x7F ratio at 9.88 (200 ps: 5.59), inside the unchanged 7-13 band; the 0x7F->0x80 ratio is
10.04 / 10.00.

## Pilot evidence (observed; carries no design-yield claim)

DUT `sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice` (sha256 `01e06dac...4d16a1`,
the DR-0043 extraction), N = 40 per corner, seed 20261008, batch backend, pilot-only limits copy with
`min_samples = 40` (production floor 500 unchanged in `limits_main.json`). Inputs/reports:
`sim/mc/results/20261123T174809Z-ctrl-pilot/`; grades `.../20261123T182646Z-ctrl-pilot-grade/`. All 24
yield verdicts have n = 40, 0 errored, 0 unmeasurable, 0 censored. Zero-mismatch control passes (codes 164/79/212).
Nominal pass fraction 40/40 (exact 95 % CI 0.912-1.000) in every cell except `ss` row 4 (0/40).

Twelve measurement verdicts for the seeded defect: **10 detected**; `ff` row 4 **not detected** (control
yield 40/40: the 70 kohm leak is too weak there, as the derivation predicted); `ss` row 4 **nominal fails,
deferred to #317** (not counted). Detected: row 2 both measurements at tt/ff/ss (control 0/40), row 4 tt
(8/40), row 5 tt/ff/ss (0/40). The 3x grades keep their existing form in `yield_<p>_row{2,4,5}.json`: all
12 `not_detected`.

## What the full-campaign grade would be (hypothetical, not asserted)

With a passing design and these controls detected at N = 500, `klt signoff` would read item 6 as
`unratified_rows` while DR-0019 remains `proposed` (`met` once ratified). `ff` row 4 would remain
`negative_control_not_detected` until a stronger or different row-4 control is defined. The committed
`signoff/signoff-report.json` is not changed; the re-grade stays with #202. #317's "Negative controls"
line needs re-curation to include these controls.

## Alternatives considered

- Per-row mismatch-scale sweep: rejected for the pilot; a scale large enough to fail a cell with margin
  moves the distribution rather than seeding a known fault, and cannot catch a stuck measurement chain.
- Widening the 7-13 band: rejected (instructed); not needed.
- A local checker instead of the grader verdict: rejected; the pinned `klt yield` expressed every control.

## Consequences

- Row 2 and row 5 gain a control that is detected in every cell whose nominal passes (pilot).
- Row 4 `ff` stays undetected; follow-up is a stronger or alternative supply-dependent defect.
- Pilot verdicts are not item-6 evidence for the design. Production campaign (#317) must re-run the
  controls at N = 500 on the then-current DUT.
