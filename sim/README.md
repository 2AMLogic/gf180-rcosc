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
    delay_probe.py        comparator/latch stage-delay instrumentation
                           (issue #51) -- reuses pvt_sweep's deck composition;
                           wrdata + Python crossing/cycle-alignment analysis
                           (edge-index meas desyncs across nodes; documented)
    corners/<runid>/      raw ngspice logs, one file per simulated operating point
    results/<runid>/      results.csv, manifest.json, summary.md for that run
  iq/
    iq_sweep.py           the quiescent-current sweep driver (issue #22,
                           extended to a full PVT-corner factorial by
                           issue #35) -- imports PROCESS_CORNERS/TEMPS_C/
                           VDDS_V/corner_include() from sim/pvt/pvt_sweep.py
                           rather than duplicating them
    run-iq-sweep.sh       wrapper: regenerates netlists, then runs iq_sweep.py
    corners/<runid>/      raw ngspice logs, one file per (corner, trim code)
                           grid point (pre-#35 runs: one per (sizing, trim
                           code) at the reference corner only)
    results/<runid>/      README.md (measurement + verdict) for that
                           quiescent-current check, plus results.csv /
                           manifest.json (the issue #20 run predates the
                           driver and holds a hand-written README plus a raw
                           log excerpt)
  pvt-postlayout/
    pex_pvt_sweep.py       the post-layout (PEX-extracted) PVT re-verification
                           driver (issue #28) -- schematic vs. `klt extract
                           --parasitics` on `layout/cells/rcosc_top.gds`,
                           corner-endpoint subset
    run-pex-pvt-sweep.sh   wrapper: regenerates netlists, extracts parasitics,
                           then runs pex_pvt_sweep.py
    corners/<runid>/      raw ngspice logs, one per (side, operating point)
    results/<runid>/      results.csv, manifest.json, summary.md, plus the
                           extracted netlist and `klt extract` JSON report
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
corner (`tt`/27 °C/3.3 V) — since issue #43 additionally sampling the
`0xkF` block-boundary codes so the frozen R map's ~1-LSB-R monotonicity
margins are *measured* (the boundary local dips of the real shunt
switches, [DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md));
single-point trim calibration (binary search per
process corner) against both the ratified 48.000 MHz target and a
surrogate target (see below); a pre-trim full factorial at a fixed
mid-scale code; two post-trim full factorials — one holding the single
code the *reference* corner calibrated to (the literal single-point
methodology the ratified spec assumes), one holding each corner's own
per-corner calibrated code against the surrogate target (the "trim every
die at test" model) — plus, since issue #43, a third holding each
corner's code against the *ratified* target (pre-#43 unmeasurable: every
corner saturated below it) and a small `switchprobe` pass re-measuring
the issue #43 acceptance pairing (`ss`/27 °C supply sensitivity, codes
`0x80` vs `0xEF`). **All post-trim passes are reported together, and the
full-temperature-range figure is always reported alongside the
calibration-point figure, never
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
| [`20260921T065703Z`](pvt/results/20260921T065703Z/summary.md) | Issue #39 **interim** exploration campaign (appended by the issue #39 branch, superseded within the same issue): against the `RZ L = 24 µm` + poly-SEED interim sizing at git sha `42b2855` — a real, full-factorial run kept for the append-only record trail; its numbers describe a sizing that was **not** the one frozen, so do not quote them for the issue #39 disposition. 285 unique operating points, 0 failed measurements. |
| [`20260921T164939Z`](pvt/results/20260921T164939Z/summary.md) | Issue #43 **interim** campaign (appended by the issue #43 branch, superseded within the same issue): against the frozen transmission-gate trim sizing at git sha `004588e`, but run with the pre-#43 campaign driver — its summary still carries the two prose claims this issue's evidence had made vacuously true ("ratified target unreachable at every corner"; unqualified trim-map monotonicity), so it is kept for the append-only record trail and **must not be cited as issue #43's final evidence**. 306 unique operating points, 0 failed measurements. |
| [`20260921T173529Z`](pvt/results/20260921T173529Z/summary.md) | Full campaign against the issue #43 transmission-gate trim shunts (per-position 24/16/12/8/6/5/4/3 µm at `L = 0.28 µm`, sizing frozen at git sha `bfeb95d`, updated driver). 361 unique operating points, 282 recorded rows, 0 failed measurements, 31.4 minutes wall clock at 12 parallel jobs (gf180mcuC, ngspice-46). **Trim range met for the first time since DR-0005** (±51.36%, 27.2955–84.9384 MHz, ratio 3.1118, covering the ratified 28.8–67.2 window); all seven corners reach the ratified 48.000 MHz inner-range with **no saturation** (cal codes tt `0x9D`, ff `0x4C`, ss `0xCF`, fs `0x9B`, sf `0xA3`, rc_f `0x58`, rc_s `0xBE`); mid-block steps live (`0x00→0x10` +5.03% vs +0.03% pre-#43); block-boundary local dips measured and reported (`0x7F→0x80` −6.40% worst at tt); slow-corner calibrated-code supply sensitivity roughly halved (ss +11.76% vs +20.05%), with the remaining high-code supply sensitivity re-attributed to the comparator/latch delay residue by the per-code rows. See [DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md). |
| [`20260921T075822Z`](pvt/results/20260921T075822Z/summary.md) | Full campaign against the issue #39 comparator/bias-path revision (self-biased current-reference core, `RZ L = 32 µm`, sizing frozen at git sha `1ac4434`). 276 unique operating points, 0 failed measurements, 66.3 minutes wall clock at 14 parallel jobs on a contended host (gf180mcuC, ngspice-46). Output frequency still **met** (max reachable 56.7060 MHz); trim range still **not met** (±34.42%, a recorded −1.08 pt regression vs. DR-0009); the post-trim per-corner-code residuals improve at the hot end — calibration point −11.65%/+8.32%, full-temperature −20.15%/+13.03% (was −11.50%/+13.19% and −19.41%/+27.85%); the per-corner ΔT spread collapses from +856…+1923 ppm/K to +774…+1003 ppm/K, eliminating the device-driven excess DR-0006 isolated. See [DR-0012](../spec/decision-records/0012-comparator-bias-path-pvt-revision.md). |
| [`20260922T004823Z`](pvt/results/20260922T004823Z/summary.md) | **Delay-probe instrumentation** (issue #51, `delay_probe.py`): stage-delay decomposition of steady-state cycles at both per-corner calibrated-code sets across the full factorial plus the DR-0014 switchprobe code pairing at `ss`/27 °C — not a spec-row campaign. 138 points, 0 failed, 9.0 minutes at 12 jobs (gf180mcuC, ngspice-46, `tran 100p`). Headline: the delay sum carries **62–82% of the period's 3.0→3.6 V span** at calibrated codes (the low-side comparator alone: 87% of the `ss` delay span); the period decomposition closes to <20 ps (DR-0012's ≈3× paid-in multiplier corrected by measurement); a further 16–36% charge-path supply term separated for the first time. See [DR-0016](../spec/decision-records/0016-comparator-latch-delay-residue-budget.md). |
| [`20260922T010039Z`](pvt/results/20260922T010039Z/summary.md) | Full campaign re-run at the **same, unchanged schematic** (issue #51's reproduction basis: netlist identical to the `bfeb95d` sizing frozen for `20260921T173529Z`; git `bd57830` + the issue #51 probe-driver commit). 361 unique operating points, 282 recorded rows, 0 failed measurements, 59.1 minutes wall clock at 12 parallel jobs on a contended host (a sibling repo's campaign was running concurrently; gf180mcuC, ngspice-46). **Every post-trim table row — spec/surrogate/ratified calibration figures, calibrated codes, and all six condition-row verdict figures — reproduces `20260921T173529Z` exactly**, which is the reproducibility anchor DR-0016's re-derived budget rows are evaluated against. See [DR-0016](../spec/decision-records/0016-comparator-latch-delay-residue-budget.md). |

## Post-layout (PEX-extracted) PVT re-verification (issue #28)

`sim/pvt-postlayout/pex_pvt_sweep.py` re-runs the corner-endpoint subset of
the PVT matrix (`tt`/`ff`/`ss` x -40/+27/+85 C x 3.0/3.3/3.6 V, 27 points)
against a parasitic-annotated netlist extracted from the full-hierarchy
`layout/cells/rcosc_top.gds` (issue #27) via `klt extract --parasitics`, at
the fixed post-#24 (DR-0009) single-code post-trim methodology's own
calibration code, and reports the per-point schematic-vs-extracted delta.
See [`sim/pvt-postlayout/README.md`](pvt-postlayout/README.md) for the
methodology and why `klt pex` was not used verbatim (a confirmed
`--deck-option`/`--pins` gap on the installed build, plus a `klt extract
--pdk ... --parasitics` capacitor-annotation issue worked around here and
both filed as friction against `2AMLogic/klayout-tools`).

### Committed runs (post-layout PEX PVT)

| Run id | Notes |
|---|---|
| [`20260907T131703Z`](pvt-postlayout/results/20260907T131703Z/summary.md) | First post-layout PEX PVT re-verification against `layout/cells/rcosc_top.gds` (issue #27), fixed trim code `0xC0` (issue #28). 27-point corner-endpoint subset x 2 sides, 0 failed runs, 102.3 s wall clock at 8 jobs (gf180mcuC, ngspice-46). **Materially diverges**: schematic-vs-extracted delta is negative (slower) at every point, -1.88% to -29.52% — layout parasitics alone exceed the ±1.1% calibration-point accuracy budget. See [DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md). *Superseded for the post-#39 schematic by the issue-#44 run below.* |
| [`20260921T164434Z`](pvt-postlayout/results/20260921T164434Z/summary.md) | Post-layout PEX PVT re-verification of the **re-spun** bias cell (issue #44), against the post-#39 schematic campaign `sim/pvt/results/20260921T075822Z/` at its own auto-read calibration code `0xD0`. 27-point corner-endpoint subset x 2 sides = 54 runs, 0 failed, 203.4 s wall clock at 8 jobs (gf180mcuC, ngspice-46). **Materially diverges, deeper than the pre-#39 pass**: delta negative (slower) at every point, -11.24% to -41.42% (mean -19.56%), worst at `ff`/-40 °C/3.6 V; in-run schematic-side cross-check vs the committed post-#39 campaign: 0.00% at matched points. See [DR-0013](../spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md). *Superseded for the post-#43 schematic by the issue-#50 run below.* |
| [`20260922T004322Z`](pvt-postlayout/results/20260922T004322Z/summary.md) | Post-layout PEX PVT re-verification of the **re-spun** trim bank (issue #50), against the post-#43 schematic campaign `sim/pvt/results/20260921T173529Z/` (DR-0014) at its own auto-read ratified-target calibration code `0x9D`. 27-point corner-endpoint subset x 2 sides = 54 runs, 0 failed, 338.0 s wall clock at 8 jobs (gf180mcuC, ngspice-47). **Materially diverges, deeper on the mean than the pre-#43 pass**: delta negative (slower) at every point, -17.46% to -40.92% (mean -27.32%), worst at `ff`/-40 °C/3.6 V; in-run schematic-side cross-check vs the committed post-#43 campaign: 0.18% at matched points. See [DR-0015](../spec/decision-records/0015-trim-bank-respin-postlayout-pex-reverification.md). *Superseded for the post-#60 schematic by the issue-#61 run below.* |
| [`20260923T152954Z`](pvt-postlayout/results/20260923T152954Z/summary.md) | Post-layout PEX PVT re-verification of the **DR-0017 re-spun** comparator hierarchy (issue #61: `rcosc_comparator_p`/`rcosc_top.gds`), against the post-#60 schematic campaign `sim/pvt/results/20260923T030125Z/` (DR-0017) at its calibration code `0xA3` (`--baseline-runid`; the newest `sim/pvt/results/` run is DR-0017's probe campaign, which has no calibration manifest). 27-point corner-endpoint subset x 2 sides = 54 runs, 0 failed, 166.3 s wall clock at 8 jobs (gf180mcuC, ngspice-46, `klt 0.4.0` pinned). **Materially diverges, same always-slower sign and ff-cold worst-corner signature**: delta negative at every point, -18.78% to -36.86% (mean -25.65%), worst at `ff`/-40 °C/3.6 V; in-run schematic-side cross-check vs the committed DR-0017 campaign: 0.00% at matched points. **Both DR-0017 guardrails hold extracted-side** (this run's `--guardrails` pass): guardrail cell `0x80`/`ff`/85 °C/3.6 V at 31.16% below its DR-0017 basis, and every corner inner-range post-layout (`0xD9`/`0xB3`/`0xF7`, none saturated; `ss` ≈+4.7% from the `0xFF` rail). See [DR-0018](../spec/decision-records/0018-comparator-pmos-respin-postlayout-pex-reverification.md). |

## Quiescent current (Iq) check (issues #20, #22, #24, #35)

`design/smoke_test.sch`'s existing `.op` analysis was extended to compute
the total DC current drawn from `vdd` (`i(vdd)`, which by KCL sums every
branch hung off the supply), to re-verify DR-0003 Row 4's `< 500 µA`
(running) target after issue #16's ~8x `RBIAS` tail-current increase.
Issue #35 extended this from a single representative-corner point check
(`tt`/27 °C/3.3 V) into the same full process x temperature x supply
factorial `sim/pvt/pvt_sweep.py` runs for frequency — 7 process corners x
3 temperatures x 3 supplies = 63 grid points per trim code, with
`PROCESS_CORNERS`/`TEMPS_C`/`VDDS_V`/`corner_include()` imported from
`sim/pvt/pvt_sweep.py` directly (not re-typed), so the two campaigns'
corner definitions cannot drift apart.

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
checkable rather than asserted.

**Issue #35**: `sim/iq/run-iq-sweep.sh` now measures both metrics at
every point of the full 63-point (7 process x 3 T x 3 V) corner grid, at
codes `0x00`/`0x80`/`0xC0`/`0xFF`, for the `as-committed` sizing (the
`pre-22` before/after comparison stays reference-corner-only —
`sim/iq/results/20260906T062311Z/` — since running it across the full
grid too would double this driver's simulation cost for a comparison the
corner campaign does not need; see `sim/iq/iq_sweep.py`'s module
docstring). `--subset endpoints` (`tt`/`ff`/`ss` x 3T x 3V, 27 points/code)
is available as a fast check; the committed record always uses the full
grid:

```bash
sim/iq/run-iq-sweep.sh                                 # full grid, codes 0x00 0x80 0xC0 0xFF
sim/iq/run-iq-sweep.sh --subset endpoints --jobs 8      # fast check, not for committed evidence
sim/iq/run-iq-sweep.sh --codes 0x00 0x40 0x80 0xC0 0xFF
```

### Committed runs (Iq check)

| Run id | Notes |
|---|---|
| [`20260906T032927Z`](iq/results/20260906T032927Z/README.md) | First post-#16 Iq measurement (issue #20). Reference corner, code `0x80`: **914.99 µA measured vs. `< 500 µA` ratified — FAIL, 1.83x over.** Independent hand-estimate sanity check corroborates the figure. See [DR-0007](../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md) for the resulting disposition (spec unchanged, follow-up issue #22 filed). Predates `iq_sweep.py`; `.op` metric only. |
| [`20260906T062311Z`](iq/results/20260906T062311Z/README.md) | Post-#22 bias re-balance (issue #22), first run of `iq_sweep.py`. Reference corner, codes `0x00`/`0x80`/`0xFF`, both sizings, both metrics. **PASS on both metrics at every code**: as-committed `iq_op` 467.13–467.18 µA and `iq_run` 136.45–218.54 µA, vs. pre-#22 `iq_op` 914.40–914.99 µA and `iq_run` 470.40–605.50 µA. The `pre-22` variant reproduces DR-0007's 914.99 µA and DR-0006's trim-curve frequencies exactly, cross-validating the driver. See [DR-0008](../spec/decision-records/0008-iq-metric-correction-and-bias-rebalance.md). |
| [`20260907T090639Z`](iq/results/20260907T090639Z/README.md) | Post-#24 running-metric re-derivation (issue #24), `RBIAS L = 210 µm`. Reference corner, codes `0x00`/`0x80`/`0xFF`, both sizings, both metrics. **`iq_run` met at every code** (359.74–468.61 µA, vs. the 500 µA target); **`iq_op` exceeds at every code** (754.82–754.90 µA) — expected, not a failure, since `iq_op` is no longer Row 4's verdict basis (DR-0009). See [DR-0009](../spec/decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md). |
| [`20260909T225306Z`](iq/results/20260909T225306Z/README.md) | First full PVT-corner Iq factorial (issue #35), `as-committed` sizing only. 63-point grid x codes `0x00`/`0x80`/`0xC0`/`0xFF` = 252 points, 0 failed measurements, 2.7 minutes wall clock at 6 parallel jobs (gf180mcuC, ngspice-46). **Row 4 met at the reference corner and across most of the grid, but exceeds at the fast corners (`ff`/`rc_f`) at hot/high-VDD, at every code** — worst case `ff`/85 °C/3.6 V: 531.18–713.68 µA depending on code, vs. 345.34–451.91 µA at the reference corner. See [DR-0011](../spec/decision-records/0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md). |
| [`20260921T091042Z`](iq/results/20260921T091042Z/README.md) | Post-#39 Iq PVT factorial (issue #39), self-biased current-reference core, `RZ L = 32 µm`. 63-point grid x codes `0x00`/`0x80`/`0xC0`/`0xFF` = 252 points, 0 failed measurements, 34.3 minutes wall clock at 10 parallel jobs on a contended host (gf180mcuC, ngspice-46). **Row 4 met at the reference corner at every code** (242.13–330.38 µA) and now met at every grid point for codes `0x00`/`0x80` (worst 459.46/498.05 µA); still exceeded at the fast corners hot/high-VDD for `0xC0`/`0xFF` — worst `ff`/85 °C/3.6 V 541.85/614.87 µA, a smaller exceed region than DR-0011's pre-revision 531.18–713.68 µA across all codes. See [DR-0012](../spec/decision-records/0012-comparator-bias-path-pvt-revision.md). |
| [`20260921T181049Z`](iq/results/20260921T181049Z/README.md) | Post-#43 Iq PVT factorial (issue #43), transmission-gate trim shunts, sizing frozen at git sha `bfeb95d`. 63-point grid x codes `0x00`/`0x80`/`0xC0`/`0xFF` = 252 points, 0 failed measurements. **Per-code verdict classes unchanged**: `0x00` (worst 460.06 µA) and `0x80` (worst 498.76 µA) still met at every grid point — `0x80` with only 1.24 µA of margin at `ff`/85 °C/3.6 V; `0xC0`/`0xFF` still exceed at the fast-corner hot/high-VDD cells, with the restored fast-end frequency raising their worst-case values (550.20 / 724.42 µA at `ff`/85 °C/3.6 V vs 541.85 / 614.87 pre-#43) — the per-cycle timing-cap charge current moves with the frequency the trim map now realizes. No bias/Iq budget re-derivation was attempted by issue #43 (one issue, one mechanism); see [DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md). |
