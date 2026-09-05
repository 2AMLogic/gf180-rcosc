# 0005: PVT campaign confirms a frequency/accuracy shortfall in the current schematic — ratified spec unchanged

- **Status**: Ratified — records simulation evidence. Does **not** supersede
  any row of [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md), or
  [0004](0004-no-active-tc-compensation-runtime-discipline.md). The ratified
  target-spec table in `README.md` stands unchanged.
- **Date**: 2026-09-05
- **Decided by**: Builder agent, issue #12

## Context

Issue #12 ran the first full PVT-corner simulation campaign against
`design/netlist/pvt_tb.spice` (derived by `design/regen-netlist.sh` from
`design/pvt_tb.sch`, exercising the unchanged-since-DR-0004
`design/rcosc_top.sch`): 7 process corners (`tt`/`ff`/`ss`/`fs`/`sf` plus
the resistor/MIM-cap-only `rc_f`/`rc_s` split DR-0003 derives its process
budget from) x 3 temperatures (−40/+27/+85 °C) x 3 supplies
(3.0/3.3/3.6 V) — 63 points per pass, pre-trim and two post-trim
methodologies, 210 unique operating points total, 0 failed measurements.
Full evidence: `sim/pvt/results/20260905T211140Z/{results.csv,manifest.json,summary.md}`,
raw logs under `sim/pvt/corners/20260905T211140Z/`.

`design/README.md` already flagged, from the single-corner/nominal-condition
smoke test (issues #6/#8), that the measured free-running frequency at code
`0x80` (≈20.2 MHz) fell well short of the ≈40.4 MHz the schematic's own
first-order `f ≈ 1/(R·C·ln 3)` trim-bank sizing model predicts at that code,
attributing the gap to comparator propagation delay, the discharge switch's
finite on-resistance, and non-ideal comparator switching — none of which the
hand-estimate model captures — and stating explicitly that closing this gap
is "schematic-refinement / PVT-corner-phase work... not something this
issue's non-goals permit fixing by adjusting the ratified spec." This record
is that PVT-corner-phase confirmation, and it forces a decision:
CLAUDE.md's evidence discipline requires recording a simulation result that
contradicts a ratified spec figure via a decision record, even when — as
here — the correct disposition is that the ratified figure is not the thing
that is wrong.

## Decision

**No ratified spec figure is superseded.** The findings, row by row against
`README.md`'s target-spec table:

| Row | Ratified | Simulated (this campaign) | Disposition |
|---|---|---|---|
| Free-running, untrimmed, process spread (fixed T=27 °C/V=3.3 V) | ±35% first-order (−27.7%/+47.6% exact) | −24.27% / +37.72% | **Confirmed.** Within the ratified bound — the first direct schematic-level simulation evidence for this row, agreeing with DR-0003's PDK-device-data derivation. |
| Output frequency | 48.000 MHz | max reachable, any corner/T/V/code: 31.18 MHz (`ff`, 85 °C, 3.6 V, code `0xFF`) — 65% of target. At the reference corner (`tt`, 27 °C, 3.3 V) the realized range is only 17.73–21.38 MHz. | **Not met by this implementation.** Not treated as evidence the target is unreachable on gf180mcu (see "Alternatives considered"). |
| Trim range | ±40% (28.8–67.2 MHz) | ±9.33% realized (17.7280–21.3761 MHz at the reference corner); trim-bank endpoint ratio realized 1.2058 vs. the 2.3333 the schematic's own sizing intended | **Not met by this implementation.** |
| Post-trim, at calibration point | ±1.1% | −27.93%/+42.10% (single global code, calibrated against the ratified target) or −23.48%/+21.20% (per-corner code, calibrated against a surrogate target — see `sim/README.md`) | **Not met by this implementation.** |
| Post-trim, full temperature range | +8%/−9% | −32.67%/+45.86% (global code) or −28.51%/+24.70% (per-corner code) | **Not met by this implementation.** |

Because the schematic cannot reach anywhere near 48.000 MHz even at the
fastest simulated corner and the maximum trim code, calibrating against the
ratified target saturates every process corner's trim search at `0xFF` —
the trim bank has **zero** remaining headroom to correct process,
temperature, or supply variation once every code is already needed just to
get as close to the target as physically possible at that corner. The two
post-trim accuracy rows above are consequently dominated by this
saturation, not by the trim-DAC mismatch / comparator-offset / supply-drift
budget DR-0002/0003 assumed would be the residual after a successful trim.

This is filed as a **PVT-wide confirmation of the gap `design/README.md`
already named**, not a new, unrelated defect: the schematic's trim-bank
sizing arithmetic (`design/README.md` §"Trim bank sizing") shows the
bank's endpoint resistance ratio was deliberately sized to match the
ratified ±40% range under the `f ≈ 1/(R·C·ln 3)` model; what this campaign
shows is that the real (transistor-level, corner- and temperature-swept)
circuit does not follow that model closely enough for the sizing to hold —
consistent with, and now quantifying, the exact mechanism `design/README.md`
already named (comparator delay and switch resistance not budgeted by the
hand estimate).

A minor secondary observation, not explained or resolved here: the
realized trim curve at the reference corner is monotonically increasing
from code `0x00` through `0xF0`, then **drops** at `0xFF` (22.2197 MHz →
21.3761 MHz, ≈4%) — see `sim/pvt/results/20260905T211140Z/summary.md`
"Realized trim curve". `calibrate()`'s binary search assumes strict
monotonicity; this is flagged for the follow-up schematic-revision work
(re-run with a longer transient / more measured cycles to rule out a
settling-window artifact at that specific code before treating it as a
real device effect) rather than investigated further by this record.

## Alternatives considered

- **Ratify a lower output-frequency target, a narrower trim range, or
  looser post-trim accuracy figures matching the as-simulated numbers.**
  Rejected — this is exactly "relax the ratified spec to make results
  pass," which CLAUDE.md prohibits outright. The ratified 48.000 MHz target,
  ±40% trim range, and post-trim accuracy budgets are anchored to external
  precedent (ST `DS9826`, Silicon Labs CP2102N) and gf180mcu's own published
  device data (DR-0002/0003), not to this specific schematic's untuned R/C
  sizing. Nothing in this campaign's evidence shows those targets are
  unreachable on gf180mcu in general — `design/README.md`'s own sizing
  arithmetic shows the trim bank's *endpoint ratio* was correctly targeted
  at the ±40% range under the topology's first-order model; the gap is
  between that model and the simulated transistor-level behavior of *this*
  implementation, which is schematic-refinement work, not a spec problem.
- **Treat this as invalidating DR-0003's process-spread derivation (Row
  1).** Rejected — that row is the one this campaign's own relative
  (percentage) measurements confirm. DR-0003 derives it from gf180mcu's
  published resistor/MIM-cap spread data, independent of this schematic's
  absolute R/C sizing choice; simulation agrees with it.
