# 0022: Monte Carlo matching model for the trim-ladder resistors and the MIM capacitor

- **Status**: proposed
- **Date**: 2026-10-09
- **Decided by**: Loom Builder (issue #85), pending operator ratification

## Context

[0019](0019-statistical-vs-deterministic-spec-rows-and-monte-carlo-evidence-plan.md)
section 2 plans the item-6 mismatch Monte Carlo (claims S1-S3). The #77
groundwork ([`sim/mc-groundwork/README.md`](../../sim/mc-groundwork/README.md),
"Feasibility verdict") found that the vendored gf180mcuC ngspice models give
per-instance mismatch for MOS devices only. `ppolyf_u_1k` (the trim ladder
and the bias divider) and `cap_mim_1f0fF` (the timing capacitor) have no
local-mismatch hook, so the trim-DAC element mismatch (+/-0.300 %, DR-0003
Row 3, a flagged unsourced assumption) cannot be sampled from the PDK, and
the groundwork left the choice to "the campaign". This record makes it
before the campaign, so S1 (code headroom, monotonicity) is not silently
reduced to MOS-only mismatch or given an unratified ladder model. It changes
no ratified value and relaxes nothing.

What the public PDK documents about this (google/gf180mcu-pdk at commit
`de3240d7`, read 2026-10-09):

- `docs/analog/model_parameters/LV/tables_clear/06_Resistors.csv` lists
  `ppolyf_u_1k` with **Local Statistical = N** (Global Statistical = Y);
  `08_MIM.csv` lists every MIM model with **Local Statistical = N**. The
  PDK documents these devices as having no local-mismatch model.
- `docs/analog/spice/elec_specs/` (the tables DR-0003 used: §5.1, §6.1A-C,
  §6.2) carries min/typ/max global process limits only. A search of those
  files finds no matching coefficient (Pelgrom-style A_R / A_C) for any
  resistor or MIM capacitor.
- The vendored `sm141064.ngspice` contains, in the unrelated diffusion
  resistor `nplus_u`, a commented-out placeholder
  (`par_r=0.012608`, `var_r='0.7071*par_r*1e-06/sqrt(par*r_l*r_w)'`), which
  works out to a relative sigma of about 0.89 % at 1 um^2 of resistor area
  (about 0.89 %.um). It is disabled in the shipped deck (`mis_r = 0`), is for
  a different resistor type, and is not a documented specification. It is
  used below only as an order-of-magnitude cross-check, not as a source.

So there is **no PDK-sourced sigma** for either device. The values below are
engineering assumptions, flagged as DR-0003 flags its own.

[0021](0021-runtime-discipline-trim-resolution-sof-loop-model.md)
(its Decision item 1), which landed before this record, constrains
S1 on the committed design: the realized trim curve has a geometric-mean
step of 0.41-0.47 %/code (not the ratified 0.314 %/code) and four
**deterministic** non-monotone carries of -1.4 % to -6.1 % (0x7F->0x80,
0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0) with no mismatch at all. Any
mismatch-driven monotonicity statement below is therefore made relative to
the zero-mismatch baseline, not to an ideal +1 LSB step.

klayout-tools#2898 (`family_mismatch` reports these subcircuits as
`other`, `active: null`) is a reporting gap and does not change the
mechanism: no `klt sim` option exists to enable mismatch on a subcircuit
whose model body lacks the hook. The declaration half of the gap is filed as
klayout-tools#2911.

## Decision

### 1. Scope: Monte Carlo additionally injects a design-owned matching model

The item-6 campaign samples MOS mismatch (from the PDK models) **and**
injects a per-instance relative mismatch on every `ppolyf_u_1k` instance
(ladder `RFIX`, `R0`-`R7`; bias divider `RBA`/`RBB`/`RBC`/`RZ`) and on the
`cap_mim_1f0fF` instance (`CTIMING`). "MOS only with a deterministic bound"
is not adopted (see alternatives).

### 2. The matching model

For each injected instance `i`, a multiplicative relative error
`delta_i ~ N(0, sigma_i^2)`, independent across instances, Gaussian, zero
mean. Area-scaled (Pelgrom-style) per instance:

```
sigma_i = mm_scale * sw_stat_mismatch * A_x / sqrt(W_i * L_i)     (W, L in um)
```

