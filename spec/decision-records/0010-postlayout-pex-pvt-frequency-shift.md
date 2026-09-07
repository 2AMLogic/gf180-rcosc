# 0010: Post-layout (PEX-extracted) PVT re-verification — layout parasitics shift frequency further below the schematic-level model, ratified spec unchanged

- **Status**: Ratified — records simulation evidence. Does **not** supersede
  any row of [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md),
  [0004](0004-no-active-tc-compensation-runtime-discipline.md),
  [0005](0005-pvt-campaign-frequency-shortfall-spec-unchanged.md),
  [0006](0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md),
  [0008](0008-iq-metric-correction-and-bias-rebalance.md), or
  [0009](0009-running-iq-metric-basis-and-partial-trim-range-recovery.md).
  The ratified target-spec table in `README.md` stands unchanged.
- **Date**: 2026-09-07
- **Decided by**: Builder agent, issue #28

## Context

Issue #27 (PR #30) landed a DRC-clean, LVS-matched full-hierarchy
`layout/cells/rcosc_top.gds`, the last prerequisite for the post-layout
verification item #5/Epic #542 always deferred ("Post-layout
verification"). This issue (#28) re-runs the corner-endpoint subset of the
PVT matrix (`tt`/`ff`/`ss` process x -40/+27/+85 C temperature x
3.0/3.3/3.6 V supply, 27 points) against a parasitic-annotated netlist
extracted from that GDS via `klt extract --parasitics`, at the fixed
trim code `0xC0` (192) — the post-#24 (DR-0009) `posttrim_spec` pass's own
single-code calibration, at the reference corner's 27 C/3.3 V point against
the ratified 48.000 MHz target — and compares it against the same code's
already-committed schematic-level campaign
(`sim/pvt/results/20260907T090653Z/`).

