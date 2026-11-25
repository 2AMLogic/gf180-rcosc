# Dense trim-code step analysis

**MEASURED CAMPAIGN DATA (analysis only; verdict belongs to #87)**

Nominal step 0.313725 %/code, half-LSB 0.156863 % (80 %/255; DR-0003). Step = 100*(f[c+1]/f[c]-1). Comparison is descriptive; verdict belongs to #87.

## s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256 / tt_27C_3p3V: OK

- f[0x00] = 27.066921 MHz, f[0xFF] = 53.151393 MHz, span +96.3703 %
- worst positive step: 0x3F->0x40 +2.20758 %
- worst negative step: 0xDF->0xE0 -3.94022 %
- smallest / largest signed step: 0xDF->0xE0 -3.94022 % / 0x3F->0x40 +2.20758 %
- non-positive transitions: 15
  - 0x7F->0x80 -0.13489 %
  - 0xBF->0xC0 -3.75648 %
  - 0xDF->0xE0 -3.94022 %
  - 0xE8->0xE9 -0.02515 %
  - 0xEC->0xED -0.07962 %
  - 0xEE->0xEF -0.02144 %
  - 0xEF->0xF0 -1.62905 %
  - 0xF0->0xF1 -0.26097 %
  - 0xF2->0xF3 -0.25209 %
  - 0xF4->0xF5 -0.39094 %
  - 0xF6->0xF7 -0.26855 %
  - 0xF8->0xF9 -0.68769 %
  - 0xFA->0xFB -0.50181 %
  - 0xFC->0xFD -0.73321 %
  - 0xFE->0xFF -0.61649 %
- carry transitions:
  - 0x7F->0x80: -0.13489 %
  - 0xBF->0xC0: -3.75648 %
  - 0xDF->0xE0: -3.94022 %
  - 0xEF->0xF0: -1.62905 %
- mean step 0.37792 %/code (1.2046 x nominal)
- steps outside nominal +/- half-LSB: 65; max |deviation| 4.25394 % (13.559 LSB) at 0xDF->0xE0

## s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256 / ss_m40C_3p0V: OK

- f[0x00] = 20.121088 MHz, f[0xFF] = 40.401161 MHz, span +100.7901 %
- worst positive step: 0x3F->0x40 +1.55422 %
- worst negative step: 0xDF->0xE0 -4.36601 %
- smallest / largest signed step: 0xDF->0xE0 -4.36601 % / 0x3F->0x40 +1.55422 %
- non-positive transitions: 13
  - 0x7F->0x80 -0.58049 %
  - 0xBF->0xC0 -3.97237 %
  - 0xDF->0xE0 -4.36601 %
  - 0xEF->0xF0 -2.46140 %
  - 0xF0->0xF1 -0.22132 %
  - 0xF2->0xF3 -0.08330 %
  - 0xF4->0xF5 -0.21280 %
  - 0xF6->0xF7 -0.13424 %
  - 0xF7->0xF8 -0.39488 %
  - 0xF8->0xF9 -0.41866 %
  - 0xFA->0xFB -0.61272 %
  - 0xFC->0xFD -0.78903 %
  - 0xFE->0xFF -0.75918 %
- carry transitions:
  - 0x7F->0x80: -0.58049 %
  - 0xBF->0xC0: -3.97237 %
  - 0xDF->0xE0: -4.36601 %
  - 0xEF->0xF0: -2.46140 %
- mean step 0.39526 %/code (1.2599 x nominal)
- steps outside nominal +/- half-LSB: 56; max |deviation| 4.67974 % (14.917 LSB) at 0xDF->0xE0

## s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256 / ff_85C_3p6V: OK

- f[0x00] = 37.487930 MHz, f[0xFF] = 71.625839 MHz, span +91.0637 %
- worst positive step: 0x3F->0x40 +2.66525 %
- worst negative step: 0xBF->0xC0 -4.19259 %
- smallest / largest signed step: 0xBF->0xC0 -4.19259 % / 0x3F->0x40 +2.66525 %
- non-positive transitions: 19
  - 0x7F->0x80 -0.26845 %
  - 0xBF->0xC0 -4.19259 %
  - 0xDF->0xE0 -3.72250 %
  - 0xE0->0xE1 -0.06939 %
  - 0xE2->0xE3 -0.02652 %
  - 0xE4->0xE5 -0.00174 %
  - 0xE8->0xE9 -0.09726 %
  - 0xEA->0xEB -0.03801 %
  - 0xEC->0xED -0.10707 %
  - 0xEE->0xEF -0.03881 %
  - 0xEF->0xF0 -1.04393 %
  - 0xF0->0xF1 -0.42034 %
  - 0xF2->0xF3 -0.36227 %
  - 0xF4->0xF5 -0.44275 %
  - 0xF6->0xF7 -0.33970 %
  - 0xF8->0xF9 -0.66539 %
  - 0xFA->0xFB -0.61377 %
  - 0xFC->0xFD -0.74339 %
  - 0xFE->0xFF -0.77640 %
- carry transitions:
  - 0x7F->0x80: -0.26845 %
  - 0xBF->0xC0: -4.19259 %
  - 0xDF->0xE0: -3.72250 %
  - 0xEF->0xF0: -1.04393 %
- mean step 0.35711 %/code (1.1383 x nominal)
- steps outside nominal +/- half-LSB: 69; max |deviation| 4.50632 % (14.364 LSB) at 0xBF->0xC0

