# gf180-rcosc

A free-running, digitally trimmable RC oscillator on
[GlobalFoundries gf180mcu](https://github.com/google/gf180mcu-pdk), a 180 nm
open PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: spec ratified.** The target spec (frequency, trim math, PVT
accuracy budget) is ratified — see below and
[`spec/`](spec/README.md). Nothing is designed yet; schematic entry and
PVT-corner simulation are the next work items.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Why this block

This is a **new block, not a port**. The fleet's existing clocking canaries
are PLLs; nothing in the fleet covers an internal RC-based clock source with
a digital trim interface. That is a different problem: no reference input,
no feedback loop to lean on — accuracy comes from the RC network itself,
from trim, and from how well the design cancels supply and temperature
dependence.

The anchor use case is well precedented in shipped commercial silicon:
crystal-less full-speed USB. The USB 2.0 specification's frequency-tolerance
clauses set the accuracy class, and multiple vendors ship MCUs that meet it
from an internal RC oscillator — post-trim accuracy plus runtime discipline
from an external timing reference such as USB start-of-frame timing (e.g.
ST's clock-recovery-system (CRS) peripheral, Silicon Labs' crystal-less USB
parts). This repo targets that public, well-documented accuracy class; the
spec will be derived from those public precedents and the USB 2.0 spec, and
from free-running accuracy figures in shipped RC-oscillator datasheets.

The sibling analog canaries on this PDK
([gf180-bandgap](https://github.com/2AMLogic/gf180-bandgap),
[gf180-temp-por](https://github.com/2AMLogic/gf180-temp-por)) are the style
reference for spec, decision-record, and evidence conventions — not the
circuit source. Topology selection (relaxation oscillator vs.
ring-with-RC-reference) was part of the spec work, decided in
[`spec/decision-records/0001`](spec/decision-records/0001-relaxation-oscillator-topology.md);
future spec changes go through their own decision record in `spec/`.

## Target specification (RATIFIED 2026-08-20, see issues #1 and #3)

Ratified per
[`spec/decision-records/0002-target-spec-ratification.md`](spec/decision-records/0002-target-spec-ratification.md),
as corrected by
[`spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md`](spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md),
which together derive every row below from cited public precedents or an
explicit, flagged engineering assumption and show the trim-math arithmetic.
DR-0003 supersedes DR-0002 for four rows (process spread, trim range/
resolution, post-trim accuracy, Iq) against gf180mcu's own published
electrical-specification tables; all other rows are DR-0002's, re-verified.

| Parameter | Target | Basis |
|---|---|---|
| Output frequency | 48.000 MHz | matches the crystal-less full-speed-USB precedent — ST `DS9826` Rev 6 Table 43 (`fHSI48` typ 48 MHz) and Silicon Labs CP2102N Rev 1.5 Table 3.5 (`fOSC` typ 48 MHz); explicit engineering choice, see DR-0002, citations verified in DR-0003 |
| Trim interface | 8-bit digital trim, ±40% range (28.8–67.2 MHz), 0.314%/code (150.6 kHz/code LSB), half-LSB ±0.157%, single-point trim at test | range covers the sourced untrimmed spread (required pull −32.3%/+38.4%) with margin; full arithmetic in DR-0003 §"Row 2" |
| Free-running, untrimmed (process spread, fixed T/V) | ±35% first-order (−27.7%/+47.6% exact in frequency) | **sourced** from gf180mcu-pdk `docs/analog/spice/elec_specs/`: poly-resistor spread ±20% (§5.1, §6.1A/B) + MIM-cap spread ±15.33% (§6.2(a)), summed worst-case as independent process modules — DR-0003 |
| Free-running, post-trim, **at calibration point** (T = 27 °C, process, VDD ±10%) | ±1.1% (≈10,600 ppm) worst-case | quantization ±0.157% + three flagged assumptions inherited from DR-0002 (trim-DAC mismatch, comparator offset, supply drift) — DR-0003 flags this as still optimistic vs. ST's shipped `ACC_HSI48` = −2.8/+2.9% at 25 °C |
| Free-running, post-trim, **full temperature range** (−40…+85 °C, VDD ±10%) | **+8% / −9%** worst-case | dominated by gf180mcu's published poly-resistor TCR of −1200 ppm/K (§6.1A), trimmed at 27 °C: ΔR/R = −6.96% at +85 °C (58 K) so f rises +6.84%, ΔR/R = +8.04% at −40 °C (67 K) so f falls −7.91%, plus the ±1.1% above — DR-0003. **Open item: whether the design adds active TC compensation or relies on runtime discipline is not yet decided** |
| Runtime-disciplined (reserved, not designed) | ≤ ±0.25% (2,500 ppm) — USB full-speed compliance | USB 2.0 Rev 2.0 §7.1.11 `TFDRATE`, verified verbatim; the clause covers temperature and supply, with no pre-/post-discipline distinction. Precedented by ST's CRS peripheral (`RM0091` Rev 10 §7, SOF-based) and Silicon Labs' crystal-less USB parts — see DR-0003 |
| Supply | 3.3 V core (3.0–3.6 V) | explicit engineering choice, matches gf180mcu's 3.3V-primary flavor and sibling canary `gf180-bandgap`'s own supply scope |
| Quiescent current (Iq) | < 500 µA (running) | anchored to ST `DS9826` Rev 6 Table 43 `IDDA(HSI48)` = 312 µA typ / 350 µA max, with headroom for gf180mcu's older 180 nm node — DR-0003 |
| Startup time | ≤ 10 µs to within trimmed accuracy | looser than the shipped precedent ST `DS9826` Rev 6 Table 43 `tsu(HSI48)` ≤ 6 µs max — DR-0002, citation verified in DR-0003 |
| Temperature range | −40 °C to +85 °C (industrial) | explicit engineering choice, standard industrial MCU/oscillator range |

An oscillator spec without its trim math is not a spec: every accuracy claim
above shows both the PVT-corner spread and the trim range/resolution that
covers it — see DR-0003 for the current arithmetic and error-budget
breakdown, and DR-0002 for the rows it did not change. **The free-running
accuracy claim must always be quoted with its temperature condition**:
≈±1% holds only at the calibration temperature, and the full-range figure
is roughly ±8–9%. Several rows still carry explicit, flagged engineering
assumptions (trim-DAC mismatch, comparator offset, supply drift) rather
than invented precision; DR-0003 states exactly which, and what would
supersede them.

Maturity ladder: spec ratified → schematic simulated across PVT → layout
DRC/LVS-clean → post-layout re-verification → shuttle seat → measured
silicon. **Current position: spec ratified, pre-schematic.**

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
