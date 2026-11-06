# Startup-time bench on the settled netlist (issue #227, item-5 row 9)

`sim/startup/` targets the pre-re-centre schematic at trim code 0xA3 and is owned by issue #82. This
directory runs the **same stimulus and the same DR-0020 analysis** on the settled P3 netlist
(`sim/recentre/p3/rcosc_top_p3.spice`, DR-0023) at its calibration code 0xA9, so item 5 row 9 has evidence on
the netlist the other rows use. `sim/startup/` is not modified.

| file | role |
|---|---|
| `gen_requests.py` | writes `tb_v{30,33,36}.spice`, `request_v{30,33,36}.json`, and the DUT copy (7 process x 3 T = 21 corners per supply, 63 points) |
| `settled_report.py` | post-processes the three reports with `startup_report.analyse` (read-only import) into `results/<runid>/` |
| `results/<runid>/` | `summary.md`, `results.csv`, `manifest.json`, `batch/` (reports and batch receipts) |

## Run

```
python3 -I sim/startup-settled/gen_requests.py
for v in 30 33 36; do KLT_SIM_BACKEND=batch klt sim sim/startup-settled/request_v$v.json -o OUT/v$v --format json > OUT/report_v$v.json; done
python3 -I sim/startup-settled/settled_report.py OUT/report_v30.json OUT/report_v33.json OUT/report_v36.json --vdd 3.0 3.3 3.6 --artifacts-root OUT/v30 OUT/v33 OUT/v36
```

## Result (`results/20261106T061500Z/`)

Batch fleet jobs `klt-sim-8bfc88ec9089` (3.0 V), `klt-sim-077f87f7e2da` (3.3 V), `klt-sim-bc8b7ef559f9` (3.6 V).
**61/63 points pass the primary DR-0020 band; 2 are NON-START**: fs / -40 C at 3.3 V and 3.6 V (the finding of
#227; root cause in `sim/startup-fs-m40c/results/20261106T061000Z/summary.md`). Those two are recorded as
failures; the bench and bands are unchanged (design fix: #229). Worst settle time of the started points: 2.56 us (fs / 27 C / 3.0 V). The 63-point pre-re-centre campaign and DR-0020 status stay with
issue #82.

## Revised comparator-H stage (issue #229, DR-0028)

Same requests, DUT replaced by `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` (`gen_requests.py --dut`, requests in
`sim/cmph-fix/startup/`), batch jobs `klt-sim-829a270ff52b` (3.0 V), `klt-sim-58ef1d67a0ce` (3.3 V),
`klt-sim-4e366a98ed46` (3.6 V); receipts in `sim/cmph-fix/results/20261106T071000Z/`, analysis in
`results/20261106T0735Z/`: **63/63 points start and settle, 0 NON-START**, worst settle 1.54 us (limit 10 us).
The earlier `results/20261106T061500Z/` stays as the pre-fix evidence.
