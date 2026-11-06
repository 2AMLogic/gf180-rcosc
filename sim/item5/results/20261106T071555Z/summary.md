# Item 5 corner campaign re-run: comparator-H-fixed netlist at the re-centred calibration code 0xA4 (DR-0029)

Requests `sim/item5/requests/request_c<code>_v<VDD*10>.json` (codes 0x00, 0x80, 0xA4, 0xA5, 0xFF x 3 supplies x 7 process
x 3 temperature corners = 315 points), regenerated with `python3 -I sim/item5/gen_requests.py` (DUT
`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, DR-0028; calibration code 0xA4, DR-0029) and submitted 2026-11-06 as
`KLT_SIM_BACKEND=batch klt sim sim/item5/requests/request_<tag>.json -o out_<tag> --format json` (one request at a
time, `klt 0.9.2.dev33+g684a7569e857` client). Every envelope carries `environment.remote` (job ids `klt-sim-*`) and a
`batch-receipt.json`. All 15 submits succeeded; no ngspice grid was run locally and no batch-submit failure occurred.

## Envelope status

| supply | envelopes | status |
|---|---|---|
| 3.0 V | 5 | all `pass`, 21 of 21 corners |
| 3.3 V | 5 | 4 `pass`; `ca4_v33` `fail` (1 corner over the Iq < 500 uA limit) |
| 3.6 V | 5 | 4 `pass`; `ca4_v36` `fail` (3 corners over the Iq < 500 uA limit) |

Every one of the 315 points returned a frequency (0 no-clock points, including fs / -40 C), confirming the DR-0028
fix carries into the campaign. The two `fail` envelopes are the row-8 Iq limit at ff corners, not a missing clock.

## Per-row verdicts (`python3 -I sim/item5/report_rows.py sim/item5/results/20261106T071555Z`, see `rows.md`)

Row 1 **passes**: f(0xA4) = 47.886 MHz (-0.24 %) at tt / 27 C / 3.3 V, inside the ratified +/-1.1 %. Rows 7 and 10 pass.
Rows 2, 4, 5 and 8 FAIL, as on the pre-re-centre netlist (the held-code process spread, the 0.539 %/code LSB step and
559.4 uA at ff/85 C/3.6 V are not calibration-code effects). Rows 4/5 at the chosen code: 7/21 and 26/63 points inside the
ratified windows; the held-code 0xA5 neighbour gives the same 7/21 and 26/63 with a slightly larger worst error
(+30.75 % / +37.91 % against +29.99 % / +37.33 %), so it is not clearly better. Nothing in the ratified spec is relaxed.
