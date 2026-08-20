# 0001: Relaxation-oscillator topology for the trimmable RC core

- **Status**: Ratified (alongside the target spec — see
  [0002-target-spec-ratification.md](0002-target-spec-ratification.md))
- **Date**: 2026-08-20
- **Decided by**: Builder agent, issue #1

## Context

This repo's first deliverable is a free-running, digitally trimmable RC
oscillator on gf180mcu, anchored to the crystal-less full-speed-USB accuracy
class (see CLAUDE.md and README). Before the target-spec trim math can be
made concrete (0002), the oscillator core topology has to be picked, because
topology drives: what PVT sensitivity the trim network has to correct, how
trim maps onto physical devices (switched R/C elements vs. bias current/cap
loading), supply sensitivity, and area/power on gf180mcu. This is explicitly
new design work — CLAUDE.md is clear that "the topology decision starts
here," not a copy from the sibling analog canaries (`gf180-bandgap`,
`gf180-temp-por`), which are the style reference only.

Two topology families are the standard candidates for an on-chip,
crystal-free clock source:

## Options considered

### 1. Relaxation oscillator (RC-timed, comparator/threshold-based)

A current (or voltage) source charges and discharges a capacitor through a
resistor (or a fixed current into a cap), with one or two comparators
switching state at defined threshold fractions of a reference voltage
(often bandgap- or VDD-referenced). Frequency is set directly by the RC
(or I·C/Vth) time constant: `f ∝ 1 / (R·C)` to first order. This is the
topology family shipped commercial crystal-less-USB MCUs use for their
internal oscillator — e.g., ST's HSI48 (STM32F0/F3/L0 crystal-less-USB
parts) and Silicon Labs' internal precision oscillator on its crystal-less
USB microcontrollers (C8051F34x / EFM8UB parts) are both RC/relaxation-type
blocks, not ring oscillators locked to an RC reference.

**PVT sensitivity**: frequency error tracks directly with R and C absolute
value spread (process), comparator/reference offset (mostly PVT-insensitive
if bandgap-referenced), and the temperature coefficients of R and C
themselves. All of these are first-order, well-characterized error sources
in the analog-design literature for RC oscillators, and — critically — they
map onto a **single dominant variable** (the RC product) that a trim network
can directly correct by switching resistor or capacitor segments in or out.

**Trim granularity**: trivial to make monotonic and fine-grained — a
binary-weighted (or thermometer + binary) switched-resistor or
switched-capacitor bank in series/parallel with the timing element gives
direct, near-linear control of `f`. This is the same trim mechanism this
project's sibling `gf180-bandgap` selected for its own resistor trim (see
that repo's DR-0001), so it is also a proven pattern on this PDK's
resistor flavors.

**Supply sensitivity**: depends on whether the charge/discharge current or
comparator threshold is derived from a supply-independent reference
(bandgap-like bias) or drawn straight off VDD. A relaxation oscillator with
a simple current source and resistor-divider threshold has first-order VDD
dependence unless deliberately cancelled (e.g., ratiometric threshold
design, or a supply-independent bias) — a known, containable design problem
with standard mitigations, not a structural flaw of the topology.

**Area/power**: modest — one or two comparators, a small current
source/bias, and the trim resistor/cap bank. No PLL/FLL loop filter, no
multi-stage ring, no lock-time budget.

### 2. Ring oscillator with RC reference (ring core, frequency/phase-locked to an RC-timed reference)

A fast CMOS ring oscillator (inverter-chain or current-starved-inverter
chain) provides the actual clock edges, with its frequency periodically
compared against — and locked to — a separate, slower RC-timed reference
via a frequency-locked loop (FLL) or similar control loop (comparable in
structure to a small PLL/FLL, adjusting ring bias current or stage loading
to track the RC reference).

