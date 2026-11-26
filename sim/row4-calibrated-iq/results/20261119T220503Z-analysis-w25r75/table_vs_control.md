# Matched-die calibrated-code running Iq - w2.5r75 vs L=1 um control (issue #337)

Candidate run `20261119T220503Z-cand-w25r75`, control run `20261119T220503Z-ctl-w25r75`. Population: DR-0032 draws (500 per process, seed 20261008), each die calibrated at 27 C / 3.3 V on the candidate DUT and the control measured at the SAME draw (same derived seed), code, supply and temperature. Iq in uA; delta = (candidate - control) / control * 100. DR-0044 nominal-cell band: -4.57..+0.18 %. Ratified row (README / DR-0003 Row 4): < 500 uA running.

## tt

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0xA4x1, 0xA5x33, 0xA6x181, 0xA7x197, 0xA8x68, 0xA9x20; dice at 0xFF: 0
- candidate Iq uA: min 241.2 / p50 330.4 / p95 404.7 / max 426.1 (control: 237.3..422.6)
- delta vs matched control %: min +0.68 / p50 +1.30 / p95 +1.66 / max +1.88 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 0 of 4500, control 0
- worst absolute: 426.1 uA (die 370, code 0xA4, 3.6 V, 85 C; control 422.6 uA, +0.85 %)
- worst increase: +1.88 % -> 272.1 uA (die 57, code 0xA9, 3.0 V, 27 C; control 267.1 uA)
- largest decrease: +0.68 % (die 370, code 0xA4, 3.6 V, -40 C)

## ff

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0x49x8, 0x4Ax40, 0x4Bx102, 0x4Cx130, 0x4Dx147, 0x4Ex53, 0x4Fx18, 0x50x2; dice at 0xFF: 0
- candidate Iq uA: min 292.6 / p50 413.6 / p95 507.8 / max 537.5 (control: 290.4..539.3)
- delta vs matched control %: min -0.35 / p50 +0.51 / p95 +0.75 / max +0.98 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 384 of 4500, control 374
- worst absolute: 537.5 uA (die 370, code 0x49, 3.6 V, 85 C; control 539.3 uA, -0.35 %)
- worst increase: +0.98 % -> 302.5 uA (die 347, code 0x4E, 3.0 V, -40 C; control 299.6 uA)
- largest decrease: -0.35 % (die 370, code 0x49, 3.6 V, 85 C)

## ss

- dice: 500 (matched control points: 4500, missing control dice: 0)
- calibrated-code occupancy: 0xD3x21, 0xD4x223, 0xD5x236, 0xD6x20; dice at 0xFF: 0
- candidate Iq uA: min 215.3 / p50 289.5 / p95 354.2 / max 371.2 (control: 205.3..358.7)
- delta vs matched control %: min +2.75 / p50 +4.12 / p95 +4.91 / max +5.42 -- DR-0044 band -4.57..+0.18: OUTSIDE
- cells >= 500 uA: candidate 0 of 4500, control 0
- worst absolute: 371.2 uA (die 370, code 0xD3, 3.6 V, 85 C; control 358.7 uA, +3.50 %)
- worst increase: +5.42 % -> 242.3 uA (die 385, code 0xD6, 3.0 V, 27 C; control 229.8 uA)
- largest decrease: +2.75 % (die 370, code 0xD3, 3.6 V, -40 C)