| Term | Coefficient | Status |
|---|---|---|
| `A_R`, `ppolyf_u_1k` relative resistance | **1.0 %.um** (per device) | **Engineering assumption, no public source.** Same order as the disabled `nplus_u` placeholder (about 0.89 %.um); rounded up. |
| `A_C`, `cap_mim_1f0fF` relative capacitance | **1.0 %.um** (per device) | **Engineering assumption, no public source.** Set equal to `A_R` for want of data. |

W and L are the drawn instance dimensions in the netlist (ladder `r_width`
2 um; `r_length` 0.7482 um for `R0`, doubling per bit to 95.7751 um for
`R7`; `CTIMING` 20 um x 10 um). Consequences of the formula on the current
design (arithmetic done for this record, not simulated):

| Instance | sigma_i (relative) | Note |
|---|---|---|
| `R0` (LSB) ... `R7` (MSB) | 0.82 %, 0.58 %, 0.41 %, 0.29 %, 0.20 %, 0.15 %, 0.10 %, 0.07 % | segments are not unit-replicated: each is one resistor of binary length, so the small ones match worst |
| `RFIX` | 0.17 % | common-mode to the code; shifts the whole curve, absorbed by trim |
| `RBA`/`RBB`/`RBC`, `RZ` | 0.07 %, 0.12 % | divider ratio and bias-resistor error |
| `CTIMING` | 0.07 % | a single capacitor has no matching partner; see claims below |

**Ideal-ladder assumption.** The LSB-unit figures below treat the segment
resistance as the only code-dependent term, i.e. an ideal binary ladder in
which segment `Ri` is worth exactly 2^i LSB. The realized curve also
contains the trim switches' on-resistance, which is MOS and is already
covered by the PDK's MOS mismatch, and it is not an ideal binary ladder
(DR-0021: 0.41-0.47 %/code mean step, four non-monotone carries at 0x). The
figures are an order-of-magnitude sizing of the injected term, not a
prediction of the realized curve.

Under that assumption, in LSB units segment `Ri` has sigma
0.0082 x 2^(i/2) LSB (0.008 LSB for `R0`, 0.093 LSB for `R7`). The summed
ladder sigma is 0.0082 x sqrt(255), about 0.13 LSB. In frequency that is
about 0.041 % at the ratified 0.314 %/code (DR-0003), or about
0.054-0.061 % at DR-0021's realized 0.41-0.47 %/code mean step. Either
figure is far inside the DR-0003 +/-0.300 % trim-DAC assumption, so the
conclusion does not depend on which step is used: the 0.300 % figure is
equivalent to a roughly 3-sigma bound only if `A_R` were about 2.4 %.um
(0.314 %/code) or about 1.6-1.9 %.um (0.41-0.47 %/code). The campaign
reports the sampled ladder contribution next to the 0.300 % figure; it does
not treat the assumption as confirmed, and does not edit it.

**Step-size deviation, not raw step sign.** For each sampled transition the
campaign reports the deviation of the sampled step from the same
transition's step in the zero-mismatch run (`sampled step - 0x step`). A
transition `k` (`R_k` against the sum of the lower segments) has a
deviation sigma of 0.0082 x sqrt(2^(k+1) - 1) LSB under the ideal-ladder
assumption; for the MSB transition (0x7F->0x80) that is 0.13 LSB at 1x. A
mismatch-induced non-monotonicity is counted only on transitions that are
monotone in the zero-mismatch run, and its likelihood depends on that
transition's baseline step margin divided by the deviation sigma. The
transitions DR-0021 lists as non-monotone at 0x (including 0x7F->0x80) are
non-monotone in essentially every sample at every scale; they are a
deterministic trim-bank property, reported as such and not attributed to
mismatch. For illustration only: a transition with an ideal +1 LSB
baseline step and the MSB-transition sigma would need about a 7.7-sigma
event at 1x.

**Not modelled** (stated so nobody infers otherwise): layout gradients and
common-centroid benefit, contact/end-resistance and edge-roughness terms
(which worsen the short segments), voltage-coefficient and self-heating
mismatch, MIM edge/fringe and capacitor-density gradients, and any
correlation between instances. The model is a random, local, area-scaled
term only. Global process spread (+/-20 % resistor, +/-15.33 % MIM) stays the
corner models' job (DR-0019 row 3).

**Reproducibility.** Draws come from ngspice's seeded generator via
`agauss(0, sigma_i, 1)` in body `.param` lines; `klt sim` `monte_carlo`
already seeds `.options seed=` per sample (the MOS terms use the same
mechanism). The recorded seed stays `20261008` (DR-0019). Each sample's
drawn values are `set`/echoed into the report with the code selection so a
sample can be re-derived.

