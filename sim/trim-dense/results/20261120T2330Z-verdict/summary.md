# Dense trim-code step analysis

**MEASURED CAMPAIGN DATA (analysis only; verdict belongs to #87)**

## Simulator-version split (disclosed, accepted on a paired A/B)

A/B: ngspice-46 vs ngspice-47, comparison sha256 `cfdeb1f51a944ae9d759a0ed291226f2d73db42e4fa2be7e80f2d3e12c51d6e3`; 47 pairs, max |delta| 0.1328 %, 0 over half-LSB (0.156863 %).

- ext_ff_85C_3p6V: 256 x ngspice-46; not sampled by the A/B
- ext_ss_m40C_3p0V: 256 x ngspice-46; A/B sampled 16 codes
- ext_tt_27C_3p3V: 256 x ngspice-46; A/B sampled 16 codes
- sch_ff_85C_3p6V: 180 x ngspice-46, 76 x ngspice-47 (internally split); A/B sampled 15 codes
- sch_ss_m40C_3p0V: 256 x ngspice-47; not sampled by the A/B
- sch_tt_27C_3p3V: 256 x ngspice-47; not sampled by the A/B

Nominal step 0.313725 %/code, half-LSB 0.156863 % (80 %/255; DR-0003). Step = 100*(f[c+1]/f[c]-1). Comparison is descriptive; verdict belongs to #87.

## sch / tt_27C_3p3V: OK

- f[0x00] = 26.638840 MHz, f[0xFF] = 85.136591 MHz, span +219.5957 %
- worst positive step: 0xFB->0xFC +2.44345 %
- worst negative step: 0x7F->0x80 -6.17616 %
- smallest / largest signed step: 0x7F->0x80 -6.17616 % / 0xFB->0xFC +2.44345 %
- non-positive transitions: 10
  - 0x7F->0x80 -6.17616 %
  - 0xBF->0xC0 -2.92825 %
  - 0xDF->0xE0 -1.55592 %
  - 0xEF->0xF0 -0.41810 %
  - 0xF0->0xF1 -0.13867 %
  - 0xF4->0xF5 -0.18985 %
  - 0xF8->0xF9 -0.82424 %
  - 0xFA->0xFB -0.85498 %
  - 0xFC->0xFD -0.99793 %
  - 0xFE->0xFF -0.99451 %
- carry transitions:
  - 0x7F->0x80: -6.17616 %
  - 0xBF->0xC0: -2.92825 %
  - 0xDF->0xE0: -1.55592 %
  - 0xEF->0xF0: -0.41810 %
- mean step 0.86116 %/code (2.7449 x nominal)
- steps outside nominal +/- half-LSB: 148; max |deviation| 6.48989 % (20.687 LSB) at 0x7F->0x80

## sch / ss_m40C_3p0V: OK

- f[0x00] = 19.374297 MHz, f[0xFF] = 63.266829 MHz, span +226.5503 %
- worst positive step: 0xFB->0xFC +2.38481 %
- worst negative step: 0x7F->0x80 -6.72178 %
- smallest / largest signed step: 0x7F->0x80 -6.72178 % / 0xFB->0xFC +2.38481 %
- non-positive transitions: 10
  - 0x3F->0x40 -0.22429 %
  - 0x7F->0x80 -6.72178 %
  - 0xBF->0xC0 -3.91261 %
  - 0xDF->0xE0 -1.69844 %
  - 0xEF->0xF0 -0.83508 %
  - 0xF6->0xF7 -0.06950 %
  - 0xF8->0xF9 -0.64716 %
  - 0xFA->0xFB -0.69256 %
  - 0xFC->0xFD -1.11640 %
  - 0xFE->0xFF -1.02746 %
- carry transitions:
  - 0x7F->0x80: -6.72178 %
  - 0xBF->0xC0: -3.91261 %
  - 0xDF->0xE0: -1.69844 %
  - 0xEF->0xF0: -0.83508 %
- mean step 0.88843 %/code (2.8319 x nominal)
- steps outside nominal +/- half-LSB: 159; max |deviation| 7.03551 % (22.426 LSB) at 0x7F->0x80

## sch / ff_85C_3p6V: OK

- f[0x00] = 37.676848 MHz, f[0xFF] = 116.052795 MHz, span +208.0215 %
- worst positive step: 0xFB->0xFC +2.25287 %
- worst negative step: 0x7F->0x80 -5.75914 %
- smallest / largest signed step: 0x7F->0x80 -5.75914 % / 0xFB->0xFC +2.25287 %
- non-positive transitions: 12
  - 0x7F->0x80 -5.75914 %
  - 0xBF->0xC0 -2.66794 %
  - 0xDF->0xE0 -1.54172 %
  - 0xE8->0xE9 -0.00654 %
  - 0xEF->0xF0 -0.17741 %
  - 0xF2->0xF3 -0.16144 %
  - 0xF4->0xF5 -0.13262 %
  - 0xF6->0xF7 -0.08442 %
  - 0xF8->0xF9 -0.65261 %
  - 0xFA->0xFB -0.34554 %
  - 0xFC->0xFD -0.67449 %
  - 0xFE->0xFF -0.58958 %
- carry transitions:
  - 0x7F->0x80: -5.75914 %
  - 0xBF->0xC0: -2.66794 %
  - 0xDF->0xE0: -1.54172 %
  - 0xEF->0xF0: -0.17741 %
- mean step 0.81577 %/code (2.6003 x nominal)
- steps outside nominal +/- half-LSB: 125; max |deviation| 6.07286 % (19.357 LSB) at 0x7F->0x80

## ext / tt_27C_3p3V: OK

- f[0x00] = 28.651571 MHz, f[0xFF] = 76.418680 MHz, span +166.7172 %
- worst positive step: 0xF9->0xFA +1.06376 %
- worst negative step: 0x7F->0x80 -9.39907 %
- smallest / largest signed step: 0x7F->0x80 -9.39907 % / 0xF9->0xFA +1.06376 %
- non-positive transitions: 5
  - 0x7F->0x80 -9.39907 %
  - 0xBF->0xC0 -5.59941 %
  - 0xDF->0xE0 -3.63967 %
  - 0xEF->0xF0 -2.64412 %
  - 0xF7->0xF8 -0.78092 %
- carry transitions:
  - 0x7F->0x80: -9.39907 %
  - 0xBF->0xC0: -5.59941 %
  - 0xDF->0xE0: -3.63967 %
  - 0xEF->0xF0: -2.64412 %
- mean step 0.65379 %/code (2.0840 x nominal)
- steps outside nominal +/- half-LSB: 119; max |deviation| 9.71279 % (30.960 LSB) at 0x7F->0x80

## ext / ss_m40C_3p0V: OK

- f[0x00] = 21.318871 MHz, f[0xFF] = 58.719181 MHz, span +175.4329 %
- worst positive step: 0xF5->0xF6 +1.09353 %
- worst negative step: 0x7F->0x80 -10.48333 %
- smallest / largest signed step: 0x7F->0x80 -10.48333 % / 0xF5->0xF6 +1.09353 %
- non-positive transitions: 8
  - 0x3F->0x40 -0.46314 %
  - 0x7F->0x80 -10.48333 %
  - 0x9F->0xA0 -0.32461 %
  - 0xBF->0xC0 -7.12790 %
  - 0xCF->0xD0 -0.05721 %
  - 0xDF->0xE0 -4.33701 %
  - 0xEF->0xF0 -3.16812 %
  - 0xF7->0xF8 -1.21210 %
- carry transitions:
  - 0x7F->0x80: -10.48333 %
  - 0xBF->0xC0: -7.12790 %
  - 0xDF->0xE0: -4.33701 %
  - 0xEF->0xF0: -3.16812 %
- mean step 0.68797 %/code (2.1929 x nominal)
- steps outside nominal +/- half-LSB: 133; max |deviation| 10.79706 % (34.416 LSB) at 0x7F->0x80

## ext / ff_85C_3p6V: OK

- f[0x00] = 39.610127 MHz, f[0xFF] = 103.388420 MHz, span +161.0151 %
- worst positive step: 0x9F->0xA0 +1.27411 %
- worst negative step: 0x7F->0x80 -8.69320 %
- smallest / largest signed step: 0x7F->0x80 -8.69320 % / 0x9F->0xA0 +1.27411 %
- non-positive transitions: 5
  - 0x7F->0x80 -8.69320 %
  - 0xBF->0xC0 -4.98386 %
  - 0xDF->0xE0 -3.34608 %
  - 0xEF->0xF0 -1.95292 %
  - 0xF7->0xF8 -0.32187 %
- carry transitions:
  - 0x7F->0x80: -8.69320 %
  - 0xBF->0xC0: -4.98386 %
  - 0xDF->0xE0: -3.34608 %
  - 0xEF->0xF0: -1.95292 %
- mean step 0.63143 %/code (2.0127 x nominal)
- steps outside nominal +/- half-LSB: 95; max |deviation| 9.00692 % (28.710 LSB) at 0x7F->0x80

