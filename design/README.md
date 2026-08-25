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
followed by a 4 µs transient measuring two consecutive rising edges of
`clk`. As of this issue's last run:

- `.op`: `vh = 2.200 V` (exactly 2/3 · VDD), `vl = 1.100 V` (exactly
  1/3 · VDD), `ibias ≈ 1.083 V` — the ratiometric bias generator is
  producing sane, non-degenerate threshold and bias nodes.
- Transient: `clk` **free-runs** (confirms the topology oscillates, not
  just a DC sanity check) — measured period ≈ 49.6 ns (≈ 20.2 MHz) at
  code `0x80`. This is **lower than the ≈ 40 MHz the first-order
  `f ≈ 1/(R·C·ln 3)` hand estimate predicts** at that code (see "Trim bank
  sizing" below) — expected, and explicitly **not** treated as an accuracy
  result: the hand estimate ignores comparator propagation delay, the
  discharge switch's finite on-resistance, and the differential comparator
  pair's real (non-ideal) switching behavior, none of which are budgeted or
  corner-simulated in this issue. Closing this gap between hand estimate
  and simulated behavior is schematic-refinement / PVT-corner-phase work
  (later increment), not something this issue's non-goals permit fixing
  by adjusting the ratified spec.

## Topology

Relaxation oscillator per
[`spec/decision-records/0001`](../spec/decision-records/0001-relaxation-oscillator-topology.md):
an RC timing element gated by threshold comparators, with a supply- and
temperature-aware bias generator, and digital trim implemented as a
switched-resistor bank directly setting the RC time constant.

`rcosc_top.sch` composes:

- **`XTRIM` (`rcosc_trim_bank`)** charges `C_TIMING` continuously from
  `VDD` through the trimmed resistance (the RC element).
- **`CTIMING`** (`cap_mim_1f0fF`, 200 fF) is the timing capacitor, at node
  `vc`.
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
resistor of the same flavor plus a diode-connected `nfet_03v3` generate a
current reference (`ibias`) that both comparator instances in
`rcosc_top.sch` mirror into their own tail current sources.

Using the **same poly-resistor flavor** (`ppolyf_u_1k`, gf180mcu §6.1A) for
the threshold divider as for the timing/trim resistor is a deliberate,
qualitative TC-tracking choice — process and temperature shifts move both
the RC time constant and the comparator thresholds together, to first
order. **This is not a quantified compensation claim.** DR-0003's
+8%/−9% full-temperature-range figure assumes no active TC compensation;
whether this ratiometric/flavor-matching choice measurably helps is
schematic-refinement and PVT-corner-phase work, explicitly out of scope
here.

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

Sized against the ratified ±40% / 28.8–67.2 MHz range
([DR-0003](../spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md)
"Row 2") using the topology's own nominal charge-time relationship,
`f ≈ 1/(R·C·ln 3)` (time to charge from ≈0 V to `V_H = 2/3·VDD` through `R`
into `C`, ignoring finite discharge time and comparator delay — a
first-order hand estimate, not a simulated result):

```
C_TIMING = 200 fF (cap_mim_1f0fF, W=20u L=10u -> area = 200 um^2)

R_min (code 0xFF) = RFIX                = 67.73 kOhm  -> f = 1/(R*C*ln3) = 67.2 MHz
R_max (code 0x00) = RFIX + 255*R_unit   = 158.00 kOhm  -> f = 1/(R*C*ln3) = 28.8 MHz

R_max / R_min = 158.00 / 67.73 = 2.3333 = 67.2 MHz / 28.8 MHz  (matches by construction)

R_unit = (R_max - R_min) / 255 = 354.0 Ohm
R_i = R_unit * 2^i  for i = 0..7  (354.0, 708.0, ..., 45312.0 Ohm)
```

All resistors use `ppolyf_u_1k` (1000 Ω/sq typ, gf180mcu §6.1A) at
`W = 2 µm`; segment lengths are solved from `R = Rsheet · L/W`:
`RFIX: L = 135.46 µm`, `R0..R7: L = 0.708, 1.416, 2.832, 5.664, 11.328,
22.656, 45.312, 90.624 µm`.

**What this sizing does and does not claim:**

- The trim bank's **endpoint ratio** (`R_max/R_min = 2.3333`) is sized to
  match the ratified frequency-range ratio exactly, so the schematic-level
  claim ("this bank can realize 28.8–67.2 MHz across 256 codes") holds by
  construction of the `f ≈ 1/(R·C·ln 3)` model.
- **Code ↔ frequency linearity within that range is NOT claimed or
  verified.** `f(code)` is linear in `1/R(code)`, and `R(code)` is a
  piecewise-linear (binary-weighted-segment) function of code, not `f`
  itself — DR-0002/0003's "linear mapping" language describes the *trim
  word design intent* (256 codes, ~0.31%/code average step), not a
  per-code DNL guarantee this schematic has verified. Trim linearity/DNL
  characterization is corner-sim-phase work.
- The measured smoke-test frequency at code `0x80` (≈20.2 MHz, see above)
  does not match the ≈40.4 MHz the `ln 3` hand estimate predicts at that
  code — flagged, not resolved, in this issue (see "Running the smoke
  test").
- Several LSB-side segment lengths (`R0`: 0.708 µm, `R1`: 1.416 µm) are
  short enough that they may not pass this PDK's resistor minimum-length
  DRC rule — **not checked**, DRC is explicitly out of scope for this
  issue (see Non-goals below). A later increment may need to widen these
  segments (e.g. drop `W` for the LSBs, or restructure the LSB end of the
  ladder) once DRC becomes in scope.
- The comparator's offset budget, the discharge switch's on-resistance,
  and the trim-DAC element mismatch/INL row DR-0002/0003 carries as a
  flagged assumption are **not** sized or verified against this specific
  transistor-level implementation here.

## Non-goals (this issue)

Per the issue's acceptance criteria and CLAUDE.md's evidence discipline:

- **No PVT-corner claim.** Every number above is either a ratified spec
  target (cited to DR-0002/DR-0003) or a first-order hand estimate/smoke
  test at nominal, room-temperature, typical-corner conditions only.
- **No DRC/LVS claim.** Device sizing (especially the LSB trim segments,
  see above) has not been checked against gf180mcu design rules.
- **No offset/mismatch budget.** The comparator and trim-bank device
  sizing are first-pass placeholders; DR-0002/0003's flagged assumption
  rows (trim-DAC mismatch, comparator offset residual, supply drift) are
  not re-derived or confirmed against this specific circuit.
- **No layout.** `layout/` remains untouched by this issue.

These are reserved for the follow-on increments tracked against the gap
tracker (#5), consistent with the "Non-goals" section of this issue and the
maturity ladder in the repo `README.md`.