### 3. Negative controls (DR-0019 section 2) for the injected terms

- **Zero-mismatch run** (`sw_stat_mismatch=0`): the injected `delta_i` are
  identically zero via the same switch the MOS terms use, so the zero run
  tests the whole plumbing, injected terms included. It must reproduce the
  corner value within the simulator tolerance recorded in the groundwork
  (set from measured repeatability, 0.25 %).
- **Inflated run (3x)**: the single `mm_scale` parameter multiplies every
  injected sigma, and the same 3x is applied to the PDK's MOS terms, as
  DR-0019 states for "the mismatch sigma". The pass criterion is DR-0019's:
  clearly degraded yield, claim fails. This record notes the honest limit: at
  `A_R` = 1.0 %.um the 3x MSB-transition deviation sigma is about 0.39 LSB
  (ideal ladder). Even on a transition with an ideal +1 LSB baseline step
  that would turn monotone into non-monotone in only about 0.5 % of dies,
  which by itself is not a clear failure. The detection of the harness
  therefore rests on the aggregate run (MOS terms dominate comparator
  offset); the injected terms are shown live by a second control.
- **Injected-term sensitivity control** (not a yield claim): with MOS
  mismatch off, injected terms alone at 1x and at 10x. **Pass criterion**:
  the sampled sigma of the step-size deviation from the zero-mismatch run
  (MSB transition and each other reported transition) and of the
  code-selection spread must scale with `mm_scale`, with a 10x/1x ratio of
  about 10 within sampling error. This criterion is insensitive to the
  deterministic carries, because a fixed offset does not change the sampled
  spread. A non-monotonic fraction is **not** the pass test: the
  0x-non-monotone transitions (DR-0021) would show a nonzero fraction even
  with a dead injection. A change in the non-monotonic fraction on
  transitions that are monotone at 0x may be reported as supporting
  information only. If the sigma does not scale, the injection is not live
  and the campaign yields no verdict, exactly as DR-0019 says for any
  control that misbehaves.

This adds a control and does not change DR-0019's.

### 4. Where it lives, and why it stays out of the committed netlist

- **Mechanism**: netlist-body multipliers generated by
  `sim/mc-groundwork/gen_bench.py` (extended by the campaign issue, not by
  this record). It rewrites the `m=1` instance multiplier on the listed
  `ppolyf_u_1k` and `cap_mim_1f0fF` X cards in the DUT text it already
  inlines from `design/netlist/pvt_tb.spice`, adding `.param` draw lines:
  `m='1/(1+d_<inst>)'` for resistors, `m='(1+d_<inst>)'` for the capacitor.
  A probe made for this record (one ngspice `.op`/`.ac`, two instances,
  `gf180mcuC`) showed that a non-integer `m` on the X card scales the
  resistor current by 1/(1+d) and the capacitor admittance by (1+d) exactly
  (1.0100 for d = 0.01 in both). Known approximation: `m` also scales the
  device's terminal (end) resistance and substrate parasitic capacitance,
  which is a small, conservative conflation (end resistance is under 10 % of
  a segment). The generator fails loudly if a `ppolyf_u_1k` or
  `cap_mim_1f0fF` X card is found that is neither mapped nor on an explicit
  exclusion list, so a new instance cannot be silently left uncovered.
- **Rejected mechanism: a model wrapper.** A modified copy of the PDK
  subcircuit would fork the vendored model (hash-pinned in the groundwork
  evidence), has to be maintained against PDK updates, and still needs a
  per-instance draw. The netlist-body route touches no PDK file.
- **Committed netlist untouched.** `design/netlist/*` (the layout-matched,
  LVS-checked, xschem-generated netlist) is not edited and gains no
  multipliers. The multipliers exist only in generated files under `sim/`
  that `gen_bench.py` writes from a read-only copy of the committed text;
  the schematic, the layout and the post-layout (PEX) benches never see
  them. A bench with injection at `mm_scale=0` must equal the committed
  netlist's behaviour (the zero control above).
- **klayout-tools#2898 / #2911.** Even if #2898 is fixed, `klt sim`'s
  `family_mismatch` will report the model's own state (resistor and MIM
  inactive) while the body injects mismatch, or `active: null` as now. The
  campaign therefore cites its own manifest of injected terms (instance,
  sigma, scale) as the evidence that they were live, and records the
  discrepancy; it does not rely on `family_mismatch`. #2911 asks for a
  first-class declaration; this record's mechanism is the stop-gap and can
  be superseded if it lands.

