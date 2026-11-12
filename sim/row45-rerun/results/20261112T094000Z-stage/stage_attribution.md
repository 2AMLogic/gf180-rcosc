# Stage-level attribution of rows 4 / 5 (generated; source sim/row45-rerun/results/20261112T094000Z-stage)

Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code (tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.

## Reference points (3.3 V / 27 C)

| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 165 | 48.22 | 20.738 | 2.245 | 0.894 | 0.058 | 1.743 | 0.341 | 15.457 | 0.6665 | 0.3331 |
| ff | 78 | 47.91 | 20.871 | 1.849 | 0.780 | -0.021 | 1.567 | 0.289 | 16.407 | 0.6668 | 0.3333 |
| ss | 212 | 47.96 | 20.852 | 2.635 | 1.059 | 0.134 | 1.955 | 0.411 | 14.657 | 0.6663 | 0.3330 |

Residuals over all 27 points: event gaps vs period 0.0000 % of T; 3-edge period vs 20-period fosc 0.076 % of T.

## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)

### tt, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.27 | +0.32 | +0.58 |
| latch set (cmph_out -> clk rise) | -0.42 | +0.32 | +0.74 |
| discharge (clk rise -> vc<vl) | -0.18 | +0.08 | +0.26 |
| comparator L (vc<vl -> cmpl_out) | -0.18 | +0.06 | +0.24 |
| latch reset (cmpl_out -> clk fall) | -0.12 | +0.10 | +0.22 |
| charge: threshold-ratio term | +0.02 | +0.01 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | -0.61 | +0.54 | +1.14 |
| charge: cross term | +0.00 | -0.00 | -0.00 |
| **sum of stages** | -1.74 | +1.42 | +3.16 |
| measured eps (periods) | -1.74 | +1.42 | +3.16 |
| measured eps (20-period fosc) | -1.67 | +1.37 | +3.04 |

### ff, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.20 | +0.04 | -0.15 |
| latch set (cmph_out -> clk rise) | -0.28 | +0.24 | +0.52 |
| discharge (clk rise -> vc<vl) | -0.06 | +0.08 | +0.14 |
| comparator L (vc<vl -> cmpl_out) | +0.07 | -0.09 | -0.17 |
| latch reset (cmpl_out -> clk fall) | -0.03 | +0.07 | +0.10 |
| charge: threshold-ratio term | +0.03 | +0.06 | +0.03 |
| charge: RC term (trim bank R, Ron, C) | -0.52 | +0.29 | +0.80 |
| charge: cross term | +0.00 | -0.00 | -0.00 |
| **sum of stages** | -0.59 | +0.69 | +1.28 |
| measured eps (periods) | -0.59 | +0.69 | +1.28 |
| measured eps (20-period fosc) | -0.62 | +0.71 | +1.32 |

### ss, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.41 | +0.47 | +0.88 |
| latch set (cmph_out -> clk rise) | -0.55 | +0.45 | +1.00 |
| discharge (clk rise -> vc<vl) | -0.22 | +0.07 | +0.29 |
| comparator L (vc<vl -> cmpl_out) | -0.31 | +0.30 | +0.61 |
| latch reset (cmpl_out -> clk fall) | -0.20 | +0.14 | +0.34 |
| charge: threshold-ratio term | -0.00 | -0.10 | -0.10 |
| charge: RC term (trim bank R, Ron, C) | -1.29 | +1.12 | +2.41 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -2.98 | +2.46 | +5.44 |
| measured eps (periods) | -2.98 | +2.46 | +5.44 |
| measured eps (20-period fosc) | -2.98 | +2.45 | +5.43 |

## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)

### ff, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +3.50 | +2.94 | +6.50 |
| latch set (cmph_out -> clk rise) | -0.51 | -0.34 | -0.86 |
| discharge (clk rise -> vc<vl) | -0.05 | -0.10 | -0.15 |
| comparator L (vc<vl -> cmpl_out) | -0.30 | +0.08 | -0.23 |
| latch reset (cmpl_out -> clk fall) | -0.25 | -0.12 | -0.37 |
| charge: threshold-ratio term | +0.12 | +0.05 | +0.16 |
| charge: RC term (trim bank R, Ron, C) | +3.03 | -0.65 | +2.43 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +5.51 | +1.87 | +7.48 |
| measured eps (periods) | +5.51 | n/a | +7.48 |
| measured eps (20-period fosc) | +5.47 | n/a | +7.46 |

### ff, 85 C, 3.3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3.3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +3.50 | -0.00 | +3.50 |
| latch set (cmph_out -> clk rise) | -0.51 | -0.00 | -0.51 |
| discharge (clk rise -> vc<vl) | -0.05 | -0.00 | -0.05 |
| comparator L (vc<vl -> cmpl_out) | -0.30 | -0.00 | -0.30 |
| latch reset (cmpl_out -> clk fall) | -0.25 | -0.00 | -0.25 |
| charge: threshold-ratio term | +0.12 | -0.00 | +0.12 |
| charge: RC term (trim bank R, Ron, C) | +3.03 | -0.00 | +3.03 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | +5.51 | +0.00 | +5.51 |
| measured eps (periods) | +5.51 | n/a | +5.51 |
| measured eps (20-period fosc) | +5.47 | n/a | +5.47 |

### ff, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.48 | -0.34 | -0.81 |
| latch set (cmph_out -> clk rise) | +0.58 | -0.24 | +0.34 |
| discharge (clk rise -> vc<vl) | +0.10 | -0.04 | +0.05 |
| comparator L (vc<vl -> cmpl_out) | +0.65 | -0.04 | +0.60 |
| latch reset (cmpl_out -> clk fall) | +0.24 | -0.09 | +0.15 |
| charge: threshold-ratio term | +0.01 | +0.01 | +0.02 |
| charge: RC term (trim bank R, Ron, C) | -5.14 | -0.37 | -5.45 |
| charge: cross term | +0.00 | +0.00 | +0.00 |
| **sum of stages** | -4.04 | -1.11 | -5.10 |
| measured eps (periods) | -4.04 | n/a | -5.10 |
| measured eps (20-period fosc) | -4.07 | n/a | -5.14 |

### ff, -40 C, 3.6 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3.6 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.48 | +0.31 | -0.18 |
| latch set (cmph_out -> clk rise) | +0.58 | +0.23 | +0.81 |
| discharge (clk rise -> vc<vl) | +0.10 | +0.03 | +0.13 |
| comparator L (vc<vl -> cmpl_out) | +0.65 | +0.01 | +0.66 |
| latch reset (cmpl_out -> clk fall) | +0.24 | +0.01 | +0.25 |
| charge: threshold-ratio term | +0.01 | -0.02 | -0.00 |
| charge: RC term (trim bank R, Ron, C) | -5.14 | +0.31 | -4.88 |
| charge: cross term | +0.00 | +0.00 | -0.00 |
| **sum of stages** | -4.04 | +0.87 | -3.20 |
| measured eps (periods) | -4.04 | n/a | -3.20 |
| measured eps (20-period fosc) | -4.07 | n/a | -3.17 |

### tt, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +1.06 | +0.73 | +1.78 |
| latch set (cmph_out -> clk rise) | -0.57 | -0.49 | -1.06 |
| discharge (clk rise -> vc<vl) | -0.23 | -0.10 | -0.34 |
| comparator L (vc<vl -> cmpl_out) | -0.54 | -0.12 | -0.65 |
| latch reset (cmpl_out -> clk fall) | -0.26 | -0.15 | -0.41 |
| charge: threshold-ratio term | +0.13 | +0.01 | +0.14 |
| charge: RC term (trim bank R, Ron, C) | +2.50 | -0.65 | +1.83 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +2.08 | -0.77 | +1.29 |
| measured eps (periods) | +2.08 | n/a | +1.29 |
| measured eps (20-period fosc) | +2.09 | n/a | +1.30 |

### tt, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.01 | -0.54 | -0.55 |
| latch set (cmph_out -> clk rise) | +0.67 | -0.35 | +0.31 |
| discharge (clk rise -> vc<vl) | +0.17 | -0.07 | +0.10 |
| comparator L (vc<vl -> cmpl_out) | +0.95 | -0.14 | +0.79 |
| latch reset (cmpl_out -> clk fall) | +0.29 | -0.11 | +0.18 |
| charge: threshold-ratio term | -0.09 | +0.04 | -0.05 |
| charge: RC term (trim bank R, Ron, C) | -4.26 | -0.58 | -4.77 |
| charge: cross term | -0.01 | +0.00 | -0.00 |
| **sum of stages** | -2.29 | -1.74 | -3.99 |
| measured eps (periods) | -2.29 | n/a | -3.99 |
| measured eps (20-period fosc) | -2.26 | n/a | -4.04 |

### ss, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.60 | +0.14 | +0.72 |
| latch set (cmph_out -> clk rise) | -0.63 | -0.61 | -1.23 |
| discharge (clk rise -> vc<vl) | -0.27 | -0.23 | -0.49 |
| comparator L (vc<vl -> cmpl_out) | -0.72 | -0.33 | -1.03 |
| latch reset (cmpl_out -> clk fall) | -0.33 | -0.21 | -0.53 |
| charge: threshold-ratio term | +0.10 | +0.15 | +0.25 |
| charge: RC term (trim bank R, Ron, C) | +2.09 | -1.48 | +0.55 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +0.82 | -2.57 | -1.76 |
| measured eps (periods) | +0.82 | n/a | -1.76 |
| measured eps (20-period fosc) | +0.81 | n/a | -1.73 |

### ss, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.23 | -0.71 | -0.48 |
| latch set (cmph_out -> clk rise) | +0.82 | -0.49 | +0.30 |
| discharge (clk rise -> vc<vl) | +0.21 | -0.05 | +0.15 |
| comparator L (vc<vl -> cmpl_out) | +1.29 | -0.49 | +0.77 |
| latch reset (cmpl_out -> clk fall) | +0.35 | -0.11 | +0.23 |
| charge: threshold-ratio term | -0.29 | +0.03 | -0.26 |
| charge: RC term (trim bank R, Ron, C) | -3.49 | -1.24 | -4.62 |
| charge: cross term | -0.01 | +0.00 | -0.02 |
| **sum of stages** | -0.89 | -3.07 | -3.93 |
| measured eps (periods) | -0.89 | n/a | -3.93 |
| measured eps (20-period fosc) | -0.89 | n/a | -3.88 |

## Bias gate voltages (3.3 V ref points, V)

| point | ibias gate | pb | vh | vl |
|---|---|---|---|---|
| tt -40 C 3 V | 0.6886 | 1.8136 | 1.9997 | 0.9995 |
| tt -40 C 3.3 V | 0.6927 | 2.0828 | 2.1997 | 1.0994 |
| tt -40 C 3.6 V | 0.6946 | 2.3505 | 2.4006 | 1.2002 |
| tt 27 C 3 V | 0.7814 | 1.8003 | 1.9999 | 0.9996 |
| tt 27 C 3.3 V | 0.7829 | 2.0743 | 2.1996 | 1.0991 |
| tt 27 C 3.6 V | 0.7829 | 2.3454 | 2.3993 | 1.1992 |
| tt 85 C 3 V | 0.8716 | 1.7644 | 1.9995 | 0.9995 |
| tt 85 C 3.3 V | 0.8702 | 2.0425 | 2.1991 | 1.0989 |
| tt 85 C 3.6 V | 0.8686 | 2.3182 | 2.3997 | 1.1995 |
| ff -40 C 3 V | 0.6254 | 1.8787 | 1.9995 | 0.9993 |
| ff -40 C 3.3 V | 0.6292 | 2.1476 | 2.1997 | 1.0993 |
| ff -40 C 3.6 V | 0.6297 | 2.4147 | 2.3997 | 1.1994 |
| ff 27 C 3 V | 0.7261 | 1.8505 | 2.0002 | 0.9997 |
| ff 27 C 3.3 V | 0.7270 | 2.1235 | 2.2003 | 1.0998 |
| ff 27 C 3.6 V | 0.7266 | 2.3945 | 2.3993 | 1.1990 |
| ff 85 C 3 V | 0.8310 | 1.7972 | 1.9991 | 0.9989 |
| ff 85 C 3.3 V | 0.8270 | 2.0742 | 2.1995 | 1.0991 |
| ff 85 C 3.6 V | 0.8218 | 2.3492 | 2.3997 | 1.1993 |
| ss -40 C 3 V | 0.7539 | 1.7437 | 2.0007 | 1.0003 |
| ss -40 C 3.3 V | 0.7580 | 2.0134 | 2.2006 | 1.1002 |
| ss -40 C 3.6 V | 0.7605 | 2.2802 | 2.3999 | 1.2000 |
| ss 27 C 3 V | 0.8469 | 1.7358 | 1.9997 | 0.9996 |
| ss 27 C 3.3 V | 0.8456 | 2.0105 | 2.1987 | 1.0990 |
| ss 27 C 3.6 V | 0.8473 | 2.2839 | 2.3995 | 1.1995 |
| ss 85 C 3 V | 0.9341 | 1.7073 | 1.9987 | 0.9989 |
| ss 85 C 3.3 V | 0.9320 | 1.9889 | 2.1996 | 1.0991 |
| ss 85 C 3.6 V | 0.9303 | 2.2665 | 2.4007 | 1.1999 |

