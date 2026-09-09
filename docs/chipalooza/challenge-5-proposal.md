# Chipalooza Challenge #5 proposal — gf180-rcosc

**Status of this repository:** the ratified spec, a full schematic, a full
PVT-corner simulation campaign, and a DRC-clean/LVS-matched GDS for the
entire `rcosc_top` hierarchy are all committed, plus a first post-layout
(parasitic-extracted) PVT re-verification pass. Nothing has been fabricated
and nothing has been measured on silicon. Two ratified spec rows are not
met by the current design — trim range and both post-trim accuracy rows —
and are reported as such below, not rounded up or hidden; that gap, and
whether it can be closed by further schematic work or is a fundamental
property of this topology on this PDK, is exactly the kind of question a
shuttle seat and a bench exist to answer.

This document contains no personal or institutional identifiers; every
number in it traces to a file already committed under this repository's
`spec/` or `sim/` directories, cited by path throughout.

---

## 1. Block type

A free-running, digitally trimmable RC (relaxation) oscillator — not a
PLL, and not a crystal oscillator. This repository's fleet siblings that
cover clock generation are all PLLs; this block is the fleet's only
internal RC-based clock source with a digital trim interface, so it has no
reference input and no feedback loop to lean on — its accuracy comes
entirely from the RC network itself, from trim, and from how well the
design's bias/comparator path holds up across process, temperature, and
supply.

## 2. I/O list mapped to the slot budget

This repository does not carry a committed, numbered Challenge #5
slot-budget ceiling document of its own (the kind of table a sibling
canary with a program-specific pin budget would cite by number). Absent a
sourced ceiling to compare against, the table below states this block's
actual top-level pin count and category, mapped into the same two digital
categories the parent epic issue names for this block ("digital control
inputs" for the trim interface, "digital test outputs" for the clock and
any test/probe points) — a digital-heavy shape, not an analog one.

The full, and only, top-level pin list is `rcosc_top`'s own symbol,
[`design/rcosc_top.sym`](../../design/rcosc_top.sym) (`* Pins: vdd, vss,
clk, t0..t7 (t7=MSB)`) — 11 pins total. This is also, independently, the
exact pin list the post-layout PEX extraction command uses (`--pins
vdd,vss,clk,t0,t1,t2,t3,t4,t5,t6,t7`,
[`sim/pvt-postlayout/results/20260907T131703Z/summary.md`](../../sim/pvt-postlayout/results/20260907T131703Z/summary.md)),
so the pin list below is not merely a schematic-level claim — it is the
same list the layout-level parasitic extraction already exercises.

### 2.1 Digital control inputs (8 of 8 trim bits)

| Pin | Width | Purpose |
|---|---|---|
| `t0`..`t7` | 8 (1 each) | 8-bit binary-weighted digital trim code, `t7` = MSB, setting the switched-resistor trim bank's resistance and therefore the RC time constant. Per the ratified spec, this is a **single-point trim at test**: one code is chosen once (see the bench test plan, §5) and held fixed, not re-trimmed continuously at runtime. |

### 2.2 Digital test outputs (1 pin)

| Pin | Width | Purpose |
|---|---|---|
| `clk` | 1 | The free-running oscillator output — the block's sole output and its only test/probe point brought to the top-level pin list. Every frequency, trim-range, and accuracy figure in §4 is a measurement of this pin. |

### 2.3 Dedicated pads (2 pins)

| Pad | Purpose |
|---|---|
| `vdd` | 3.3 V core supply (3.0–3.6 V) — see §4's explicit no-5.0V-rail note. |
| `vss` | Ground. |

### 2.4 No analog I/O

`rcosc_top`'s top-level pin list exposes **no analog pin**. The
analog-domain nodes internal to the design — the bias generator's
threshold outputs `vh`/`vl` and current reference `ibias`
(`rcosc_bias.sch`), and the RC timing node `vc` — are wired entirely
within the `rcosc_top` hierarchy and are not brought out to `rcosc_top`'s
own pins (confirmed directly against `design/rcosc_top.sym`'s pin list
above). Nothing in this proposal requests shared-analog-line or
bandgap-reference budget.