- **Leave the discrepancy undocumented, noted only in the PR description.**
  Rejected — CLAUDE.md's evidence discipline and issue #12's acceptance
  criteria both require a decision-record artifact whenever simulation
  contradicts a ratified figure, even when the record's disposition is
  "spec unchanged, implementation flagged" rather than "spec revised."
- **Re-derive the post-trim accuracy rows now, using the as-simulated
  (saturated) trim behavior as the new baseline.** Rejected — a residual
  accuracy figure computed against a saturated, non-functional trim range
  is not a meaningful accuracy budget for a properly-sized implementation;
  re-deriving it now would launder a broken-trim artifact into what looks
  like a mature, PDK-sourced accuracy figure.

## Consequences

- `README.md`'s target-spec table is **unchanged** by this record.
- `design/README.md`'s smoke-test observation (a single nominal-corner
  reading) is now corroborated by full-PVT evidence
  (`sim/pvt/results/20260905T211140Z/summary.md`); a future schematic
  revision should cite this record when it updates that section.
- A follow-up issue is required to close the gap between the
  `f ≈ 1/(R·C·ln 3)` hand-estimate and the simulated transistor-level
  behavior (comparator propagation delay, discharge-switch on-resistance,
  non-ideal comparator switching per `design/README.md`'s own naming of the
  mechanism, and the trim-bank's realized-vs-intended endpoint ratio) before
  the ratified output-frequency, trim-range, or either post-trim accuracy
  row can be claimed met by an actual implementation. That issue is out of
  scope for #12 (schematic-level evidence recording only, per its own
  Problem Statement) and is filed separately as #16.
- Sub-issue #14 (Chipalooza proposal document) must report every spec-table
  row's met/unmet status from this record's table, not the pre-simulation
  targets, per its own acceptance criteria ("every spec row states
  met/unmet against the brief").
- Sub-issue #13 (layout/DRC/LVS + post-layout PVT re-verification), if run
  against the current, not-yet-retuned schematic, will necessarily inherit
  this same frequency/accuracy shortfall in its post-layout comparison;
  this record does not decide #13's sequencing relative to the follow-up
  schematic-revision work, only flags the dependency.
- **What is not invalidated**: the relaxation-oscillator topology
  ([0001](0001-relaxation-oscillator-topology.md)), the decision not to add
  active TC compensation ([0004](0004-no-active-tc-compensation-runtime-discipline.md)),
  and the free-running untrimmed process-spread figure
  ([0003](0003-pdk-sourced-process-spread-tcr-and-iq.md) Row 1) all stand —
  the last one now with direct schematic-level simulation support in
  addition to its PDK-derived basis.
- If a future schematic revision's own PVT campaign shows the ratified
  targets genuinely cannot be met by any realizable implementation of this
  topology on gf180mcu (as opposed to this specific first-cut sizing), that
  finding must be recorded in its own superseding decision record — not
  folded into this one.
