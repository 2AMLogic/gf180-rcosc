# 0030: Item-6 Monte Carlo campaign — row 4 fails at `ss`, row 5 fails at `ff`, negative controls incomplete; ratified spec unchanged

- **Status**: proposed — records simulation evidence. Changes no ratified
  value and relaxes no row. It executes the plan of
  [0019](0019-statistical-vs-deterministic-spec-rows-and-monte-carlo-evidence-plan.md)
  (itself `proposed`) under the matching model of
  [0022](0022-mc-matching-model-trim-ladder-resistors-and-mim-capacitor.md)
  (`proposed`) on the sizing of
  [0023](0023-recentre-timing-ladder-for-extracted-parasitics.md) (`proposed`).
- **DUT scope**: every figure in this record, pass and fail, measures the
  **pre-[0028](0028-comparator-h-output-stage-fix.md) P3 netlist**
  (`sim/recentre/p3/rcosc_top_p3.spice`). That netlist is **no longer the
  design on `main`**: the DR-0028 change (MBUFN W 2u -> 1u, #229/#234) is
  already in `design/netlist/rcosc_top.spice` and in the layout and extraction.
  See "DUT status" below.
- **Date**: 2026-11-06
- **Decided by**: Loom Builder (issue #202), pending operator ratification

## Context

T1 item 6 was `unmet / no_evidence`: no Monte Carlo had produced a result
(groundwork #77, injector #135/#186). #66 settled the sizing (P3, 27-point
batch confirmation `sim/recentre/results/20261106T044714Z/`), the fleet runner
now has `gf180mcuC`, and `klayout-tools[yield]==0.8.0` (the repo's grader pin)
installs. The campaign DR-0019 section 5 named was therefore run:
500 samples per process corner, seed `20261008`, on the P3 extracted netlist
with the DR-0022 injected ladder/capacitor mismatch plus the PDK's MOS
mismatch, each die calibrated at 27 C / 3.3 V and then held at its code over
3 supplies x 3 temperatures. Everything is in
[`sim/mc/`](../../sim/mc/README.md); graded by `klt yield` in
`sim/mc/results/20261106T072000Z/`.

### DUT status: superseded on `main`

The campaign DUT is the P3 extracted netlist, last touched by #66, which
predates the DR-0028 comparator-H output-stage fix. DR-0028 states that
`sim/recentre/p3/` is "unchanged append-only evidence of the pre-fix netlist"
and reports, at the unchanged calibration code: tt / 27 C / 3.3 V
48.05 -> 49.14 MHz (+2.4 %, so row 1 now fails and the calibration code moves
to about `0xA4`/`0xA5`), and ff / -40 C / 3.6 V +21 %. The `ff` row 5 low-side
tail (-40 C, 3.6 V) is the cell most likely to change, and a strong cold-`ff`
supply dependence (-4.31 % at 3.0 V against -9.37 % at 3.6 V) is the kind of
comparator-delay term DR-0028 altered. The results below are therefore
statements about the measured pre-DR-0028 netlist, not about the current
design. **The campaign must be re-run on the post-DR-0028 netlist, after the
calibration code is re-centred, before any cell says anything about the
current design.** The item-6 citations in `signoff/block-manifest.json` grade
this non-current DUT (item 6 is `unmet` either way; `ff` row 4 grades `met` on
the stale DUT only).

## Decision

Nothing in the ratified table changes. This record states what the campaign
shows and what it does not, so the numbers cannot be quoted past their
controls.

**Results (`klt yield`, 95 % confidence, 500 samples, target yield 99 %).**

| process | row 2 (S1: residual, headroom; monotonicity fails deterministically, DR-0022 section 5, not gated) | row 4 (S2, 27 C, 3.0-3.6 V) | row 5 (S3, -40..85 C, 3.0-3.6 V) |
|---|---|---|---|
| `tt` | 100 % (lower bound 99.26 %) | 100 % (99.26 %) | 100 % (99.26 %) |
| `ff` | 100 % (99.26 %) | 100 % (99.26 %) | **60.4 % (lower bound 55.96 %), fails** |
| `ss` | 100 % (99.26 %) | **0 % (0 %), fails** | 100 % (99.26 %) |

Every "100 %" cell is a point estimate from a run whose controls were not
detected: **not a claim** (see Controls). The figures describe the pre-DR-0028
netlist only.

- **Row 4 at `ss` is a deterministic miss, not a mismatch effect.** The
  27-point grid already shows `ss` at 27 C spanning -2.82 % (3.0 V) to +2.66 %
  (3.6 V) at the calibrated code
  (`sim/recentre/results/20261106T044714Z/summary.md`). The sampled dies'
  supply span at the held code is 5.44 points (median; range 4.89-6.09). For
  498 of 500 dies the span exceeds the whole 4.9-point ratified window
  (-2.9 % / +2.0 %); the two narrowest (4.891) would fit by less than 0.01
  point, far below one trim step (0.41-0.47 %). At the calibrated code the
  3.6 V error alone (median +2.38 %) exceeds +2.0 % on every die. Re-centring cannot fix this; the span has to
  shrink (design) or the row has to be re-decided by the owner. The limit is
  not relaxed here.
- **Row 5 at `ff`** fails on both sides: 26 % of dies exceed +8.8 % (worst
  +11.79 % at 85 C / 3.0 V) and 17 % fall below -10.8 % (worst -15.10 % at
  -40 C). The deterministic grid had -9.37 % / +8.21 % at the calibrated code,
  inside the limits by 1.4 and 0.6 points, and the die-to-die spread uses
  that margin up.
- S1's residual and headroom pass everywhere (calibration residual p99
  0.19-0.34 % against the 0.757 % harness limit; every die's code is at least 38 codes from a rail). Monotonicity is reported, not gated (DR-0022 section 5: the
  DR-0021 carries are non-monotone at 0x).

**Controls (DR-0019 section 2 / DR-0022 section 3), against criteria fixed
before the run.**

| control | outcome |
|---|---|
| zero mismatch (plumbing) | **pass** at all three corners: three identical draws, calibration code equal to the deterministic P3 code (`0xA9`/`0x59`/`0xD7`), calibration frequency within -0.023 / -0.016 / -0.013 % of the 27-point grid (tolerance 0.25 %) |
| inflated 3x (MOS and injected sigma) | **detected only for `ff` rows 4 and 5.** Not detected for 10 of the 12 measurement rows: the 3x yield stays at or near the nominal yield (for example `tt` row 5 99.4 %, `ss` row 2 100 %), or the nominal is already at 0 % (`ss` row 4, 5.2 % at 3x). `klt signoff` grades this `negative_control_not_detected` |
| injected-term sensitivity (MOS off, 1x vs 10x, n=100) | **partial.** The MSB transition (0x7F->0x80) step sigma scales 9.65x (accepted band 7-13); the 0x7E->0x7F step sigma scales 4.99x, outside the band. The code-selection spread scales 0.10 -> 1.44. By the stated criterion the control fails; the cause is not established (the 1x sigma, 4.5 kHz, is close to the timing resolution of the `tran 200p` edge measurement, a hypothesis not tested here) |

Per DR-0019 section 2, a campaign whose controls do not behave as stated
yields no verdict. The passing yield figures above are therefore **not**
claims: they are the point estimates of runs whose harness could not show it
would have failed them. The two failing cells (`ss` row 4, `ff` row 5) are
claims in the other direction, with the caveat that the sigmas are flagged
assumptions. The `ss` row 4 miss does not depend on them (the supply span, 498 of 500
dies wider than the window, is set by the process and supply corners, not by
mismatch).

Every main-run corner carries an ngspice `nonconvergence` warning ("Dynamic
gmin stepping failed"). The zero-mismatch control reproduces the deterministic
grid to within 0.023 %, so no bias is evident, but it is not ruled out. The
by-product Iq measurement named in DR-0019 section 5 was **not taken** in this
campaign.

**Assumptions the numbers carry, quoted with every yield figure:** ladder
resistor and MIM capacitor mismatch `A_R = A_C = 1.0 %.um` (DR-0022, no
public source); the P3 extracted netlist under the extractor's lumped
parasitic model (klayout-tools#3089 on the substrate-node modelling); default
solver `reltol` on ngspice 46 (the groundwork measured a ~0.2 % solver
dependence, comparable to the half-LSB the residual is judged against); the
fixed-grid 27 C calibration of DR-0019; one seed.

## Alternatives considered

- **Drop the failing cells or report the pass cells only.** Rejected: the
  grader and DR-0019 require every declared row; a campaign reported without
  its failures is not evidence.
- **Re-run with a stronger control until it is "detected".** Rejected here:
  the control was fixed in DR-0019/0022 (3x). A different control is a spec
  decision for the owner (it is an amendment of 0022), not a way for this
  record to obtain a verdict. Filed as follow-up.
- **Widen the limits or change the calibration point to make `ss` row 4
  pass.** Rejected: agents do not relax the ratified spec; the operator ruling
  of 2026-10-08 is that misses are design fixes.
- **Run on the schematic.** Rejected: the schematic carries the pre-recentre
  sizing and would measure a design known to miss its mean (DR-0019 section 4).

## Consequences

- Every cell is evidence about the pre-DR-0028 P3 netlist only. A re-run on the
  post-DR-0028 netlist (re-centred first) is required before this record
  describes the block on `main`; the Iq by-product can be taken then.
- Item 6 grades `unmet` with reason `negative_control_not_detected` (not
  `no_evidence`) in `signoff/signoff-report.json`; the three declared rows are
  `unratified_rows` while DR-0019 is `proposed`. The block stays below T1.
- Two design/spec questions are open and filed as issues: the `ss` row 4
  deterministic miss and the `ff` row 5 spread (a design fix, a trim-scheme
  change, or a spec decision for the owner), and the control sufficiency
  (stronger or differently-defined negative control, finer timing resolution
  for the LSB-transition sensitivity measurement).
- The fleet cost was about 3,200 samples (roughly 64,000 transient solves of
  the extracted netlist) on the Spot batch fleet.
- The campaign, its controls, and the matching-model assumption are one
  reproducible command each (`sim/mc/run-campaign.sh`, `sim/mc/grade.sh`);
  `sim/mc/results/` is append-only like the rest of `sim/`.
