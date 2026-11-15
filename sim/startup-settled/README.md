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

## Comparator-H mirror-load L 0.7 um rebuild (issue #346, DR-0039/DR-0042)

Same bench, DUT replaced by the rebuilt-layout extraction
`sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice`
(sha256 `01e06daeb8cf341189207770f982c32a4b288b3bca504614262353ef324d16a1`) at the DR-0029 calibration code 0xA4
(trim bits 2, 5, 7 ramp; `gen_requests.py --out sim/startup-settled/l07/ --code 0xA4 --dut ...`, requests in
`sim/startup-settled/l07/`), batch jobs `klt-sim-4d3ab740fc79` (3.0 V), `klt-sim-a4d9b66d2086` (3.3 V),
`klt-sim-948c39ec8591` (3.6 V); receipts and reports in `results/20261114T221218Z/batch/`, analysis in
`results/20261114T221218Z/`: **63/63 points start and settle within the 10 us DR-0020 bound, 0 NON-START**,
worst primary-band settle 0.947 us (fs / -40 C / 3.0 V). The two `0xA9` runs above stay as the evidence for that
code; the run's `manifest.json` records the actual DUT path, its sha256 and the trim code (`settled_report.py
--dut --code`, fixing the hardcoded-provenance defect that misstated the 0735Z manifest's DUT).
