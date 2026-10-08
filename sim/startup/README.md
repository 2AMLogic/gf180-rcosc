# Startup-time bench (issue #78)

Bench for the ratified row "Startup time <= 10 us to within trimmed accuracy"
(characterization report row 10). Band definition and bench assumptions:
[DR-0020](../../spec/decision-records/0020-startup-time-trimmed-accuracy-band-definition.md).

| file | role |
|---|---|
| `gen_requests.py` | writes `tb_v{30,33,36}.spice`, `rcosc_top_schematic.spice` (extracted from `design/netlist/pvt_tb.spice`) and `request_v{30,33,36}.json`; imports `PROCESS_CORNERS`/`TEMPS_C`/`VDDS_V` from `sim/pvt/pvt_sweep.py` (not re-typed) |
| `request_v*.json` | the `klt sim` corners requests: 7 process x 3 T = 21 corners each, one per supply (a PWL ramp source cannot take a `supply_v` alter) = 63 points total |
| `startup_report.py` | post-processes `klt sim` reports + waveforms into `results/<runid>/` (append-only; refuses to overwrite) |
| `results/<runid>/` | `summary.md`, `results.csv`, `manifest.json`, `edges.json.gz` (clk edge times in ns) |
| `batch-attempts/` | raw `klt sim` batch reports that failed (see below), kept as evidence of the attempt |

Stimulus: VDD (and the set trim bits) ramp 0 -> VDD linearly in 1 us from
t = 0; trim code 0xA3 held; 20 us transient, 200 ps step. Startup time is
measured from t = 0. Non-start is reported as `NON-START`, never as a blank.

## Run

```
python3 sim/startup/gen_requests.py
for v in 30 33 36; do klt sim sim/startup/request_v$v.json -o OUT/v$v --format json > OUT/report_v$v.json; done
python3 -I sim/startup/startup_report.py OUT/report_v30.json OUT/report_v33.json OUT/report_v36.json --vdd 3.0 3.3 3.6 --artifacts-root OUT/v30 OUT/v33 OUT/v36
```

`KLT_SIM_BACKEND=batch` sends each request to the Spot fleet. Do not hand-launch
ngspice grids; single-corner probes use `--backend local`.

## Status of the evidence

**The 63-point factorial has not been run.** All four batch submissions failed
before simulating anything (`batch-attempts/`):

- `klt 0.7.0` client: job `klt-sim-dc36ead70420` (v30), `klt-sim-8cfbc84880ad`
  (v33), `klt-sim-6ee7fb2db163` (v36): exit 87,
  `batch_runner_version_mismatch` -- the fleet runner image runs klt 0.5.0.
- `klt 0.6.0` client: job `klt-sim-69b745c69c5d` (v33): exit 1, "failed
  without a usable report".
- `klt 0.5.0` has no `batch` backend (`supported: local, local-parallel, remote`).

Per host policy the grid was not run locally as a fallback. What exists is two
single-corner local probes (`results/20261008T235538Z/`):
`ss`/-40 C/3.0 V (the expected slowest corner) and `tt`/27 C/3.3 V, both
started and settled well inside 10 us at every band. That is not a factorial
verdict. To complete the evidence, re-run the three requests once the fleet
runner image matches the client klt.
