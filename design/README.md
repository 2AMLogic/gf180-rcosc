# design — gf180-rcosc schematic sources

**Status: schematic capture (issue #6, T1 item 1 of the gap tracker #5) —
design sources committed and netlist-reproducible — since carried through a
full PVT-corner campaign and several re-sizing/re-balancing passes (issues
#12/#16/#18/#20/#22/#24, decision records DR-0005 through DR-0009 below)
and instantiated into a DRC-clean, LVS-matched layout with a first
post-layout (PEX) re-verification pass (issues #13/#27/#28, see
[`layout/README.md`](../layout/README.md) and
[DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)).
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
left open by that record rather than a bandgap-style reference). A fourth
resistor of the same flavor (`RBIAS`) plus a diode-connected `nfet_03v3`
generate a current reference (`ibias`) that both comparator instances in
`rcosc_top.sch` mirror into their own tail current sources.

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
shunted by an `nfet_03v3` pass switch gated directly by its trim bit
(`t0..t7`, `t7` = MSB). Bit = 1 shorts (removes) that segment's resistance,
so `R(code)` is **monotonically decreasing** in code by construction — more
bits set can only remove series resistance, never add it. Both extreme
codes are directly representable: code `0x00` (all switches open) is the
full series chain (`R_max`); code `0xFF` (all switches closed) shorts every
variable segment down to `RFIX` alone (`R_min`) — verified at the schematic
level (8 switches present, one per bit) and exercised functionally by the
`t7`-only smoke-test code (`0x80`) above.

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

## Non-goals

Per the issue #6 acceptance criteria that first wrote this section, and
CLAUDE.md's evidence discipline (updated by issue #12's PVT-corner
campaign against the pre-#16 schematic, [DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md),
by issues #16/#18's post-resize campaign,
[DR-0006](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md),
by issue #22's bias re-balance,
[DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md),
and by issue #24's running-metric re-derivation,
[DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md) —
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
- **No PVT factorial for Iq.** Every Iq figure above is the single
  reference corner (`tt`/27 °C/3.3 V), as DR-0007's was. The DR-0009
  sizing's `iq_run` margin (~6.3% at the worst code) is comparable to
  DR-0008's `.op` margin (~6.6%) that this same gap already applied to; a
  corner sweep for Iq remains a future increment (DR-0008/DR-0009
  "Consequences").
- ~~No layout.~~ **Resolved by issues #13/#27, post-layout re-verification
  by issue #28.** `layout/cells/rcosc_top.gds` is DRC-clean and
  LVS-matched, with a first post-layout (PEX-extracted) PVT
  re-verification pass now committed — see
  [`layout/README.md`](../layout/README.md) and
  [DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md).

These are reserved for follow-on increments tracked against the gap
tracker (#5), consistent with the maturity ladder in the repo `README.md`.
