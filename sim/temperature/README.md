# sim/temperature - interior-temperature curvature harness (issue #125, offline subset)

The historical PVT grid (`sim/pvt/pvt_sweep.py` `TEMPS_C`) samples only
-40 / 27 / 85 C, so it says nothing about how frequency bends **between** those
points. The DR-0021 discipline plant (`sim/discipline/`) interpolates its
temperature factor `g_p(T,V)` linearly across that three-point grid. This
directory prepares, but does **not run**, a 36-point fixed-code campaign that
can later test that assumed shape.

**There are no measured results here.** This PR delivers offline request
generation, an analyzer and synthetic-fixture tests. Every number the tests
produce comes from a synthetic fixture and is labelled
`SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE`. The measured campaign is deferred
(see "Deferred measured campaign").

```
sim/temperature/
  prepare.py            offline request generator (no simulator, PDK, cloud or network)
  analyze.py            curvature / slope / monotonicity analyzer of klt sim reports
  test_temperature.py   synthetic-fixture tests (no subprocess except git, no sockets)
```

Generated benches and requests are **not committed**: `prepare.py` writes them
into a new directory at campaign time, so the manifest's design-revision and
hashes describe the tree the requests were actually generated from.

## Commands

```
# generate into a NEW directory (refuses to overwrite; --cal-run is mandatory)
python3 -I sim/temperature/prepare.py --cal-run sim/pvt/results/20260923T030125Z --out <new dir>

# tests (stdlib + pytest; synthetic only; keep it small on the shared host)
python3 -I -m pytest -p no:cacheprovider sim/temperature sim/waveform

# analysis, one klt sim report per request (new outdir each time)
python3 -I sim/temperature/analyze.py rep_tt.json rep_ss.json rep_ff.json \
    --manifest <new dir>/provenance.json --outdir sim/temperature/results/<runid>
```

CI: `.github/workflows/temperature-offline.yml` runs
`python3 -I -m pytest -p no:cacheprovider sim/temperature/test_temperature.py`
(Python 3.12, pytest only; no PDK, klt, ngspice or batch credentials).

The test file is named `test_temperature.py` rather than `test_harness.py` so
one pytest session can collect `sim/temperature` and `sim/waveform` together
(identical basenames in two package-less directories clash under pytest's
default import mode); both harness modules are imported under unique names for
the same reason.

## Grid and held codes

- Temperature axis (fixed): **-40, -27.5, -15, -2.5, 10, 22.5, 27, 35, 47.5,
  60, 72.5, 85 C**. Processes `tt, ss, ff`, supply 3.3 V, no added clk
  capacitance (`--load-f` is not offered; a non-zero load is refused).
  **36 unique points**, emitted as three process-specific requests of 12
  temperature corners each (`request_t12_{tt,ss,ff}.json`): a `klt sim` corner
  carries library sections and temperature only, so trim code and supply are
  baked into each bench (`tb_t12_<proc>.spice`).
- Calibration: `--cal-run sim/pvt/results/20260923T030125Z`, the ratified
  48 MHz target (`calibration_spec_target`). Held per-process codes **tt 0xA3,
  ss 0xCD, ff 0x59** at every temperature; nothing is recalibrated at interior
  points and no surrogate code is used. Validation is
  `sim/waveform/prepare.py`'s `load_calibration` (committed file, in-range and
  unsaturated codes, campaign rows hold the same code status ok at all nine
  T/V points, manifest and results.csv sha256, committing hash); on top of it
  `prepare.py` refuses any other run id, a calibration manifest `git_sha`
  other than `ed26786191202a85a71b6938563c45a1eaaa5582`, a dirty calibration
  tree, or codes other than the three above.
  `sim/pvt/results/20260923T030905Z` is a delay probe (`delay_probe.py`), not a
  replacement calibration; the loader rejects it.
- Reuse: DUT extraction (`dut_block`), bench (`tb_text`), request (`request`)
  and solver defaults (`_cfg_from`: 1 us ramp, 20 us transient, 2 us steady
  window, 200 ps step/max step, reltol 1e-3, abstol 1e-12 A, vntol 1e-6 V) come
  from `sim/waveform/prepare.py`; per-corner frequency and its failure
  semantics from `sim/waveform/analyze.py`. The waveform harness, its 27-point
  grid, its `--probe` validation (off-grid temperatures still rejected) and the
  historical PVT axes are unchanged; this coordinator passes its own
  temperature list to the request builder.

## Manifest (`provenance.json`, NOT evidence)

