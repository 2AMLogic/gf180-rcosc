# 0017: Low-side comparator re-referenced to a complementary PMOS-input cell — supply slope flattened, post-trim rows re-derived

- **Status**: Ratified — supersedes the Row 3 re-derivation (both sub-rows
  a and b, and the delay-residue attribution behind them) of
  [0016](0016-comparator-latch-delay-residue-budget.md), which itself
  superseded DR-0003 Row 3. DR-0016's instrumentation (`sim/pvt/delay_probe.py`)
  and its F1/F2/F5/F6 stage-decomposition findings stand unchanged; its
  budgeted delay-residue figures do not. DR-0003 Rows 1, 2 and 4 stand
  (Row 4's margin in fact widens, below). [0004](0004-no-active-tc-compensation-runtime-discipline.md)
  is untouched: this is a supply-slope change, not a compensation mechanism.
- **Date**: 2026-09-23
- **Decided by**: Builder agent, issue #57

## Context

DR-0016 measured the comparator/latch delay residue and found the low-side
comparator `XCMPL` dominant: comparing `vl` (= VDD/3) against `vc` as it
dives toward 0 V puts the NMOS input pair's source node against `vss`, the
tail leaves saturation exactly at slow-cold-low-supply, and `t_cmp_l` runs
3.81 ns at `ss`/27 °C/3.0 V vs 1.90 ns at 3.6 V — 87% of that corner's
`Δdsum` and 62–82% of the whole post-trim supply span. DR-0016 budgeted the
rows at −9.2/+6.5% (at-cal) and −17.1/+13.4% (full-temp) and filed this
circuit-side lever as issue #57, with two hard constraints: the free-running
frequency must not increase (DR-0003 Row 4's knife-edge 1.24 µA Iq margin at
`0x80`/`ff`/85 °C/3.6 V), and the trim range must not regress.

## Decision

**XCMPL is re-referenced to the vdd rail as a complementary PMOS-input
comparator — a new `rcosc_comparator_p` cell ("swapped comparator
orientation", the issue's first-listed flavor of re-referencing) — and the
two post-trim accuracy rows are re-derived against the flattened delay
path.** XCMPH keeps the unchanged NMOS cell (it was already supply-flat).
Details, all measured in this issue's campaigns:

- **Cell**: PMOS input pair (`W=8u L=0.5u nf=4`), NMOS mirror load
  (`W=4u L=1u`, matching the NMOS cell's pfet loads), tail `MPTAIL`
  (`W=16u L=1u nf=4`) mirroring `rcosc_bias`'s P1 diode from the newly
  exported `pb` pin at **4:1**, and a two-inverter buffer whose first
  pull-down is deliberately weak (`MBUFN W=0.5u` vs `MBUFP 4u`) so its trip
  sits high and sets the stage's nominal delay ratiometrically. At the
  crossing the pair's `|VSG|` is set by the supply-independent tail current,
  the tail keeps headroom at every corner, and the diving `vc` input only
  increases its overdrive — the near-ground region becomes the pair's
  favorable one instead of its worst.
- **Input mapping**: the moving input (`inn` = `vc`) drives the output-side
  pfet and the fixed threshold (`inp` = `vl`) the diode-side pfet — the
  direct complement (moving input on the diode side) measured 0.3–0.5 ns,
  i.e. a 4–6× `dsum(3.3 V)` **cut** that raises f at fixed code, colliding
  with Row 4 exactly as DR-0016's lever-(a) rejection warned. The chosen
  mapping + weak-trip buffer land the stage at ≈ nominal delay instead.
- **Bias re-budget (deliberate, part of the lever)**: XCMPL's tail goes
  8:1 → 4:1 (`17×ibias` → `13×ibias` total). Half the tail was needed to
  slow the complementary stage back to its nominal-delay target, and the
  freed current widens Row 4's margin at every cell (below). DR-0009's
  M-saturation finding is untouched (that knob traded trim recovery against
  total Iq at *both* tails jointly; this is a one-tail re-budget for a
  different objective — flattening, not speed).

Row 3(a) — at the calibration point (T = 27 °C, process, VDD ±10%),
per-corner ratified-calibrated codes, campaign
`sim/pvt/results/20260923T030125Z/` (363 points, 0 failed):

| Contributor | DR-0016 basis | This record's basis |
|---|---|---|
| Trim quantization | ±0.157% | unchanged |
| Trim-DAC element mismatch / INL | ±0.300% | unchanged |
| Comparator/reference offset residual | ±0.300% | unchanged |
| Supply drift, VDD ±10% | −8.4% / +5.8% measured (62–82% delay) | **−2.07% / +1.17% measured** (probe `20260923T030905Z`, 138/138: delay share of the supply span now 7.6–33%, the residual dominated by the charge path DR-0016 first separated) |

```
down = -(0.157 + 0.300 + 0.300 + 2.07)% = -2.827%  -> ratified -2.9%
up   = +(0.157 + 0.300 + 0.300 + 1.17)% = +1.927%  -> ratified +2.0%
```

Row 3(b) — full temperature range, DR-0003/0016's TCR legs retained
unchanged (+6.844% / −7.906%):

```
hot  = +6.844 + 1.927  = +8.771%  -> ratified +8.8%
cold = -7.906 - 2.827  = -10.733% -> ratified -10.8%
```

Bounding check: the ratified stack over-bounds every measured factorial
cell (ratified-basis worst −6.84% (`sf`/−40 °C/3.0 V) / +6.74%
(`rc_f`/85 °C/3.0 V); surrogate basis −6.08/+7.76%). No measured cell falls
outside.

### Row verdicts, re-evaluated (both bases stated together, never one alone)

| Row | Basis | Measured | vs DR-0016 (−9.2/+6.5%, −17.1/+13.4%) | vs superseded DR-0003 (±1.1%, −9/+8%) |
|---|---|---|---|---|
| At calibration point | ratified codes | −2.07% / +1.17% | **met** (7.1 / 5.3 pt) | lower **exceeds** (−2.07 < −1.1), upper met |
| At calibration point | surrogate codes | −1.31% / +1.26% | **met** | lower exceeds, upper met |
| Full temperature range | ratified codes | −6.84% / +6.74% | **met** (10.3 / 6.6 pt) | **met** (2.2 / 1.3 pt) |
| Full temperature range | surrogate codes | −6.08% / +7.76% | **met** | met (−9 side) / exceeds (+7.76 < +8 — met) |

### The two issue-#57 guardrails

- **Row 4 / f-must-not-increase**: `f(0x80, ff, 85 °C, 3.6 V)` drops
  58.22 → 55.42 MHz (probe basis; campaign 55.32) and `iq_run` at that cell
  drops 498.756 → 475.778 µA — **margin 1.24 µA → 24.2 µA** (Iq sweep
  `sim/iq/results/20260923T031214Z/`, 252 points, 0 failed; every `0x80`
  cell improves by 20–25 µA). `dsum(3.3 V)` per-corner, old → new (both
  stated): tt 4.419→4.463, ff 3.502→3.734, fs 4.183→4.240, rc_s
  4.685→4.947 (increased, safe direction); ss 5.810→5.260, sf 4.859→4.783,
  rc_f 4.099→3.899 (reduced — a flat stage cannot match a corner-spread
  old value everywhere; the binding operational constraint, f at the
  guardrail cell, is met with −4.8%).
- **Trim range**: every corner calibrates inner-range, none saturated
  (codes 0x59…0xCD; `ss` moves *down* 0xCF→0xCD, the fast-at-3.0-V
  direction, i.e. more headroom at the high-code end).

## Alternatives considered

- **Level shift inside the shared `rcosc_comparator` cell** (satisfying the
  issue's file list most literally): rejected — the cell is shared, so a
  follower shift also lifts XCMPH's common mode toward the vdd rail where
  its PMOS loads lose headroom at 3.0 V, endangering the one stage that is
  already flat. The complementary sibling cell touches only XCMPL.
- **Rail-to-rail (parallel NMOS+PMOS pairs) input stage in the shared
  cell**: rejected — at a frozen total tail current the active-pair gm at
  each crossing drops ~√2 per side and the inactive side wastes current;
  at the current budget it is slower everywhere or, at raised current, a
  Row 4 regression.
- **Discharge-floor change**: rejected for this issue as larger-scope — it
  re-opens the frozen issue-#16 trim-bank R sizing (0→`vh` charge
  assumption) and DR-0014's guardrail.
- **The direct complement with the moving input on the diode side**
  (measured): rejected on its own numbers — 4–6× faster, an f-raising
  `dsum` cut, the exact lever-(a) hazard.
- **Charge-path residual (16–36% share)**: left as its own mechanism, per
  the issue; it now dominates what remains of the supply span and is the
  natural next lever (transmission-gate shunt `R_on(VDD)` / loaded divider
  ratio).
- **Silently re-rounding figures to "met"**: rejected (CLAUDE.md); the
  superseded-basis columns stay stated above.

## Consequences

- The post-trim rows tighten from −9.2/+6.5% and −17.1/+13.4% to
  **−2.9/+2.0% and −10.8/+8.8%**; against the original DR-0003 full-temp
  row (−9/+8%) the block now measures within on both legs.
- Layout: `rcosc_comparator_p.gds` is built and verified (DRC clean, LVS
  match, supply ERC one-island-per-supply; `rcosc_bias` re-spun only to
  export the `pb` pad, `rcosc_top` recomposed — evidence in
  `layout/reports/`). The post-layout (PEX) PVT re-verification is **not**
  part of this record: it follows the repo's convention of a separate
  re-verification pass (as #28/#44/#50 did for their re-spins) against the
  new cell.
- Two verification-apparatus repairs shipped with the re-run, both
  pre-existing on `main` and both disclosed in `layout/run_checks.sh` /
  `layout/erc-supply-spec.json`: the klt toolchain pin (0.5.0's generators
  draw different geometry and silently rewrite committed cells) and the ERC
  tie's tap layer (klt erc 0.4.0 ignores `tap_requires`, merging every
  in-well diffusion into the supply net — upstream klayout-tools#2358; the
  old spelling reported vdd/vss shorted on the untouched pre-#57 GDS).
- The sizing narrative (moving-input mapping, weak-trip buffer, 4:1 tail)
  is documented in `design/rcosc_comparator_p.sch`'s header; the delay
  probe's decomposition remains the instrument for any future re-derivation.
