# Stage-level attribution of rows 4 / 5 (generated; source results/20261112T070000Z)

Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code (tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.

## Reference points (3.3 V / 27 C)

| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 165 | 48.14 | 20.773 | 2.227 | 0.895 | 0.047 | 1.733 | 0.339 | 15.533 | 0.6664 | 0.3330 |
| ff | 78 | 47.97 | 20.848 | 1.836 | 0.767 | -0.023 | 1.547 | 0.292 | 16.429 | 0.6668 | 0.3333 |
| ss | 212 | 47.95 | 20.855 | 2.592 | 1.061 | 0.100 | 1.945 | 0.417 | 14.740 | 0.6662 | 0.3329 |

Residuals over all 27 points: event gaps vs period 0.0000 % of T; 3-edge period vs 20-period fosc 0.058 % of T.

## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)

### tt, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.26 | +0.32 | +0.58 |
| latch set (cmph_out -> clk rise) | -0.43 | +0.33 | +0.76 |
| discharge (clk rise -> vc<vl) | -0.14 | +0.11 | +0.25 |
| comparator L (vc<vl -> cmpl_out) | -0.14 | +0.03 | +0.17 |
| latch reset (cmpl_out -> clk fall) | -0.14 | +0.09 | +0.23 |
| charge: threshold-ratio term | -0.01 | -0.03 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | -0.80 | +0.73 | +1.53 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -1.93 | +1.59 | +3.51 |
| measured eps (periods) | -1.93 | +1.59 | +3.51 |
| measured eps (20-period fosc) | -1.92 | +1.55 | +3.48 |

### ff, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.18 | +0.04 | -0.14 |
| latch set (cmph_out -> clk rise) | -0.35 | +0.25 | +0.60 |
| discharge (clk rise -> vc<vl) | -0.06 | +0.07 | +0.13 |
| comparator L (vc<vl -> cmpl_out) | -0.01 | -0.09 | -0.09 |
| latch reset (cmpl_out -> clk fall) | -0.08 | +0.05 | +0.12 |
| charge: threshold-ratio term | +0.01 | +0.05 | +0.05 |
| charge: RC term (trim bank R, Ron, C) | -0.51 | +0.38 | +0.89 |
| charge: cross term | +0.00 | -0.00 | -0.00 |
| **sum of stages** | -0.81 | +0.75 | +1.55 |
| measured eps (periods) | -0.81 | +0.75 | +1.55 |
| measured eps (20-period fosc) | -0.78 | +0.78 | +1.55 |

### ss, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.41 | +0.48 | +0.89 |
| latch set (cmph_out -> clk rise) | -0.52 | +0.45 | +0.97 |
| discharge (clk rise -> vc<vl) | -0.21 | +0.10 | +0.31 |
| comparator L (vc<vl -> cmpl_out) | -0.40 | +0.26 | +0.65 |
| latch reset (cmpl_out -> clk fall) | -0.19 | +0.14 | +0.33 |
| charge: threshold-ratio term | -0.04 | -0.11 | -0.07 |
| charge: RC term (trim bank R, Ron, C) | -1.60 | +1.43 | +3.03 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -3.38 | +2.75 | +6.13 |
| measured eps (periods) | -3.38 | +2.75 | +6.13 |
| measured eps (20-period fosc) | -3.37 | +2.73 | +6.10 |

## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)

### ff, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +3.38 | +2.84 | +6.27 |
| latch set (cmph_out -> clk rise) | -0.57 | -0.34 | -0.93 |
| discharge (clk rise -> vc<vl) | -0.07 | -0.09 | -0.16 |
| comparator L (vc<vl -> cmpl_out) | -0.41 | +0.10 | -0.31 |
| latch reset (cmpl_out -> clk fall) | -0.21 | -0.16 | -0.37 |
| charge: threshold-ratio term | +0.13 | +0.01 | +0.15 |
| charge: RC term (trim bank R, Ron, C) | +2.85 | -0.67 | +2.23 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +5.10 | +1.70 | +6.88 |
| measured eps (periods) | +5.10 | n/a | +6.88 |
| measured eps (20-period fosc) | +5.10 | n/a | +6.93 |

### ff, 85 C, 3.3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3.3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +3.38 | -0.00 | +3.38 |
| latch set (cmph_out -> clk rise) | -0.57 | -0.00 | -0.57 |
| discharge (clk rise -> vc<vl) | -0.07 | -0.00 | -0.07 |
| comparator L (vc<vl -> cmpl_out) | -0.41 | -0.00 | -0.41 |
| latch reset (cmpl_out -> clk fall) | -0.21 | -0.00 | -0.21 |
| charge: threshold-ratio term | +0.13 | -0.00 | +0.13 |
| charge: RC term (trim bank R, Ron, C) | +2.85 | -0.00 | +2.85 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | +5.10 | +0.00 | +5.10 |
| measured eps (periods) | +5.10 | n/a | +5.10 |
| measured eps (20-period fosc) | +5.10 | n/a | +5.10 |

### ff, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.47 | -0.32 | -0.79 |
| latch set (cmph_out -> clk rise) | +0.54 | -0.24 | +0.29 |
| discharge (clk rise -> vc<vl) | +0.10 | -0.06 | +0.04 |
| comparator L (vc<vl -> cmpl_out) | +0.60 | -0.03 | +0.56 |
| latch reset (cmpl_out -> clk fall) | +0.24 | -0.05 | +0.19 |
| charge: threshold-ratio term | -0.00 | -0.04 | -0.04 |
| charge: RC term (trim bank R, Ron, C) | -4.74 | -0.45 | -5.13 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | -3.74 | -1.18 | -4.88 |
| measured eps (periods) | -3.74 | n/a | -4.88 |
| measured eps (20-period fosc) | -3.69 | n/a | -4.86 |

### ff, -40 C, 3.6 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3.6 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.47 | +0.31 | -0.16 |
| latch set (cmph_out -> clk rise) | +0.54 | +0.22 | +0.76 |
| discharge (clk rise -> vc<vl) | +0.10 | +0.07 | +0.17 |
| comparator L (vc<vl -> cmpl_out) | +0.60 | +0.06 | +0.66 |
| latch reset (cmpl_out -> clk fall) | +0.24 | +0.04 | +0.28 |
| charge: threshold-ratio term | -0.00 | +0.01 | +0.01 |
| charge: RC term (trim bank R, Ron, C) | -4.74 | +0.38 | -4.41 |
| charge: cross term | -0.00 | -0.00 | +0.00 |
| **sum of stages** | -3.74 | +1.08 | -2.70 |
| measured eps (periods) | -3.74 | n/a | -2.70 |
| measured eps (20-period fosc) | -3.69 | n/a | -2.69 |

### tt, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +1.03 | +0.70 | +1.72 |
| latch set (cmph_out -> clk rise) | -0.62 | -0.47 | -1.09 |
| discharge (clk rise -> vc<vl) | -0.14 | -0.13 | -0.27 |
| comparator L (vc<vl -> cmpl_out) | -0.54 | -0.06 | -0.60 |
| latch reset (cmpl_out -> clk fall) | -0.27 | -0.20 | -0.46 |
| charge: threshold-ratio term | +0.09 | -0.10 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | +2.50 | -0.76 | +1.72 |
| charge: cross term | -0.00 | -0.00 | +0.00 |
| **sum of stages** | +2.06 | -1.04 | +1.00 |
| measured eps (periods) | +2.06 | n/a | +1.00 |
| measured eps (20-period fosc) | +2.02 | n/a | +1.00 |

### tt, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.00 | -0.53 | -0.54 |
| latch set (cmph_out -> clk rise) | +0.67 | -0.35 | +0.31 |
| discharge (clk rise -> vc<vl) | +0.19 | -0.06 | +0.12 |
| comparator L (vc<vl -> cmpl_out) | +0.93 | -0.22 | +0.70 |
| latch reset (cmpl_out -> clk fall) | +0.29 | -0.09 | +0.20 |
| charge: threshold-ratio term | -0.11 | +0.04 | -0.07 |
| charge: RC term (trim bank R, Ron, C) | -4.18 | -0.90 | -4.99 |
| charge: cross term | -0.01 | +0.00 | -0.00 |
| **sum of stages** | -2.22 | -2.11 | -4.29 |
| measured eps (periods) | -2.22 | n/a | -4.29 |
| measured eps (20-period fosc) | -2.28 | n/a | -4.26 |

### ss, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.55 | +0.08 | +0.62 |
| latch set (cmph_out -> clk rise) | -0.62 | -0.62 | -1.22 |
| discharge (clk rise -> vc<vl) | -0.24 | -0.26 | -0.49 |
| comparator L (vc<vl -> cmpl_out) | -0.78 | -0.30 | -1.05 |
| latch reset (cmpl_out -> clk fall) | -0.29 | -0.21 | -0.49 |
| charge: threshold-ratio term | +0.08 | +0.01 | +0.08 |
| charge: RC term (trim bank R, Ron, C) | +1.98 | -1.67 | +0.25 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +0.67 | -2.96 | -2.31 |
| measured eps (periods) | +0.67 | n/a | -2.31 |
| measured eps (20-period fosc) | +0.67 | n/a | -2.31 |

### ss, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.27 | -0.68 | -0.42 |
| latch set (cmph_out -> clk rise) | +0.82 | -0.47 | +0.32 |
| discharge (clk rise -> vc<vl) | +0.20 | -0.10 | +0.09 |
| comparator L (vc<vl -> cmpl_out) | +1.23 | -0.52 | +0.67 |
| latch reset (cmpl_out -> clk fall) | +0.39 | -0.11 | +0.26 |
| charge: threshold-ratio term | -0.29 | +0.04 | -0.24 |
| charge: RC term (trim bank R, Ron, C) | -3.35 | -1.61 | -4.84 |
| charge: cross term | -0.01 | +0.00 | -0.02 |
| **sum of stages** | -0.74 | -3.46 | -4.18 |
| measured eps (periods) | -0.74 | n/a | -4.18 |
| measured eps (20-period fosc) | -0.76 | n/a | -4.21 |

## Bias gate voltages (3.3 V ref points, V)

| point | ibias gate | pb | vh | vl |
|---|---|---|---|---|
| tt -40 C 3 V | 0.6857 | 1.8134 | 1.9993 | 0.9992 |
| tt -40 C 3.3 V | 0.6889 | 2.0824 | 2.1995 | 1.0993 |
| tt -40 C 3.6 V | 0.6910 | 2.3501 | 2.4005 | 1.2001 |
| tt 27 C 3 V | 0.7787 | 1.8002 | 1.9997 | 0.9993 |
| tt 27 C 3.3 V | 0.7796 | 2.0739 | 2.1991 | 1.0988 |
| tt 27 C 3.6 V | 0.7800 | 2.3453 | 2.3992 | 1.1991 |
| tt 85 C 3 V | 0.8692 | 1.7652 | 2.0010 | 1.0004 |
| tt 85 C 3.3 V | 0.8670 | 2.0424 | 2.1989 | 1.0989 |
| tt 85 C 3.6 V | 0.8655 | 2.3182 | 2.3997 | 1.1995 |
| ff -40 C 3 V | 0.6226 | 1.8788 | 2.0002 | 0.9998 |
| ff -40 C 3.3 V | 0.6255 | 2.1472 | 2.2000 | 1.0996 |
| ff -40 C 3.6 V | 0.6274 | 2.4147 | 2.3997 | 1.1993 |
| ff 27 C 3 V | 0.7244 | 1.8504 | 2.0001 | 0.9997 |
| ff 27 C 3.3 V | 0.7248 | 2.1234 | 2.2003 | 1.0998 |
| ff 27 C 3.6 V | 0.7250 | 2.3947 | 2.3996 | 1.1991 |
| ff 85 C 3 V | 0.8292 | 1.7970 | 1.9992 | 0.9991 |
| ff 85 C 3.3 V | 0.8251 | 2.0740 | 2.1992 | 1.0990 |
| ff 85 C 3.6 V | 0.8196 | 2.3492 | 2.3997 | 1.1993 |
| ss -40 C 3 V | 0.7506 | 1.7436 | 2.0005 | 0.9999 |
| ss -40 C 3.3 V | 0.7531 | 2.0127 | 2.2008 | 1.1003 |
| ss -40 C 3.6 V | 0.7579 | 2.2798 | 2.3989 | 1.1991 |
| ss 27 C 3 V | 0.8425 | 1.7353 | 1.9998 | 0.9997 |
| ss 27 C 3.3 V | 0.8419 | 2.0101 | 2.1984 | 1.0987 |
| ss 27 C 3.6 V | 0.8447 | 2.2842 | 2.3993 | 1.1990 |
| ss 85 C 3 V | 0.9310 | 1.7081 | 2.0000 | 0.9997 |
| ss 85 C 3.3 V | 0.9277 | 1.9882 | 2.1988 | 1.0986 |
| ss 85 C 3.6 V | 0.9259 | 2.2664 | 2.4012 | 1.2003 |