Full evidence: `sim/pvt-postlayout/results/20260907T131703Z/{results.csv,
manifest.json, summary.md}`, the extracted netlist and `klt extract` JSON
report in that same directory, raw logs under
`sim/pvt-postlayout/corners/20260907T131703Z/`. Methodology, and why `klt
pex` was not used verbatim (a confirmed `--deck-option`/`--pins` gap on the
installed build, plus a `klt extract --pdk ... --parasitics`
capacitor-annotation issue worked around here), are in
`sim/pvt-postlayout/README.md`; both gaps are filed as friction against
`2AMLogic/klayout-tools`
([issue #1558](https://github.com/2AMLogic/klayout-tools/issues/1558)).

## Decision

No ratified spec-table row's disposition changes. Every post-trim accuracy
row this issue's data bears on (calibration-point and full-temperature-range
post-trim accuracy) was already **exceeds** at the schematic level in every
campaign since DR-0005 — this record adds a further, real divergence on top
of that pre-existing gap, it does not flip a `met` verdict to `exceeds` or
vice versa. Per CLAUDE.md ("agents do not relax the ratified spec to make
results pass"), the spec is unchanged; this record's sole purpose is to
state the post-layout finding with numbers, as issue #28's acceptance
criteria require, and place it in the same evidence lineage as DR-0005
through DR-0009.

**Finding**: at every one of the 27 corner-endpoint points, the
PEX-extracted netlist oscillates **slower** than the schematic-level
netlist — the delta is negative at every point, ranging **-1.88% to
-29.52%** (mean -10.32%). This is over an order of magnitude beyond the
ratified ±1.1% post-trim calibration-point accuracy budget
([0002](0002-target-spec-ratification.md)/[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md))
on its own, before even combining with the pre-existing process-spread
residual. The divergence is not uniform: it is worst at the `ff` corner's
coldest, highest-supply point (`ff` / -40 C / 3.6 V: -29.52%) and mildest at
`ff` / 27 C / 3.0 V (-1.88%) — every corner's delta also grows monotonically
with supply voltage at fixed process/temperature.

**Interpretation**: `klt extract --parasitics`'s first-order lumped-RC model
(one series R + one ground C per net, from the deck's curated
sheet-resistance/capacitance table, plus vertical-overlap coupling) adds
real parasitic capacitance on the oscillator's switching/timing nodes (the
comparator inputs, the discharge-switch gate/drain, the trim-bank's
internal nodes) that the schematic-level netlist has no representation of
at all. A relaxation oscillator's frequency is directly RC-time-constant
limited, so added parasitic C on any node in that charge/discharge/compare
path lengthens the period — the sign of every single delta (always slower,
never faster) is exactly the expected direction for a first-order parasitic
model of an RC-timed core, not noise or an extraction artifact. A same-run,
same-host cross-check (this run's own freshly re-simulated schematic side
against the already-committed `sim/pvt/` baseline, same code, same
methodology, different host) bounds cross-host/cross-run ngspice numerical
noise at ≤2.46% — over an order of magnitude smaller than this finding's
29.52% maximum, so the finding is not attributable to that noise floor. See
`sim/pvt-postlayout/results/20260907T131703Z/summary.md`'s "Cross-check"
section.

## Alternatives considered

- **Running the full 7-process x 3-temperature x 3-VDD factorial
  post-layout, not just the corner-endpoint subset.** Rejected as
  out-of-scope for this issue (issue #28's Acceptance Criteria explicitly
  bound it to the corner-endpoint subset, matching #12/#16's own
  precedent for a first post-layout pass); a full post-layout factorial is
  possible future work, not silently substituted for here.
- **Sweeping the full trim code (0x00..0xFF) post-layout to re-derive the
  realized trim range against the extracted netlist.** Rejected for the
  same scope reason — this record holds the code fixed (the existing
  post-#24 single-code methodology), per issue #28's explicit instruction
  to reuse `sim/pvt/`'s existing testbench infrastructure and fixed
  post-trim code rather than re-deriving it.
- **Using `klt pex` end-to-end instead of a manual `klt extract` +
  `sim/pvt/pvt_sweep.py`-derived sweep.** Rejected: `klt pex` has no
  `--deck-option`/`--pins` passthrough on the installed build (`klt
  0.4.0`), so it cannot select this design's non-default MiM-cap density
  (`cap_mim_1f0_m4m5_noshield` vs. the deck's own
  `cap_mim_2f0_m4m5_noshield` default) — using it anyway would have
  extracted against 2x this design's actual timing-capacitor density and
  invalidated every delta reported here. See `sim/pvt-postlayout/README.md`
  for the full mechanism and the filed friction issue.

## Consequences

- **No spec-table row's verdict changes** (see "Decision" above) — every
  bearing row was already `exceeds` at the schematic level.
- **The post-trim accuracy gap DR-0005 through DR-0009 already report is
  understated, not just at the process-spread level.** Any future work on
  closing that gap (active TC compensation, a different core topology, a
  post-layout-aware calibration target) needs to budget for a real,
  monotonic, up-to-~30% layout-parasitic frequency shift on top of the
  schematic-level process/temperature/supply spread already measured — the
  schematic-level netlist alone is not a sufficient predictor of silicon
  frequency for this design at its current layout.
- **This is a first-order lumped-RC parasitic model** (`klt extract
  --parasitics`'s own documented scope: quasi-static, one R+C per net,
  vertical-overlap coupling only, no lateral/distributed-RC unless
  `--critical-net`/`--distributed-rc` are opted into, neither used here).
  A finer-grained extraction (critical-net lateral coupling on the
  comparator/timing-cap nodes, or a full parasitic extraction flow) could
  move this number in either direction and is not run here — this record
  states what the *current* extraction methodology finds, not a final
  silicon-accurate figure.
- **Only the corner-endpoint subset at one fixed code is verified
  post-layout.** The full PVT factorial, the realized trim curve, and the
  per-corner surrogate-calibration methodology remain schematic-level-only
  claims, same as before this issue (`design/README.md` "Non-goals").
- Two `klt extract`/`klt pex` tool gaps encountered while building this
  campaign are filed as friction against `2AMLogic/klayout-tools`
  ([issue #1558](https://github.com/2AMLogic/klayout-tools/issues/1558)),
  generic and design-detail-free, per `CLAUDE.md`'s friction protocol.