**PVT sensitivity**: a bare ring oscillator's frequency is set by MOSFET
gate delay, which is strongly nonlinear in V and T (gate delay depends on
`I_D ∝ (V_GS - V_T)^n` and mobility's own strong temperature dependence) —
substantially worse raw PVT sensitivity than an RC time constant, which is
why this topology needs the locking loop at all: the loop, not the ring
itself, is what delivers accuracy. That loop adds its own error sources
(reference comparison noise, loop-filter settling, lock-time-to-accuracy
tradeoff) on top of the RC reference's own PVT sensitivity — so this
topology inherits RC-reference error sources (like topology 1) *and* adds
ring-specific ones, rather than avoiding them.

**Trim granularity**: less direct — trim typically acts on ring bias
current or loading capacitance, which has a less linear relationship to
output frequency than a switched-RC element does, and the loop's own
dynamics (bandwidth, lock time) interact with how quickly a trim step
settles to a stable frequency.

**Supply sensitivity**: ring oscillators are notoriously supply-sensitive
(gate delay depends directly on the effective drive voltage), so this
topology needs either a regulated/supply-independent bias for the ring
*and* a well-behaved reference-lock loop to avoid compounding two sources
of supply sensitivity — more design surface than topology 1's single
supply-sensitive stage.

**Area/power**: the ring core itself can be small and low-power, but the
FLL/lock loop (frequency detector, loop filter, control DAC feeding the
ring bias) adds area, power, and — materially for this repo's own framing
in CLAUDE.md ("Not a crystal oscillator, not a PLL") — architectural
complexity that looks like a small PLL, which cuts against the block's own
stated identity as a free-running RC-based source with a digital trim
interface, not a locked/synthesized clock.

I am not aware of a shipped, crystal-less full-speed-USB MCU precedent that
uses this topology for its *primary* free-running RC-class internal
oscillator (the shipped precedents cited in CLAUDE.md and 0002 — ST HSI48,
Silicon Labs' crystal-less USB parts — are relaxation/RC-timed, not
ring-plus-FLL). Flagged: I could not independently re-verify every vendor's
internal architecture in this offline session, since MCU vendors don't
always publish oscillator-core schematics; the datasheet-level behavior
(comparator/RC-language in ST's reference manuals, "RC oscillator"
terminology in Silicon Labs' datasheets) is treated here as sufficient
evidence of the topology family, not a claim of exact circuit-level
architecture.

## Decision

**Use a relaxation oscillator core**: an RC (or I·C) timing element gated by
one or two threshold comparators, with a supply- and temperature-aware bias
generator, and digital trim implemented as a switched-resistor (or
switched-capacitor) bank directly setting the RC time constant.

Reasons, in order of weight:

1. **Matches the shipped precedent this project is anchored to.** CLAUDE.md
   sets the accuracy class from crystal-less full-speed-USB parts (ST HSI48,
   Silicon Labs crystal-less USB internal oscillators); those are RC/
   relaxation-type blocks. Following the same topology family means the
   error-budget structure this repo derives (0002) is directly comparable to
   the precedents it cites, rather than importing a different error-budget
   shape (loop lock time, loop noise) that those precedents don't have to
   account for.
2. **Direct, linear trim mapping.** A switched-RC trim bank gives a
   near-linear, monotonic `code -> frequency` relationship, which is what
   makes the explicit trim-math requirement in this repo's spec
   (CLAUDE.md: "an oscillator spec without its trim math is not a spec")
   tractable to derive and verify. A ring+FLL's `code -> frequency`
   relationship through a loop is materially harder to characterize and
   verify by hand or in a straightforward ngspice sweep.
3. **Single dominant PVT sensitivity, not two compounded ones.** A
   relaxation oscillator's accuracy problem is "the RC product moves with
   process/temperature/supply" — one story, well precedented in the
   analog-IC-design literature. A ring+FLL has two: the ring's own
   (worse) PVT sensitivity, plus the loop's residual tracking error and
   dynamics — a strictly harder verification problem for a first-block
   canary whose device models (gf180mcu's own R/C process-corner and
   mismatch data) are not yet characterized in this repo.
4. **Consistent with the block's own stated identity.** CLAUDE.md
   explicitly frames this block as "not a PLL." A ring core locked to an
   RC reference via an FLL is architecturally a small PLL/FLL variant;
   choosing it would blur the block's own scope statement for no
   documented accuracy benefit over the relaxation-oscillator precedent.
5. **Lower area/power, no lock-time budget.** No loop filter, no
   frequency/phase detector, no lock-time-to-accuracy tradeoff to spec and
   verify separately from the oscillator's own startup time.

## Alternatives considered

- **Ring oscillator with RC reference (FLL-locked)** — rejected. Strictly
  worse raw PVT sensitivity in the ring core itself, adds loop-related error
  sources and lock-time budget on top of (not instead of) the RC
  reference's own PVT sensitivity, has no identified shipped
  crystal-less-USB precedent for the primary oscillator role this block
  fills, and architecturally drifts toward the "small PLL" identity this
  block's own spec explicitly disclaims. See "Options considered" above for
  the full tradeoff analysis.
- **Bare (unreferenced) ring oscillator, no RC reference at all** — not
  separately analyzed above because it fails a harder requirement before
  the PVT comparison even matters: without any RC (or other absolute-value)
  timing reference, there is nothing for a digital trim word to correct
  against in a repeatable, characterizable way — trim would only be
  correcting against itself (a "trim to the same untethered gate-delay
  chain" tautology), which cannot deliver the process-spread-covering trim
  range this repo's spec requires (0002). Excluded from further
  consideration for that structural reason, not as a close call against the
  ring+RC-reference option.

## Consequences

- The target-spec trim math in
  [0002-target-spec-ratification.md](0002-target-spec-ratification.md)
  is derived assuming an RC-product-dominated frequency error model
  (`f ∝ 1/RC`), consistent with this topology — a future topology change
  would require re-deriving that trim math, not just re-running the same
  numbers.
- Device sizing (resistor flavor, capacitor flavor, comparator offset
  budget, bias generator design) depends on gf180mcu-specific process-
  corner and mismatch data for the chosen R/C devices, which is **not yet
  characterized in this repo** — the process-spread figure used in 0002 is
  flagged there as an explicit engineering assumption pending that
  characterization, to be confirmed once schematic-level corner sweeps
  begin (per the maturity ladder in `README.md`: spec ratified -> schematic
  simulated across PVT).
- Supply-independence of the bias/threshold generator becomes a concrete
  design requirement (feeding the PSRR/supply-sensitivity budget implicit
  in the free-running PVT spread target) — this record does not yet fix how
  that bias is generated (e.g., whether it borrows a bandgap-style
  reference or a simpler ratiometric scheme); that is schematic-phase work.
- A future runtime-discipline mechanism (e.g., a USB-SOF-driven trim
  update, analogous to ST's CRS peripheral) is architecturally compatible
  with this topology's trim interface (a digital code driving a switched-RC
  bank can be updated in real time), but designing that loop is explicitly
  out of scope for this record and for the current target spec (see
  0002's PVT budget) — reserved as a follow-on decision.
- If a later measurement or device-characterization pass shows the
  relaxation oscillator's PVT sensitivity or supply sensitivity cannot be
  contained within the budget in 0002 even with the chosen trim range, that
  is grounds to revisit this record with a superseding decision — not to
  quietly loosen the ratified target spec.
