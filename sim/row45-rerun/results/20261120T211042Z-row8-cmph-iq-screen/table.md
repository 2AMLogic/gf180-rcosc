# Row-8 comparator-H current screen (issue #458, DR-0046 lever)

Campaign `20261120T211042Z-row8-cmph-iq-screen`; DUTs from `gen_row8_screen.py dut` on the DR-0044 extraction (`results/20261112T200335Z-extract-l07`, sha256 `01e06dae...d16a1`); `dut_check`: every variant moves only the comparator-H tail fingers (X$39..X$46) and/or the mirror loads (X$65/X$66).
Iq = DR-0009 charge integral over clk rising edges 5..25 (DR-0044 bench, batch fleet). Row-4/5 deviations are graded against **each die's own 3.3 V / 27 C held-code frequency** (DR-0043/DR-0045 convention); the calibration residue vs 48.000 MHz is in the calibration table. Row-4/5/10 use held-code cells only.

## Variant DUTs (sha256 of `<variant>/iq/rcosc_top_variant.spice`; the delay set's copy differs only by the three analysis probe taps, the startup set's is the same DUT under its `rcosc_top_p3.spice` bench name)

| variant | sha256 |
|---|---|
| control | `01e06daeb8cf341189207770f982c32a4b288b3bca504614262353ef324d16a1` |
| tail x0.85 | `4a1706282881e1a16d63c383324edc0aafb9aa33adbfc209cf35fe3e143f0fdb` |
| tail x0.70 | `897df1595f0b39089c040fda118183a19a8e1fe1e667964312a37fa651052a42` |
| tail x0.55 | `95885cb41b704a21dc9fac03dcbda4808bd38376dc8aa49eed712352819e2d0f` |
| tail x0.40 | `0dacad9a6e93bef1f4e09d965fb07d7310e2f3efbf01314f4103dc75d89d13d9` |
| load L 0.6 | `08a4c193d37b201bbd35c9c5f061b8daeaa8cf89e0fafb011f68feb019986d8e` |
| tail x0.70 + load L 0.6 | `cbe033d91bb8efbff4159af20bfd98c8c651b574b2eb028c1d2d154cd2db69a7` |

## Calibration (27 C / 3.3 V; nearest scanned code to 48 MHz, step 4)

| variant | tt code | f (MHz) | ff code | f (MHz) | ss code | f (MHz) |
|---|---|---|---|---|---|---|
| control | 0xA4 | DR-0043 | 0x4F | DR-0043 | 0xD4 | DR-0043 |
| tail x0.85 | 0xA4 | 47.594 | 0x4F | 47.689 | 0xD4 | 47.655 |
| tail x0.70 | 0xA8 | 48.144 | 0x53 | 48.044 | 0xD8 | 48.490 |
| tail x0.55 | 0xA8 | 47.591 | 0x57 | 48.253 | 0xD8 | 47.832 |
| tail x0.40 | 0xAC | 47.887 | 0x57 | 47.686 | 0xDC | 48.207 |
| load L 0.6 | 0xA4 | 47.906 | 0x4F | 47.932 | 0xD4 | 48.056 |
| tail x0.70 + load L 0.6 | 0xA8 | 48.180 | 0x53 | 48.039 | 0xD8 | 48.546 |

The control's codes and scan frequencies are DR-0043's committed calibration (`20261112T201500Z-calib-extracted-l07`, same DUT sha).  All row-4/5 references below are each die's own 3.3 V / 27 C held-code cell of this campaign's iq grid.

Calibration residue of the references vs 48.000 MHz (max |f-48| per variant): 0.54 MHz worst across variants.

## Running Iq vs the strict 500 uA row-8 limit (worst cell named)

| variant | worst Iq @ cal code (uA, cell) | n>=500 | miss | worst Iq @ 0xFF (uA, cell) | n>=500 | miss | d(worst cal) vs control (uA) |
|---|---|---|---|---|---|---|---|
| control | 505.4 (ff/85C/3.6V) | 1 | 0/27 | 759.0 (ff/85C/3.6V) | 12 | 0/27 | +0.0 |
| tail x0.85 | 474.5 (ff/85C/3.6V) | 0 | 0/27 | 726.1 (ff/85C/3.6V) | 10 | 0/27 | -30.9 |
| tail x0.70 | 445.4 (ff/85C/3.6V) | 0 | 0/27 | 693.3 (ff/85C/3.6V) | 9 | 0/27 | -59.9 |
| tail x0.55 | 417.1 (ff/85C/3.6V) | 0 | 0/27 | 661.5 (ff/85C/3.6V) | 7 | 0/27 | -88.3 |
| tail x0.40 | 390.3 (ff/85C/3.6V) | 0 | 0/27 | 632.4 (ff/85C/3.6V) | 6 | 0/27 | -115.0 |
| load L 0.6 | 505.2 (ff/85C/3.6V) | 1 | 0/27 | 758.0 (ff/85C/3.6V) | 12 | 0/27 | -0.2 |
| tail x0.70 + load L 0.6 | 445.3 (ff/85C/3.6V) | 0 | 0/27 | 693.7 (ff/85C/3.6V) | 9 | 0/27 | -60.0 |

