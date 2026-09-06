# design — gf180-rcosc schematic sources

**Status: first schematic-capture increment (issue #6).** T1 item 1 of the
gap tracker (#5) — design sources committed and netlist-reproducible. No
PVT-corner, DRC, or LVS claim is made from this directory yet; that is
explicitly out of scope for this increment (items 2-7 of #5).

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
`t0..t6 = 0`) and runs an `.op` (prints the bias/threshold node voltages)
followed by a transient measuring two consecutive rising edges of `clk`
(the window was shortened from the original 4 µs to 400 ns in issue #16 —
the re-sized schematic free-runs several times faster than the original, so
4 µs simulated far more periods than the two-edge measurement needs). As of
issue #16's last run (post-resize; see "Trim bank sizing" below for the
resizing itself):

- `.op`: `vh = 2.200 V` (exactly 2/3 · VDD), `vl = 1.100 V` (exactly
  1/3 · VDD) — the ratiometric bias generator is producing sane,
  non-degenerate threshold nodes.
- Transient: `clk` **free-runs** — measured period ≈ 23.8 ns (≈ 42.0 MHz)
  at code `0x80`, using the same first-two-rising-edges methodology as the
  original issue #6 measurement. This is **not** a steady-state accuracy
  figure (see the caveat issue #6 already carried forward, and "Trim bank
  sizing" below for the steady-state, corner-simulated numbers this issue
  adds): the first two edges include a few cycles of startup transient
  before the oscillator settles, and this design's higher post-resize
  bias current makes that startup transient more visible in a short,
  few-edge window than it was pre-resize. It remains a useful bring-up
  sanity check (confirms free-running oscillation and sane bias nodes),
  not a substitute for the reference-corner steady-state and PVT-corner
  results below.

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
unchanged: only the current-reference leg is re-sized.

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
- Several LSB-side segment lengths (`R0`: 0.7482 µm, `R1`: 1.4965 µm) are
  short enough that they may not pass this PDK's resistor minimum-length
  DRC rule — **not checked**, DRC is explicitly out of scope for this
  issue (see Non-goals below), same flagged gap as the pre-#16 sizing.
- The comparator's offset budget, the discharge switch's on-resistance
  (beyond the qualitative root-cause role identified above), and the
  trim-DAC element mismatch/INL row DR-0002/0003 carries as a flagged
  assumption are **not** sized or verified against this specific
  transistor-level implementation here.
- Increasing `RBIAS`'s current raises this block's quiescent current draw
  (Row 4 of the ratified spec, `< 500 µA`) — **not re-verified against
  that row by this issue**; flagged as a follow-up check, not a silent
  regression claim either way.

### Full PVT-corner re-verification — in progress, tracked separately

This issue's acceptance criteria call for re-running the same full
process×temperature×supply campaign methodology issue #12 used
(`sim/pvt/run-pvt-sweep.sh`) against this re-sized schematic, as a new,
dated evidence directory under `sim/pvt/results/` (append-only — the
issue #12 evidence directory, `20260905T211140Z`, is never overwritten).

That campaign was started against this resize (`sim/pvt/pvt_sweep.py`'s
`TSTOP_NS_DEFAULT`/`TSTOP_NS_RETRY` were lowered from 4000 ns/12000 ns to
1200 ns/4000 ns first — the pre-#16 schematic free-ran at ~20 MHz, so
4000 ns gave ample margin for the 25-edge measurement window, but the
re-sized schematic free-runs several times faster, so the old window
simulated far more oscillation cycles than the measurement needs, at a
real wall-clock cost with no accuracy benefit). It did **not** complete
within this issue: the shared build host was under sustained, heavy
multi-tenant simulation load for the duration of this issue's work (other
concurrent design sessions' PVT/eye-diagram sweeps observed via `ps`/`top`
throughout), which by itself (independent of this schematic's own
resimulation cost) pushed single-corner-point wall-clock times from the
low single-digit minutes issue #12 saw to 5–20+ minutes per point even
after the `TSTOP` reduction above — intractable for a ~200-point full
factorial within this issue's session. This is a **follow-up issue**, not
a decomposition of unfinished design work: the schematic resize itself,
its root cause, and its reference-corner validation (this section and
"Re-sizing methodology and result" above) are complete and are what this
issue's PR closes out.

## Non-goals

Per the issue #6 acceptance criteria that first wrote this section, and
CLAUDE.md's evidence discipline (updated by issue #12, which added a
PVT-corner claim against the pre-#16 schematic — see `sim/README.md` and
[DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md).
Issue #16 re-derives the sizing with real reference-corner simulation
evidence but did not complete a full PVT-corner re-campaign against it —
see "Full PVT-corner re-verification" above):

- **No DRC/LVS claim.** Device sizing (especially the LSB trim segments,
  see above) has not been checked against gf180mcu design rules.
- **No offset/mismatch budget.** The comparator and trim-bank device
  sizing are first-pass placeholders; DR-0002/0003's flagged assumption
  rows (trim-DAC mismatch, comparator offset residual, supply drift) are
  not re-derived or confirmed against this specific circuit.
- **No quiescent-current (Iq) re-verification.** Issue #16 raised
  `RBIAS`'s current ~8×; DR-0003 Row 4's `< 500 µA` target is not
  re-checked against this circuit by any issue to date.
- **No layout.** `layout/` remains untouched to date.

These are reserved for follow-on increments tracked against the gap
tracker (#5), consistent with the maturity ladder in the repo `README.md`.
