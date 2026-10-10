# sim/supply-transient - dynamic supply-step and ripple response bench (issue #92, offline subset)

Prepares, but does **not run**, a bench for what the oscillator does when VDD
*moves* while it runs: a 3.3 V -> 3.0 V / 3.6 V step, and sinusoidal ripple on
the rail. Supply sensitivity is so far characterized only statically
(VDD 3.0 / 3.3 / 3.6 V at each corner; DR-0017). DR-0021's runtime-discipline
model treats temperature as the only drift between SOF corrections; this bench
prepares the measurement that can say whether a supply-disturbance term is
needed. This directory contains a generator, an analyzer and synthetic-fixture
tests. **There are no measured results here and no conclusion about the
discipline model.** Every number the tests produce comes from a synthetic
fixture and is labelled `SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE`. The
physical campaign is deferred (see "Campaign handoff"). No ratified spec row,
design file or committed result is touched.

```
sim/supply-transient/
  prepare.py        offline bench + `klt sim` request generator (no simulator, no cloud)
  analyze.py        klt sim report analyzer -> results.json / results.csv / summary.md / cycles_<TAG>.csv
  test_harness.py   synthetic-fixture + request tests (28 tests, run in CI)
```

Nothing is generated into this directory: `prepare.py` requires a caller-chosen
**new (or empty)** `--out`, and `analyze.py` a new `--outdir`. A future campaign
commits its generated inputs and results under a new timestamped
`sim/supply-transient/results/<runid>/` (append-only, see `sim/README.md`).

## Commands

```
# generate 21 benches/requests/cases + provenance.json into a NEW directory (calibration source is mandatory)
python3 -I sim/supply-transient/prepare.py --cal-run sim/pvt/results/20260923T030125Z --out /tmp/st-bench

# analysis of klt sim reports: TAG=report.json for every case of the bench (a missing case is a FAIL row)
python3 -I sim/supply-transient/analyze.py step_dn_r1us_tt=rep.json ... --bench-dir /tmp/st-bench --outdir <NEW dir>

# tests (stdlib + pytest; no simulator; small, fits the shared host)
python3 -I -m pytest -p no:cacheprovider sim/supply-transient/test_harness.py
```

CI: `.github/workflows/offline-suites.yml` (matrix entry `supply-transient-offline`)
runs exactly the pytest line above on every pull request and push to
main (Python 3.12, pytest only; no PDK, klt, ngspice or batch credentials).

`prepare.py` options (all recorded in `provenance.json`): `--cal-target
{ratified,surrogate}` (default `ratified`), `--strict-dut`, `--startup-ramp-ns`,
`--disturb-ns`, `--baseline-ns`, `--post-ns`, `--endpoint-ns`,
`--ripple-discard`, `--ripple-observe`, `--ripple-margin-ns`, `--band`,
`--min-cycles`, `--min-samples-per-cycle`, `--tstep/--tmax` (steps),
`--ripple-tstep/--ripple-tmax`, `--timeout-s/--ripple-timeout-s`, `--load-f`,
`--reltol/--abstol/--vntol`. `analyze.py` options: `--artifacts-root`, `--band`,
`--min-cycles`, `--min-remaining-us`, `--min-samples-per-cycle`, `--vdd-tol`,
`--synthetic`, `--allow-local`, `--note`. Exit status is non-zero if any case fails.

## Conditions and cases

Bounding conditions: `tt @ 27 C`, `ss @ -40 C`, `ff @ 85 C`. Per condition:

- **Steps**: 3.3 -> 3.0 V (`dn`) and 3.3 -> 3.6 V (`up`), ramp duration 1 us and
  100 us: four cases, tags `step_{dn,up}_r{1us,100us}_<proc>`.
- **Ripple**: 3.3 V mean, 100 mV peak-to-peak sine at 10 kHz, 100 kHz, 1 MHz:
  three cases, tags `ripple_f{10kHz,100kHz,1MHz}_<proc>`. These frequencies and
  the amplitude are illustrative engineering choices, non-exhaustive, and
  informational.

