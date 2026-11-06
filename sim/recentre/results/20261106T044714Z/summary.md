# P3 27-point confirmation: batch run COMPLETED (27 of 27 corners measured)

Requests `sim/recentre/p3/request_{tt,ff,ss}.json` (3 x 9 corners), submitted 2026-11-06 with
`KLT_SIM_BACKEND=batch klt sim sim/recentre/p3/request_<p>.json -o out_<p> --format json`
from client `klt 0.9.2.dev42+g94b54d114210`. Reports `report_<p>.json`, client stderr `stderr_<p>.txt`,
receipts `out_<p>/batch-receipt.json`. No ngspice grid was run locally.

| request | batch job id | report status | corners passed |
|---|---|---|---|
| tt | `klt-sim-ed85f6213b57` | pass | 9 of 9 |
| ff | `klt-sim-4cc6809679de` | pass | 9 of 9 |
| ss | `klt-sim-8a59154d5f31` | pass | 9 of 9 |

The earlier failures (runner version mismatch, missing gf180mcuC PDK) are gone. Several corners carry a
`nonconvergence` warning ("Dynamic gmin stepping failed", 4/5/6 corners in tt/ff/ss); all measurements
still returned and every corner is `pass`.

Frequency f = 20 / (t25 - t5) of the rising edges 5 and 25; grid produced by
`python3 -I sim/recentre/report_range.py sim/recentre/results/20261106T044714Z`.
Trim codes: tt 0xA9, ff 0x59, ss 0xD7 (27 C / 3.3 V calibration, DR-0023). Target 48 MHz.

| proc | VDD | T (C) | status | f(0x00) MHz | f(0xFF) MHz | f(cal) MHz | cal err % | range ok | ratified range ok | acc ok |
|---|---|---|---|---|---|---|---|---|---|---|
| tt | 3.0 | -40 | pass | 26.697 | 71.258 | 46.208 | -3.73 | yes | yes | yes |
| tt | 3.0 | 27 | pass | 28.074 | 71.862 | 47.371 | -1.31 | yes | yes | yes |
| tt | 3.0 | 85 | pass | 29.313 | 74.123 | 48.698 | +1.45 | yes | NO | yes |
| tt | 3.3 | -40 | pass | 26.831 | 72.355 | 46.843 | -2.41 | yes | yes | yes |
| tt | 3.3 | 27 | pass | 28.207 | 73.582 | 48.060 | +0.13 | yes | yes | yes |
| tt | 3.3 | 85 | pass | 29.295 | 74.868 | 49.041 | +2.17 | yes | NO | yes |
| tt | 3.6 | -40 | pass | 26.849 | 71.433 | 47.057 | -1.96 | yes | yes | yes |
| tt | 3.6 | 27 | pass | 28.289 | 74.293 | 48.486 | +1.01 | yes | yes | yes |
| tt | 3.6 | 85 | pass | 29.314 | 75.483 | 49.364 | +2.84 | yes | NO | yes |
| ff | 3.0 | -40 | pass | 34.472 | 83.612 | 45.930 | -4.31 | yes | NO | yes |
| ff | 3.0 | 27 | pass | 36.735 | 91.462 | 48.192 | +0.40 | yes | NO | yes |
| ff | 3.0 | 85 | pass | 40.006 | 102.826 | 51.941 | +8.21 | yes | NO | NO |
| ff | 3.3 | -40 | pass | 33.988 | 74.804 | 45.373 | -5.47 | yes | NO | yes |
| ff | 3.3 | 27 | pass | 36.524 | 89.291 | 48.092 | +0.19 | yes | NO | yes |
| ff | 3.3 | 85 | pass | 38.950 | 99.443 | 50.772 | +5.78 | yes | NO | yes |
| ff | 3.6 | -40 | pass | 32.496 | 67.487 | 43.500 | -9.37 | yes | NO | NO |
| ff | 3.6 | 27 | pass | 36.060 | 84.272 | 47.613 | -0.81 | yes | NO | yes |
| ff | 3.6 | 85 | pass | 38.238 | 95.628 | 49.985 | +4.14 | yes | NO | yes |
| ss | 3.0 | -40 | pass | 21.157 | 57.747 | 46.467 | -3.19 | yes | NO | yes |
| ss | 3.0 | 27 | pass | 22.205 | 57.656 | 46.649 | -2.82 | yes | NO | yes |
| ss | 3.0 | 85 | pass | 23.023 | 58.113 | 47.002 | -2.08 | yes | NO | yes |
| ss | 3.3 | -40 | pass | 21.360 | 60.231 | 48.010 | +0.02 | yes | NO | yes |
| ss | 3.3 | 27 | pass | 22.391 | 59.989 | 48.129 | +0.27 | yes | NO | yes |
| ss | 3.3 | 85 | pass | 23.166 | 60.160 | 48.321 | +0.67 | yes | NO | yes |
| ss | 3.6 | -40 | pass | 21.501 | 61.977 | 49.107 | +2.31 | yes | NO | yes |
| ss | 3.6 | 27 | pass | 22.536 | 61.791 | 49.277 | +2.66 | yes | NO | yes |
| ss | 3.6 | 85 | pass | 23.284 | 61.792 | 49.389 | +2.89 | yes | NO | yes |

* points: 27; 48 MHz inside [f(0x00), f(0xFF)]: 27/27; covers ratified 28.8-67.2 MHz: 6/27; post-trim error inside +8/-9 %: 25/27
* tt (code 0xA9): worst error -3.73 % / +2.84 %
* ff (code 0x59): worst error -9.37 % / +8.21 %
* ss (code 0xD7): worst error -3.19 % / +2.89 %

## Reading

* **Trim range reaches 48 MHz at every point (27/27)**: f(0x00) <= 48 MHz <= f(0xFF) at all PVT points
  (lowest f(0xFF) is 57.656 MHz at ss/27 C/3.0 V; highest f(0x00) is 40.006 MHz at ff/85 C/3.0 V).
* **Ratified trim window 28.800-67.200 MHz is covered at only 6 of 27 points** (tt at -40/27 C, all
  VDD; the "ratified range ok" column). It fails at the low end (f(0x00) > 28.8 MHz) at tt/85 C and at
  all ff points, and at the high end (f(0xFF) < 67.2 MHz) at all ss points and ff/3.6 V/-40 C.
  DR-0023 sized the range at tt/27 C/3.3 V only (28.203 / 73.524 MHz, extracted); this grid is the full-PVT
  picture, and the ratified window is not relaxed here. The window is a spec row, so whether it is
  meant to hold at every PVT point is a decision for the spec owner, not this evidence.
* **Post-trim error with one code per process**: tt -3.73 / +2.84 %, ss -3.19 / +2.89 %, ff -9.37 / +8.21 %.
  Inside the ratified +8 % / -9 % at 25 of 27 points; the two misses are both ff
  (ff/-40 C/3.6 V -9.37 %, ff/85 C/3.0 V +8.21 %), matching the six-probe numbers in DR-0023
  (-9.41 % / +8.16 %, within 0.05 points). The ratified +/-1.1 % row is a calibration-point
  quantity and is covered by DR-0023, not by this grid.
