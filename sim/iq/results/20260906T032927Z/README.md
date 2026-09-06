# Quiescent current (Iq) measurement — issue #20

**Status: FAIL against DR-0003 Row 4's `< 500 µA` target.** See
[DR-0007](../../../../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md)
for the disposition (spec unchanged, evidence recorded, follow-up filed).

## Setup

- **Schematic under test**: `design/rcosc_top.sch` as landed by issue #16 /
  PR #19 (`RBIAS` `L = 25 µm`, ~8× the pre-#16 tail current), unchanged by
  this issue.
- **Testbench**: `design/smoke_test.sch`, extended by this issue to compute
  and print the total DC current drawn from `vdd`. No other change to the
  testbench's operating point.
- **Corner**: `tt` (typical) process corner (the only corner
  `pdk_include.spice` resolves — `sm141064.ngspice typical`/`res_typical`/
  `mimcap_typical`), `T = 27 °C` (ngspice default `TEMP`/`TNOM`, not
  overridden), `VDD = 3.3 V` — the same reference corner used elsewhere in
  this repo (`sim/pvt`'s reference corner, `design/smoke_test.sch`'s fixed
  bring-up point). Per the issue's acceptance criteria, only this single
  representative corner was run; a full PVT factorial for Iq is explicitly
  a possible future increment, not required here.
- **Trim code**: `0x80` (`t7 = 1`, `t0..t6 = 0`) — `design/smoke_test.sch`'s
  existing fixed code, unchanged.
- **Method**: an `.op` analysis with `let iq_ua = -1e6*i(vdd)` immediately
  after the existing node-voltage `print`. `i(vdd)` reads the current
  through the independent voltage source named `VDD` directly from the
  `.op` solve; ngspice's passive sign convention on an independent source
  reports current flowing *into* its positive terminal, so the raw value is
  negative when the circuit is actually drawing current from the supply
  (confirmed directly: the `.op` printout's own `vdd#branch` row reads
  `-0.00091499`, matching `i(vdd)` exactly) — negated and scaled to µA for
  a directly-readable positive quiescent-current figure. `i(vdd)` is the
  single source's own branch current, which by KCL already sums every
  branch hung off `vdd`: both `rcosc_bias` legs (threshold divider
  `RBA/RBB/RBC` and the `RBIAS`/diode-connected-mirror reference), both
  `rcosc_comparator` instances' tail current sources, and the trim bank's
  continuous charging current through the trimmed resistance chain.

## Result

```
iq_ua = 9.149895e+02
```

**Measured Iq = 914.99 µA** at the reference corner, code `0x80`.

| Target (DR-0003 Row 4) | Measured | Ratio | Verdict |
|---|---|---|---|
| `< 500 µA` (running) | 914.99 µA | 1.83x | **FAIL** |

This is not a near-miss (the "edge case" the issue's Test Plan flags) — the
measured figure is well outside the 500 µA target by an amount that
comfortably clears the "close to the line" threshold that would call for
finer PVT-sweep resolution before declaring a verdict.

## Sanity check (independent hand estimate)

To confirm the `.op` figure is a real circuit effect and not a testbench
artifact, an independent order-of-magnitude estimate from the schematic's
own device sizing (`design/netlist/rcosc_top.spice`):

- `RBIAS` (`ppolyf_u_1k`, `W = 2 µm`, `L = 25 µm`) ≈ 1000 Ω/sq ×
  (25 µm / 2 µm) = 12.5 kΩ.
- Assuming a diode-connected `nfet_03v3` `Vgs` of roughly 1.0 V at this
  current level: `I_bias_ref ≈ (3.3 V − 1.0 V) / 12.5 kΩ ≈ 184 µA`.
- Each `rcosc_comparator` tail mirror device is `W = 4 µm`/`L = 1 µm`
  against the bias generator's diode-connected reference at
  `W = 2 µm`/`L = 1 µm` — a ~2x mirror ratio per comparator. Two comparator
  instances (`XCMPH`, `XCMPL`) together draw ≈ 4x `I_bias_ref` ≈ 736 µA.
- Adding the reference branch itself (≈184 µA, already counted once, not
  double-counted with the mirrored tails) and the threshold-divider branch
  (`RBA + RBB + RBC` ≈ 150 kΩ series => ≈22 µA) totals ≈942 µA.

942 µA (hand estimate) vs. 914.99 µA (simulated) — same order of magnitude
and dominated by the same term (the mirrored comparator tail currents),
corroborating that the `.op` measurement reflects the real re-sized
circuit's behavior, not a testbench error.

## Evidence

- Raw ngspice run log excerpt: `smoke_test_iq_excerpt.log`
  (copied from `design/netlist/smoke_test.log`'s append-only run section
  timestamped `2026-09-06T03:29:27Z` — that file remains the primary,
  append-only record of the run per `design/README.md`'s own convention;
  this copy is for `sim/`-local self-containedness per `sim/README.md`).
- Testbench diff: `design/smoke_test.sch`'s `.control` block gained the
  `let iq_ua = ...` / `print iq_ua` lines (issue #20); no other schematic
  in `design/` was touched by this issue.

## Disposition

Recorded in [DR-0007](../../../../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md):
the ratified `< 500 µA` target is **not** relaxed. Issue #22 is filed to
re-balance the bias generator's sizing (trading off against issue #16's
frequency/trim-range fix, which is what raised this current in the first
place) rather than silently absorbing the overshoot.
