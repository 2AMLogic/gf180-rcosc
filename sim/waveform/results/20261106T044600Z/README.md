# Waveform campaign (issue #213) - run 20261106T044600Z

Informational evidence, **not ratified**. First measured clk pulse-width /
duty / rise-fall / period-spread results for the 27-point grid prepared by
`sim/waveform/prepare.py` (#91). The earlier preflight failure record
`../20261104T182047Z/` is untouched.

## Provenance

| Field | Value |
|---|---|
| Date | 2026-11-06 (UTC), batch fleet only (`--backend batch`); nothing ran locally |
| Client `klt` | `0.9.2.dev42+g94b54d114210` (commit `94b54d1142107ad2e8c765a2195afaa3b656e93a`) |
| Runner `klt` | `0.9.0`, `runner_compatibility: match` |
| Runner image / fleet | `ami-095c25ae241a4d360`, aws-batch-fleet us-east-1, m7i.4xlarge spot |
| Simulator | ngspice-46, binary sha256 `dc859418...cc60` |
| PDK | gf180mcuC, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (runner `stamp_text`; client reports the same revision) |
| Model deck | `sm141064.ngspice`, sha256 `f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24` |
| Benches | unmodified copies of the committed `sim/waveform/` benches/requests; trim code per process from `sim/pvt/results/20260923T030125Z` (tt `0xA3`, ss `0xCD`, ff `0x59`), unloaded |
| Default solver settings | max step/print step 200 ps, reltol 1e-3, abstol 1e-12, vntol 1e-6, 20 us transient, 2 us analysis window |

Layout: `preflight/` (v33_tt, 1 job), `grid/` (other 8 requests, `--batch-set`,
8 jobs), `analysis/` (`analyze.py` output for all 27 points),
`convergence/` (1 job + its analysis), `noise/` (trnoise smoke test).
Each directory has the klt envelope (`submit.json`), `stderr.txt` and the
`batch-receipt.json` with job ids. Jobs: preflight `klt-sim-2a8309a6a73f`;
grid `klt-sim-547053932e84` (v30_ff), `-267a55bf6a8a` (v30_ss),
`-bb8b1b3a0e08` (v30_tt), `-13b40f52bc85` (v33_ff), `-9389c50ccd6f` (v33_ss),
`-a3c41690ed6d` (v36_ff), `-8f2d479015d8` (v36_ss), `-b926efdc1341` (v36_tt);
convergence `klt-sim-24afedd86c47`; noise smoke `klt-sim-858211387aa8`.

Waveform bytes (56 files, ~345 MB) are in the artifact store, not git:
`manifests/artifacts/waveform-20261106T044600Z.manifest.json` (fetch with
`klt artifact get <manifest>#<name>`). The `waveform` paths inside the
committed reports are the absolute scratch paths of the run host; the
manifest `name`s are the logical paths under this directory.

## Per-point status (27 points)

26 points were measured and analysed (`OK`). One point was simulated but
**the analyzer refused it**:

| Point | Status | Cause |
|---|---|---|
| ff / 85 C / 3.6 V | simulated, `analyze.py` FAIL: "transition end (90/10 % level) not in waveform" | the last rising 50 % crossing is at 19.99978 us, 22 ps before the 20 us end of the run, so its 90 % level is not in the data. An end-of-window truncation of the analyzer, not a circuit finding. No number is reported for this point; the harness was not changed. |

Batch submissions: 9 of 9 requests passed (27 of 27 corners `pass`), none
refused, none errored.

## Results table

`analysis/summary.md` (and `analysis/results.csv`) is the full 27-row table.
Ranges over the 26 measured points, default solver settings:

| Quantity | Min | Max |
|---|---|---|
| Mean period | 19.716 ns (ff/85/3.0) | 21.973 ns (ss/-40/3.0) |
| Mean frequency (1/mean period) | 45.51 MHz (ss/-40/3.0) | 50.72 MHz (ff/85/3.0) |
| High pulse (50 %) | 1.545 ns (ff/85/3.0) | 2.461 ns (ss/-40/3.6) |
| Low pulse (50 %) | 17.72 ns (ss/85/3.6) | 20.29 ns (ff/-40/3.0) |
| Duty (high/period) | 0.0730 (ff/-40/3.0) | 0.1171 (ss/85/3.6) |
| Rise 10-90 % | 607.5 ps (ff/-40/3.6) | 1222 ps (ss/85/3.0) |
| Fall 90-10 % | 359.1 ps (ff/-40/3.3) | 518.1 ps (ss/85/3.0) |
| Period peak-to-peak (deterministic) | 28.1 ps (ss/85/3.3) | 575.5 ps (ff/-40/3.6) |
| Max abs cycle-to-cycle (deterministic) | 19.0 ps (ss/85/3.3) | 404.5 ps (ff/-40/3.6) |

The clk output is a narrow positive pulse (duty about 7-12 %), not a
50 % square wave. Frequencies are with the code held per process at every
T/V point (no recalibration), so this is the post-trim PVT spread, not a
spec check.

## Convergence (one corner, one refinement)

tt / 27 C / 3.3 V rerun with max step and print step 50 ps, reltol 1e-4,
abstol 1e-13, vntol 1e-7 (`convergence/`; the committed benches were not
touched):

| Metric | Default | Tight | Change |
|---|---|---|---|
| Mean period | 20.7811 ns | 20.7036 ns | -0.37 % |
| High pulse | 1.97441 ns | 1.93643 ns | -1.92 % |
| Duty | 0.095008 | 0.093531 | -1.55 % |
| Rise 10-90 % | 859.1 ps | 830.6 ps | -3.3 % |
| Fall 90-10 % | 410.9 ps | 326.2 ps | **-20.6 %** |
| Period peak-to-peak | 159.9 ps | 7.1e-7 ps | -100 % |
| Max abs cycle-to-cycle | 143.2 ps | 5.96e-7 ps | -100 % |

Reading: at default settings, period/pulse-width means moved by 0.4-2 %, the
fall time by 21 % and the period spread **vanished** (to ~1e-6 ps). So the
deterministic spread and cycle-to-cycle columns in the grid are solver
artifacts of the default settings, not oscillator behaviour, and the fall
times are not converged. One refinement of one corner shows sensitivity; it is
not an order-of-convergence study, and the other 26 points were not repeated
at tight settings.

## Noise support

See `noise/`. `trnoise` on an independent source runs under `klt sim`
(batch): RC smoke test, job `klt-sim-858211387aa8`, v(out) rms 0.786 mV.
That shows the source works, nothing about noise of the gf180mcu devices in
the oscillator. No noise source was added to the DUT and **no RMS jitter
number is claimed**. The first attempt (`noise/attempt1-missing-param-preamble/`)
failed on my staging error (the netlist lacked the `.param ... fnoicor=0`
preamble every bench carries); only the second counts.
