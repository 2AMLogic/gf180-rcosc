# design — gf180-rcosc schematic sources

**Status: schematic capture (issue #6, T1 item 1 of the gap tracker #5) —
design sources committed and netlist-reproducible — since carried through a
full PVT-corner campaign and several re-sizing/re-balancing passes (issues
#12/#16/#18/#20/#22/#24, decision records DR-0005 through DR-0009 below)
and a comparator/bias-path PVT revision (issue #39,
[DR-0012](../spec/decision-records/0012-comparator-bias-path-pvt-revision.md)).
The layout is **current with the post-#39 schematic**: the bias cell was
re-drawn and the whole hierarchy re-verified (issues #13/#27/#28/#44, see
[`layout/README.md`](../layout/README.md)),
[DR-0013](../spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md))
— DRC-clean, LVS-matched, and post-layout (PEX) re-verified against the
re-spun `rcosc_bias` GDS; DR-0013 supersedes
[DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)'s
post-layout figures for the post-#39 schematic (the parasitic shift
deepened to −11.24 % … −41.42 %, always slower).
This directory holds the schematic sources and their PVT-corner evidence;
layout geometry and DRC/LVS/PEX results live under `layout/`.

## What's checked in

```
design/
  rcosc_bias.sch/.sym        ratiometric V_H/V_L threshold + tail-current bias
  rcosc_comparator.sch/.sym  5T differential-pair comparator + output buffer
  rcosc_trim_bank.sch/.sym   8-bit binary-weighted switched-resistor trim bank
  rcosc_top.sch/.sym         the composed oscillator block (top of the hierarchy)
  smoke_test.sch             bring-up testbench: DC supplies + fixed trim code
  xschemrc                   project-local xschem config (PDK resolution)
  regen-netlist.sh           regenerates design/netlist/*.spice from the .sch files
  run-smoke-test.sh          regenerates netlists + runs the ngspice smoke test
  netlist/                   xschem-derived SPICE netlists (see below)
```

`design/netlist/` is **derived, not hand-written**: `regen-netlist.sh`
re-exports it from the `.sch` sources every time it is run, so it stays in
sync with schematic edits (the T1 pass condition requires reproducibility,
not a one-off export). `design/netlist/pdk_include.spice` is regenerated
per-machine from `$PDK_ROOT`/`$PDK` and is **not** committed (see
`.gitignore`) because it embeds an absolute, machine-specific path;
`design/netlist/smoke_test.log` **is** committed — it is append-only
evidence of an actual run, not a scratch file.

## Regenerating the netlist

```bash
# PDK_ROOT is resolved automatically via `klt pdk find --pdk gf180mcuC` if
# not already set; PDK defaults to gf180mcuC.
design/regen-netlist.sh
```

This netlists every entry-point schematic (`rcosc_top.sch`, the block
itself, and `smoke_test.sch`, the bring-up testbench) with
`xschem -n -x -q -r --rcfile design/xschemrc`, and writes the model-library
include shim `design/netlist/pdk_include.spice` for the smoke test to
`.include`. Confirmed to run with **zero xschem warnings/errors** (no
unresolved symbols, no shorted/overlapped-instance ERC flags) as of this
issue.

## Running the smoke test

```bash
design/run-smoke-test.sh
```

Regenerates the netlist, then runs `design/netlist/smoke_test.spice`
through `ngspice -b`, appending output to `design/netlist/smoke_test.log`.
**This is a functional/DC sanity check only — not a PVT-corner or accuracy
claim** (explicitly out of scope for this issue; see `spec/README.md`'s
maturity ladder: schematic simulated across PVT is a later increment).

The smoke test drives `VDD = 3.3 V` and trim code `0x80` (`t7 = 1`,
`t0..t6 = 0`) and runs an `.op` (prints the bias/threshold node voltages
and the `.op` supply current) followed by a transient measuring two
consecutive rising edges of `clk` plus the block's **running** supply
current. The transient window went 4 µs → 400 ns in issue #16 (the re-sized
schematic free-runs several times faster, so 4 µs simulated far more
periods than the two-edge measurement needed) and 400 ns → 1200 ns in issue
#22, to fit the 20-whole-period averaging window the running-current
measurement needs. As of issue #24's last run (see "Bias generator" below
for the re-sizing itself):

- `.op`: `vh = 2.200 V` (exactly 2/3 · VDD), `vl = 1.100 V` (exactly
  1/3 · VDD) — the ratiometric bias generator is producing sane,
  non-degenerate threshold nodes (the threshold divider is untouched by
  every `RBIAS` re-size to date).
