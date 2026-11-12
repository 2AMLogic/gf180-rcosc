# Stage-level attribution of rows 4 / 5 (generated; source sim/row45-rerun/results/20261112T210000Z-stage-schematic-control-l1)

Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code (tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.

## Reference points (3.3 V / 27 C)

| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 165 | 47.89 | 20.883 | 1.687 | 0.531 | 0.097 | 1.608 | 0.248 | 16.713 | 0.6666 | 0.3333 |
| ff | 78 | 48.10 | 20.789 | 1.351 | 0.468 | 0.019 | 1.266 | 0.210 | 17.475 | 0.6666 | 0.3333 |
| ss | 212 | 47.85 | 20.900 | 2.002 | 0.613 | 0.153 | 1.919 | 0.299 | 15.913 | 0.6666 | 0.3333 |

Residuals over all 27 points: event gaps vs period 0.0000 % of T; 3-edge period vs 20-period fosc 0.801 % of T.

## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)

### tt, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.16 | +0.23 | +0.39 |
| latch set (cmph_out -> clk rise) | -0.24 | +0.24 | +0.48 |
| discharge (clk rise -> vc<vl) | -0.13 | +0.12 | +0.26 |
| comparator L (vc<vl -> cmpl_out) | +0.16 | -0.12 | -0.27 |
| latch reset (cmpl_out -> clk fall) | -0.12 | +0.02 | +0.14 |
| charge: threshold-ratio term | -0.00 | +0.00 | +0.01 |
| charge: RC term (trim bank R, Ron, C) | -0.33 | +0.56 | +0.90 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | -0.82 | +1.07 | +1.89 |
| measured eps (periods) | -0.82 | +1.07 | +1.89 |
| measured eps (20-period fosc) | -1.05 | +0.76 | +1.80 |

### ff, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.07 | +0.04 | -0.03 |
| latch set (cmph_out -> clk rise) | -0.16 | +0.06 | +0.22 |
| discharge (clk rise -> vc<vl) | -0.16 | +0.02 | +0.17 |
| comparator L (vc<vl -> cmpl_out) | +0.08 | -0.29 | -0.37 |
| latch reset (cmpl_out -> clk fall) | -0.06 | -0.03 | +0.03 |
| charge: threshold-ratio term | -0.03 | +0.00 | +0.03 |
| charge: RC term (trim bank R, Ron, C) | -0.24 | +0.63 | +0.87 |
| charge: cross term | -0.00 | -0.00 | +0.00 |
| **sum of stages** | -0.50 | +0.43 | +0.93 |
| measured eps (periods) | -0.50 | +0.43 | +0.93 |
| measured eps (20-period fosc) | -0.58 | +0.43 | +1.01 |

### ss, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.26 | +0.34 | +0.59 |
| latch set (cmph_out -> clk rise) | -0.37 | +0.21 | +0.58 |
| discharge (clk rise -> vc<vl) | -0.16 | +0.10 | +0.26 |
| comparator L (vc<vl -> cmpl_out) | +0.05 | -0.30 | -0.36 |
| latch reset (cmpl_out -> clk fall) | -0.12 | +0.06 | +0.19 |
| charge: threshold-ratio term | -0.01 | -0.01 | +0.00 |
| charge: RC term (trim bank R, Ron, C) | -1.13 | +1.07 | +2.20 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -2.00 | +1.47 | +3.46 |
| measured eps (periods) | -2.00 | +1.47 | +3.46 |
| measured eps (20-period fosc) | -1.88 | +1.48 | +3.36 |

## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)

### ff, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +1.78 | +1.78 | +3.58 |
| latch set (cmph_out -> clk rise) | -0.29 | -0.10 | -0.39 |
| discharge (clk rise -> vc<vl) | -0.17 | +0.01 | -0.16 |
| comparator L (vc<vl -> cmpl_out) | -0.04 | +0.28 | +0.24 |
| latch reset (cmpl_out -> clk fall) | -0.19 | -0.04 | -0.23 |
| charge: threshold-ratio term | -0.01 | -0.01 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | +3.29 | -0.64 | +2.70 |
| charge: cross term | +0.00 | -0.00 | +0.00 |
| **sum of stages** | +4.38 | +1.29 | +5.72 |
| measured eps (periods) | +4.38 | n/a | +5.72 |
| measured eps (20-period fosc) | +4.57 | n/a | +5.68 |

### ff, 85 C, 3.3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3.3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +1.78 | -0.00 | +1.78 |
| latch set (cmph_out -> clk rise) | -0.29 | -0.00 | -0.29 |
| discharge (clk rise -> vc<vl) | -0.17 | -0.00 | -0.17 |
| comparator L (vc<vl -> cmpl_out) | -0.04 | -0.00 | -0.04 |
| latch reset (cmpl_out -> clk fall) | -0.19 | -0.00 | -0.19 |
| charge: threshold-ratio term | -0.01 | -0.00 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | +3.29 | -0.00 | +3.29 |
| charge: cross term | +0.00 | -0.00 | +0.00 |
| **sum of stages** | +4.38 | +0.00 | +4.38 |
| measured eps (periods) | +4.38 | n/a | +4.38 |
| measured eps (20-period fosc) | +4.57 | n/a | +4.57 |

### ff, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.39 | -0.14 | -0.52 |
| latch set (cmph_out -> clk rise) | +0.31 | -0.03 | +0.28 |
| discharge (clk rise -> vc<vl) | -0.03 | -0.11 | -0.14 |
| comparator L (vc<vl -> cmpl_out) | -0.42 | +0.13 | -0.29 |
| latch reset (cmpl_out -> clk fall) | +0.11 | -0.09 | +0.02 |
| charge: threshold-ratio term | -0.04 | -0.02 | -0.05 |
| charge: RC term (trim bank R, Ron, C) | -4.58 | -0.66 | -5.20 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | -5.03 | -0.93 | -5.91 |
| measured eps (periods) | -5.03 | n/a | -5.91 |
| measured eps (20-period fosc) | -5.13 | n/a | -5.66 |

### ff, -40 C, 3.6 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3.6 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.39 | +0.25 | -0.14 |
| latch set (cmph_out -> clk rise) | +0.31 | +0.16 | +0.48 |
| discharge (clk rise -> vc<vl) | -0.03 | -0.02 | -0.05 |
| comparator L (vc<vl -> cmpl_out) | -0.42 | +0.04 | -0.39 |
| latch reset (cmpl_out -> clk fall) | +0.11 | -0.02 | +0.09 |
| charge: threshold-ratio term | -0.04 | +0.10 | +0.05 |
| charge: RC term (trim bank R, Ron, C) | -4.58 | +0.78 | -3.86 |
| charge: cross term | -0.00 | -0.00 | +0.00 |
| **sum of stages** | -5.03 | +1.29 | -3.81 |
| measured eps (periods) | -5.03 | n/a | -3.81 |
| measured eps (20-period fosc) | -5.13 | n/a | -4.52 |

### tt, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.55 | +0.21 | +0.76 |
| latch set (cmph_out -> clk rise) | -0.33 | -0.31 | -0.64 |
| discharge (clk rise -> vc<vl) | -0.00 | -0.16 | -0.16 |
| comparator L (vc<vl -> cmpl_out) | +0.28 | +0.23 | +0.51 |
| latch reset (cmpl_out -> clk fall) | -0.19 | -0.10 | -0.29 |
| charge: threshold-ratio term | +0.02 | +0.02 | +0.04 |
| charge: RC term (trim bank R, Ron, C) | +3.11 | -0.78 | +2.30 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +3.44 | -0.89 | +2.52 |
| measured eps (periods) | +3.44 | n/a | +2.52 |
| measured eps (20-period fosc) | +3.28 | n/a | +2.45 |

### tt, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.11 | -0.31 | -0.42 |
| latch set (cmph_out -> clk rise) | +0.45 | -0.26 | +0.18 |
| discharge (clk rise -> vc<vl) | +0.06 | -0.12 | -0.06 |
| comparator L (vc<vl -> cmpl_out) | -0.34 | -0.15 | -0.48 |
| latch reset (cmpl_out -> clk fall) | +0.18 | -0.12 | +0.06 |
| charge: threshold-ratio term | -0.01 | -0.11 | -0.11 |
| charge: RC term (trim bank R, Ron, C) | -4.86 | -0.25 | -5.04 |
| charge: cross term | -0.00 | -0.00 | -0.01 |
| **sum of stages** | -4.62 | -1.32 | -5.88 |
| measured eps (periods) | -4.62 | n/a | -5.88 |
| measured eps (20-period fosc) | -4.85 | n/a | -5.75 |

### ss, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.29 | -0.08 | +0.20 |
| latch set (cmph_out -> clk rise) | -0.43 | -0.37 | -0.79 |
| discharge (clk rise -> vc<vl) | -0.08 | -0.15 | -0.23 |
| comparator L (vc<vl -> cmpl_out) | +0.30 | +0.19 | +0.49 |
| latch reset (cmpl_out -> clk fall) | -0.18 | -0.09 | -0.26 |
| charge: threshold-ratio term | +0.07 | +0.02 | +0.09 |
| charge: RC term (trim bank R, Ron, C) | +2.34 | -1.27 | +1.03 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +2.32 | -1.74 | +0.54 |
| measured eps (periods) | +2.32 | n/a | +0.54 |
| measured eps (20-period fosc) | +2.37 | n/a | +0.49 |

### ss, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.05 | -0.40 | -0.45 |
| latch set (cmph_out -> clk rise) | +0.42 | -0.27 | +0.14 |
| discharge (clk rise -> vc<vl) | +0.09 | -0.10 | -0.01 |
| comparator L (vc<vl -> cmpl_out) | -0.83 | +0.42 | -0.40 |
| latch reset (cmpl_out -> clk fall) | +0.16 | -0.04 | +0.12 |
| charge: threshold-ratio term | -0.11 | -0.00 | -0.12 |
| charge: RC term (trim bank R, Ron, C) | -3.62 | -1.01 | -4.58 |
| charge: cross term | -0.01 | -0.00 | -0.01 |
| **sum of stages** | -3.95 | -1.41 | -5.30 |
| measured eps (periods) | -3.95 | n/a | -5.30 |
| measured eps (20-period fosc) | -3.88 | n/a | -5.45 |

## Bias gate voltages (3.3 V ref points, V)

| point | ibias gate | pb | vh | vl |
|---|---|---|---|---|
| tt -40 C 3 V | 0.9478 | 1.8428 | 2.0001 | 1.0001 |
| tt -40 C 3.3 V | 0.9627 | 2.1210 | 2.1999 | 1.0999 |
| tt -40 C 3.6 V | 0.9799 | 2.3958 | 2.4000 | 1.2000 |
| tt 27 C 3 V | 0.9520 | 1.8099 | 2.0000 | 1.0000 |
| tt 27 C 3.3 V | 0.9666 | 2.0895 | 2.1998 | 1.0998 |
| tt 27 C 3.6 V | 0.9830 | 2.3667 | 2.4001 | 1.2001 |
| tt 85 C 3 V | 0.9677 | 1.7710 | 1.9999 | 0.9999 |
| tt 85 C 3.3 V | 0.9823 | 2.0516 | 2.2000 | 1.1000 |
| tt 85 C 3.6 V | 0.9983 | 2.3301 | 2.4000 | 1.2000 |
| ff -40 C 3 V | 0.8783 | 1.9094 | 2.0000 | 0.9999 |
| ff -40 C 3.3 V | 0.8949 | 2.1849 | 2.1999 | 1.0999 |
| ff -40 C 3.6 V | 0.9131 | 2.4579 | 2.3999 | 1.2000 |
| ff 27 C 3 V | 0.8955 | 1.8605 | 1.9998 | 0.9999 |
| ff 27 C 3.3 V | 0.9115 | 2.1384 | 2.1999 | 1.0999 |
| ff 27 C 3.6 V | 0.9289 | 2.4140 | 2.4001 | 1.2001 |
| ff 85 C 3 V | 0.9263 | 1.8035 | 2.0001 | 1.0001 |
| ff 85 C 3.3 V | 0.9421 | 2.0825 | 2.2001 | 1.1000 |
| ff 85 C 3.6 V | 0.9591 | 2.3598 | 2.4000 | 1.2000 |
| ss -40 C 3 V | 1.0278 | 1.7607 | 2.0001 | 1.0001 |
| ss -40 C 3.3 V | 1.0400 | 2.0432 | 2.2001 | 1.1000 |
| ss -40 C 3.6 V | 1.0553 | 2.3210 | 2.4000 | 1.2000 |
| ss 27 C 3 V | 1.0238 | 1.7377 | 1.9999 | 0.9998 |
| ss 27 C 3.3 V | 1.0364 | 2.0205 | 2.1998 | 1.0998 |
| ss 27 C 3.6 V | 1.0513 | 2.2997 | 2.4000 | 1.2000 |
| ss 85 C 3 V | 1.0305 | 1.7099 | 1.9999 | 1.0000 |
| ss 85 C 3.3 V | 1.0434 | 1.9928 | 2.1998 | 1.0999 |
| ss 85 C 3.6 V | 1.0582 | 2.2730 | 2.4000 | 1.2000 |

