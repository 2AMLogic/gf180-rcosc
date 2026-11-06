# Item 5 corner campaign: 15 batch envelopes on the settled netlist (P3, DR-0023)

Requests `sim/item5/requests/request_c<code>_v<VDD*10>.json` (5 trim codes x 3 supplies x 7 process x 3 temperature
corners = 315 points), submitted 2026-11-06 as
`KLT_SIM_BACKEND=batch klt sim sim/item5/requests/request_<tag>.json -o out_<tag> --format json`
from client `klt 0.9.2.dev33+g684a7569e857`; runner `klt 0.9.0`, `gf180mcuC`, ngspice-46 (per-envelope
`environment.remote`, receipts `out_<tag>/batch-receipt.json`). No ngspice grid was run locally. DUT:
`sim/recentre/p3/rcosc_top_p3.spice`, byte-for-byte (the netlist `sim/recentre/results/20261106T044714Z` measured).
Calibration code 0xA9 (tt, DR-0023) is held across all process corners; no per-die recalibration.

## Envelope status

| supply | envelopes | status |
|---|---|---|
| 3.0 V | 5 | all `pass`, 21 of 21 corners |
| 3.3 V, 3.6 V | 10 | all `error`: 1 corner errored in each, **fs / -40 C** (the other 20 corners returned) |

## Finding: fs / -40 C / VDD >= 3.3 V does not oscillate in this bench

At fs/-40 C the DC operating point does not converge ("Dynamic gmin stepping failed") and `clk` stays at
about 16 uV for the whole 1200 ns window (Iq reads 463 uA at code 0xA9), so edges 5 and 25 never occur and
`fosc` has no value. It is code-independent (0x00, 0x80, 0xA9, 0xAA, 0xFF all fail) and absent at 3.0 V.
Two single-corner local probes (one ngspice process each, not a grid) reproduced it: the step-supply bench
at the same corner, and a 1 us ramped supply with trim bits ramping with it (`clk` flat at 16 uV over
1.5-3 us after one early edge at ~685 ns). Whether this is a real start-up failure of the P3 design at that corner or a
simulator artifact is open; it is filed as #227 and is **not** worked around here (no `.ic`, no relaxed
bench). Several other corners carry a `nonconvergence` warning but return all measurements.

## Per-row verdicts (`python3 -I sim/item5/report_rows.py sim/item5/results/20261106T051832Z`)

| Row | Verdict | Binding corner | Evidence |
|---|---|---|---|
| 1 | pass | tt/27C/3.3V | f(0xA9) = 48.048 MHz (+0.10 %) vs 48.000 MHz; ratified calibration tolerance +/-1.1 % (DR-0023 re-derives it at the calibration point) |
| 2 | FAIL | tt/27C/3.3V | f(0x00) = 28.202 MHz (needs <= 28.800), f(0xFF) = 73.502 MHz (needs >= 67.200), LSB 0xA9->0xAA = 0.501 %/code (ratified 0.314 %/code); Monte Carlo remainder (claim S1) is a declared gap |
| 3 | pass | ff/27C/3.3V | 0x80 at 27 C / 3.3 V vs tt: tt +0.0 %, ff +26.7 %, ss -19.6 %, fs -11.0 %, sf -0.8 %, rc_f +26.0 %, rc_s -17.8 % (ratified +/-35 %) |
| 4 | FAIL | fs/27C/3.6V | one code (0xA9) held across 7 process corners: 7/21 points inside -2.9 %/+2.0 %; largest |error| -35.83 % at fs/27 C/3.6 V; per-die recalibration is NOT modelled here (see sim/recentre per-process-code grid); Monte Carlo remainder (claim S2/S3) is a declared gap |
| 5 | FAIL | fs/-40C/3V | one code (0xA9) held across 7 process corners: 22/63 points inside -10.8 %/+8.8 %; largest |error| -44.63 % at fs/-40 C/3 V; 2 point(s) returned no frequency; per-die recalibration is NOT modelled here (see sim/recentre per-process-code grid); Monte Carlo remainder (claim S2/S3) is a declared gap |
| 7 | FAIL | fs/-40C at 3.3 V and 3.6 V | 10 (code, VDD, process, T) points returned no frequency, in 10 of 15 envelopes; all at fs/-40C/3.3V, fs/-40C/3.6V |
| 8 | FAIL | ff/85C/3.6V (code 0xA9) | max iq_run_ua = 576.2 uA over 63 measured calibration-code (0xA9) points (limit < 500 uA); window is the fixed 200-1200 ns, not whole periods |
| 10 | FAIL | fs/-40C at 3.3 V and 3.6 V | temperature axis -40/27/85 C present in every request; 10 (code, VDD, process, T) points returned no frequency, in 10 of 15 envelopes; all at fs/-40C/3.3V, fs/-40C/3.6V |
| 6 | declared gap | n/a | reserved, not designed (DR-0004) |
| 9 | declared gap | n/a | startup bench not re-run on the settled netlist (see ROWS.md) |

Rows 1 and 3 pass; rows 2, 4, 5, 7, 8 and 10 fail on the settled netlist. Row 2: both nominal range ends pass
(28.202 / 73.502 MHz against 28.8 / 67.2 MHz); the failing part is the LSB step, 0.501 %/code against the
ratified 0.314 %/code (DR-0023 reports the same 0.50 %/code). Rows 4 and 5 fail because one code is held across
process corners (the per-process-code picture is `sim/recentre/results/20261106T044714Z`). Row 8: 576.2 uA at
ff/85 C/3.6 V at the tt code (DR-0023 measured 415 uA at ff's own calibration code). Rows 7 and 10 fail on the
fs/-40 C finding above. Nothing in the ratified spec is relaxed.
