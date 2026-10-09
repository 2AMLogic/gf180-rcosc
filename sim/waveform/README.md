# sim/waveform - clk pulse-width / cycle-statistics harness (issue #91, offline subset)

Prepares, but does **not run**, a waveform-shape characterization of the `clk`
output: high/low pulse width, duty, rise/fall time, period statistics and
cycle-to-cycle period differences. This directory contains a bench/request
generator, an analyzer and synthetic-fixture tests. **There are no measured
results here.** Every number the tests produce comes from a synthetic fixture
and is labelled `SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE`. The physical
campaign is a deferred, separately approved work item (see "Campaign handoff").

```
sim/waveform/
  prepare.py            offline bench + `klt sim` request generator (no simulator, no cloud)
  analyze.py            klt sim report / waveform analyzer
  test_harness.py       synthetic-fixture + request tests (22 tests)
  provenance.json       GENERATED: grid, library mapping, calibration source, settings (not evidence)
  rcosc_top_schematic.spice   GENERATED: DUT extracted from design/netlist/pvt_tb.spice (no device edited)
  tb_v{30,33,36}_{tt,ss,ff}.spice, request_v{30,33,36}_{tt,ss,ff}.json   GENERATED: nine benches/requests
```

## Commands

```
# regenerate benches/requests (explicit calibration source is mandatory)
python3 -I sim/waveform/prepare.py --cal-run sim/pvt/results/20260923T030125Z
# offline one-corner probe request (-> request_probe.json / tb_probe.spice)
python3 -I sim/waveform/prepare.py --cal-run sim/pvt/results/20260923T030125Z --probe tt:27:3.3 --out /tmp/wf-probe

# tests (stdlib + pytest; no simulator; keep it small on the shared host)
python3 -I -m pytest -p no:cacheprovider sim/waveform

# CI: .github/workflows/waveform-offline.yml ("Waveform offline suite") runs exactly
#   python3 -I -m pytest -p no:cacheprovider sim/waveform/test_harness.py
# on every pull request and push to main (Python 3.12, pytest only; no PDK, klt,
# ngspice or batch credentials). Its fixtures are SYNTHETIC, not measured evidence.

# analysis of klt sim reports, one per request, nominal supply per report (new outdir each time)
python3 -I sim/waveform/analyze.py rep_v33_tt.json rep_v33_ss.json --vdd 3.3 3.3 --outdir sim/waveform/results/<runid>
```

`prepare.py` options: `--cal-target {ratified,surrogate}`, `--ramp-ns`,
`--tstop-ns`, `--tstep`, `--tmax`, `--window-ns`, `--min-cycles`, `--load-f`,
`--reltol/--abstol/--vntol`. `analyze.py` options: `--artifacts-root`,
`--window-ns`, `--min-cycles`, `--min-samples-per-cycle`, `--drift-tol`,
`--vdd-tol`, `--synthetic`, `--note`. Exit status is non-zero if any corner row fails.

## Grid

Exactly 27 points: process `tt, ss, ff` x temperature `-40, 27, 85` C x supply
`3.0, 3.3, 3.6` V. This is a subset of the seven-process 63-point grid of
`sim/pvt/pvt_sweep.py` (process sections, `TEMPS_C`, `VDDS_V` are imported from
there) and is **not full signoff**.

One deviation from "three requests of nine corners": a `klt sim` corner carries
library sections and temperature only, so a bench netlist (trim pins are baked
in) holds one trim code, while the calibrated code differs per process. The nine
process x temperature corners of each supply are therefore emitted as three
requests (one per process, three temperatures each): nine requests, 27 unique
dispatched corners, one transient per corner, three supply groups (`v30`, `v33`,
`v36`; the supply is baked into the PWL ramp, as in `sim/startup`).

## Calibration, load, stimulus (recorded in `provenance.json`)

- **Trim code**: per process, held at every temperature/supply point. Source:
  `sim/pvt/results/20260923T030125Z` (`calibration_spec_target`, the per-corner
  calibration at that process's own 27 C / 3.3 V point against the ratified
  48.000 MHz target): tt `0xA3`, ss `0xCD`, ff `0x59`. `prepare.py` requires the
  source explicitly, requires it to be a committed file, rejects out-of-range or
  saturated codes, and checks that the campaign's own `posttrim_ratif` rows hold
  the same code, status ok, at all nine T/V points of each process. It records
  campaign dir, run id, campaign git SHA, committing hash and sha256 of the
  manifest and results.csv. Nothing is recalibrated per PVT point.