### 5. What the campaign may and may not claim

May claim:
- S1-S3 yield **under the stated model** ("with an assumed area-scaled
  random mismatch, `A_R` = `A_C` = 1.0 %.um, plus the PDK's MOS mismatch"),
  with the sigma assumption quoted next to every yield figure.
- The sampled ladder contribution (step-size deviation sigma relative to
  the zero-mismatch run, mismatch-induced non-monotonic fraction on
  transitions monotone at 0x, code-headroom) as simulation outputs of that
  model. The 0x non-monotone carries (DR-0021) are reported separately as a
  deterministic property of the design, not as a mismatch yield.
- A sensitivity statement: the yield at 1x and 3x, and the `A_R` at which
  the claim would stop passing if the campaign computes it.

May not claim:
- That trim-DAC element mismatch is "validated", "measured", or
  "PDK-characterised", or that the DR-0003 +/-0.300 % assumption is
  confirmed or tightened by this campaign. The sigma is an assumption with
  no public source, and a silicon matching measurement would supersede it.
- That capacitor mismatch limits or does not limit accuracy in silicon: a
  lone timing capacitor has no partner, its die-level deviation is absorbed
  by the single-point trim, and global spread stays a corner matter.
- Any effect of layout gradients, common-centroid benefit, or end/contact
  resistance (not modelled).
- Anything about the ratified rows other than a yield statement under the
  model. No row is relaxed or tightened; a failure is a separate evidence
  record (DR-0019 consequences).

### 6. Effect on ratified rows

None. No value in DR-0002, DR-0003, DR-0017 or DR-0019 changes. This record
fixes only how the yield evidence is produced.

## Alternatives considered

- **MOS mismatch only, with the ladder/cap bounded deterministically**
  (the other option in #85). Rejected: S1 monotonicity and headroom are
  most sensitive to ladder matching, and a deterministic +/-0.300 % bound
  says nothing about per-die step-size spread; it would leave the flagged
  assumption exactly as unexamined as today. Kept only as the fallback if
  the injection cannot be made to scale (the sensitivity control fails).
- **Take the commented-out `nplus_u` placeholder as the source.** Rejected
  as a source: a different device, disabled by the PDK, undocumented.
  Used as a cross-check only.
- **Model wrapper / patched PDK subcircuit.** Rejected, see section 4.
- **Wait for a klt-native injection feature (#2911).** Rejected: unbounded
  wait, and the campaign design should not depend on it. This record is
  supersedable when it lands.
- **A larger, "safe" `A_R` (for example 3 %.um).** Rejected for the base
  run: an unsourced pessimistic number reads as a result. The 3x control
  already brackets it.

## Consequences

- The campaign issue now has a defined injection design to implement in
  `gen_bench.py` (parameters `mm_scale`, per-instance `d_<inst>`, an
  instance-coverage assertion, a per-sample manifest). This record does not
  implement it and no evidence is added.
- S1/S2/S3 yield statements are conditional on two flagged assumptions
  (`A_R`, `A_C`); the sigma must be quoted with every figure, and revised by
  a superseding record if a public source or silicon data appears.
- At 1x the ladder term (about 0.041 % f at the ratified 0.314 %/code, about
  0.054-0.061 % at DR-0021's realized 0.41-0.47 %/code, both under the
  ideal-ladder assumption) is well under the DR-0003 +/-0.300 % assumption,
  so the sampled ladder is unlikely to be the dominant term. That is a
  property of the assumed sigma and is not evidence that the assumption is
  conservative.
- S1 monotonicity cannot be a plain "all steps positive" yield on the
  committed design: DR-0021's four carries are non-monotone at 0x. The
  campaign reports the mismatch contribution relative to the 0x baseline;
  whether the deterministic carries fail S1 is a trim-bank question
  (DR-0021 consequences), not something this record or the mismatch
  campaign resolves.
- The 3x control may not by itself fail the claim for the ladder; the
  extra sensitivity control carries that burden, and a failure there means
  no verdict.
- The mismatch seed and run count are unchanged. The `m` approximation adds
  a small, bounded modelling error that the zero control exposes.
- Cost: negligible extra solver time (parameters only); one more control run
  in the campaign.