- Transient: `clk` **free-runs** — measured period ≈ 25.5 ns (≈ 39.1 MHz)
  at code `0x80`, using the same first-two-rising-edges methodology as the
  original issue #6 measurement. This is **not** a steady-state accuracy
  figure (see the caveat issue #6 already carried forward, and "Trim bank
  sizing" below for the steady-state, corner-simulated numbers): the first
  two edges include a few cycles of startup transient before the
  oscillator settles. It remains a useful bring-up sanity check (confirms
  free-running oscillation and sane bias nodes), not a substitute for the
  reference-corner steady-state and PVT-corner results below.
- Quiescent current, **both metrics, reported together** (issue #22,
  [DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md);
  metric-basis update issue #24,
  [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md)):
  `iq_ua = 754.90 µA` (the `.op` figure issue #20 introduced — no longer
  DR-0003 Row 4's verdict basis, see below) and `iq_run_ua = 387.09 µA`
  (`-i(vdd)` averaged over 20 whole periods, rising edges 5..25 — **this
  is** Row 4's basis). `iq_run` is under DR-0003 Row 4's ratified
  `< 500 µA` (running) target at every simulated code; `iq_op` is not, and
  as of DR-0009 that is expected rather than a failure. Both metrics are
  still always measured and reported together — see
  [`sim/README.md`](../sim/README.md)'s "Quiescent current (Iq) check" for
  why the `.op` figure is **not** the quantity Row 4 names (a relaxation
  oscillator has no stable DC operating point, so that solve pins the
  charge-complete comparator `XCMPH` at its own output inverter's trip
  point, holding that buffer and the SR-latch NOR gate it drives in full
  crowbar conduction) and `sim/iq/run-iq-sweep.sh` for the across-codes,
  across-sizings sweep.

## Topology

Relaxation oscillator per
[`spec/decision-records/0001`](../spec/decision-records/0001-relaxation-oscillator-topology.md):
an RC timing element gated by threshold comparators, with a supply- and
temperature-aware bias generator, and digital trim implemented as a
switched-resistor bank directly setting the RC time constant.

`rcosc_top.sch` composes:

- **`XTRIM` (`rcosc_trim_bank`)** charges `C_TIMING` continuously from
  `VDD` through the trimmed resistance (the RC element).
- **`CTIMING`** (`cap_mim_1f0fF`, 200 fF, unchanged by issue #16) is the
  timing capacitor, at node `vc`.
- **`XCMPH`** compares `vc` against `vh` (2/3 · VDD) — fires when the
  charge phase completes.
- **`XCMPL`** compares `vl` (1/3 · VDD) against `vc` — fires when the
  discharge phase completes.
- An inline **NOR-NOR SR latch** (8 transistors): `S = cmph_out` sets the
  latch to the discharge state, `R = cmpl_out` resets it back to charge.
  The latch state **is** the free-running clock output (`clk`).
- **`MDISCH`** (`nfet_03v3`, wide W) shorts `vc` to `vss` while the latch
  is in the discharge state, resetting the timing node for the next charge
  cycle.
- **`XBIAS` (`rcosc_bias`)** generates the two threshold references and the
  comparator tail-current bias (see "Bias generator" below).

This is a single-resistor-charge / switch-discharge ("sawtooth") relaxation
oscillator — a standard, well-precedented variant of the RC-relaxation
family DR-0001 selected (not symmetric charge/discharge; duty cycle is not
a row in the ratified target spec, see
[`spec/decision-records/0002`](../spec/decision-records/0002-target-spec-ratification.md)/[0003](../spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md)).

## Bias generator

`rcosc_bias.sch`: three equal `ppolyf_u_1k` resistors from `VDD` to `VSS`
divide the supply into `vh = 2/3 · VDD` and `vl = 1/3 · VDD` — **ratiometric**
to the supply (DR-0001's "simpler ratiometric scheme" option, explicitly
left open by that record rather than a bandgap-style reference). The current
reference that both comparator instances in `rcosc_top.sch` mirror into
their tail currents was, through issue #24, a fourth same-flavor resistor
(`RBIAS`) plus a diode-connected `nfet_03v3` (`ibias ≈ (VDD − V_GS)/R`); as
of issue #39 it is the self-biased supply-independent core described in the
issue #39 paragraph below — the exported `ibias` net is still a gate-voltage
net that `MTAIL` mirrors 8:1, so the comparator side is unchanged.

**`RBIAS` re-sized issue #16**: `L = 200 µm → 25 µm` (~8× higher tail
current). This raises comparator bandwidth/slew and so reduces
comparator propagation delay — one of the two root-cause mechanisms this
issue's "Trim bank sizing" section identifies for the pre-#16 frequency
shortfall. The threshold-divider resistors (`RBA`/`RBB`/`RBC`) are
unchanged: only the current-reference leg is re-sized. **This raised the
block's quiescent current above the ratified `< 500 µA` target** —
measured at 914.99 µA by issue #20, see
[DR-0007](../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md).

**Bias re-balanced issue #22** (current sizing), to close that Iq gap
without giving back issue #16's frequency fix. `RBIAS` and the comparator
tail-mirror ratio are re-derived **together**, from a simulated 2-D
`(RBIAS L) × (MTAIL W)` grid at the reference corner — not from a
hand-estimated closed form:

| device | file | issue #16 | **now** |
|---|---|---|---|
| `RBIAS` | `rcosc_bias.sch` | `W = 2 µm`, `L = 25 µm` | `W = 2 µm`, **`L = 1000 µm`** |
| `MBIASD` (mirror reference) | `rcosc_bias.sch` | `W = 2 µm`, `L = 1 µm`, `nf = 1` | unchanged |
| `MTAIL` (per comparator) | `rcosc_comparator.sch` | `W = 4 µm`, `nf = 1` (2:1) | **`W = 16 µm`, `nf = 8`** (8:1) |

Why both knobs and not just `RBIAS`: the bias budget is
`ibias × (1 + 2M)` — one reference branch plus two comparator tails at `M`
times `ibias` each — so at any fixed total supply current, a larger mirror
ratio `M` puts a larger share of that total into comparator tail current
(where it buys the bandwidth issue #16 was after) instead of into the
reference leg (where it buys nothing). `RBIAS` alone, at matched Iq,
reaches only 50.85 MHz maximum against this point's 51.94 MHz. The gain
from raising `M` saturates at `M ≈ 8`: `M = 16` and `M = 32` were both
simulated and land within 0.2% at equal Iq, so 8:1 is the knee rather than
an arbitrary pick. `MTAIL`'s `W = 16 µm` is drawn as `nf = 8` fingers of
2 µm — eight copies of `MBIASD`'s own unit geometry, the matched form for
a ratioed mirror, simulated equivalent to a single wide finger within 0.6%.

**Result** (reference corner `tt`/27 °C/3.3 V, `sim/iq/results/20260906T062311Z/`):
`.op` Iq **914.99 µA → 467.18 µA** and running Iq **502.31 µA → 157.27 µA**
at code `0x80` — DR-0003 Row 4's `< 500 µA` target is now **met on both
metrics at every simulated code** (worst case 467.18 µA `.op` / 218.54 µA
running, both at `0xFF`). The ratified 500 µA figure is unchanged; nothing
was relaxed. The price paid is trim range — see "Full PVT-corner
re-verification" below and
[DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md).

**`RBIAS` re-derived again, issue #24** (current sizing), against the
**running** Iq metric specifically — DR-0008 itself found that `.op` is a
DC-equilibrium artifact, not the quantity DR-0003 Row 4 names, but sized
against `.op` anyway (the stricter reading) rather than change the metric
basis inside the record that first identified the discrepancy, and
deferred that change to this issue:

| device | file | DR-0008 (post-#22) | **now (post-#24)** |
|---|---|---|---|
| `RBIAS` | `rcosc_bias.sch` | `W = 2 µm`, `L = 1000 µm` | `W = 2 µm`, **`L = 210 µm`** |
| `MTAIL` (per comparator) | `rcosc_comparator.sch` | `W = 16 µm`, `nf = 8` (8:1) | **unchanged** |

The mirror ratio was re-checked, not just left stale: `M = 4:1` and
`M = 16:1` were each swept to their own `iq_run(0xFF) = 500 µA` boundary,
and both land within about a percentage point of `M = 8:1`'s recovered
trim range at matched margin — DR-0008's saturation finding at `M ≈ 8`
holds under the running metric too, so `RBIAS` is the only device resized.
A 1-D grid over `RBIAS L` at the unchanged `M = 8:1` finds the
`iq_run(0xFF) = 500 µA` boundary between `L = 185 µm` (502.61 µA, exceeds)
and `L = 190 µm` (495.58 µA, met, <1% margin); `L = 210 µm` is chosen with
a DR-0008-comparable ~6.3% margin (468.61 µA at worst code `0xFF`).

**Result** (reference corner, `sim/iq/results/20260907T090639Z/`): running
Iq **218.54 µA → 468.61 µA at worst code `0xFF`** — still **met** against
the ratified `< 500 µA` (running) target, DR-0003 Row 4's actual basis as
of [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md).
This deliberately runs `.op` Iq back up (467.18 → 754.90 µA at code
`0x80`) — expected, not a regression, since `.op` is no longer the
verdict basis (DR-0008/DR-0009) and was never the quantity being
targeted. Realized reference-corner trim range recovers from DR-0008's
±32.42% to **±35.50%** — about 54% of the range DR-0008 traded away for
Iq, still short of DR-0006's pre-#22 ±38.16% and of the ratified ±40%.
See DR-0009 for the full grid, the PVT-corner campaign at this sizing, and
a real, not-hidden regression it also found: the post-trim,
full-temperature, per-corner-code residual widens to −19.41%/+27.85%
(vs. DR-0008's −17.38%/+13.46%), traced to the `fs` process corner's own
calibration code landing on its untrimmed reference code at this sizing.

**Current reference re-architected issue #39** (the DR-0006-sanctioned
follow-up targeting the comparator/bias path's own supply and temperature
sensitivity — never budgeted by DR-0003's timing-TCR-only post-trim
derivation). The pre-#39 reference was `RBIAS` from `VDD` into a
diode-connected `MBIASD`, i.e. `ibias ≈ (VDD − V_GS)/R`: instrumented at
**+24.5% supply sensitivity over 3.0→3.6 V** (and ~+900 ppm/K of its own)
before any change, and the comparator path pays its delay ≈3× into the charge
phase (slope-to-threshold conversion at `vh`, issue #16's writeup above), so
that current-reference slope appeared directly in the free-running frequency
(post-trim supply rows `ss` +20.77% / `tt` +8.52% at per-corner calibrated
codes, DR-0009's campaign). The `RBIAS`/`MBIASD` leg is replaced by a
**self-biased (supply-independent) beta-multiplier core**: `P1` (pfet diode,
branch 2) and `P2` (pfet mirror, branch 1), `N1` (`W=2u L=1u`, diode — its
gate node **is** the exported `ibias` net, so the comparator's `MTAIL`
(`W=16u nf=8`) still mirrors it 8:1 exactly as it mirrored `MBIASD`), and
`N2` (`W=16u nf=8`, gate on `ibias`, source degenerated by
`RZ = ppolyf_u_1k W=2u L=32u`), with `SEED` (`nfet_03v3 W=2u L=20u`, gate at
`vl`, pull-down on the PMOS gate bus) making the loop's zero-current state
non-stationary. `VDD` appears nowhere in the current-setting constraint.
The threshold divider (`RBA`/`RBB`/`RBC`) and the vh/vl ratiometric behavior
are unchanged, the trim bank is untouched (per this issue's guardrail), and
**no compensation of the timing resistor's TCR is attempted — DR-0004
stands** (the core makes the current reference supply-independent, the
nominal assumption DR-0003's post-trim arithmetic was derived under; it does
not shape the free-running tempco below the ratified +8%/−9% figure).

Sizing was gridded, not closed-form-derived (the reference point first, then
a structural spot grid over the campaign's own deck at 16 worst cells):
`RZ L=32µ` rests at `f(0x80) ≈ 38.2 MHz`, `iq_run(0x80) ≈ 265 µA` (worst-code
projection ~340 µA, inside DR-0003 Row 4), with the per-corner ΔT spread
collapsed from +856…+1923 ppm/K (pre-revision, calibrated codes) to
≈ +800…+1100 ppm/K at mid-scale — the device-driven excess is gone and what
remains is the pure-TCR-class behavior the post-trim rows budget for.

**A second, distinct defect was isolated by the same instrumentation and is
deliberately *not* fixed here** (one issue, one mechanism — it is filed as
its own follow-up issue): the trim-bank pass switches `SW0..SW7` lose
effectiveness across the top of the charge ramp. Each switch's effective
gate drive is `t_i − v(c_{i+1})`, and as the timing node rises toward `vh`
that drive collapses into the body-effected threshold region — so the
segments stop being removed exactly where the RC charge time concentrates.
The realized trim curve shows the symptom: mid-block codes are near-dead
(`0x00 → 0x10`: +0.04%) while MSB-boundary codes jump (`0x70 → 0x80`:
+33%), and high-crawl codes carry a "phantom" series resistance that is
itself PVT-dependent (`ss`@`0xEF` +20.0% vs `ss`@`0x80` +11.0% supply
sensitivity, pre-revision structural grid). This mechanism caps the
realizable trim range from *below* the comparator-delay compression alone
would predict, contaminates per-code steps, and contributes its own supply
and temperature sensitivity at the codes the per-corner calibration lands
on. It is a *switch*-design flaw, not a resistor-value question — the issue
#39 guardrail ("not `rcosc_trim_bank.sch`'s R values again") is respected:
the resistor values stand; the switches need their own sizing pass, with
its own campaign and record — filed as issue [#43](https://github.com/2AMLogic/gf180-rcosc/issues/43).

Using the **same poly-resistor flavor** (`ppolyf_u_1k`, gf180mcu §6.1A) for
the threshold divider as for the timing/trim resistor is a deliberate,
qualitative TC-tracking choice — process and temperature shifts move both
the RC time constant and the comparator thresholds together, to first
order. **This is not a quantified compensation claim.**

Whether this design adds *active* TC compensation on top of that qualitative
choice, or relies entirely on runtime discipline, is resolved by
[`spec/decision-records/0004`](../spec/decision-records/0004-no-active-tc-compensation-runtime-discipline.md):
**no active compensation is added.** DR-0004 found no PDK-published resistor,
diffusion, or capacitor flavor with a positive TCR at a sheet resistance
usable for this design's several-tens-of-kΩ timing resistor (gf180mcu's only
characterized positive-TCR devices are interconnect — metal, contacts, and
vias, §5.7 — which would need on the order of 10⁵–10⁶ squares to cancel the
timing resistor's TCR, wholly impractical for this die), and judged a
closed-loop or bandgap-referenced compensation circuit out of scope for a
canary block verifying the PDK/tooling flow rather than competing on TC spec
with a production part. `design/rcosc_bias.sch` and
`design/rcosc_trim_bank.sch` are therefore **unchanged** by DR-0004.
DR-0003's +8%/−9% full-temperature-range figure stands as the free-running
spec; closing the remaining gap to USB full-speed compliance is entirely the
job of the ratified spec's reserved "Runtime-disciplined" stage (SOF-based,
still undesigned) — see DR-0004 for the full alternatives analysis.

## Device selection

Per DR-0003 §5.1/§6.1/§6.2, confirmed against the installed PDK via
`klt pdk find --pdk gf180mcuC` and the gf180mcuC xschem symbol library
(`~/.volare/gf180mcuC/libs.tech/xschem/symbols/`):

| Role | Device | Flavor | Why |
|---|---|---|---|
| Timing / trim resistor | `ppolyf_u_1k` | 1000 Ω/sq high-sheet SAB poly (gf180mcu §6.1A) | The flavor DR-0003 sources its ±20% process-spread and −1200 ppm/K worst-case TCR figures from — the only standard-or-SAB poly flavor with **published TCR data** (§5.1's plain poly has none; §6.1C's 3000 Ω/sq flavor also has none) |
| Threshold-divider / bias resistor | `ppolyf_u_1k` | same as above | Deliberately matched to the timing resistor for qualitative TC tracking (see "Bias generator") |
| Timing capacitor | `cap_mim_1f0fF` | 1.0 fF/µm², ±10% spread (gf180mcu §6.2(b)) | **DR-0003's explicit recommendation**: the 1.5 fF/µm² flavor (±15.33% spread) leaves only ~1.6 points of pull-up trim margin against the ratified ±40% range, vs. ~8 points with the 1.0/2.0 fF/µm² flavor — DR-0003 calls switching flavor "the cheapest available fix" and says it "should be evaluated first." **This issue takes that fix**: 1.5 fF/µm² (`cap_mim_1f5fF`) is not used anywhere in this design, so no superseding decision record is needed. |
| Comparator / latch / discharge switch transistors | `nfet_03v3` / `pfet_03v3` | 3.3 V core devices | Matches the ratified 3.3 V-core supply target (DR-0002/DR-0003) |

## Trim bank sizing

`rcosc_trim_bank.sch`: a fixed floor resistor (`RFIX`) in series with eight
binary-weighted segments (`R0..R7`, weights `1,2,4,...,128 × R_unit`), each
shunted by a switched-resistor pass element gated by its trim bit
(`t0..t7`, `t7` = MSB). Bit = 1 shorts (removes) that segment's resistance,
so `R(code)` is **monotonically decreasing** in code in the ideal-switch
model — more bits set can only remove series resistance, never add it. Both
extreme codes are directly representable: code `0x00` (all switches open)
is the full series chain (`R_max`); code `0xFF` (all switches closed)
shorts every variable segment down to `RFIX` alone (`R_min`) — verified at
the schematic level (one shunt per bit) and exercised functionally by the
`t7`-only smoke-test code (`0x80`) above.

**Pass-switch restructure (issue #43, [DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md)).**
Pre-#43 each segment was shunted by a single `nfet_03v3` pass switch
(gate = `t_i`, bulk = `vss`), whose effective drive `t_i − v(low node)`
collapsed into the body-effected subthreshold region as the timing node
rose toward `vh`: mid-block trim steps dead (`0x00→0x10` measured +0.03%
against a ~+5% ideal block step) and a PVT-dependent phantom series
resistance on every ON code. Each shunt is now a **transmission gate** —
`SW<i>` (nfet, gate = `t_i`) paralleled with `PW<i>` (pfet, gate = `tb_i`)
— with `tb_i` generated by a per-bit CMOS inverter (2u/4u, `L=0.5u`) on a
new `vdd` pin, so the cell-boundary trim semantics are unchanged. Pass
devices run at `L=0.28u` (the DRM 7.7 `PL.2` gate minimum for the 3.3V
column, and the model's own default `l`) with per-position widths
24/16/12/8/6/5/4/3 µm: the timing capacitor is only ~270 fF, so a shunt's
own on-channel capacitance loads it hardest at the m-adjacent position and
least at the ladder top, exactly opposite to where the segments need the
lowest on-resistance. The `RFIX`/`R0..R7` values are untouched (issue #43's
explicit guardrail). Known characterized limit: the frozen R map leaves
~1 LSB-R (~374 Ω) of ideal-switch monotonicity margin per `0xkF→0x(k+1)0`
block-boundary code pair, so those specific adjacent pairs dip a few
percent locally with real switches (measured and reported by the campaign
driver; see DR-0014 for the numbers and the sizing-space argument that no
endpoints-preserving width fixes them).

### Root cause of the pre-#16 frequency/trim-range shortfall (issue #16)

Issue #12's PVT campaign ([DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md))
found the pre-#16 schematic realized only 17.7–21.4 MHz (reference corner)
against a 48.000 MHz target — a ~2.3× shortfall — and a compressed
trim-bank endpoint ratio (1.2058 realized vs. 2.3333 intended). This issue
root-caused that gap by instrumenting the transient directly (measuring
node-crossing timestamps on `vc`, `cmph_out`, `cmpl_out`, and `clk`, not
just the oscillation period) at the reference corner, code `0x80`:

1. **The discharge phase does not stop at `V_L`.** `MDISCH` is a strong,
   low-`R_on` switch (`nfet_03v3`, `W=20µm`): its own discharge time
   constant (`R_on · C_TIMING`, tens of picoseconds) is far *faster* than
   `XCMPL`'s propagation delay (measured ≈2.4 ns at the pre-#16 bias
   point). By the time `cmpl_out` registers `vc` crossing `V_L` and the
   latch turns `MDISCH` back off, `vc` has already been pulled to ≈0 V —
   well past the intended `V_L = 1/3·VDD` stopping point. This means the
   *next* charge phase must traverse the **full `0 V → V_H` range**, not
   the `V_L → V_H` partial swing the `ln 3` hand estimate's charge-time
   term implicitly assumes is being avoided by design.
2. **Comparator + latch propagation delay is a fixed-ish per-cycle
   overhead the closed form does not budget**, and it is large relative
   to the target period: at the pre-#16 bias point, `XCMPH`'s measured
   delay (vc crossing `V_H` to `cmph_out` crossing mid-rail) was ≈4.1 ns
   and the latch's own set/reset delay another ≈0.3–0.5 ns per edge —
   several nanoseconds added to *every* half-cycle against a 20.8 ns
   target period at 48.000 MHz. Because this overhead is roughly
   independent of the trim resistance while the RC charge term scales
   with it, the overhead dominates the period at every code, compressing
   the realized frequency range and the trim-bank ratio well below what
   the `R_max/R_min = 2.3333` sizing intended.
3. **Increasing bias current alone cannot restore the intended `V_L`-bounded
   discharge floor** — confirmed by direct simulation: even at the ~8×
   higher comparator tail current this issue ultimately adopts (see
   "Re-sizing methodology" below), `vc` still discharges to ≈0 V every cycle,
   because `MDISCH`'s own RC time constant is orders of magnitude faster
   than any propagation delay reachable at a practical bias current. The
   correct fix is therefore **not** "make the comparator instantaneous"
   but to re-derive the trim-bank's R sizing treating the realized
   sawtooth as a `0 V → V_H` charge (not `V_L → V_H`) plus whatever
   residual delay simulation shows, using the *simulated* charge-time
   relationship rather than the `ln 3` closed form.

### Re-sizing methodology and result (issue #16)

Two changes, both simulation-derived rather than formula-derived:

- **`rcosc_bias.sch`'s `RBIAS`: `L = 200 µm → 25 µm`** (~8× higher
  comparator tail current — see "Bias generator" above). This does not
  restore the `V_L`-bounded discharge (point 3 above), but it does reduce
  the fixed comparator+latch delay overhead (point 2), which matters at
  the fast (small-R) end of the trim range where that overhead would
  otherwise be a large fraction of the period.
- **`rcosc_trim_bank.sch`'s `RFIX`/`R0..R7`: re-derived from simulated
  transient data**, not `f ≈ 1/(R·C·ln 3)`. Method: hold `C_TIMING`
  and the new `RBIAS` fixed, sweep `RFIX` alone (all other trim bits at
  `0xFF`, i.e. shorted) across several decades, and directly measure the
  realized free-running frequency at the reference corner (`tt`, 27 °C,
  3.3 V) for each swept value using the same skip-5-startup-edges /
  average-20-cycles methodology `sim/pvt/pvt_sweep.py` uses. Four real
  (not extrapolated-only) data points were measured this way (`R`, steady-state `f`):
  `8.6 kΩ → 83.5 MHz`, `32.4 kΩ → 65.5 MHz`, `56.4 kΩ → 50.1 MHz`,
  `90.0 kΩ → 33.6 MHz` — a quadratic fit through these (period vs. `R`,
  residuals < 0.1 ns) was then solved for the `R` values whose *simulated*
  (not `ln 3`-predicted) frequency lands near the ratified endpoints,
  rounding to:

```
C_TIMING = 200 fF (cap_mim_1f0fF, W=20u L=10u -> area = 200 um^2, UNCHANGED by issue #16)

R_min (code 0xFF) = RFIX                = 8.599 kOhm  (simulated f = 83.5 MHz, real data point)
R_max (code 0x00) = RFIX + 255*R_unit   = 104.0 kOhm  (simulated f ~= 29-34 MHz range, quadratic-fit target;
                                                         nearest real data point: 90.0 kOhm -> 33.6 MHz)

R_unit = (R_max - R_min) / 255 = 374.12 Ohm
R_i = R_unit * 2^i  for i = 0..7  (374.12, 748.24, ..., 47887.56 Ohm)
```

All resistors use `ppolyf_u_1k` (1000 Ω/sq typ, gf180mcu §6.1A) at
`W = 2 µm`; segment lengths are solved from `R = Rsheet · L/W`:
`RFIX: L = 17.198 µm`, `R0..R7: L = 0.7482, 1.4965, 2.9930, 5.9859,
11.9719, 23.9438, 47.8876, 95.7751 µm`.

**What this sizing does and does not claim:**

- **`R_min` (code `0xFF`) is a directly-measured data point**, not an
  extrapolation: `RFIX = 8.599 kΩ` was one of the four real transient
  measurements above, giving 83.5 MHz — comfortably above the 67.2 MHz
  ratified upper trim-range endpoint.
- **`R_max` (code `0x00`) is a modest extrapolation** (~15% beyond the
  farthest real data point, 90.0 kΩ → 33.6 MHz) from a well-conditioned
  quadratic fit (max residual < 0.1 ns across four real points spanning
  8.6–90.0 kΩ) targeting the ratified 28.8 MHz lower endpoint. This is a
  materially smaller extrapolation than an earlier iteration of this same
  sizing attempt made (which assumed the pre-#16-schematic's naive `ln 3`-style
  R-vs-frequency curvature and was off by ~74% when checked against real
  simulation) — flagged explicitly because trusting curve-fit extrapolation
  *without* real data points bracketing the target was the specific mistake
  this issue's own process caught and corrected.
- **This sizing is not claimed to hit the ratified endpoints exactly** —
  see "Full PVT-corner re-verification" below for what the campaign
  against this sizing actually shows row-by-row against the ratified
  target-spec table. Re-deriving from simulated (not `ln 3`) behavior is
  what issue #16 commits to; whether the result meets every ratified row
  is reported there, not asserted here.
- **Code ↔ frequency linearity within the range is still NOT claimed or
  verified** — same caveat as the pre-#16 sizing; DR-0002/0003's "linear
  mapping" language describes trim word design intent, not a per-code DNL
  guarantee.
- Several LSB-side segment lengths (`R0`: 0.7482 µm, `R1`: 1.4965 µm) were
  flagged here as possibly short enough to fail this PDK's resistor
  minimum-length DRC rule, not checked at the time (DRC was out of scope
  for the issue that wrote this note). **Checked and resolved by issue
  #13** (layout increment): `klt`'s curated gf180mcu DRC deck has no
  resistor minimum-*length* rule at all (only a minimum *width* rule every
  segment's `r_width=2u` clears trivially) — `R0` is DRC-clean as drawn,
  unchanged. `R1` hit an unrelated, half-nanometre-grid-tie generator bug
  at its exact length (filed as
  [klayout-tools#1551](https://github.com/2AMLogic/klayout-tools/issues/1551)),
  worked around with a 0.1 nm / <0.007% layout-only nudge (not a resistor-
  ratio or schematic change) — see `layout/README.md`'s "Known `klt` gaps"
  and "Scope and follow-up" sections for the full evidence.
- The comparator's offset budget, the discharge switch's on-resistance
  (beyond the qualitative root-cause role identified above), and the
  trim-DAC element mismatch/INL row DR-0002/0003 carries as a flagged
  assumption are **not** sized or verified against this specific
  transistor-level implementation here.
- Increasing `RBIAS`'s current raises this block's quiescent current draw
  (Row 4 of the ratified spec, `< 500 µA`) — **re-verified by issue #20**:
  the total `vdd` current at the reference corner, code `0x80`, is
  **914.99 µA, 1.83x the ratified target**. See
  [DR-0007](../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md)
  and `sim/iq/results/20260906T032927Z/README.md` for the full measurement,
  an independent hand-estimate sanity check, and disposition — the ratified
  spec is unchanged; issue #22 tracks re-balancing the bias generator's
  sizing.

### Full PVT-corner re-verification (issues #16 / #18)

The full process×temperature×supply campaign methodology issue #12 used
(`sim/pvt/run-pvt-sweep.sh`) has been re-run against this re-sized
schematic (git sha `af1cf30c`, unchanged by this campaign), recorded as a
new, dated evidence directory:
`sim/pvt/results/20260906T030219Z/{results.csv,manifest.json,summary.md}`,
raw logs under `sim/pvt/corners/20260906T030219Z/` — append-only, the
issue #12 evidence directory (`20260905T211140Z`) is untouched. 278
unique operating points, 0 failed measurements, 15.0 minutes wall clock
at 14 parallel jobs (the shared-host contention that blocked this
campaign within issue #16's own session, per the prior revision of this
section, had cleared by the time issue #18 ran it).

Disposition, in full, is [DR-0006](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md).
Summary:

| Spec row | Ratified | Simulated | Verdict |
|---|---|---|---|
| Free-running, untrimmed, process spread | ±35% (−27.7%/+47.6% exact) | −28.73% / +46.53% | met |
| Output frequency | 48.000 MHz | reachable, 29.5–65.9 MHz range at the reference corner | met |
| Trim range | ±40% (28.8–67.2 MHz) | ±38.16% (29.5072–65.9204 MHz) | **not met** (close: 96% of the intended endpoint ratio) |
| Post-trim, at calibration point | ±1.1% | −34.83%/+53.97% (global code) or −16.28%/+15.24% (per-corner code) | **exceeds**, both methodologies |
| Post-trim, full temperature range | +8%/−9% | −42.43%/+62.77% (global code) or −25.74%/+21.18% (per-corner code) | **exceeds**, both methodologies |

The trim bank is no longer saturated against the ratified target at
almost every corner (unlike DR-0005's pre-resize finding, where every
corner saturated at code `0xFF`), so the two "exceeds" rows above are
**not** a saturation artifact this time: DR-0006 finds a comparable
per-corner-calibrated residual to DR-0005's own (pre-resize, partially
saturation-limited) figure, meaning the comparator/bias path's own
temperature and supply sensitivity — not the timing resistor's TCR
DR-0003's post-trim-accuracy derivation was based on — is the dominant
remaining residual. See DR-0006's "Consequences" for the follow-up
direction (comparator/bias-path PVT sensitivity, not further timing R/C
retuning).

The top-code non-monotonicity DR-0005 flagged (`0xF0` → `0xFF`, pre-resize)
**does not reproduce** at the resized operating point — the realized trim
curve is monotonically increasing end to end (see DR-0006).

### Full PVT-corner re-verification (issue #22 bias re-balance)

The same campaign was re-run against the issue #22 re-balanced sizing
(`RBIAS L = 1000 µm`, 8:1 tail mirror) and recorded as
`sim/pvt/results/20260906T060104Z/`, raw logs under
`sim/pvt/corners/20260906T060104Z/` — append-only; both prior campaigns are
untouched. 271 unique operating points, 0 failed measurements, 11.9 minutes
wall clock at 14 parallel jobs.

Disposition, in full, is [DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md).
Against DR-0006's post-#16 campaign:

| Spec row | Ratified | DR-0006 (post-#16) | **now** (post-#22) | Verdict change |
|---|---|---|---|---|
| Quiescent current | `< 500 µA` (running) | 914.99 µA `.op` | **467.18 µA `.op` / 157.27 µA running** | **exceeds → met** |
| Output frequency | 48.000 MHz | max reachable 65.9204 MHz | max reachable 51.9415 MHz | none — met both |
| Trim range | ±40% (28.8–67.2 MHz) | ±38.16% (29.5072–65.9204 MHz) | ±32.42% (26.5059–51.9415 MHz) | none — **not met** both, margin worse |
| Trim step | 0.314 %/code | 0.4839 %/code | 0.3763 %/code | none — met both |
| Free-running untrimmed process spread | ±35% | −25.60% / +38.71% | −25.46% / +38.54% | none — within both |
| Post-trim, at calibration point | ±1.1% | −11.38% / +10.56% (per-corner code) | −10.18% / +10.30% (per-corner code) | none — **exceeds** both |
| Post-trim, full temperature range | +8% / −9% | −18.00% / +12.91% (per-corner code) | −17.38% / +13.46% (per-corner code) | none — **exceeds** both |

**Row 4 (Iq) is the only verdict that moves, and the trim-range margin is
the price paid for it**: still not met, as it already was, but the gap to
±40% widens from 1.84 to 7.58 percentage points. The ratified 48.000 MHz
output frequency stays reachable with 8.2% headroom, and the design remains
far from DR-0005's pre-#16 shortfall (31.18 MHz maximum reachable at *any*
corner or code) — but this is a real regression against DR-0006's
trim-range finding, recorded rather than buried. Trim-curve monotonicity is
not degraded: the `0xE0` → `0xF0` → `0xFF` region stays monotonic
(48.5043 → 50.7721 → 51.9415 MHz) and the small LSB-region non-monotonicity
is marginally smaller than DR-0006's (−0.09% vs. −0.11% at `0x10`).

Issue #24 re-derives the sizing against the **running** Iq metric — which
had 44% margin at the worst code at this point, where the `.op` metric
this sizing was constrained by had only 6.6% — and determines how much of
the lost trim range is recoverable while still meeting Row 4 as worded;
see the next section for that campaign.

### Full PVT-corner re-verification (issue #24 running-metric re-derivation)

The same campaign was re-run again against the issue #24 sizing
(`RBIAS L = 210 µm`, 8:1 tail mirror unchanged) and recorded as
`sim/pvt/results/20260907T090653Z/`, raw logs under
`sim/pvt/corners/20260907T090653Z/` — append-only; all three prior
campaigns are untouched. 277 unique operating points, 206 recorded rows,
0 failed measurements, 4.0 minutes wall clock at 8 parallel jobs.

Disposition, in full, is [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md).
Against DR-0006 (post-#16) and DR-0008 (post-#22):

| Spec row | Ratified | DR-0006 (post-#16) | DR-0008 (post-#22) | **now (post-#24)** |
|---|---|---|---|---|
| Quiescent current | `< 500 µA` (running) | 914.99 µA `.op` (only metric then measured) | 467.18 µA `.op` / 157.27 µA running — met both | 754.90 µA `.op` (not the verdict basis) / **468.61 µA running — met** |
| Output frequency | 48.000 MHz | max reachable 65.9204 MHz | max reachable 51.9415 MHz | max reachable **58.9870 MHz** — met |
| Trim range | ±40% (28.8–67.2 MHz) | ±38.16% | ±32.42% | **±35.50%** (28.0769–58.9870 MHz) — not met, narrower gap than DR-0008 |
| Trim step | 0.314 %/code | 0.4839 %/code | 0.3763 %/code | **0.4317 %/code** — met |
| Free-running untrimmed process spread | ±35% | −25.60% / +38.71% | −25.46% / +38.54% | **−26.34% / +42.68%** — within |
| Post-trim, at calibration point (per-corner code) | ±1.1% | −11.38% / +10.56% | −10.18% / +10.30% | **−11.50% / +13.19%** — exceeds |
| Post-trim, full temperature range (per-corner code) | +8% / −9% | −18.00% / +12.91% | −17.38% / +13.46% | **−19.41% / +27.85%** — exceeds, worse than both priors |

**Row 4's verdict basis is now `iq_run`** (DR-0009), and Row 4 is met on
that basis at every simulated code — the elevated `.op` figure (754.90 µA)
is expected, not a regression, since `.op` was never the quantity being
targeted (DR-0008 Finding 1). **Trim range recovers about 54% of what
DR-0008 traded away** (±32.42% → ±35.50%; DR-0006's pre-#22 ±38.16% and
the ratified ±40% both remain out of reach). **A real, not-hidden
regression**: the post-trim, full-temperature, per-corner-code residual
widens to −19.41%/+27.85%, worse than both DR-0006 and DR-0008 — traced to
the `fs` process corner's own per-corner calibration code coinciding with
its untrimmed reference code at this sizing, so its post-trim figure is
effectively its (comparatively high, +1923 ppm/K) untrimmed temperature
drift. The verdict ("exceeds") does not change — every post-trim row has
been "exceeds" since DR-0005 — but the margin does, and DR-0009 records it
rather than omitting it. The coarse (`0x10`-step) trim curve shows the
same small LSB-region non-monotonicity dips prior campaigns flagged
(e.g. `0x10`→`0x20`: −0.14%), not a new or worsened pattern.

### Full PVT-corner re-verification (issue #39 comparator/bias-path revision)

The same campaign was re-run against the issue #39 self-biased
current-reference core (`RZ = 32 µm`, nfet SEED, sizing frozen at git sha
`1ac4434`) and recorded as `sim/pvt/results/20260921T075822Z/`, raw logs under
`sim/pvt/corners/20260921T075822Z/` — append-only; every prior campaign is
untouched. 276 unique operating points, 0 failed measurements.

Disposition, in full, is [DR-0012](../spec/decision-records/0012-comparator-bias-path-pvt-revision.md).
Against DR-0009 (post-#24):

| Spec row | Ratified | DR-0009 (post-#24) | **now (post-#39)** | Verdict change |
|---|---|---|---|---|
| Post-trim, at calibration point (per-corner code) | ±1.1% | −11.50% / +13.19% | **−11.65% / +8.32%** | none — **exceeds** both; upper excess improves by ~4.9 pt |
| Post-trim, full temperature range (per-corner code) | +8% / −9% | −19.41% / +27.85% | **−20.15% / +13.03%** | none — **exceeds** both; upper excess improves by ~14.8 pt |
| ΔT coefficient spread (per-corner calibrated codes) | (budget basis ≈ +1177 ppm/K) | +856 … +1923 ppm/K | **+774 … +1003 ppm/K** | — the device-driven excess DR-0006 named is eliminated |
| Supply sensitivity, slow-corner calibrated codes (`ss`/`sf`/`rc_s`) | ~0 (ratiometric ideal) | +20.77% / +12.58% / +14.13% | +20.05% / +12.02% / +13.70% | unchanged — dominated by the trim-bank phantom-resistance path (follow-up issue) |
| Output frequency | 48.000 MHz | max reachable 58.9870 MHz | max reachable **56.7060 MHz** | none — met both |
| Trim range | ±40% (28.8–67.2 MHz) | ±35.50% | **±34.42%** (27.6659–56.7060 MHz, ratio 2.0497) | **not met** — small recorded regression, −1.08 pt |
| Trim step | 0.314 %/code | 0.4317 %/code | **0.4116 %/code** | none — met both |
| Free-running untrimmed process spread | ±35% | −26.34% / +42.68% | **−26.11% / +39.90%** | none — within both |

The two post-trim rows remain **not met** — but the dominant unbudgeted
mechanism DR-0006 isolated (the comparator/bias path's own temperature
sensitivity, visible as the ΔT spread across identical-passive corners) is
eliminated, and the remaining per-cell excess is now dominated by the
trim-bank pass-switch phantom-resistance path isolated by the same
instrumentation and filed as its own follow-up issue, together with a
comparator/latch delay residue. The quiescent-current row is re-verified
by the Iq PVT factorial (`sim/iq/results/`, DR-0011's methodology) — see
DR-0012 for the disposition. The trim curve's LSB-region non-monotonicity
dips persist (`0x00`-block cells within ±0.09%, and the same
`0x10`-block dip pattern as prior campaigns), the same small-magnitude
pattern as before, now with a mechanistic explanation (delay/phantom
interplay at the low-crawl codes) rather than a new instance of the pre-#16
anomaly.

### Full PVT-corner re-verification (issue #43 trim-bank pass-switch revision)

The campaign was re-run against the transmission-gate trim shunts
(sizing frozen at git sha `bfeb95d`, committed driver) and recorded as
`sim/pvt/results/20260921T173529Z/`, raw logs under
`sim/pvt/corners/20260921T173529Z/` — append-only; every prior campaign is
untouched. 361 unique operating points, 0 failed measurements. The Iq
PVT factorial was re-run in step (`sim/iq/results/20260921T181049Z/`,
252 points, 0 failed) because the restored fast-end frequency changes
the per-cycle timing-cap charge current at high codes. An interim
campaign from this same branch (`sim/pvt/results/20260921T164939Z/`,
pre-driver-fix) is kept append-only for the record trail — do not cite
it as final; its summary still carries the prose this issue's driver
update corrected.

Disposition, in full, is
[DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md).
Against DR-0012 (post-#39):

| Spec row | Ratified | DR-0012 (post-#39) | **now (post-#43)** | Verdict change |
|---|---|---|---|---|
| Post-trim, at calibration point (per-corner code, surrogate) | ±1.1% | −11.65% / +8.32% | **−7.14% / +4.62%** | none — still **exceeds**; both sides improve |
| Post-trim, full temperature range (per-corner code, surrogate) | +8% / −9% | −20.15% / +13.03% | **−14.53% / +7.00%** | upper side now **within** +8%; lower still **exceeds** −9% |
| Post-trim, per-corner code against the **ratified 48.000 MHz target** (pass new in #43) | ±1.1% resp. +8%/−9% | unmeasurable — every corner saturated below 48 MHz | **−8.13% / +5.79%**, resp. **−15.49% / +7.78%** | measurable for the first time |
| ΔT coefficient spread (per-corner calibrated codes) | (budget basis ≈ +1177 ppm/K) | +774 … +1003 ppm/K | **+559 … +756 ppm/K** | all corners now below the budgeted basis |
| Supply sensitivity, slow-corner calibrated codes (`ss`/`sf`/`rc_s`) | ~0 (ratiometric ideal) | +20.05% / +12.02% / +13.70% | **+11.76% / +7.73% / +6.09%** | roughly halved — the phantom share removed; the remainder is re-attributed to the comparator/latch delay residue by the campaign's own per-code rows (DR-0014) |
| Output frequency | 48.000 MHz | max reachable 56.7060 MHz | max reachable **84.9384 MHz**; **all seven corners reach 48.000 inner-range, none saturates** | met — stronger: trim-reachable on every corner for the first time |
| Trim range | ±40% (28.8–67.2 MHz) | ±34.42% | **±51.36% (27.2955–84.9384 MHz, ratio 3.1118)** | **met — first campaign since DR-0005** |
| Trim step | 0.314 %/code | 0.4116 %/code | **0.8282 %/code**; mid-block step `0x00→0x10` **+5.03%** (≈0.31 %/code) vs +0.03% pre-#43 | met — the previously-dead mid-block steps are live at ≈ their binary weights |
| Quiescent current (running, Row 4) | < 500 µA | `0x00`/`0x80` met everywhere (worst 459–498 µA); `0xC0`/`0xFF` exceed at ff/85 °C/3.6 V (541.85 / 614.87 µA) | `0x00` 460.06 **met**; `0x80` 498.76 **met** (1.24 µA margin); `0xC0` **550.20**; `0xFF` **724.42** `exceeds` | verdict classes unchanged; the fast-hot high-code values grow with the restored fast-end frequency |
| Free-running untrimmed process spread | ±35% | −26.11% / +39.90% | **−23.72% / +34.56%** | none — within both |

The trim-range row is met for the first time since DR-0005. The two
post-trim accuracy rows remain **not met**: the phantom-resistance share is
removed, the per-code supply-sensitivity row at `ss` no longer tracks the
switch mechanism (it now tracks the comparator/latch delay residue,
monotone in the code's period-share of the delay — `0x80` +8.34%,
`0x9D` +10.5%, `0xCF` +13.9%, `0xEF` +18.78% as in-chain trim mass falls),
and the block-boundary code pairs carry the characterized ~1-LSB-margin
local dips the campaign now samples explicitly. The block staircase stays
monotone at every sampled 16-code step at every corner. No ratified row is
relaxed, and no result is rounded up to "met".

## Non-goals

Per the issue #6 acceptance criteria that first wrote this section, and
CLAUDE.md's evidence discipline (updated by issue #12's PVT-corner
campaign against the pre-#16 schematic, [DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md),
by issues #16/#18's post-resize campaign,
[DR-0006](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md),
by issue #22's bias re-balance,
[DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md),
by issue #24's running-metric re-derivation,
[DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md),
and by issue #35's Iq PVT-corner factorial,
[DR-0011](../spec/decision-records/0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md) —
see the three "Full PVT-corner re-verification" sections above):

- ~~No DRC/LVS claim.~~ **Resolved by issues #13/#27.** The LSB trim
  segments' DRC risk flagged above is checked and clean, and the full
  `rcosc_top` hierarchy (bias generator, trim bank, comparator, top-level
  composition) has a DRC-clean, LVS-matched GDS — see
  [`layout/README.md`](../layout/README.md) for the sizing-to-geometry
  translation and evidence.
- **No offset/mismatch budget.** The comparator and trim-bank device
  sizing are first-pass placeholders; DR-0002/0003's flagged assumption
  rows (trim-DAC mismatch, comparator offset residual, supply drift) are
  not re-derived or confirmed against this specific circuit.
- ~~No quiescent-current (Iq) re-verification.~~ **Resolved by issue #20,
  re-balanced by issue #22, re-derived against its actual verdict metric by
  issue #24.** Issue #20 measured 914.99 µA at the reference corner (code
  `0x80`) against DR-0003 Row 4's `< 500 µA` target — **failing, 1.83x
  over** ([DR-0007](../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md),
  `sim/iq/results/20260906T032927Z/README.md`). Issue #22 re-balanced
  `RBIAS` and the tail-mirror ratio jointly and brought it to 467.18 µA
  (`.op`) / 157.27 µA (running) at code `0x80` ([DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md),
  `sim/iq/results/20260906T062311Z/README.md`), sized against the
  *stricter* `.op` reading rather than the running current DR-0003 Row 4
  actually names. Issue #24 re-derived `RBIAS` again against `iq_run`
  specifically, recovering trim range at the cost of letting `.op` run
  back up (754.90 µA at code `0x80`, no longer the verdict basis) —
  **met on `iq_run` at every simulated code** ([DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md),
  `sim/iq/results/20260907T090639Z/README.md`). See "Bias generator" above
  for the sizing and "Full PVT-corner re-verification (issue #24 …)" for
  the recovered trim range and the residual-accuracy trade-off it cost.
- ~~No PVT factorial for Iq.~~ **Resolved by issue #35.** `sim/iq/iq_sweep.py`
  now runs the full 7-process × 3-temperature × 3-supply factorial (63
  grid points/code, corner definitions imported from `sim/pvt/pvt_sweep.py`
  so the two campaigns cannot drift), at codes `0x00`/`0x80`/`0xC0`/`0xFF`.
  **Finding: DR-0003 Row 4 is met at the reference corner and across most
  of the grid, but exceeds at the fast corners (`ff`/`rc_f`) once
  temperature and supply move toward their hot/high-VDD extreme, at every
  simulated code** — worst case `ff`/85 °C/3.6 V, e.g. 623.68 µA at code
  `0xC0` (the code the block would actually ship at) vs. 400.87 µA at the
  reference corner. See
  [DR-0011](../spec/decision-records/0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md)
  and `sim/iq/results/20260909T225306Z/README.md` for the full grid and
  per-code worst-case table. Re-sizing to close this off-reference gap is
  a follow-on, not done here — DR-0009's ~6.3% reference-corner-only
  margin was exactly the kind of unstress-tested margin this gap made
  possible.
- ~~No layout.~~ **Resolved by issues #13/#27, post-layout re-verification
  by issues #28/#44.** `layout/cells/rcosc_top.gds` is DRC-clean and
  LVS-matched, with post-layout (PEX-extracted) PVT re-verification passes
  committed — the re-spin pass against the post-#39 `rcosc_bias` GDS (issue
  #44) is the current one: see
  [`layout/README.md`](../layout/README.md) and
  [DR-0013](../spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md)
  (which supersedes
  [DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)
  for the post-#39 schematic).

These are reserved for follow-on increments tracked against the gap
tracker (#5), consistent with the maturity ladder in the repo `README.md`.