## Row 4 (supply response at 27 C, held code; window -2.9 / +2.0 % vs the die's 3.3 V / 27 C reference)

| variant | tt low/high (%) | ff low/high (%) | ss low/high (%) | worst span (pt) | verdict |
|---|---|---|---|---|---|
| control | -1.94 / +1.57 | -1.06 / +0.92 | -3.37 / +2.72 | 6.09 | FAIL |
| tail x0.85 | -1.96 / +1.61 | -1.14 / +0.92 | -3.36 / +2.74 | 6.10 | FAIL |
| tail x0.70 | -2.09 / +1.71 | -1.21 / +0.98 | -3.67 / +3.00 | 6.68 | FAIL |
| tail x0.55 | -2.13 / +1.76 | -1.29 / +1.06 | -3.70 / +3.01 | 6.71 | FAIL |
| tail x0.40 | -2.28 / +1.88 | -1.36 / +1.09 | -3.96 / +3.34 | 7.31 | FAIL |
| load L 0.6 | -1.93 / +1.53 | -1.08 / +0.92 | -3.35 / +2.71 | 6.06 | FAIL |
| tail x0.70 + load L 0.6 | -2.10 / +1.69 | -1.22 / +0.96 | -3.66 / +2.99 | 6.65 | FAIL |

## Row 5 (held code over the 9-cell grid; window -10.8 / +8.8 % vs the die's 3.3 V / 27 C reference)

| variant | worst cold cell (%) | worst hot cell (%) | ff/85C/3.0V (%) | verdict |
|---|---|---|---|---|
| control | -4.40 (ff/3V) | +3.05 (ff/3.6V) | +1.65 | pass |
| tail x0.85 | -4.44 (ff/3V) | +3.07 (ss/3.6V) | +1.29 | pass |
| tail x0.70 | -4.50 (ff/3V) | +3.13 (ss/3.6V) | +1.10 | pass |
| tail x0.55 | -4.67 (ss/3V) | +3.24 (ss/3.6V) | +0.87 | pass |
| tail x0.40 | -4.60 (ss/3V) | +3.36 (ss/3.6V) | +0.78 | pass |
| load L 0.6 | -4.34 (ff/3V) | +2.95 (ff/3.6V) | +1.32 | pass |
| tail x0.70 + load L 0.6 | -4.47 (ff/3V) | +3.08 (ss/3.6V) | +1.02 | pass |

## Row 10 (lost clock over the held-code grid)

| variant | cells with no clock (f < 1 MHz or failed) |
|---|---|
| control | 0 |
| tail x0.85 | 0 |
| tail x0.70 | 0 |
| tail x0.55 | 0 |
| tail x0.40 | 0 |
| load L 0.6 | 0 |
| tail x0.70 + load L 0.6 | 0 |

## Comparator-H delay at the ff held code (vc rises through vh -> cmph_out rise)

| variant | ff code | 3.0V/85C (ns) | 3.0V/-40C (ns) | 3.6V/85C (ns) | d(3.0V/85C) vs control (ns) |
|---|---|---|---|---|---|
| control | 0x4F | 1.75 | 2.02 | 1.80 | +0.00 |
| tail x0.85 | 0x4F | 1.96 | 2.16 | 1.96 | +0.21 |
| tail x0.70 | 0x53 | 2.15 | 2.32 | 2.10 | +0.40 |
| tail x0.55 | 0x57 | 2.36 | 2.53 | 2.29 | +0.61 |
| tail x0.40 | 0x57 | 2.63 | 2.81 | 2.53 | +0.88 |
| load L 0.6 | 0x4F | 1.84 | 2.02 | 1.84 | +0.09 |
| tail x0.70 + load L 0.6 | 0x53 | 2.17 | 2.32 | 2.12 | +0.41 |

## Startup at fs / -40 C (1 us ramp, the variant's held tt code; DR-0020 primary band 1.1 %, bound 10 us)

| variant | tt code | 3.3V status / settle (us) | 3.6V status / settle (us) | verdict |
|---|---|---|---|---|
| control | 0xA4 | STARTED / 0.93 | STARTED / 0.91 | pass |
| tail x0.85 | 0xA4 | STARTED / 0.92 | STARTED / 0.91 | pass |
| tail x0.70 | 0xA8 | STARTED / 0.93 | STARTED / 0.91 | pass |
| tail x0.55 | 0xA8 | STARTED / 0.95 | STARTED / 0.91 | pass |
| tail x0.40 | 0xAC | STARTED / 0.94 | STARTED / 0.92 | pass |
| load L 0.6 | 0xA4 | STARTED / 0.92 | STARTED / 0.90 | pass |
| tail x0.70 + load L 0.6 | 0xA8 | STARTED / 0.94 | STARTED / 0.92 | pass |

Control back-to-back gate: the control DUT's 27 `0xFF` cells reproduce DR-0044's committed figures (20261113T064105Z-iq-extracted-l07) to -0.01..+0.01 % (n=27).

