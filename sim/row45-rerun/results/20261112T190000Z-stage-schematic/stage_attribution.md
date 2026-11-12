# Stage-level attribution of rows 4 / 5 (generated; source sim/row45-rerun/results/20261112T190000Z-stage-schematic)

Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code (tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.

## Reference points (3.3 V / 27 C)

| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 165 | 48.03 | 20.820 | 1.665 | 0.539 | 0.104 | 1.620 | 0.255 | 16.637 | 0.6666 | 0.3333 |
| ff | 78 | 47.95 | 20.856 | 1.381 | 0.483 | 0.037 | 1.333 | 0.206 | 17.415 | 0.6666 | 0.3333 |
| ss | 212 | 48.00 | 20.834 | 1.962 | 0.612 | 0.154 | 1.929 | 0.302 | 15.874 | 0.6666 | 0.3333 |

Residuals over all 27 points: event gaps vs period 0.0000 % of T; 3-edge period vs 20-period fosc 0.291 % of T.

## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)

### tt, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.19 | +0.21 | +0.40 |
| latch set (cmph_out -> clk rise) | -0.19 | +0.29 | +0.48 |
| discharge (clk rise -> vc<vl) | -0.00 | +0.17 | +0.17 |
| comparator L (vc<vl -> cmpl_out) | +0.26 | -0.03 | -0.29 |
| latch reset (cmpl_out -> clk fall) | -0.05 | +0.06 | +0.11 |
| charge: threshold-ratio term | -0.06 | -0.02 | +0.03 |
| charge: RC term (trim bank R, Ron, C) | -0.85 | +0.27 | +1.12 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -1.08 | +0.95 | +2.02 |
| measured eps (periods) | -1.08 | +0.95 | +2.02 |
| measured eps (20-period fosc) | -1.15 | +0.79 | +1.94 |

### ff, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.12 | +0.08 | +0.20 |
| latch set (cmph_out -> clk rise) | -0.05 | +0.17 | +0.22 |
| discharge (clk rise -> vc<vl) | -0.04 | +0.10 | +0.14 |
| comparator L (vc<vl -> cmpl_out) | -0.06 | +0.14 | +0.20 |
| latch reset (cmpl_out -> clk fall) | -0.14 | -0.05 | +0.09 |
| charge: threshold-ratio term | -0.02 | +0.03 | +0.05 |
| charge: RC term (trim bank R, Ron, C) | -0.25 | +0.25 | +0.50 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | -0.68 | +0.72 | +1.40 |
| measured eps (periods) | -0.68 | +0.72 | +1.40 |
| measured eps (20-period fosc) | -0.78 | +0.48 | +1.26 |

### ss, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.25 | +0.35 | +0.59 |
| latch set (cmph_out -> clk rise) | -0.31 | +0.15 | +0.47 |
| discharge (clk rise -> vc<vl) | -0.14 | +0.14 | +0.28 |
| comparator L (vc<vl -> cmpl_out) | +0.17 | -0.30 | -0.47 |
| latch reset (cmpl_out -> clk fall) | -0.13 | +0.08 | +0.21 |
| charge: threshold-ratio term | +0.01 | -0.02 | -0.03 |
| charge: RC term (trim bank R, Ron, C) | -1.28 | +0.99 | +2.27 |
| charge: cross term | +0.00 | +0.00 | +0.00 |
| **sum of stages** | -1.93 | +1.39 | +3.31 |
| measured eps (periods) | -1.93 | +1.39 | +3.31 |
| measured eps (20-period fosc) | -1.94 | +1.39 | +3.33 |

## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)

### ff, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.48 | +0.12 | +0.60 |
| latch set (cmph_out -> clk rise) | -0.22 | -0.27 | -0.49 |
| discharge (clk rise -> vc<vl) | -0.05 | -0.02 | -0.07 |
| comparator L (vc<vl -> cmpl_out) | +0.33 | +0.23 | +0.56 |
| latch reset (cmpl_out -> clk fall) | -0.21 | -0.07 | -0.28 |
| charge: threshold-ratio term | -0.03 | +0.01 | -0.02 |
| charge: RC term (trim bank R, Ron, C) | +3.07 | -0.56 | +2.50 |
| charge: cross term | +0.00 | +0.00 | +0.00 |
| **sum of stages** | +3.38 | -0.56 | +2.80 |
| measured eps (periods) | +3.38 | n/a | +2.80 |
| measured eps (20-period fosc) | +3.22 | n/a | +2.60 |

### ff, 85 C, 3.3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3.3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.48 | -0.00 | +0.48 |
| latch set (cmph_out -> clk rise) | -0.22 | -0.00 | -0.22 |
| discharge (clk rise -> vc<vl) | -0.05 | -0.00 | -0.05 |
| comparator L (vc<vl -> cmpl_out) | +0.33 | -0.00 | +0.33 |
| latch reset (cmpl_out -> clk fall) | -0.21 | -0.00 | -0.21 |
| charge: threshold-ratio term | -0.03 | -0.00 | -0.03 |
| charge: RC term (trim bank R, Ron, C) | +3.07 | -0.00 | +3.07 |
| charge: cross term | +0.00 | -0.00 | +0.00 |
| **sum of stages** | +3.38 | +0.00 | +3.38 |
| measured eps (periods) | +3.38 | n/a | +3.38 |
| measured eps (20-period fosc) | +3.22 | n/a | +3.22 |

### ff, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.13 | -0.20 | -0.33 |
| latch set (cmph_out -> clk rise) | +0.42 | -0.07 | +0.34 |
| discharge (clk rise -> vc<vl) | -0.01 | -0.02 | -0.03 |
| comparator L (vc<vl -> cmpl_out) | -0.21 | +0.07 | -0.14 |
| latch reset (cmpl_out -> clk fall) | +0.10 | -0.04 | +0.06 |
| charge: threshold-ratio term | -0.01 | -0.02 | -0.02 |
| charge: RC term (trim bank R, Ron, C) | -4.57 | -0.47 | -5.00 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | -4.40 | -0.75 | -5.12 |
| measured eps (periods) | -4.40 | n/a | -5.12 |
| measured eps (20-period fosc) | -4.84 | n/a | -5.54 |

### ff, -40 C, 3.6 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3.6 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.13 | +0.19 | +0.06 |
| latch set (cmph_out -> clk rise) | +0.42 | +0.18 | +0.60 |
| discharge (clk rise -> vc<vl) | -0.01 | +0.02 | +0.01 |
| comparator L (vc<vl -> cmpl_out) | -0.21 | -0.01 | -0.23 |
| latch reset (cmpl_out -> clk fall) | +0.10 | +0.01 | +0.11 |
| charge: threshold-ratio term | -0.01 | -0.04 | -0.04 |
| charge: RC term (trim bank R, Ron, C) | -4.57 | +0.01 | -4.57 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | -4.40 | +0.35 | -4.07 |
| measured eps (periods) | -4.40 | n/a | -4.07 |
| measured eps (20-period fosc) | -4.84 | n/a | -4.21 |

### tt, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.23 | -0.03 | +0.19 |
| latch set (cmph_out -> clk rise) | -0.25 | -0.35 | -0.60 |
| discharge (clk rise -> vc<vl) | -0.06 | -0.09 | -0.15 |
| comparator L (vc<vl -> cmpl_out) | +0.38 | +0.18 | +0.55 |
| latch reset (cmpl_out -> clk fall) | -0.17 | -0.04 | -0.21 |
| charge: threshold-ratio term | +0.00 | +0.02 | +0.03 |
| charge: RC term (trim bank R, Ron, C) | +2.69 | -0.64 | +2.03 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +2.82 | -0.95 | +1.84 |
| measured eps (periods) | +2.82 | n/a | +1.84 |
| measured eps (20-period fosc) | +2.94 | n/a | +1.92 |

### tt, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.09 | -0.23 | -0.33 |
| latch set (cmph_out -> clk rise) | +0.44 | -0.26 | +0.18 |
| discharge (clk rise -> vc<vl) | +0.09 | -0.00 | +0.09 |
| comparator L (vc<vl -> cmpl_out) | -0.37 | +0.25 | -0.11 |
| latch reset (cmpl_out -> clk fall) | +0.16 | -0.14 | +0.02 |
| charge: threshold-ratio term | -0.11 | +0.16 | +0.04 |
| charge: RC term (trim bank R, Ron, C) | -5.10 | -0.66 | -5.71 |
| charge: cross term | -0.01 | +0.00 | +0.00 |
| **sum of stages** | -4.98 | -0.87 | -5.81 |
| measured eps (periods) | -4.98 | n/a | -5.81 |
| measured eps (20-period fosc) | -4.77 | n/a | -5.93 |

### ss, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.17 | -0.17 | +0.00 |
| latch set (cmph_out -> clk rise) | -0.42 | -0.38 | -0.79 |
| discharge (clk rise -> vc<vl) | -0.08 | -0.21 | -0.28 |
| comparator L (vc<vl -> cmpl_out) | +0.35 | +0.12 | +0.46 |
| latch reset (cmpl_out -> clk fall) | -0.15 | -0.11 | -0.26 |
| charge: threshold-ratio term | +0.07 | +0.05 | +0.12 |
| charge: RC term (trim bank R, Ron, C) | +2.20 | -1.24 | +0.91 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +2.13 | -1.93 | +0.16 |
| measured eps (periods) | +2.13 | n/a | +0.16 |
| measured eps (20-period fosc) | +2.21 | n/a | +0.27 |

### ss, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.02 | -0.37 | -0.35 |
| latch set (cmph_out -> clk rise) | +0.38 | -0.18 | +0.19 |
| discharge (clk rise -> vc<vl) | +0.09 | -0.09 | -0.01 |
| comparator L (vc<vl -> cmpl_out) | -0.62 | +0.23 | -0.38 |
| latch reset (cmpl_out -> clk fall) | +0.22 | -0.17 | +0.04 |
| charge: threshold-ratio term | -0.08 | +0.14 | +0.05 |
| charge: RC term (trim bank R, Ron, C) | -3.80 | -1.42 | -5.14 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -3.80 | -1.85 | -5.59 |
| measured eps (periods) | -3.80 | n/a | -5.59 |
| measured eps (20-period fosc) | -3.79 | n/a | -5.45 |

## Bias gate voltages (3.3 V ref points, V)

| point | ibias gate | pb | vh | vl |
|---|---|---|---|---|
| tt -40 C 3 V | 0.9478 | 1.8427 | 2.0000 | 1.0000 |
| tt -40 C 3.3 V | 0.9627 | 2.1211 | 2.2000 | 1.1000 |
| tt -40 C 3.6 V | 0.9799 | 2.3958 | 2.4000 | 1.2000 |
| tt 27 C 3 V | 0.9520 | 1.8099 | 2.0000 | 1.0001 |
| tt 27 C 3.3 V | 0.9666 | 2.0895 | 2.1998 | 1.0998 |
| tt 27 C 3.6 V | 0.9829 | 2.3667 | 2.4001 | 1.2001 |
| tt 85 C 3 V | 0.9677 | 1.7709 | 1.9999 | 0.9999 |
| tt 85 C 3.3 V | 0.9822 | 2.0516 | 2.2001 | 1.1000 |
| tt 85 C 3.6 V | 0.9983 | 2.3301 | 2.4000 | 1.2000 |
| ff -40 C 3 V | 0.8783 | 1.9094 | 2.0000 | 1.0000 |
| ff -40 C 3.3 V | 0.8949 | 2.1849 | 2.1999 | 1.0999 |
| ff -40 C 3.6 V | 0.9131 | 2.4580 | 2.4001 | 1.2001 |
| ff 27 C 3 V | 0.8955 | 1.8606 | 2.0001 | 1.0001 |
| ff 27 C 3.3 V | 0.9115 | 2.1383 | 2.1999 | 1.0999 |
| ff 27 C 3.6 V | 0.9289 | 2.4140 | 2.4000 | 1.2001 |
| ff 85 C 3 V | 0.9263 | 1.8035 | 1.9999 | 0.9999 |
| ff 85 C 3.3 V | 0.9421 | 2.0825 | 2.2000 | 1.1000 |
| ff 85 C 3.6 V | 0.9591 | 2.3598 | 2.4000 | 1.2000 |
| ss -40 C 3 V | 1.0278 | 1.7606 | 1.9999 | 0.9999 |
| ss -40 C 3.3 V | 1.0400 | 2.0432 | 2.2000 | 1.1000 |
| ss -40 C 3.6 V | 1.0553 | 2.3210 | 2.4000 | 1.2000 |
| ss 27 C 3 V | 1.0238 | 1.7377 | 1.9999 | 0.9999 |
| ss 27 C 3.3 V | 1.0364 | 2.0205 | 2.1998 | 1.0998 |
| ss 27 C 3.6 V | 1.0513 | 2.2998 | 2.4000 | 1.1999 |
| ss 85 C 3 V | 1.0305 | 1.7099 | 1.9999 | 0.9999 |
| ss 85 C 3.3 V | 1.0434 | 1.9928 | 2.1998 | 1.0999 |
| ss 85 C 3.6 V | 1.0582 | 2.2730 | 2.4000 | 1.2000 |

