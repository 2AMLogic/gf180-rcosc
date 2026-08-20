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

## Target specification (RATIFIED 2026-08-20, see issue #1)

Ratified per
[`spec/decision-records/0002-target-spec-ratification.md`](spec/decision-records/0002-target-spec-ratification.md),
which derives every row below from cited public precedents or an explicit,
flagged engineering assumption and shows the trim-math arithmetic. This
table supersedes the prior DRAFT.

| Parameter | Target | Basis |
|---|---|---|
| Output frequency | 48.000 MHz | matches the crystal-less full-speed-USB precedent (e.g. ST HSI48) — explicit engineering choice, see DR-0002 |
| Trim interface | 8-bit digital trim, ±35% range (31.2–64.8 MHz), ~0.27%/code (~132 kHz/code LSB), single-point trim at test | range covers the assumed ±30% untrimmed process spread (flagged assumption, pending gf180mcu device data) plus margin; full arithmetic in DR-0002 |
| Free-running, untrimmed (process spread, fixed T/V) | ±30% | explicit engineering assumption — not yet confirmed against gf180mcu-specific device data, flagged in DR-0002 |
| Free-running, post-trim (single-point trim, full PVT: process + −40…+85 °C + VDD ±10%) | ±2% (20,000 ppm) worst-case | budget breakdown (quantization, trim-DAC mismatch, comparator offset, temperature drift, supply drift) in DR-0002; temperature drift is the largest flagged risk |
| Runtime-disciplined (reserved, not designed in this issue) | ≤ ±0.25% (2,500 ppm) — USB full-speed compliance | precedented by ST's CRS peripheral and Silicon Labs' crystal-less USB parts using SOF-based correction; closes the gap from ±2% free-running — see DR-0002 "Consequences" |
| Supply | 3.3 V core (3.0–3.6 V) | explicit engineering choice, matches gf180mcu's 3.3V-primary flavor and sibling canary `gf180-bandgap`'s own supply scope |
| Quiescent current (Iq) | < 200 µA (running) | explicit engineering target, flagged — pending schematic-phase confirmation |
| Startup time | ≤ 10 µs to within trimmed accuracy | explicit engineering target, flagged — motivated by the RC-vs-crystal startup-time precedent |
| Temperature range | −40 °C to +85 °C (industrial) | explicit engineering choice, standard industrial MCU/oscillator range |

An oscillator spec without its trim math is not a spec: every accuracy claim
above shows both the PVT-corner spread and the trim range/resolution that
covers it — see DR-0002 for the full arithmetic and error-budget breakdown.
Several rows carry explicit, flagged engineering assumptions (not yet
confirmed against gf180mcu-specific device data) rather than invented
precision; DR-0002 states exactly which and what would supersede them.

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