- **Nominal load**: the calibration bench (`design/netlist/pvt_tb.spice`) has no
  explicit capacitance on `clk`, so the nominal output load is **no extra load**
  (0 F; DUT-internal loading only). No integration load is assumed. `--load-f`
  adds a capacitor; provenance then records
  `load_matches_calibration_bench: false` since the codes were set unloaded.
- **Stimulus**: VDD and the high trim pins ramp linearly 0 -> VDD in 1 us
  (same ramp-following trim pins as `sim/startup`); transient 20 us; saved
  signals `v(clk)`, `v(vdd)` (`save_mode: netlist`). Max time step 200 ps, print
  step 200 ps, reltol 1e-3, abstol 1e-12 A, vntol 1e-6 V (all configurable and
  recorded). Steady window: final 2 us (>= 20 complete cycles required).
- Units in generated JSON: seconds, volts, farads, amperes, degrees C.

## Measurement definitions (analyze.py)

Level = 50 % of **nominal** VDD, linear interpolation. Rising edges `r[i]`,
falling edges `f[i]` between them, inside the window: `P[i]=r[i+1]-r[i]`,
`H[i]=f[i]-r[i]`, `L[i]=r[i+1]-f[i]`, `duty=H/P`, cycle-to-cycle
`P[i+1]-P[i]`. Rise/fall time are 10-90 % / 90-10 % of nominal VDD on the same
transition. Reported per statistic: count, mean, min, max, peak-to-peak,
population standard deviation (periods, widths, duty, rise/fall, c2c). A leading
falling edge before the first rising edge and a trailing falling edge after the
last are incomplete boundary cycles: omitted and counted in `omitted_boundary`.

Explicit failures (`status: FAIL: <reason>`, no metrics emitted): missing or
unreadable report, report/corner `error`, `corner_count` mismatch, missing
waveform artifact, missing `v(clk)`/`v(vdd)`, non-numeric or non-finite values,
non-increasing time, fewer than 4 window crossings, invalid crossing order,
fewer than `min_cycles` complete cycles, fewer than 10 samples per cycle, a clk
that does not swing through 10-90 %, a rail outside +/-2 % of nominal in the
window, and an **unsettled tail** (mean period of the last vs first half of the
window - each an even number of cycles - differing by more than 0.5 %). Limit:
the drift test is a coarse two-half comparison; it will not flag a slow
oscillation of the period inside the window, which is reported as spread.

## Three different "jitter-like" quantities - kept apart

1. **Deterministic period spread** (this harness): `period_s.peak_to_peak` and
   `std_deterministic`, cycle-to-cycle differences. A noiseless transient, so
   these include residual settling and solver/sample artifacts (adaptive-step
   edge-time noise of order 0.2 ns on single edges was documented in
   `sim/startup/startup_report.py`; here single edges are *not* averaged).
   The standard deviation is deterministic spread, **not** RMS stochastic jitter.
2. **Stochastic oscillator jitter** (not done, feasibility **unverified**): would
   need transistor/resistor noise models with validated coverage for the
   gf180mcu models, a stated method, seeds, noise bandwidth, sample count and
   numerical-convergence evidence. `trnoise` availability alone does not
   establish that coverage. No noise source is added to the DUT.
3. **SOF-arrival jitter** (+/-500 ns, `sim/discipline/README.md`): an
   external-reference assumption of the discipline model. Oscillator
   measurements neither validate nor replace it.

## Solver limitations

Linear interpolation between adaptive-step samples; the 200 ps max step bounds
edge-time interpolation error but a convergence study across step/tolerance is
part of the deferred campaign, not done here. Rails are ideal sources, no
package/bond inductance, no extracted parasitics (schematic netlist only), no
mismatch/Monte Carlo.

## Campaign handoff (deferred, not part of this issue's acceptance)

Execution must go through `klt sim --backend batch` (the host forbids
hand-launched `ngspice` grids; a one-corner `--probe` may run locally). It needs
a usable batch runner: 2AMLogic/klayout-tools#2851 was OPEN on 2026-10-09, and
`sim/mc-groundwork/README.md` records a historical runner refusal - verify the
runner/version and artifact availability first. Record failed submissions; do
not substitute a local multi-corner campaign. A later work item must keep
timestamped immutable results with tool/PDK revision provenance (coordinate with
#65), check time-step/tolerance convergence, publish an informational table and
decision record (no ratified row is altered), and assess stochastic-noise
support separately; unsupported noise coverage is a limitation, not a number.
