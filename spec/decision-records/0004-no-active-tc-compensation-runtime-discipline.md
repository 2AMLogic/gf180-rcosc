# 0004: No active temperature-coefficient compensation — rely on runtime discipline

- **Status**: Ratified
- **Date**: 2026-09-05
- **Decided by**: Builder agent, issue #11

## Context

[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md) derived this block's
full-temperature-range post-trim accuracy (**+8% / −9%**, −40…+85 °C) from
gf180mcu's own published poly-resistor TCR (−1200 ppm/K, §6.1A) and left one
question explicitly open (0003 "Consequences", lines ~416-441): whether the
schematic should add **active temperature-coefficient (TC) compensation** in
the bias/reference generator, or place the entire burden of closing the gap
to USB full-speed compliance (±0.25%) on the ratified spec's reserved
"Runtime-disciplined" stage (e.g. USB start-of-frame timing, per ST's CRS
peripheral). 0003 flagged that "the public evidence strongly favors [active
compensation] but does not settle it here" — Silicon Labs' CP2102N ships
`TSOSC` = 45 ppm/°C typ, ~26.7× better than gf180mcu's raw TCR, meaning
shipped crystal-less-USB parts are not running on a wholly uncompensated
RC network.

`design/README.md`'s "Bias generator" section (written for issue #6, the
first-cut schematic) already documents that the current schematic uses the
**same poly-resistor flavor** (`ppolyf_u_1k`) for both the timing/trim
resistor and the threshold-divider resistors — a deliberate, qualitative
TC-tracking choice — but explicitly disclaims it as "not a quantified
compensation claim" and defers the question to this record.

