# Matched-die calibrated-code running Iq - w3r65 vs L=1 um control (issue #337)

Candidate run `20261119T220503Z-cand-w3r65`, control run `20261119T220503Z-ctl-w3r65`. Population: DR-0032 draws (500 per process, seed 20261008), each die calibrated at 27 C / 3.3 V on the candidate DUT and the control measured at the SAME draw (same derived seed), code, supply and temperature. Iq in uA; delta = (candidate - control) / control * 100. DR-0044 nominal-cell band: -4.57..+0.18 %. Ratified row (README / DR-0003 Row 4): < 500 uA running.

## tt

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0x7Fx2, 0xA5x11, 0xA6x139, 0xA7x215, 0xA8x102, 0xA9x31; dice at 0xFF: 0
- candidate Iq uA: min 242.6 / p50 332.1 / p95 406.7 / max 427.1 (control: 237.3..420.9)
- delta vs matched control %: min +1.11 / p50 +1.80 / p95 +2.22 / max +3.02 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 0 of 4500, control 0
- worst absolute: 427.1 uA (die 313, code 0xA6, 3.6 V, 85 C; control 420.9 uA, +1.46 %)
- worst increase: +3.02 % -> 255.5 uA (die 106, code 0x7F, 3.0 V, -40 C; control 248.0 uA)
- largest decrease: +1.11 % (die 368, code 0xA5, 3.6 V, -40 C)

## ff

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0x48x5, 0x49x28, 0x4Ax92, 0x4Bx133, 0x4Cx153, 0x4Dx62, 0x4Ex25, 0x4Fx2; dice at 0xFF: 0
- candidate Iq uA: min 293.0 / p50 414.1 / p95 508.3 / max 537.9 (control: 290.2..539.0)
- delta vs matched control %: min -0.20 / p50 +0.68 / p95 +0.95 / max +1.16 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 387 of 4500, control 363
- worst absolute: 537.9 uA (die 370, code 0x48, 3.6 V, 85 C; control 539.0 uA, -0.20 %)
- worst increase: +1.16 % -> 305.3 uA (die 419, code 0x4E, 3.0 V, -40 C; control 301.8 uA)
- largest decrease: -0.20 % (die 370, code 0x48, 3.6 V, 85 C)

## ss

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0xD3x46, 0xD4x323, 0xD5x130, 0xD6x1; dice at 0xFF: 0
- candidate Iq uA: min 218.8 / p50 293.2 / p95 358.3 / max 375.8 (control: 205.3..358.7)
- delta vs matched control %: min +3.90 / p50 +5.55 / p95 +6.42 / max +7.08 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 0 of 4500, control 0
- worst absolute: 375.8 uA (die 370, code 0xD3, 3.6 V, 85 C; control 358.7 uA, +4.77 %)
- worst increase: +7.08 % -> 247.8 uA (die 463, code 0xD6, 3.0 V, 27 C; control 231.4 uA)
- largest decrease: +3.90 % (die 434, code 0xD3, 3.6 V, -40 C)

