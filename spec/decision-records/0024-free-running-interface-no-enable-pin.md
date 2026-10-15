# 0024: `rcosc_top` stays free-running - no enable/standby pin, and Iq-off is not a specified quantity

- **Status**: proposed (records the operator ruling of 2026-10-15; needs the normal review and operator ratification)
- **Date**: 2026-10-15
- **Decided by**: Operator ruling on issue #131 (option a); written up by Loom Builder, pending ratification

## Context

`rcosc_top` has exactly these ports: `vdd vss clk t0 t1 t2 t3 t4 t5 t6 t7`
(supply, clock out, 8 trim bits; `design/netlist/rcosc_top.spice:2`,
`design/netlist/pvt_tb.spice:40`). It has no enable or standby input, and no
record or issue had said that was a choice. The shipped precedents the README
anchors to (ST HSI48, Silicon Labs crystal-less USB parts) are gated
oscillators with a defined off state, so the question was whether to add one
active-high `en` pin (cut the bias tail, park `clk` low) or stay free-running.
Issue #131 put that to the operator as a ranked decision; the operator ruled
for option (a) on 2026-10-15.

This record covers only the interface question. The startup time-origin and
"within trimmed accuracy" band ruling is owned by #82 (open) and by
[0020](0020-startup-time-trimmed-accuracy-band-definition.md) (Proposed). This
record does not ratify, restate or amend 0020.

## Decision

- `rcosc_top` is a **free-running** oscillator: the port list above is the
  interface, with **no enable / standby pin**.
- **Iq-off is not a specified quantity.** The block has no off state, so no
  off-state leakage row exists or is added. The README "Quiescent current
  (Iq)" row keeps its existing meaning (running).
- Nothing else changes: no schematic, layout, testbench or README spec-row
  edit. Rows that mention "startup" are unchanged by this record; their time
  origin is whatever #82 / 0020 end up ratifying, and is cited here as
  **pending**, not assumed.

## Alternatives considered

- **Add one active-high `en` pin (cuts bias tail, parks `clk` low)** - matches
  the gated shipped precedents and would give a defined startup-from-enable
  origin and an off-state leakage row. Not chosen: it costs a schematic and
  layout change, a re-run of the Startup and Iq benches and a new spec row,
  and no wake-from-off requirement is sourced today. It is also not needed by
  single-point trim at test.

## Consequences

- Good: the documented interface matches the implemented one; no unsourced
  duty-cycling requirement enters the spec; the decision is cheap to reverse.
- Bad: the block cannot be duty-cycled, and the Iq comparison against gated
  precedents (ST HSI48-class) is running-current only, with no off-state
  figure to compare.
- Reversal path: if a wake-from-off requirement is later sourced, a new
  record supersedes this one and files the follow-ups (schematic and layout
  change, Startup and Iq bench re-runs, an off-state leakage row). None are
  filed now because option (b) was not chosen.
- Startup-time interpretation remains open under #82; until it lands, the
  supply-ramp origin in 0020 is a Proposed bench convention, not a ratified
  definition.
