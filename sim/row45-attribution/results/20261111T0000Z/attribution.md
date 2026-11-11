# Row 4 / row 5 cause attribution (generated; source sim/item5/results/20261106T071555Z, code 0xA4)

| process | f(27C,3.3V) MHz | process offset vs 48 MHz | supply term (3.0 / 3.6 V) | temp term (-40 / 85 C) |
|---|---|---|---|---|
| tt | 47.89 | -0.2 % | -1.90 / +1.55 % | -2.43 / +2.12 % |
| ff | 61.77 | +28.7 % | -0.96 / +1.01 % | -2.83 / +4.98 % |
| ss | 38.24 | -20.3 % | -2.35 / +1.92 % | -2.31 / +1.73 % |
| fs | 48.62 | +1.3 % | -0.69 / +1.07 % | -3.32 / +5.66 % |
| sf | 47.02 | -2.0 % | -1.71 / +1.35 % | -2.54 / +1.65 % |
| rc_f | 59.71 | +24.4 % | -1.33 / +1.35 % | -2.94 / +6.54 % |
| rc_s | 39.73 | -17.2 % | -1.83 / +1.51 % | -2.38 / +1.63 % |

| basis | row 4 in-window (27 C) | worst | row 5 in-window (-40..85 C) | worst |
|---|---|---|---|---|
| fixed code 0xA4, as graded (DR-0029) | 7/21 | 29.99 % | 26/63 | 37.33 % |
| L1: supply term removed exactly (row 4); L2: temperature term removed exactly (row 5) | 9/21 | 28.69 % | 27/63 | 29.99 % |
| process offset removed too (each die at its own 27 C / 3.3 V frequency; DR-0017 basis, NOT the fixed-code ruling) | 21/21 | 2.35 % | 63/63 | 8.57 % |

Row 5 under L2 keeps the supply term, so its idealised window check is `f(proc, 27 C, V)`.

