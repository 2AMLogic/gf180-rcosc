# 0019: Statistical vs deterministic spec rows, and the Monte Carlo evidence plan

- **Status**: proposed
- **Date**: 2026-10-08
- **Decided by**: Loom Builder (issue #71), pending operator ratification

## Context

T1 item 6 ("statistical claims carry Monte Carlo evidence") is `unmet /
no_evidence`, and `signoff/README.md` justified that by saying the repo makes
no statistical accuracy/yield claim. The tier text says the opposite for an
oscillator: any accuracy, offset, or matching row is statistical, and a corner
matrix cannot validate it. The post-trim accuracy rows are accuracy rows
built from a quantization term plus trim-DAC mismatch and comparator offset
(DR-0003 Row 3, DR-0017), which are random per-die quantities, and the
2026-10-08 operator ruling on #66 treats those rows as statistical claims
needing a mismatch campaign. The repo had no record of which ratified rows
are deterministic and which are statistical, so the claim could neither be
made nor graded. This record adds that classification and the evidence plan.
It changes no ratified value and relaxes nothing.

## Decision

### 1. Classification (one row per ratified spec row)

Rows are those of the top-level `README.md` target-specification table, as
currently in force (DR-0002, DR-0003, DR-0017). "Deterministic" means
bounded by the PVT corner matrix (a worst case over named corners decides
it); "statistical" means a per-die random quantity (local mismatch) decides
it, so a corner can only bound the mean and the claim is a yield.

| # | Ratified row | Class | Reason |
|---|---|---|---|
| 1 | Output frequency, 48.000 MHz | Deterministic | A nominal target, not a limit on a distribution; the per-die offset from it is what the trim and accuracy rows (2, 4, 5) bound. |
| 2 | Trim interface: 8-bit, +/-40 % range, 0.314 %/code, half-LSB +/-0.157 % | **Statistical** (mixed) | The nominal range and LSB are deterministic design values, but "range covers the spread" and "resolution holds" depend on trim-DAC element mismatch: per-die step size, monotonicity, and whether the required pull stays off the code rails (headroom, cf. DR-0018's `ss` at `0xF7`). The nominal-range part stays corner-checked; the coverage/resolution part is the statistical claim S1. |
| 3 | Free-running untrimmed spread, +/-35 % | Deterministic | Sourced from the PDK's published min/typ/max global process-module limits (DR-0003 Row 1); global process spread is exactly what the corner models enumerate, not local mismatch. |
| 4 | Post-trim accuracy at calibration point, -2.9 % / +2.0 % | **Statistical** | An accuracy row. Its budget contains trim-DAC mismatch (+/-0.300 %) and comparator offset (+/-0.300 %), both flagged assumptions that are per-die random; the supply-span term is deterministic but is added to them. Claim S2. |
| 5 | Post-trim accuracy over -40..+85 C, +8.8 % / -10.8 % | **Statistical** | Same mismatch terms as row 4 plus the temperature term; the TCR term is deterministic but the sum is only meaningful as a per-die distribution. Claim S3. |
| 6 | Runtime-disciplined, <= +/-0.25 % | Deterministic (reserved) | Reserved, not designed (DR-0004); the figure is the USB 2.0 `TFDRATE` clause, an external requirement, and no measurement is claimed. Re-classify when a discipline loop is designed. |
| 7 | Supply, 3.0-3.6 V | Deterministic | An operating-condition range; it is a corner axis, not a measured result. |
| 8 | Quiescent current, < 500 uA (running) | Deterministic (watch) | A maximum-limit row set by bias-resistor and process-corner current; bias mirror mismatch is second-order against the corner swing. Margin is thin (DR-0017: 24.2 uA), so Iq is recorded as a free by-product measurement in the S2/S3 runs; if its sampled spread threatens the margin the row is re-classified by a later record. |
| 9 | Startup time, <= 10 us | Deterministic | A transient bound on a settling path, bounded by corners; bench added in issue #78 (`sim/startup/`), factorial not yet evaluated (see DR-0020 and `signoff/testbench-inventory.md`). A mismatch-induced failure to start is a separate robustness check, not this row. |
| 10 | Temperature range, -40..+85 C | Deterministic | An operating-condition range, a corner axis. |

### 2. Statistical claims and Monte Carlo design

Common design for S1-S3:

- **Claim form.** "At least the target yield of dies meet the ratified
  limit at each evaluated corner, with the stated confidence." The limit is
  the ratified value, unmodified. Pass is judged on the lower confidence
  bound `klt yield` reports, never the point estimate.
- **Yield target and confidence.** Target yield 99 % per measurement per
  corner; two-sided 95 % confidence (the `klt yield` default). With zero
  failures the lower bound at n = 500 is about 99.3 %; any failure leaves a
  lower bound near or under 99 %, so the campaign is sized to pass on a
  clean run and `klt yield`'s own sample-size verdict decides borderline
  cases.
- **Sample count.** 500 samples per corner per claim. `--min-samples` is set
  so a smaller run is reported as inconclusive, not as a pass.
- **Seed.** One recorded seed, `20261008`, written into the request and the
  committed manifest; the campaign may add seeds only by appending, never by
  re-drawing until a claim passes.
- **Per-die calibration inside each sample.** Each sample is one die: its
  trim code is selected by the single-point test procedure (the same one the
  accuracy rows assume: calibrate at 27 C, nominal supply, then hold the code
  across the other conditions), then the residual error is measured. The
  testbench must do the code selection per sample; a fixed-code MC would
  measure the untrimmed spread instead (see follow-up scope).
- **Combination with corners.** Monte Carlo is mismatch-only and runs *on
  top of* each corner; it does not replace the corner matrix, which stays the
  evidence for the deterministic rows and for the corner-bounded mean. The
  corner set is the typical anchor (`tt`, 27 C, 3.3 V) plus the extreme
  corners the settled-sizing PVT campaign identifies as worst (for the current
  hierarchy per DR-0018: `ff`/-40 C/3.6 V, the slow-corner low-headroom case
  at `ss`, and the temperature/supply extremes of the full-range row); the
  exact list is frozen in the campaign issue from the settled #66 results
  before the run.
- **Deterministic negative control.** The same seed is re-run with the
  mismatch sigma inflated (3x), plus a zero-mismatch run. The inflated run
  must show a clearly degraded yield and fail the claim (otherwise the
  harness cannot detect mismatch and the pass means nothing); the zero-
  mismatch run must reproduce the corner value within simulator tolerance
  (otherwise the sample plumbing perturbs the circuit). A campaign whose
  controls do not behave as stated yields no verdict.

Per-claim specifics:

| Claim | Row | Measurement | Limit (ratified) | Notes |
|---|---|---|---|---|
| S1 | 2 | residual error after best code; chosen-code headroom to the rails; minimum step (monotonicity) | residual within the half-LSB plus mismatch budget of DR-0003 Row 3; code not saturated at either rail; every step positive | headroom is the DR-0018 `ss`/`0xF7` risk made quantitative |
| S2 | 4 | f error at the calibration point over process/supply corners | -2.9 % / +2.0 % | 99 % yield, 95 % confidence |
| S3 | 5 | f error over -40..+85 C, VDD +/-10 % | +8.8 % / -10.8 % | 99 % yield, 95 % confidence |

Whether the PDK's gf180mcu ngspice models expose mismatch parameters
usable through `klt sim` `monte_carlo` is verified by the campaign's first
step; if not, that is a recorded blocker and a generic tool-gap issue, not a
reason to substitute a corner sweep.

### 3. Evidence verb and execution

The evidence verb is `klt yield`, which needs the `klayout-tools[yield]`
extra, consuming a `klt sim --format json` Monte Carlo report directly with a
limits file carrying min/max/target_yield and the confidence and min-samples
defaults above. The multi-sample run is expressed as a `klt sim` request with
a `monte_carlo` section and is submitted to the batch fleet (the worker
exports `KLT_SIM_BACKEND=batch`); it is not a hand-launched local ngspice
loop. If the batch submit fails the failure is reported on the campaign
issue, not worked around locally. The envelope lands under `sim/` append-only.

### 4. Sequencing

The campaign runs only after #66 settles the sizing. A Monte Carlo run on a
design known to miss its mean is wasted evidence, and the corner list above
depends on #66's settled results. This record can be ratified now; the
campaign cannot start before then.

### 5. Follow-up campaign

Named: **item-6 mismatch Monte Carlo campaign** (results under
`sim/mc/results/`), covering S1-S3, the controls, and the by-product Iq
measurement. It also owns making `signoff/README.md` item 6 gradeable
(a `yield` envelope plus the grader row) and updating
`signoff/testbench-inventory.md`. It is opened as an issue once #66 settles.

## Alternatives considered

- **Keep "no statistical claim" and leave the accuracy rows as corner
  figures.** Rejected: the tier text and the #66 ruling classify accuracy
  rows as statistical, and the ratified rows' own error budgets contain
  random mismatch terms.
- **Replace corners with Monte Carlo.** Rejected: MC here is mismatch-only
  and cannot stand in for global process/temperature/supply extremes; the
  two answer different questions.
- **Run the MC now, ahead of #66.** Rejected: it would be run on a design
  not yet meeting its mean.
- **Hand-run local ngspice sampling.** Rejected: batch fleet is the
  mandated path for multi-sample runs and yields the `klt yield`-readable
  report with provenance.

## Consequences

- Item 6 becomes a real, nameable obligation (rows 2, 4, 5) rather than a
  vacuous one; it stays `unmet` until the campaign runs, and the machine
  row stays `no_evidence` until a `yield` envelope exists.
- Rows 4 and 5 stay quoted as the ratified worst-case figures; they gain a
  yield qualifier only after the campaign passes. A failure produces a
  separate evidence record, not a relaxed row.
- The classification is itself revisable: rows 6 and 8 carry explicit
  re-classification triggers.
- Costs batch-fleet time (roughly 500 samples x corners x claims, plus
  controls) and per-sample trim-code search in the testbench.