This record resolves that open item before any further schematic or
PVT-corner work (issue #11, sub-issue A of the #9/#542 decomposition;
unblocks issue #12, the PVT-corner simulation sub-issue).

## Decision

**No active TC compensation is added to the bias/reference generator. The
design relies entirely on runtime discipline (USB SOF-style, per the
ratified "Runtime-disciplined" spec row) to close the gap from the
free-running figure to USB full-speed compliance.**

Concretely:

- The ratified full-temperature-range figure, **+8% / −9%** (−40…+85 °C,
  DR-0003 Row 3(b)), **stands unchanged as the free-running spec**. This is
  not a relaxation — DR-0003's number is not touched, and no compensation
  mechanism is assumed anywhere in the spec that would have made that
  number optimistic.
- The **path to the ≤ ±0.25% USB full-speed figure is entirely the reserved
  runtime-discipline stage** — SOF-based correction, still "reserved, not
  designed" exactly as DR-0002/DR-0003 already stated. This record does not
  design that stage; it confirms which stage carries the whole burden, so
  that sub-issue B (PVT-corner simulation, issue #12) knows what it is
  characterizing and does not need to budget headroom for an
  as-yet-undesigned compensation circuit.
- **No schematic topology change is required or made.** `design/rcosc_bias.sch`,
  `design/rcosc_trim_bank.sch`, and `design/rcosc_top.sch` are unchanged by
  this record. `design/README.md`'s "Bias generator" section is updated
  (see `design/` changes in this same PR) to point at this record instead
  of describing the TC question as still open.
- The existing **ratiometric flavor-matching** of the bias/threshold
  resistors to the timing/trim resistor (same `ppolyf_u_1k` device,
  documented in `design/README.md` since issue #6) is retained as-is. It
  remains a qualitative, unquantified choice — this record does not upgrade
  it to a compensation claim, and DR-0003's +8%/−9% figure already assumes
  no benefit from it (that figure is derived purely from the timing
  resistor's own TCR against a fixed voltage/current reference, so
  ratiometric tracking of the *comparator thresholds* does not appear in
  its arithmetic one way or the other).
- `README.md`'s ratified spec table is **not changed** by this decision:
  the full-temperature-range row's derivation (dominated by the timing
  resistor's own TCR, independent of any comparator-threshold tracking) is
  unaffected by choosing not to add compensation, since no compensation was
  assumed in that derivation to begin with.

## Alternatives considered

- **(a) Active TC compensation in the bias/reference generator** — e.g. a
  bandgap-referenced (BJT-based) bias generator instead of the current
  supply-ratiometric divider, a temperature-aware trim-code adjustment, or
  a dedicated TC-canceling current source biasing the comparator
  thresholds. Rejected for this block, for three compounding reasons:
  1. **No PDK-published path to it at the required magnitude.** gf180mcu's
     electrical-spec tables (re-checked live for this record,
     `google/gf180mcu-pdk` `docs/analog/spice/elec_specs/`, fetched
     2026-09-05) publish exactly one *positive*-TCR device family: §5.7
     "Temperature Coefficient" gives interconnect TC for Metal 1–5
     (+2800…+3800 ppm/°C typ +3300), Top Metal (+3000…+4500 ppm/°C), and
     contacts/vias (+620…+1230 ppm/°C) — no resistor, diffusion, or
     junction device with a *characterized* positive TCR exists in these
     tables. Canceling the timing resistor's −1200 ppm/K (§6.1A, this
     design's flavor) with, say, Metal 1's +3300 ppm/K typ would require a
     metal-resistor leg supplying a fraction `x` of the total resistance
     such that `x·3300 = (1−x)·1200`, i.e. `x ≈ 0.267` of the ~68–158 kΩ
     timing resistor (DR-0003 Row 2 / `design/README.md` "Trim bank
     sizing") from metal — roughly 18–42 kΩ. At Metal 1's published sheet
     resistance (76–104 mΩ/sq, §5.1), that is **170,000–550,000 squares**;
     even at gf180mcu's minimum M1 drawn width (~0.23 µm) that is roughly
     **4–13 cm** of folded wire, wholly impractical for a canary-block die. No bandgap-adjacent
     parasitic-BJT device with a published `Vbe`-vs-temperature figure
     appears in these same tables either (§5.4/§5.5/§5.6 cover oxide and
     junction breakdown and parasitic capacitance only, not TC) — building
     one would mean characterizing a device this record's evidence base
     does not cover, not selecting a documented one.
  2. **A closed-loop or bandgap-referenced compensation circuit is real
     design scope, not a refinement.** It would add at minimum a new
     sub-block (bias generator replacement or supplement), new
     device-mismatch and offset budget rows, and its own PVT-corner
     characterization burden on top of sub-issue B's — the kind of scope
     issue #11 (and CLAUDE.md's decomposition discipline generally) is
     explicit should not be folded into a single sub-issue, let alone a
     schematic-refinement pass with no PVT-sim budget of its own.
  3. **The precedent does not compel it for this block's scope.** DR-0003
     is right that CP2102N's 45 ppm/°C figure implies *some* on-chip
     stabilization beyond a raw RC network, but this repo's explicit
     anchor (CLAUDE.md, "What the block is") is a **canary block**
     verifying the open-source PDK/tooling flow, not a production part
     competing on TC spec with a finer-node commercial IC. Both cited
     precedents (ST's HSI48/CRS, Silicon Labs' crystal-less USB parts)
     *ship* with SOF-style runtime discipline as the mechanism that closes
     the gap to USB compliance — that mechanism is what makes crystal-less
     USB work at all, whatever headroom their on-chip oscillators start
     from. Reproducing that mechanism (already reserved in this repo's
     ratified spec) is in scope and precedented; reproducing an
     uncharacterized on-chip TC-compensation circuit to shrink the
     *free-running* number is neither required by the precedent nor
     supported by any PDK data this record can cite.
- **(c) Hybrid — partial passive compensation via device/flavor selection,
  plus runtime discipline.** Rejected for the same evidentiary reason as
  (a): a passive complementary-TC option is the cheapest fix *if one
  exists* (DR-0003 already took this approach for the MIM-cap flavor, Row
  2's "Trim-bank sizing gets harder" consequence), but no PDK-published
  resistor, diffusion, or capacitor flavor offers a positive TCR at a
  sheet resistance usable for a several-tens-of-kΩ timing resistor (see
  (a)(1) above) — the search this record performed for a partial fix found
  the same "impractical at any dose" result as for a full fix, so there is
  no partial version to select. If a future revision of gf180mcu's
  published tables adds a characterized positive-TCR resistor flavor at a
  practical sheet resistance, this alternative should be re-evaluated via
  a superseding record.
- **(b) Rely entirely on runtime discipline — CHOSEN.** See "Decision"
  above.

## Consequences

- **No design-team blocker on issue #12 (PVT-corner simulation).** That
  sub-issue can proceed to sweep the schematic exactly as committed for
  issue #6 (no new sub-block, no new device count) across process,
  voltage, and temperature, characterizing the free-running +8%/−9% figure
  DR-0003 already ratified — it does not need to also characterize an
  undesigned compensation circuit's closed-loop behavior.
- **The full-temperature-range headline number does not improve.** This
  block's free-running accuracy claim remains ≈±1.1% at the calibration
  point and **+8% / −9% across −40…+85 °C**, exactly as DR-0003 ratified.
  Nothing in this record makes that number tighter, and nothing makes it
  looser — DR-0003's arithmetic is untouched.
- **The runtime-discipline stage's job is now explicit rather than
  implicit.** It must close the full ~35× gap DR-0003 already flagged
  (±9% → ±0.25%), not a partially-pre-compensated gap. This is a
  clarification of scope for whichever future issue designs that stage,
  not a new requirement — DR-0003 already computed this same ~35× figure
  as the consequence of *not* adding compensation; this record is what
  makes that the ratified path rather than an open branch.
- **`design/rcosc_bias.sch` and `design/rcosc_trim_bank.sch` are
  unchanged.** No new devices, no new corners, no new offset/mismatch
  budget rows. `design/regen-netlist.sh` and `design/run-smoke-test.sh`
  are re-run for this record purely to re-confirm the existing schematic
  still nets and simulates cleanly after `design/README.md`'s text edit —
  not because the circuit changed.
- **What is invalidated.** Nothing — no simulation or layout work assumed
  either outcome of this open item, so neither is invalidated by resolving
  it this way.
- **What remains open.** Designing the SOF-based runtime-discipline stage
  itself remains future, out-of-scope work (as it was before this record;
  DR-0002/DR-0003 already reserved it, undesigned). If a future PVT-corner
  campaign (issue #12) or a later shuttle/measurement result shows the
  free-running figure is materially worse than DR-0003's +8%/−9% — e.g. if
  the ratiometric bias generator's own supply/PVT sensitivity turns out to
  dominate over the timing-resistor TCR this record's arithmetic assumed —
  that must be corrected via a further superseding decision record, not by
  reopening this record's active-vs-passive choice on the same evidence.