Per request and per corner (all 36): temperature, process, supply, load, held
code, calibration run id and directory, target, solver settings, and sha256 of
the generated request, bench netlist and extracted DUT. Also: the calibration
source block (as above), the sha256 of the two reused waveform modules, and
the **current design revision recorded separately** from the calibration's
`git_sha` (`design_revision.head`, `design_last_change_commit`, whether the
calibration commit object is available locally). Generation refuses a dirty
`design/` tree.

**Schematic equivalence is `UNVERIFIED`.** The calibration manifest's
`git_sha` (`ed26786...`) is not present in this repository's history (the run
was committed in `7383d62`). Between `7383d62` and the base of this work
(`e84aff2`) no schematic, symbol or netlist under `design/` changed (`git diff`
shows only three added netlist-consistency check files), but the revision the run actually
simulated cannot be inspected, so the hash is not proof that the DUT matches
the schematic the codes were calibrated on.
Before measured execution, verify the DUT against that revision or regenerate
the calibration for the actual schematic and cite a new immutable run. The
analyzer copies this status into every result.

## Analysis definitions (analyze.py)

Per process, on the 12-point axis, normalised to the **freshly measured 27 C
frequency `f27` of the same process and code**:

- raw adjacent difference `f[i+1]-f[i]` (Hz) and `1e6*(f[i+1]-f[i])/f27` (ppm of f27);
- adjacent slope `1e6*(f[i+1]-f[i])/(f27*(T[i+1]-T[i]))` (ppm/C), endpoint slope
  `1e6*(f(85)-f(-40))/(f27*125)`;
- curvature residual `1e6*(f(T)-f_linear(T))/f27` (signed ppm), `f_linear` the
  piecewise-linear interpolation of the newly measured -40/27/85 C anchors
  (segments -40..27 and 27..85); maximum absolute residual and its temperature.
- Tolerance **100 ppm of f27, diagnostic, not a spec**. An adjacent difference
  above +100 ppm is rising, below -100 ppm falling, otherwise flat (exactly
  100 ppm is flat). Monotonicity from the set of non-flat signs: none -> flat,
  only rising -> monotone increasing, only falling -> monotone decreasing,
  both -> nonmonotone. A residual with |r| > 100 ppm is flagged
  `EXCEEDS_TOLERANCE`; exactly 100 ppm is inside. A measured campaign must
  first establish numerical convergence before this tolerance is read as
  physical evidence.

Status per process: `COMPLETE` (all 12 valid), `INCOMPLETE` (a missing
report or row, failed waveform/corner, missing 27 C or endpoint anchor,
non-finite / zero / negative frequency) or `INVALID` (duplicate point,
off-grid temperature, report whose netlist or DUT sha256 does not match the
manifest, corner from the wrong process, second report for one request).
Only `COMPLETE` produces a monotonicity class or curvature verdict; otherwise
both read `NOT EVALUATED`. Valid rows are kept as diagnostics, but intervals
and residuals are computed only where their own endpoints/anchors are valid -
nothing is interpolated across missing data. The manifest itself is checked
against the fixed campaign definition (grid, codes, calibration run, target).
Output directories are never overwritten. Exit status is 0 only when every
process is `COMPLETE`.

## Deferred measured campaign (not part of this issue's acceptance)

Execution must go through `klt sim --backend batch`; do not replace it with
local multi-corner ngspice loops. It needs a compatible batch runner:
2AMLogic/klayout-tools#2851 was OPEN on 2026-10-10, and the startup campaign
recorded a runner/client klt version mismatch (`sim/startup/batch-attempts/`).
Before the 36-point submission: demonstrate compatible client/runner versions
with a successful single-corner batch preflight, resolve the schematic
equivalence above, record failed submissions, tool/PDK revisions (coordinate
with #65) and time-step/tolerance convergence evidence, and keep immutable
dated results under `sim/temperature/results/<runid>/`.

## Why DR-0021 / the discipline plant is not updated

No interior point has been measured, so there is nothing to update with. The
discipline plant (`sim/discipline/README.md`) stays based on the three
committed temperatures. Even a measured fixed-code curve would not by itself
establish a code-independent temperature gain (an assumption that README
documents and bounds at 0.95-1.24 % from the 0x80 vs 0xA3 grids). Replacing
`g_p(T,V)` needs an explicit validated assumption and must preserve the
existing voltage grid and post-layout plants: separate follow-up work. A
decision record is warranted only if measured interior excursions materially
change the documented margin; no ratified row or spec is relaxed.
