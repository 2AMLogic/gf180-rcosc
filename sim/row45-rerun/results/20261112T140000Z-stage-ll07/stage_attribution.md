# Stage-level attribution of rows 4 / 5 (generated; source sim/row45-rerun/results/20261112T140000Z-stage-ll07)

Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code (tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.

## Reference points (3.3 V / 27 C)

| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 165 | 47.90 | 20.877 | 2.245 | 0.898 | 0.052 | 1.740 | 0.339 | 15.603 | 0.6664 | 0.3331 |
| ff | 78 | 47.95 | 20.856 | 1.930 | 0.769 | -0.024 | 1.559 | 0.299 | 16.324 | 0.6666 | 0.3332 |
| ss | 212 | 48.04 | 20.818 | 2.568 | 1.061 | 0.103 | 1.948 | 0.415 | 14.722 | 0.6661 | 0.3328 |

Residuals over all 27 points: event gaps vs period 0.0000 % of T; 3-edge period vs 20-period fosc 0.095 % of T.

## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)

### tt, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.35 | +0.35 | +0.71 |
| latch set (cmph_out -> clk rise) | -0.40 | +0.33 | +0.73 |
| discharge (clk rise -> vc<vl) | -0.12 | +0.13 | +0.24 |
| comparator L (vc<vl -> cmpl_out) | -0.09 | +0.16 | +0.25 |
| latch reset (cmpl_out -> clk fall) | -0.14 | +0.03 | +0.16 |
| charge: threshold-ratio term | +0.01 | -0.05 | -0.06 |
| charge: RC term (trim bank R, Ron, C) | -0.84 | +0.64 | +1.48 |
| charge: cross term | +0.00 | +0.00 | +0.00 |
| **sum of stages** | -1.93 | +1.58 | +3.51 |
| measured eps (periods) | -1.93 | +1.58 | +3.51 |
| measured eps (20-period fosc) | -1.93 | +1.57 | +3.50 |

### ff, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.17 | +0.17 | +0.34 |
| latch set (cmph_out -> clk rise) | -0.35 | +0.18 | +0.53 |
| discharge (clk rise -> vc<vl) | -0.07 | +0.06 | +0.13 |
| comparator L (vc<vl -> cmpl_out) | +0.04 | -0.05 | -0.09 |
| latch reset (cmpl_out -> clk fall) | -0.02 | +0.09 | +0.11 |
| charge: threshold-ratio term | -0.02 | -0.03 | -0.01 |
| charge: RC term (trim bank R, Ron, C) | -0.44 | +0.47 | +0.91 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -1.03 | +0.89 | +1.92 |
| measured eps (periods) | -1.03 | +0.89 | +1.92 |
| measured eps (20-period fosc) | -1.06 | +0.90 | +1.96 |

### ss, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)

| stage | 3.0 V | 3.6 V | span |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.45 | +0.47 | +0.92 |
| latch set (cmph_out -> clk rise) | -0.54 | +0.48 | +1.02 |
| discharge (clk rise -> vc<vl) | -0.20 | +0.06 | +0.27 |
| comparator L (vc<vl -> cmpl_out) | -0.41 | +0.30 | +0.71 |
| latch reset (cmpl_out -> clk fall) | -0.16 | +0.13 | +0.29 |
| charge: threshold-ratio term | -0.04 | -0.18 | -0.14 |
| charge: RC term (trim bank R, Ron, C) | -1.59 | +1.46 | +3.05 |
| charge: cross term | -0.00 | +0.00 | +0.00 |
| **sum of stages** | -3.39 | +2.72 | +6.12 |
| measured eps (periods) | -3.39 | +2.72 | +6.12 |
| measured eps (20-period fosc) | -3.37 | +2.72 | +6.09 |

## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)

### ff, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.66 | +0.20 | +0.85 |
| latch set (cmph_out -> clk rise) | -0.55 | -0.34 | -0.89 |
| discharge (clk rise -> vc<vl) | -0.10 | -0.08 | -0.18 |
| comparator L (vc<vl -> cmpl_out) | -0.35 | +0.13 | -0.21 |
| latch reset (cmpl_out -> clk fall) | -0.18 | -0.13 | -0.31 |
| charge: threshold-ratio term | +0.06 | +0.00 | +0.06 |
| charge: RC term (trim bank R, Ron, C) | +2.91 | -0.52 | +2.36 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | +2.45 | -0.75 | +1.68 |
| measured eps (periods) | +2.45 | n/a | +1.68 |
| measured eps (20-period fosc) | +2.43 | n/a | +1.65 |

### ff, 85 C, 3.3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3.3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.66 | -0.00 | +0.66 |
| latch set (cmph_out -> clk rise) | -0.55 | -0.00 | -0.55 |
| discharge (clk rise -> vc<vl) | -0.10 | -0.00 | -0.10 |
| comparator L (vc<vl -> cmpl_out) | -0.35 | -0.00 | -0.35 |
| latch reset (cmpl_out -> clk fall) | -0.18 | -0.00 | -0.18 |
| charge: threshold-ratio term | +0.06 | -0.00 | +0.06 |
| charge: RC term (trim bank R, Ron, C) | +2.91 | -0.00 | +2.91 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | +2.45 | +0.00 | +2.45 |
| measured eps (periods) | +2.45 | n/a | +2.45 |
| measured eps (20-period fosc) | +2.43 | n/a | +2.43 |

### ff, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.08 | -0.34 | -0.41 |
| latch set (cmph_out -> clk rise) | +0.56 | -0.24 | +0.31 |
| discharge (clk rise -> vc<vl) | +0.11 | -0.07 | +0.05 |
| comparator L (vc<vl -> cmpl_out) | +0.67 | -0.04 | +0.62 |
| latch reset (cmpl_out -> clk fall) | +0.29 | -0.10 | +0.19 |
| charge: threshold-ratio term | -0.03 | +0.01 | -0.02 |
| charge: RC term (trim bank R, Ron, C) | -4.71 | -0.45 | -5.10 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | -3.19 | -1.21 | -4.36 |
| measured eps (periods) | -3.19 | n/a | -4.36 |
| measured eps (20-period fosc) | -3.22 | n/a | -4.39 |

### ff, -40 C, 3.6 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3.6 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | -0.08 | +0.30 | +0.22 |
| latch set (cmph_out -> clk rise) | +0.56 | +0.19 | +0.75 |
| discharge (clk rise -> vc<vl) | +0.11 | +0.02 | +0.13 |
| comparator L (vc<vl -> cmpl_out) | +0.67 | +0.02 | +0.69 |
| latch reset (cmpl_out -> clk fall) | +0.29 | +0.03 | +0.32 |
| charge: threshold-ratio term | -0.03 | -0.02 | -0.05 |
| charge: RC term (trim bank R, Ron, C) | -4.71 | +0.41 | -4.34 |
| charge: cross term | -0.00 | +0.00 | -0.00 |
| **sum of stages** | -3.19 | +0.94 | -2.28 |
| measured eps (periods) | -3.19 | n/a | -2.28 |
| measured eps (20-period fosc) | -3.22 | n/a | -2.25 |

### tt, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.36 | -0.14 | +0.21 |
| latch set (cmph_out -> clk rise) | -0.58 | -0.49 | -1.06 |
| discharge (clk rise -> vc<vl) | -0.14 | -0.14 | -0.28 |
| comparator L (vc<vl -> cmpl_out) | -0.51 | -0.08 | -0.58 |
| latch reset (cmpl_out -> clk fall) | -0.27 | -0.16 | -0.42 |
| charge: threshold-ratio term | +0.01 | -0.00 | +0.01 |
| charge: RC term (trim bank R, Ron, C) | +2.70 | -0.80 | +1.85 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | +1.57 | -1.80 | -0.27 |
| measured eps (periods) | +1.57 | n/a | -0.27 |
| measured eps (20-period fosc) | +1.52 | n/a | -0.26 |

### tt, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.14 | -0.47 | -0.34 |
| latch set (cmph_out -> clk rise) | +0.66 | -0.32 | +0.33 |
| discharge (clk rise -> vc<vl) | +0.20 | -0.09 | +0.11 |
| comparator L (vc<vl -> cmpl_out) | +0.98 | -0.23 | +0.73 |
| latch reset (cmpl_out -> clk fall) | +0.29 | -0.08 | +0.21 |
| charge: threshold-ratio term | -0.13 | +0.00 | -0.13 |
| charge: RC term (trim bank R, Ron, C) | -4.47 | -0.81 | -5.19 |
| charge: cross term | -0.01 | +0.00 | -0.01 |
| **sum of stages** | -2.35 | -2.00 | -4.30 |
| measured eps (periods) | -2.35 | n/a | -4.30 |
| measured eps (20-period fosc) | -2.33 | n/a | -4.26 |

### ss, 85 C, 3 V

| stage | T step (85 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.21 | -0.25 | -0.05 |
| latch set (cmph_out -> clk rise) | -0.64 | -0.61 | -1.22 |
| discharge (clk rise -> vc<vl) | -0.23 | -0.25 | -0.48 |
| comparator L (vc<vl -> cmpl_out) | -0.77 | -0.30 | -1.05 |
| latch reset (cmpl_out -> clk fall) | -0.30 | -0.21 | -0.50 |
| charge: threshold-ratio term | +0.10 | -0.04 | +0.06 |
| charge: RC term (trim bank R, Ron, C) | +2.03 | -1.55 | +0.42 |
| charge: cross term | -0.00 | -0.00 | -0.00 |
| **sum of stages** | +0.40 | -3.21 | -2.82 |
| measured eps (periods) | +0.40 | n/a | -2.82 |
| measured eps (20-period fosc) | +0.40 | n/a | -2.81 |

### ss, -40 C, 3 V

| stage | T step (-40 C @3.3 V) | V step (3.3->3 V) | total |
|---|---|---|---|
| comparator H (vc>vh -> cmph_out) | +0.34 | -0.68 | -0.34 |
| latch set (cmph_out -> clk rise) | +0.80 | -0.48 | +0.29 |
| discharge (clk rise -> vc<vl) | +0.24 | -0.08 | +0.15 |
| comparator L (vc<vl -> cmpl_out) | +1.29 | -0.56 | +0.68 |
| latch reset (cmpl_out -> clk fall) | +0.37 | -0.12 | +0.24 |
| charge: threshold-ratio term | -0.31 | +0.01 | -0.29 |
| charge: RC term (trim bank R, Ron, C) | -3.35 | -1.58 | -4.81 |
| charge: cross term | -0.01 | +0.00 | -0.02 |
| **sum of stages** | -0.64 | -3.49 | -4.11 |
| measured eps (periods) | -0.64 | n/a | -4.11 |
| measured eps (20-period fosc) | -0.72 | n/a | -4.09 |

## Bias gate voltages (3.3 V ref points, V)

| point | ibias gate | pb | vh | vl |
|---|---|---|---|---|
| tt -40 C 3 V | 0.6860 | 1.8140 | 2.0000 | 0.9996 |
| tt -40 C 3.3 V | 0.6887 | 2.0824 | 2.1999 | 1.0996 |
| tt -40 C 3.6 V | 0.6927 | 2.3504 | 2.4001 | 1.1997 |
| tt 27 C 3 V | 0.7774 | 1.7995 | 1.9992 | 0.9991 |
| tt 27 C 3.3 V | 0.7782 | 2.0732 | 2.1990 | 1.0991 |
| tt 27 C 3.6 V | 0.7813 | 2.3462 | 2.3997 | 1.1992 |
| tt 85 C 3 V | 0.8676 | 1.7650 | 2.0005 | 1.0002 |
| tt 85 C 3.3 V | 0.8654 | 2.0425 | 2.2002 | 1.1000 |
| tt 85 C 3.6 V | 0.8663 | 2.3187 | 2.3998 | 1.1993 |
| ff -40 C 3 V | 0.6230 | 1.8786 | 1.9994 | 0.9992 |
| ff -40 C 3.3 V | 0.6253 | 2.1471 | 2.1997 | 1.0994 |
| ff -40 C 3.6 V | 0.6273 | 2.4147 | 2.3998 | 1.1994 |
| ff 27 C 3 V | 0.7237 | 1.8503 | 1.9998 | 0.9995 |
| ff 27 C 3.3 V | 0.7244 | 2.1229 | 2.1996 | 1.0994 |
| ff 27 C 3.6 V | 0.7244 | 2.3947 | 2.3999 | 1.1994 |
| ff 85 C 3 V | 0.8253 | 1.7970 | 1.9996 | 0.9994 |
| ff 85 C 3.3 V | 0.8237 | 2.0740 | 2.1995 | 1.0992 |
| ff 85 C 3.6 V | 0.8204 | 2.3494 | 2.3997 | 1.1992 |
| ss -40 C 3 V | 0.7494 | 1.7431 | 2.0008 | 1.0004 |
| ss -40 C 3.3 V | 0.7526 | 2.0126 | 2.2009 | 1.1005 |
| ss -40 C 3.6 V | 0.7582 | 2.2800 | 2.3989 | 1.1990 |
| ss 27 C 3 V | 0.8427 | 1.7354 | 1.9997 | 0.9995 |
| ss 27 C 3.3 V | 0.8426 | 2.0103 | 2.1981 | 1.0983 |
| ss 27 C 3.6 V | 0.8449 | 2.2849 | 2.4005 | 1.1998 |
| ss 85 C 3 V | 0.9304 | 1.7080 | 1.9998 | 0.9996 |
| ss 85 C 3.3 V | 0.9272 | 1.9879 | 2.1985 | 1.0983 |
| ss 85 C 3.6 V | 0.9257 | 2.2664 | 2.4013 | 1.2004 |

