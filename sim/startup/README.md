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

**The 63-point factorial has run** on the batch fleet (runner `eda-batch-runner`
v11, `ami-095c25ae241a4d360`, runner klt 0.9.0, client klt
`0.9.2.dev47+g581de87616d8`, `runner_compatibility: match`, PDK `gf180mcuC`,
open_pdks `f6eeac7`). Jobs `klt-sim-971dfc731fe7` (v30), `klt-sim-b591e450d02c`
(v33), `klt-sim-fbe71ced6e21` (v36); every unit passed at the simulator level.
Evidence: `results/20261106T052948Z/` (append-only).

**Measured verdict under the ratified DR-0020 definition: 61/63 PASS, 2 FAIL.**
Primary band +/-1.1% of the corner's final mean period (8-cycle windows),
<= 10 us from ramp start, trim `0xA3`. Worst settle time of the passing points
is 1.174 us (`ss`/-40 C/3.0 V). The two failures are `ff`/-40 C at 3.3 V and
3.6 V: they started (first edge 0.59 / 0.54 us) but the settled-tail check
(last 2 us steady to +/-0.5%) is not met -- measured tail period deviation
0.78% / 0.61% -- so no settle time is defined and the points are recorded as
FAIL, not as passes. The bench and the +/-0.5% tail tolerance were not
changed to make them pass. The same two points also fail the looser
diagnostic bands because the verdict path stops at the tail check.

A relative-settling pass does **not** imply a target-accurate or USB-ready
clock: settled frequencies span 35.6-66.7 MHz at fixed trim `0xA3` and are
graded against 48 MHz by the separate frequency / PVT-accuracy rows.

Earlier failed submissions are kept as evidence in `batch-attempts/`:

- `klt 0.7.0` client: jobs `klt-sim-dc36ead70420` (v30), `klt-sim-8cfbc84880ad`
  (v33), `klt-sim-6ee7fb2db163` (v36): exit 87, `batch_runner_version_mismatch`
  (runner image klt 0.5.0).
- `klt 0.6.0` client: job `klt-sim-69b745c69c5d` (v33): exit 1, no usable report.
- `klt 0.5.0` has no `batch` backend.
- Runner v10 (`ami-04591566329422a44`, runner klt 0.9.0): jobs
  `klt-sim-1410c9044c01`, `klt-sim-2b23c329351d`, `klt-sim-34c8f65a8ba2` failed
  in ~5 s, no `gf180mcuC` PDK on the image (fixed in v11).

Two local single-corner probes (`results/20261008T235538Z/`, `ss`/-40 C/3.0 V
and `tt`/27 C/3.3 V) pre-date the factorial and agree with it (1.174 us and
0.891 us at +/-1.1%).