## 3. Functional description

Relaxation oscillator per
[`spec/decision-records/0001`](../../spec/decision-records/0001-relaxation-oscillator-topology.md):
a single-resistor-charge / switch-discharge ("sawtooth") variant, not a
symmetric charge/discharge design (duty cycle is not a ratified spec row).
`rcosc_top.sch` composes four sub-blocks
([`design/README.md`](../../design/README.md) "Topology"):

- **`rcosc_trim_bank`** charges the timing capacitor `CTIMING`
  (`cap_mim_1f0fF`, 200 fF, at node `vc`) continuously from `VDD` through
  an 8-bit binary-weighted switched resistance — the trim bank directly
  sets the RC time constant, driven by the `t0..t7` control-input pins
  (§2.1).
- **`rcosc_comparator`**, instantiated twice, compares `vc` against the
  two threshold references `vh` (2/3 · VDD, fires at charge-complete) and
  `vl` (1/3 · VDD, fires at discharge-complete).
- An inline NOR-NOR SR latch (8 transistors) toggles between charge and
  discharge state on those two comparator firings; the latch state **is**
  `clk`.
- **`MDISCH`** shorts `vc` to `VSS` during the discharge state, resetting
  the timing node for the next cycle.
- **`rcosc_bias`** generates `vh`/`vl` from a supply-ratiometric resistor
  divider (not a bandgap reference — an explicit, open option under
  [DR-0001](../../spec/decision-records/0001-relaxation-oscillator-topology.md))
  and a current reference (`ibias`, via `RBIAS`) that both comparator
  instances mirror into their own tail current sources. `RBIAS`'s length
  and the comparator tail-mirror ratio have been re-derived twice since
  first schematic capture to bring the block's running quiescent current
  under the ratified target — final sizing `RBIAS L = 210 µm`,
  `MTAIL W = 16 µm`/`nf = 8` (8:1 mirror), ratified by
  [DR-0009](../../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md).

**Temperature-coefficient compensation.** No active TC compensation is
present in the bias/reference generator. This was an explicitly open
question in the ratified spec (whether to add active compensation or rely
entirely on runtime discipline to close the gap to USB full-speed
compliance) and was resolved — before any PVT-corner or layout work — by
[DR-0004](../../spec/decision-records/0004-no-active-tc-compensation-runtime-discipline.md):
**no active compensation is added**; the design relies entirely on runtime
discipline (e.g. USB start-of-frame timing, the ratified spec's reserved
"Runtime-disciplined" row) to close the gap from the free-running
figure — ±1.1% at the calibration point, worsening to +8%/−9% across the
full −40…+85 °C temperature range (both figures always read together, see
§4) — down to the ≤ ±0.25% USB full-speed target. No schematic topology
change resulted from that decision; `rcosc_bias.sch`, `rcosc_trim_bank.sch`,
and `rcosc_top.sch` are exactly as this section describes them.

## 4. Target specification

**Every row is re-derived directly from this repository's `sim/` results**,
cited by path. **This block has no 5.0 V rail dependency**: every device in
this design is instantiated from gf180mcu's 3.3 V-rated device families,
and no `sim/` evidence exercises it above 3.6 V — the table is stated only
at 3.3 V nominal (3.0–3.6 V), consistent with the ratified spec's own
supply row. This is an explicit statement, not a blank or omitted row.