3 x (4 + 3) = 21 cases. Each is its own single-corner `klt sim` request
(`request_<TAG>.json`, `tb_<TAG>.spice`, `case_<TAG>.json`): `klt` corners carry
library sections and temperature only, while the trim code is baked into the
bench and differs per process. The DUT (`rcosc_top` hierarchy extracted from
`design/netlist/pvt_tb.spice`, unchanged) is inlined as
`rcosc_top_schematic.spice` in each generated directory, not staged by sibling
include across directories (klayout-tools#2882).

## Calibration (recorded in `provenance.json`)

`--cal-run` is mandatory; the target defaults to `ratified`. `prepare.py` calls
`load_calibration` of `sim/waveform/prepare.py` (shared, not re-typed): the
manifest and `results.csv` must be committed, codes must be unsaturated
integers in 0..255, and the campaign's own `posttrim_ratif` rows must hold the
same code, status ok, at all nine T/V points of each process. Source/manifest
sha256, campaign run id, UTC stamp, campaign git SHA and committing hash are
recorded. Reference source `sim/pvt/results/20260923T030125Z`: tt `0xA3` (163),
ss `0xCD` (205), ff `0x59` (89), each calibrated at **its own process's**
27 C / 3.3 V point. That code is **held** at the proposed tt/27 C, ss/-40 C and
ff/85 C conditions and across the supply step: nothing is recalibrated at the
extreme temperatures or after a step.

Source/DUT relation is reported explicitly (`provenance.json: dut`, and a
stderr warning plus source age in days): the DUT netlist hash, the extracted
hash, and one of `unchanged`, `CHANGED` (netlist modified after the results were
committed), `UNVERIFIED` (netlist changed between the campaign's recorded
git SHA and the commit that committed its results; the manifest records no DUT
hash) or `UNKNOWN` (campaign commit not in the repository, e.g. a shallow clone).
`--strict-dut` fails unless it is `unchanged`. Legacy calibration cannot imply
signoff of a changed DUT. **Observed for the reference source at the time of
writing: `UNVERIFIED`** - `design/netlist/pvt_tb.spice` was modified in the same
commit that committed that campaign (the DR-0017 comparator re-reference, #60)
while the manifest's `git_sha` predates it. The deferred campaign must
resolve this (e.g. re-confirm the codes on the current DUT) before its results
are presented as at the calibrated code.

## Stimulus

Rail `0 -> 3.3 V` in 1 us (startup ramp), held; the disturbance starts at 10 us;
baseline window = the final 2 us before it. Step: linear ramp of 1 us or 100 us
to the target, then 20 us of post-ramp observation (endpoint window = final
2 us of the record). Ripple: a sine (`SIN`, zero phase at its start) in series
with the 3.3 V rail from 10 us; after the start, five ripple periods are
discarded and ten full periods observed, so the record length adapts to
frequency (1.5 ms for 10 kHz; larger step 500 ps, longer timeout - a heavy but
batchable transient). **High trim inputs follow VDD** (PWL copy of the step
waveform; VCVS `ET<i>` from the rippled node for ripple); the code is fixed.
Extra clk load: none by default (matches the calibration bench); `--load-f`
adds a capacitor and provenance records `load_matches_calibration_bench:
false`. Saved signals `v(clk)`, `v(vdd)`. Ideal source, no package inductance,
no extracted parasitics.

## Measurement definitions (analyze.py)

- **Crossings** are interpolated zero crossings of `v(clk) - 0.5*v(vdd)`, so a
  moving rail is not mistaken for a timing change. Crossings from the baseline
  window start must strictly alternate. A *complete rising-edge period* is
  `r[i] -> r[i+1]`; cycle frequency `1/P`, stamped at the start edge.
- Required: at least 20 baseline and endpoint cycles, at least ten samples per
  cycle, finite and strictly ordered samples, both signals present.
- **Step**: baseline frequency = mean cycle frequency in the baseline window;
  endpoint frequency = mean cycle frequency in the final 2 us. *Peak deviation*
  = max `|f_i - f_end|` over complete cycles from the disturbance start to the
  end (during and after the ramp), absolute and as a fraction of `f_end`, with
  its signed value and time. *Settling*: the first complete cycle starting at or
  after ramp completion such that it and all later cycles are within `+/-band`
  (default 1 %) of `f_end`, with at least 20 qualifying cycles and 2 us of record
  remaining after it starts; elapsed = that cycle's start edge minus ramp
  completion. Otherwise `censored` (record or in-band tail too short; or the
  record ends before ramp completion plus the endpoint window) or
  `not_settled` (the final cycle is outside the band) - never reported as zero.
  The band is a configurable engineering metric, **not** the ratified
  trimmed-accuracy band and not an acceptance threshold.
- **Ripple**: baseline (as above, before the ripple starts) and, over cycles
  lying entirely in the observed ten periods, `depth = (max f - min f)/mean f`
  and normalized sensitivity `depth / (Vpp/Vmean)` (configured values; the
  measured rail mean and p-p are also reported and must agree within 2 % / 25 %).
  Dimensionless. It is **not** called a dB PSRR: no transfer-function
  convention is defined. Requires at least 8 clk cycles per ripple period.
- Per-cycle period/frequency vs time is written to `cycles_<TAG>.csv`.

Explicit failures (`status: FAIL: <reason>`, no metrics): missing report, missing
case (a case of the bench provenance without a report), report tag not in the
bench, unreadable/invalid report, refused or errored batch submission (report
status `refused`/`rejected`/`submit_failed`/`error`, message included),
per-corner `error`, corner not matching the case, wrong corner count, report not
executed on the batch fleet (`environment.remote` missing, unless `--allow-local`
for a single debug probe), missing waveform artifact or signals, nonfinite or
unordered samples, inadequate sampling, too few cycles, rail not at the expected
level, invalid crossing order, record shorter than the ripple observation.

## What is and is not evidence

Fixtures are built in `test_harness.py` (known settling, overshoot, persistent
modulation, truncated records, known ripple modulation at all three
frequencies). Anything analyzed from a `--synthetic` run or from a report
carrying `"synthetic": true` is labelled `SYNTHETIC FIXTURE - NOT MEASURED
EVIDENCE`, sets `measured_evidence: false`, and taints the whole run.
`provenance.json` of the generator is `NOT EVIDENCE: offline request
generation`.

## Campaign handoff (deferred, not part of this issue's acceptance)

- Execution is deferred: 2AMLogic/klayout-tools#2851 (runner/client version
  mismatch) is open. A campaign needs a **successful batch preflight** first.
  Submit every request with `klt sim <request> --backend batch` (single-corner
  requests included, since `klt` keeps single units local by default) using an
  absolute `-o`. **No local grid fallback**; a refused submission or a per-corner
  error is recorded and reported (the analyzer turns each into a FAIL row), not
  worked around.
- Copy the generated directory into a new `results/<runid>/` with the reports
  (append-only), run `analyze.py` into a new `analysis/` directory, check
  time-step/tolerance convergence (10 kHz ripple runs at 500 ps), and decide the
  DUT/calibration question above.
- Measured tables (settling time, dynamic sensitivity with conditions) and the
  one-paragraph conclusion on whether DR-0021's temperature-only drift
  assumption needs a supply-disturbance term (and a decision record if so) belong
  to that campaign. Ratified spec rows are not altered.
