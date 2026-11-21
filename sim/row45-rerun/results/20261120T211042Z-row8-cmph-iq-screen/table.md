# Row-8 comparator-H current screen (issue #458, DR-0046 lever)

Campaign `20261120T211042Z-row8-cmph-iq-screen`; DUTs from `gen_row8_screen.py dut` on the DR-0044 extraction (`results/20261112T200335Z-extract-l07`, sha256 `01e06dae...d16a1`).
Iq = DR-0009 charge integral over clk rising edges 5..25; frequency reference 48.000 MHz.
Codes: control per DR-0043 (`20261112T201500Z-calib-extracted-l07`), variants per this campaign's calib scans (nearest 48 MHz at 27 C / 3.3 V).

## Running Iq vs the 500 uA row-8 limit (worst cell named)

| variant | worst Iq @ cal code (uA, cell) | n>=500 | worst Iq @ 0xFF (uA, cell) | n>=500 |
|---|---|---|---|---|
| control | 505.4 (ff/85C/3.6V) | 1 | pending | 0 |
| tail x0.85 | 385.4 (ff/85C/3V) | 0 | 726.1 (ff/85C/3.6V) | 8 |
| tail x0.70 | pending | 0 | pending | 0 |
| tail x0.55 | pending | 0 | pending | 0 |
| tail x0.40 | 390.3 (ff/85C/3.6V) | 0 | 364.7 (tt/85C/3V) | 0 |
| load L 0.6 | pending | 0 | pending | 0 |
| tail x0.70 + load L 0.6 | pending | 0 | pending | 0 |

## Row 4 (supply span at 27 C, calibrated code; window -2.9 / +2.0 % vs 48 MHz)

| variant | tt low/high (%) | ff low/high (%) | ss low/high (%) | verdict |
|---|---|---|---|---|
| control | -2.12 / +1.37 | -1.13 / +0.85 | -3.30 / +2.80 | FAIL |
| tail x0.85 | +nan / +nan | -1.78 / -1.78 | +nan / +nan | FAIL |
| tail x0.70 | +nan / +nan | +nan / +nan | +nan / +nan | FAIL |
| tail x0.55 | +nan / +nan | +nan / +nan | +nan / +nan | FAIL |
| tail x0.40 | +nan / +nan | -2.00 / +0.43 | +nan / +nan | FAIL |
| load L 0.6 | +nan / +nan | +nan / +nan | +nan / +nan | FAIL |
| tail x0.70 + load L 0.6 | +nan / +nan | +nan / +nan | +nan / +nan | FAIL |

## Row 5 (held calibration code over T; window -10.8 / +8.8 % vs 48 MHz)

| variant | worst cold cell (%) | worst hot cell (%) | ff/85C/3.0V (%) | verdict |
|---|---|---|---|---|
| control | -4.47 (ff/3V) | +3.05 (ss/3.6V) | +1.58 | pass |
| tail x0.85 | -5.06 (ff/3V) | +102.35 (ff/3.6V) | +0.63 | FAIL |
| tail x0.70 | pending | | | |
| tail x0.55 | pending | | | |
| tail x0.40 | -5.05 (ff/3V) | +44.87 (tt/3V) | +0.12 | FAIL |
| load L 0.6 | pending | | | |
| tail x0.70 + load L 0.6 | pending | | | |

## Row 10 (lost clock over the held-code temperature sweep)

| variant | cells with no clock (fosc < 1 MHz or failed) |
|---|---|
| control | 0 |
| tail x0.85 | 0 |
| tail x0.70 | 0 |
| tail x0.55 | 0 |
| tail x0.40 | 0 |
| load L 0.6 | 0 |
| tail x0.70 + load L 0.6 | 0 |

## Comparator-H delay at the ff held code (threshold crossing -> comparator output edge)

| variant | 3.0V/85C (ns) | 3.0V/-40C (ns) | 3.6V/85C (ns) | d(3.0V/85C) vs control |
|---|---|---|---|---|
| control | 1.75 | 2.02 | 1.80 | +0.00 |
| tail x0.85 | missing | | | |
| tail x0.70 | missing | | | |
| tail x0.55 | missing | | | |
| tail x0.40 | missing | | | |
| load L 0.6 | missing | | | |
| tail x0.70 + load L 0.6 | missing | | | |

## Startup at fs / -40 C (1 us ramp, held tt code; bound 10 us)

| variant | code | 3.3V first edge (us) | 3.6V first edge (us) | verdict |
|---|---|---|---|---|
| control | 0xA4 | 0.60 | 0.59 | pass |
| tail x0.85 | 0xA4 | None | None | FAIL |
| tail x0.70 | 0xA8 | None | None | FAIL |
| tail x0.55 | 0xA8 | None | None | FAIL |
| tail x0.40 | 0xAC | None | None | FAIL |
| load L 0.6 | 0xA4 | None | None | FAIL |
| tail x0.70 + load L 0.6 | 0xA8 | None | None | FAIL |
