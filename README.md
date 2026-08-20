# gf180-rcosc

A free-running, digitally trimmable RC oscillator on
[GlobalFoundries gf180mcu](https://github.com/google/gf180mcu-pdk), a 180 nm
open PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: just opened.** Nothing is designed yet — the first work item is the
spec itself.

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
circuit source. Topology selection (relaxation vs. ring-with-RC-reference)
is part of the spec work, decided by decision record.

## Target specification (DRAFT — engineering to ratify, see issue #1)

| Parameter | Target | Notes |
|---|---|---|
| Output frequency | TBD by spec (MHz-class) | derived from the anchor use case |
| Trim interface | digital, range and resolution TBD | trim math must be explicit in the spec |
| Post-trim accuracy | crystal-less full-speed-USB class | with optional runtime discipline (e.g. USB SOF) |
| Free-running accuracy over PVT | TBD from shipped-part precedents | PVT-corner spread is required evidence |
| Supply / Iq / startup | TBD | ratified with the spec |

An oscillator spec without its trim math is not a spec: every accuracy claim
must show both the PVT-corner spread and the trim range/resolution that
covers it.

Maturity ladder: spec ratified → schematic simulated across PVT → layout
DRC/LVS-clean → post-layout re-verification → shuttle seat → measured
silicon. **Current position: pre-spec.**

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
