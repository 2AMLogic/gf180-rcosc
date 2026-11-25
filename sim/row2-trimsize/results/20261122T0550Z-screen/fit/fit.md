# Row-2 trim-bank effective bit-weight fit (offline, committed #87 campaign)

- compensation corner: `ext_tt_27C_3p3V`
- ratified: mean step 0.3137 %/code, half-LSB 0.1569 %, ends ratio 2.3333 (28.8-67.2 MHz)

## Per-curve fit (T = intercept + sum bit_b * beta_b)

| curve | f(0x00) MHz | f(0xFF) MHz | mean step % | worst+ % | worst- % | nonpos | max resid %T |
|---|---|---|---|---|---|---|---
| ext_tt_27C_3p3V | 28.652 | 76.419 | 0.6538 | 1.064 | -9.399 | 5 | 4.49 |
| ext_ss_m40C_3p0V | 21.319 | 58.719 | 0.6880 | 1.094 | -10.483 | 8 | 6.67 |
| ext_ff_85C_3p6V | 39.610 | 103.388 | 0.6314 | 1.274 | -8.693 | 5 | 2.89 |

## Weight ratios rho_b (1.000 = binary-exact)

| curve | b0 | b1 | b2 | b3 | b4 | b5 | b6 | b7 | B s/ohm | Ron b0..b7 ohm |
|---|---|---|---|---|---|---|---|---|---|
| ext_tt_27C_3p3V | 1.192 | 1.184 | 1.192 | 1.165 | 1.156 | 1.131 | 1.052 | 0.901 | 2.741e-13 | -495,-743,-991,-1486,-1982,-2378,-2973,-3964 |
| ext_ss_m40C_3p0V | 1.399 | 1.300 | 1.260 | 1.201 | 1.170 | 1.129 | 1.040 | 0.898 | 3.746e-13 | -522,-783,-1045,-1567,-2089,-2507,-3134,-4178 |
| ext_ff_85C_3p6V | 1.101 | 1.128 | 1.152 | 1.146 | 1.158 | 1.143 | 1.065 | 0.895 | 1.913e-13 | -526,-788,-1051,-1577,-2102,-2523,-3153,-4205 |

## Measured DR-0021 carries (% f-step / ns T-step)

| ext_tt_27C_3p3V | 0x7F->0x80: -9.40%/+2.33ns | 0xBF->0xC0: -5.60%/+1.07ns | 0xDF->0xE0: -3.64%/+0.59ns | 0xEF->0xF0: -2.64%/+0.39ns |
| ext_ss_m40C_3p0V | 0x7F->0x80: -10.48%/+3.45ns | 0xBF->0xC0: -7.13%/+1.78ns | 0xDF->0xE0: -4.34%/+0.91ns | 0xEF->0xF0: -3.17%/+0.60ns |
| ext_ff_85C_3p6V | 0x7F->0x80: -8.69%/+1.59ns | 0xBF->0xC0: -4.98%/+0.71ns | 0xDF->0xE0: -3.35%/+0.40ns | 0xEF->0xF0: -1.95%/+0.21ns |

## Sizing proposals (drawn lengths, um; r_width 2u unchanged)

| name | RFIX | r0..r7 | f_lo/f_hi MHz (tt) | ss top margin MHz | ff bottom margin MHz |
|---|---|---|---|---|---|
| F1.85 | 30.871 | 0.181,0.451,0.977,2.087,4.293,8.855,19.146,44.825 | 34.24/63.34 | +0.67 | +0.67 |
| F1.95 | 28.379 | 0.212,0.506,1.079,2.288,4.692,9.662,20.873,48.847 | 33.32/64.98 | +1.93 | +1.93 |
| F2.50 | 22.837 | 0.401,0.839,1.694,3.499,7.085,14.503,31.234,72.983 | 27.50/68.75 | +4.83 | +9.98 |

Predicted residual carries at the non-compensation corners (period step / W; negative = monotone f-increase): see fit.json `proposals.*.predict_*`.