**Post-layout divergence, applies to every accuracy row below**: post-layout
(PEX-extracted) re-verification
([DR-0010](../../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md),
[`sim/pvt-postlayout/results/20260907T131703Z/summary.md`](../../sim/pvt-postlayout/results/20260907T131703Z/summary.md))
found that, at the same fixed trim code and the same `tt`/`ff`/`ss` ×
3-temperature × 3-supply corner-endpoint subset used for its 27-point
check, a `klt extract --parasitics`-annotated netlist oscillates
**slower** than the schematic-level netlist at every single point checked,
by **−1.88% to −29.52%** (mean −10.32%) — well beyond the ratified ±1.1%
calibration-point accuracy budget (which, per this document's own
reporting convention, is always read alongside the ratified full
temperature-range budget of +8% / −9%) on its own. DR-0010 did not re-run the
full per-corner-code trim/calibration methodology under PEX (only this
fixed-code, corner-endpoint subset), so the table below reports the
schematic-level simulated figures as the primary numbers, with this
divergence footnoted rather than blended in: **actual post-layout accuracy
is worse than the schematic-level figures shown**, in every row the
divergence bears on.

| # | Parameter | Ratified target | Simulated result | `sim/`\* citation | Verdict |
|---|---|---|---|---|---|
| 1 | Output frequency | 48.000 MHz | Max reachable (schematic, reference corner): **58.9870 MHz** at code `0xFF` | `sim/pvt/results/20260907T090653Z/summary.md` | **Met** |
| 2 | Trim range | ±40% (28.8–67.2 MHz) | **±35.50%** realized (28.0769–58.9870 MHz) | `sim/pvt/results/20260907T090653Z/summary.md` | **Not met** — 4.5 percentage points short, per DR-0009 |
| 3 | Trim step (resolution) | 0.314 %/code (150.6 kHz/code LSB); half-LSB ±0.157% (arithmetic, not separately simulated) | **0.4317 %/code** average, realized over the trim range in row 2 | `sim/pvt/results/20260907T090653Z/summary.md` | **Met**, per the campaign's own generated verdict (average step at the realized range) |
| 4 | Free-running, untrimmed process spread (fixed T = 27 °C, V = 3.3 V) | ±35% first-order (−27.7%/+47.6% exact) | **−26.34% / +42.68%** across the 7 simulated process corners at code `0x80` | `sim/pvt/results/20260907T090653Z/summary.md` | **Within** the ratified bound |
| 5 | Post-trim accuracy — **global code `0xC0`** (one code applied across every corner, calibrated at `tt`/27 °C/3.3 V against the ratified 48.000 MHz target) — **calibration point** (±1.1% ratified) **and full temperature range** (+8%/−9% ratified), stated together | ±1.1% at the calibration point; **+8% / −9% across the full −40…+85 °C temperature range** (both ratified, read together) | Calibration point: **−34.85% / +54.78%**. Full temperature range: **−40.82% / +68.13%** (both simulated, read together) | `sim/pvt/results/20260907T090653Z/summary.md` | **Exceeds** both, this methodology†|
| 6 | Post-trim accuracy — **per-corner code** (each process corner individually calibrated at its own 27 °C/3.3 V point against the surrogate target 39.1204 MHz — closer to the ratified spec's "single-point trim at test" description, since the ratified 48.000 MHz target is unreachable at every corner, per [DR-0005](../../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md)/[DR-0006](../../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md)) — **calibration point** (±1.1% ratified) **and full temperature range** (+8%/−9% ratified), stated together | ±1.1% at the calibration point; **+8% / −9% across the full −40…+85 °C temperature range** (both ratified, read together) | Calibration point: **−11.50% / +13.19%**. Full temperature range: **−19.41% / +27.85%** (both simulated, read together) | `sim/pvt/results/20260907T090653Z/summary.md` | **Exceeds** both, this methodology†|
| 7 | Runtime-disciplined accuracy (reserved) | ≤ ±0.25% (USB full-speed compliance) | Not designed, per [DR-0004](../../spec/decision-records/0004-no-active-tc-compensation-runtime-discipline.md) — this stage carries the entire burden of closing the gap from row 5/row 6's free-running figures (calibration point **and** full-temperature-range, always read together, per rows 5–6 above) down to this target | — (reserved, no `sim/` evidence exists or is expected pre-design) | **Not evaluated** — reserved, undesigned |
| 8 | Supply | 3.3 V core (3.0–3.6 V); **no 5.0 V rail dependency** | Exercised across 3.0/3.3/3.6 V in every PVT campaign committed to date | `sim/pvt/results/20260907T090653Z/summary.md` | **Met** (exercised as specified; explicitly no 5.0 V row — see note above) |
| 9 | Quiescent current, running (`< 500 µA`) | < 500 µA (running) | **Met at the reference corner only; exceeds elsewhere in the full PVT-corner grid** (issue #35/[DR-0011](../../spec/decision-records/0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md)). Reference corner (`tt`/27 °C/3.3 V): met at every code, worst case 468.61 µA at `0xFF` (`sim/iq/results/20260907T090639Z/`). Full 63-point process × temperature × supply grid: worst-case corner `ff`/85 °C/3.6 V **exceeds** at every simulated code, e.g. **623.68 µA** at code `0xC0` (the single-point post-trim calibration code, [DR-0010](../../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)/#28) vs. 400.87 µA at the reference corner — 8 of 63 grid points exceed at `0xC0` (`iq_run`, the metric this row actually names, per [DR-0008](../../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md)/[DR-0009](../../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md)). `iq_op` (continuity only) is not this row's verdict basis | `sim/iq/results/20260907T090639Z/README.md` (reference corner); `sim/iq/results/20260909T225306Z/README.md` (full grid) | **Exceeds**, off-reference — re-sizing is a follow-on, not done in DR-0011 (ratified `< 500 µA` target unchanged) |
| 10 | Startup time | ≤ 10 µs to within trimmed accuracy | No `sim/` evidence exists for a measured startup time in this repository to date; the ratified target's own numeric precedent is flagged "unverified this session" in [DR-0003](../../spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md) | — (gap, not invented) | **Not evaluated** — no simulation evidence exists; see §5 for how the bench closes this |
| 11 | Temperature range | −40 °C to +85 °C (industrial) | Exercised at −40/27/85 °C in every PVT campaign committed to date | `sim/pvt/results/20260907T090653Z/summary.md` | **Met** (exercised as specified) |

\* All schematic-level citations above are to the same run,
`sim/pvt/results/20260907T090653Z/` (the final campaign against the
[DR-0009](../../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md)
sizing) except row 9, which cites the reference-corner Iq sweep
`sim/iq/results/20260907T090639Z/` (the matching Iq sweep at the same
sizing) and the full PVT-corner Iq grid
`sim/iq/results/20260909T225306Z/` (issue #35/DR-0011).

† See the post-layout divergence note above this table: post-layout
(PEX-extracted) re-verification at this same trim code
([DR-0010](../../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md))
shows a further, real, monotonic frequency reduction of up to 29.52% on
top of the schematic-level residual reported in rows 5–6 — no ratified
row's disposition changes as a result (both rows were already "exceeds" at
the schematic level), but the true post-layout accuracy is worse than what
rows 5–6 show.

## 5. Bench test plan

This is a plan for measuring the physical part on a bench — distinct from,
and downstream of, the simulation testbenches already committed under
`sim/` (`design/smoke_test.sch` bring-up,
[`sim/pvt/pvt_sweep.py`](../../sim/pvt/) full-factorial PVT campaigns,
[`sim/iq/iq_sweep.py`](../../sim/iq/) quiescent-current sweeps, and
[`sim/pvt-postlayout/pex_pvt_sweep.py`](../../sim/pvt-postlayout/)
post-layout re-verification).

1. **Bring-up.** Apply `VDD = 3.3 V`, hold trim code mid-scale (`0x80`),
   confirm `clk` free-runs on an oscilloscope/frequency counter at a
   sensible frequency, and cross-check against row 4's untrimmed
   process-spread figure (±26.34%/+42.68% about the schematic-level
   nominal).
2. **Trim sweep.** Drive the 8-bit trim bus (`t0..t7`, digital control
   inputs, §2.1) from a test fixture or FPGA across the full `0x00..0xFF`
   code space, logging `clk` frequency at each code with a frequency
   counter. Compare the realized curve's range, step size, and
   monotonicity against row 2/row 3's schematic-level figures (and, where
   available, the post-layout comparison in the divergence note above §4).
3. **Single-point trim calibration at test.** At bench-ambient temperature
   (nominally 27 °C) and nominal `VDD = 3.3 V`, binary-search (mirroring
   the per-corner-code methodology row 6 already uses in simulation) the
   trim code that brings `clk` closest to the 48.000 MHz target — or, if
   that target proves unreachable on the packaged part (as it is at every
   simulated corner, per DR-0005/DR-0006), a fixture-defined surrogate
   target — and fix that single code as the part's permanent trim, per the
   ratified spec's own "single-point trim at test" methodology.
4. **Post-trim accuracy at the calibration point.** With the code fixed
   from step 3, sweep `VDD` across 3.0–3.6 V at bench-ambient temperature
   and record `clk` frequency deviation from the calibration point.
   Compare against the ratified ±1.1% calibration-point target — always
   read together with the ratified full-temperature-range target of
   **+8% / −9%** measured in the next step, never alone.
5. **Full-temperature-range accuracy.** Place the packaged part in a
   temperature chamber and sweep −40 °C to +85 °C at each of 3.0/3.3/3.6 V
   supply, with the calibration code from step 3 held fixed (not
   re-trimmed at each temperature, to isolate temperature-driven drift
   from the trim mechanism itself). Record `clk` frequency deviation from
   the calibration point at every condition, and compare against the
   ratified **+8% / −9%** full-temperature-range target — reported in the
   same breath as step 4's ratified ±1.1% calibration-point target, per
   this document's own reporting convention.
6. **Quiescent current.** Measure `VDD` supply current with a bench
   ammeter while `clk` is actively toggling (the "running" reading — this
   is the ratified target's actual basis, `iq_run`, per DR-0008/DR-0009)
   at each trim code and PVT condition exercised in steps 2–5. Also record
   a DC/idle-adjacent reading for continuity with the `iq_op` figure
   already tracked in `sim/`, explicitly noting that the DC-equilibrium
   reading is not the quantity the ratified `< 500 µA` (running) row
   names.
7. **Startup time.** Trigger an oscilloscope on the `VDD` rail's rising
   edge at power-on and measure time to the first `clk` edge that falls
   within the calibrated accuracy window. No `sim/` evidence exists for
   this figure today (row 10) — this bench step is the first place it
   gets an actual measurement, closing that gap on the packaged part
   rather than by further pre-tapeout simulation.
8. **Untrimmed process-spread cross-check.** Across a batch of packaged
   parts spanning normal process-lot variation, measure `clk` frequency
   at trim code `0x80` (mid-scale) at fixed `T = 27 °C` / `V = 3.3 V`, and
   compare the measured spread against the ratified ±35% (−27.7%/+47.6%)
   target and the schematic-level ±26.34%/+42.68% simulated figure (row
   4) — this step is what would show whether the schematic-level model,
   or the further-negative post-layout PEX-extracted shift (DR-0010,
   §4), tracks real silicon more closely.

Minimum bench instrumentation: a programmable `VDD` supply (3.0–3.6 V), a
frequency counter or oscilloscope on `clk`, a digital test fixture/FPGA
capable of driving the 8-bit `t0..t7` trim bus and reading `clk` back, an
oscilloscope for the startup-time trigger measurement (step 7), a bench
ammeter in series with `VDD` for the quiescent-current measurements (step
6), and a temperature chamber for step 5 (every row in §4 that carries a
temperature dependence was simulated across −40…+85 °C, so the chamber
must cover at least that range).
