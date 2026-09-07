# sim — verification evidence (append-only)

Per `CLAUDE.md` ("Verification is the product: no claim without a
testbench... `sim/` results are append-only evidence"), everything under
this directory is a dated, immutable record of a simulation run. **Never
overwrite or edit a prior run's raw output** — a re-run adds a new,
timestamped directory alongside the old one, never in place of it.

```
sim/
  README.md              this file
  pvt/
    pvt_sweep.py          the PVT-corner campaign driver (issue #12)
    run-pvt-sweep.sh      wrapper: regenerates netlists, then runs pvt_sweep.py
    corners/<runid>/      raw ngspice logs, one file per simulated operating point
    results/<runid>/      results.csv, manifest.json, summary.md for that run
  iq/
    iq_sweep.py           the quiescent-current sweep driver (issue #22)
    run-iq-sweep.sh       wrapper: regenerates netlists, then runs iq_sweep.py
    corners/<runid>/      raw ngspice logs, one file per (sizing, trim code)
    results/<runid>/      README.md (measurement + verdict) for that quiescent-
                           current check, plus results.csv / manifest.json
                           (the issue #20 run predates the driver and holds a
                           hand-written README plus a raw log excerpt)
```

`<runid>` is a UTC timestamp (`YYYYMMDDTHHMMSSZ`) assigned at invocation
time. The driver refuses to start if a run id's directories already exist
and are non-empty, so a re-run can never clobber committed evidence.

## PVT-corner campaign (issue #12)

`sim/pvt/pvt_sweep.py` runs the full process x temperature x supply
factorial against `design/netlist/pvt_tb.spice` (derived from
`design/pvt_tb.sch` by `design/regen-netlist.sh`) and records every point's
measured frequency as append-only evidence.

**Regenerate / extend the evidence**:

```bash
# Requires: ngspice, xschem, python3, and a gf180mcuC PDK resolvable the same
# way design/regen-netlist.sh resolves it (PDK_ROOT env var, or `klt pdk find`).
sim/pvt/run-pvt-sweep.sh                # full campaign, a fresh runid
sim/pvt/run-pvt-sweep.sh --jobs 8       # limit parallel ngspice processes
sim/pvt/run-pvt-sweep.sh --keep-build   # keep the generated per-run decks under sim/build/<runid>/
```

**Sweep matrix** (full factorial, every combination simulated):

- **Process** (7 corners): `tt`, `ff`, `ss`, `fs`, `sf` (gf180mcuC's
  standard FET corners, each paired with the matching or typical
  resistor/MIM-cap corner) plus `rc_f`/`rc_s` (typical FETs, only the
  poly-resistor and MIM-cap corner moved) — the module split
  [DR-0003](../spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md)'s
  ±35% untrimmed-spread derivation is sized from.
- **Temperature**: −40 °C, +27 °C, +85 °C.
- **Supply**: 3.0 V, 3.3 V, 3.6 V.

**Passes, every run**: a realized trim curve at the nominal reference
corner (`tt`/27 °C/3.3 V); single-point trim calibration (binary search per
process corner) against both the ratified 48.000 MHz target and a
surrogate target (see below); a pre-trim full factorial at a fixed
mid-scale code; and two post-trim full factorials — one holding the single
code the *reference* corner calibrated to (the literal single-point
methodology the ratified spec assumes), one holding each corner's own
per-corner calibrated code (the "trim every die at test" model). **Both
post-trim passes are reported together, and the full-temperature-range
figure is always reported alongside the calibration-point figure, never
alone** — per the acceptance criteria for issue #12.

**Why a surrogate calibration target exists**: the pre-#16 schematic
(unchanged since DR-0004) did not reach anywhere close to the ratified
48.000 MHz target at any simulated corner — see
[`spec/decision-records/0005`](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md)
for the full evidence and disposition. Calibrating against the unreachable
ratified target saturated every corner's trim code at `0xFF`, which would
have made every "post-trim" pass degenerate into the pre-trim spread. The
surrogate target (the reference corner's own realized frequency at the
mid-scale code) is simulated *in addition to* the ratified-target pass so
the single-point trim methodology can still be exercised meaningfully; both
are reported, and neither silently substitutes for the other. Issue
#16's resize (see [`spec/decision-records/0006`](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md))
makes the ratified target reachable at almost every corner without
saturation, but both methodologies continue to be run and reported for
every campaign, since the surrogate methodology is what isolates the
post-trim residual once saturation is no longer the dominant effect.

Every committed run's `results/<runid>/summary.md` states, for each
ratified spec row, the simulated value and an explicit met/exceeds verdict
against `README.md`'s target-spec table — see
[DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md)
and [DR-0006](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md)
for each campaign's overall disposition of those verdicts.

## Committed runs (PVT campaign)

| Run id | Notes |
|---|---|
| [`20260905T211140Z`](pvt/results/20260905T211140Z/summary.md) | First full campaign against the DR-0004 (pre-#16) schematic (issue #12). 210 unique operating points, 0 failed measurements, 49.5 minutes wall clock at 16 parallel jobs (gf180mcuC, ngspice-46). See [DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md) for the resulting spec-compliance disposition. |
| [`20260906T030219Z`](pvt/results/20260906T030219Z/summary.md) | Full campaign against the issue #16 re-sized schematic (issues #16/#18). 278 unique operating points, 0 failed measurements, 15.0 minutes wall clock at 14 parallel jobs (gf180mcuC, ngspice-46). See [DR-0006](../spec/decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md) for the resulting spec-compliance disposition. |
| [`20260906T060104Z`](pvt/results/20260906T060104Z/summary.md) | Full campaign against the issue #22 bias re-balance (`RBIAS L = 1000 µm`, 8:1 tail mirror). 271 unique operating points, 0 failed measurements, 11.9 minutes wall clock at 14 parallel jobs (gf180mcuC, ngspice-46). Output frequency still **met** (max reachable 51.9415 MHz vs. the ratified 48.000 MHz); trim range still **not met** and its margin worse than DR-0006's (±32.42% vs. ±38.16%) — the price paid for the Iq fix. See [DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md). |
| [`20260907T090653Z`](pvt/results/20260907T090653Z/summary.md) | Full campaign against the issue #24 running-metric re-derivation (`RBIAS L = 210 µm`, 8:1 tail mirror unchanged). 277 unique operating points, 206 recorded rows, 0 failed measurements, 4.0 minutes wall clock at 8 parallel jobs (gf180mcuC, ngspice-46). Output frequency still **met** (max reachable 58.9870 MHz); trim range still **not met** but its margin recovers about half of DR-0008's loss (±35.50% vs. DR-0008's ±32.42% and DR-0006's ±38.16%); the post-trim, full-temperature, per-corner-code residual widens to −19.41%/+27.85% (worse than both priors — see DR-0009 for the root cause). See [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md). |

## Quiescent current (Iq) check (issues #20, #22, #24)

`design/smoke_test.sch`'s existing `.op` analysis was extended to compute
the total DC current drawn from `vdd` (`i(vdd)`, which by KCL sums every
branch hung off the supply) at the reference corner (`tt`/27 °C/3.3 V) and
the smoke test's existing representative trim code (`0x80`), to re-verify
DR-0003 Row 4's `< 500 µA` (running) target after issue #16's ~8x `RBIAS`
tail-current increase. This is a single representative-corner point check,
not a PVT factorial — a full corner sweep for Iq is a possible future
increment, not part of this check's scope.

**Two metrics, always reported together** (issue #22,
[DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md);
metric-basis update issue #24,
[DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md)):

- **`iq_op`** — the `.op` figure above, which issue #20 introduced and
  DR-0007 quoted. A relaxation oscillator has no stable DC operating point,
  so that solve converges on the unstable equilibrium, which pins the
  charge-complete comparator `XCMPH` at its own output inverter's trip
  point — holding that buffer, and the SR-latch NOR gate its mid-rail
  output drives, in full crowbar conduction, a state the running circuit
  passes through but never rests in. Every raw log under
  `iq/corners/<runid>/` prints those `.op` node voltages so the claim is
  checkable, not merely asserted. Kept for continuity with DR-0007, but
  **not**, as of DR-0009, DR-0003 Row 4's verdict basis — it can exceed
  500 µA at a sizing that meets Row 4 as actually worded, and that is
  expected rather than a failure.
- **`iq_run`** — `-i(vdd)` averaged over 20 whole oscillation periods
  (rising edges 5..25 of `clk`, startup skipped, the same window convention
  `pvt_sweep.py` uses). This **is** the quantity DR-0003 Row 4 names —
  `< 500 µA` **(running)**, anchored to ST `DS9826`'s `IDDA(HSI48)`, a
  datasheet supply current for an oscillator that is oscillating — and,
  as of issue #24/DR-0009, the metric Row 4's pass/fail verdict is
  actually read from.

Both are always measured and reported together — DR-0008's own sizing
happened to satisfy both, but the two are **not** expected to agree on
verdict in general (DR-0009); reporting both, always, is what makes that
checkable rather than asserted. `sim/iq/run-iq-sweep.sh` measures
both, across trim codes, for **both** the as-committed sizing and the
pre-#22 sizing it replaced, so the before/after comparison is produced by
one command from one netlist under one ngspice:

```bash
sim/iq/run-iq-sweep.sh                                 # codes 0x00 0x80 0xFF
sim/iq/run-iq-sweep.sh --codes 0x00 0x40 0x80 0xC0 0xFF --jobs 8
```

### Committed runs (Iq check)

| Run id | Notes |
|---|---|
| [`20260906T032927Z`](iq/results/20260906T032927Z/README.md) | First post-#16 Iq measurement (issue #20). Reference corner, code `0x80`: **914.99 µA measured vs. `< 500 µA` ratified — FAIL, 1.83x over.** Independent hand-estimate sanity check corroborates the figure. See [DR-0007](../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md) for the resulting disposition (spec unchanged, follow-up issue #22 filed). Predates `iq_sweep.py`; `.op` metric only. |
| [`20260906T062311Z`](iq/results/20260906T062311Z/README.md) | Post-#22 bias re-balance (issue #22), first run of `iq_sweep.py`. Reference corner, codes `0x00`/`0x80`/`0xFF`, both sizings, both metrics. **PASS on both metrics at every code**: as-committed `iq_op` 467.13–467.18 µA and `iq_run` 136.45–218.54 µA, vs. pre-#22 `iq_op` 914.40–914.99 µA and `iq_run` 470.40–605.50 µA. The `pre-22` variant reproduces DR-0007's 914.99 µA and DR-0006's trim-curve frequencies exactly, cross-validating the driver. See [DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md). |
| [`20260907T090639Z`](iq/results/20260907T090639Z/README.md) | Post-#24 running-metric re-derivation (issue #24), `RBIAS L = 210 µm`. Reference corner, codes `0x00`/`0x80`/`0xFF`, both sizings, both metrics. **`iq_run` met at every code** (359.74–468.61 µA, vs. the 500 µA target); **`iq_op` exceeds at every code** (754.82–754.90 µA) — expected, not a failure, since `iq_op` is no longer Row 4's verdict basis (DR-0009). See [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md). |
