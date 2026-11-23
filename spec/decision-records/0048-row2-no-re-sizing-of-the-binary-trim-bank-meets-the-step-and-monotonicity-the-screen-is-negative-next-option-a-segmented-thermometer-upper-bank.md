# 0048: Row 2: no re-sizing of the binary trim bank meets the 0.314 %/code step with monotone carries - the bounded screen is negative; the next option is a segmented (thermometer-coded) upper bank

- **Status**: proposed - the bounded design iteration [0049](0049-row2-dense-256-code-trim-analysis-step-and-monotonicity-misses-on-the-p3-extraction.md) asked for (#460).
  Sizes nothing into the design; the ratified row 2 (8-bit, +/-40 %, 0.3137 %/code, half-LSB 0.1569 %) is unchanged, and the measured step is NOT recorded as the design's resolution.
- **Date**: 2026-11-22
- **Decided by**: Loom Builder (issue #460), pending operator ratification

## Context

[0049](0049-row2-dense-256-code-trim-analysis-step-and-monotonicity-misses-on-the-p3-extraction.md) measured the committed bank on the P3 extraction: endpoint-span step 2.01-2.19x nominal, arithmetic-mean step 1.21-1.28x, 95-133 of 255 steps outside nominal +/- half-LSB per curve, and the four DR-0021 carries negative on every measured curve.
#460 bounds the design response: attribute the miss, screen at most about six re-sizings of the SAME binary ladder (netlist text only, the `sim/row4-nonron` mechanism), full-curve the best one or two, price rows 4/5/8, and either name a candidate or record the negative result with the next structural option. Evidence: `sim/row2-trimsize/results/` (screen `20261122T0550Z-screen/`, full curve `20261122T0810Z-full-s22-83/`, pricing `20261122T0815Z-pricing/`); every job on the batch fleet (ngspice 47, open_pdks stamp `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`, the #87 campaign's stamp set).

## Attribution (offline fit, `results/20261122T0550Z-screen/fit/`)

The committed #87 curves are fitted by `T(c) = intercept + sum_b bit_b(c) beta_b` to 1.1-6.7 % of T (period-linear, so the per-code FREQUENCY steps grow with f). In `rho_b = |beta_b| / (W 2^b)` units (1.000 = binary-exact):

- the defect is a gradient, not one bad bit: low bits 1.10-1.40x overweight, bit 7 ~0.90x underweight, on every corner;
- the carry period step is `W (sum_{k<b} rho_k 2^k - rho_b 2^b)`; the measured rho makes all four DR-0021 carries negative and sizes 0x7F->0x80 at -9.4 % - exactly what [0049](0049-row2-dense-256-code-trim-analysis-step-and-monotonicity-misses-on-the-p3-extraction.md) lists;
- the excess range is real but secondary: the bank spans f(0xFF)/f(0x00) = 2.67x at tt against the ratified 2.33x, worth ~14 % of the 2.08x step multiple; the period-linear law contributes the rest.

A one-shot "ratio rule" re-sizing `r_b' = r_b (W' 2^b) / |beta_b|` should make the effective weights binary-exact at the compensation corner. The screen tested exactly that.

## Screen (6 variants x 57 codes x tt 27 C / 3.3 V, 342 batch reports)

`analysis/screen.md`, sparse-code set = endpoints, +/-1 around every power-of-two and DR-0021 carry, single-bit and spread codes:

| variant | f ends MHz (tt) | mean step %/code (x nominal) | non-positive steps (of 34 pairs) | DR-0021 carries % |
|---|---|---|---|---|
| ctrl (P3 bank) | 28.652 / 76.391 | 0.6534 (2.08x) | 4 | -9.40 -5.60 -3.64 -2.64 |
| F1.85@tt | 34.476 / 43.625 | 0.1041 (0.33x) | 10 | -2.13 -4.53 -1.83 **+0.94** |
| F1.85@ss | 40.251 / 43.721 | 0.0338 (0.11x) | 10 | -3.28 -3.48 -0.15 **+2.31** |
| F1.95@tt | 33.592 / 46.232 | 0.1476 (0.47x) | 8 | -1.36 -4.50 -2.35 **+0.43** |
| F2.50@tt | 27.067 / 53.151 | 0.3779 (1.20x) | 6 | -0.14 -3.76 -3.94 -1.63 |
| F1.85@tt-w2 | 33.643 / 34.522 | 0.0102 (0.03x) | 10 | -8.72 -9.95 -4.75 -0.25 |

Three measured failure modes, none of which any drawn-length choice in this family avoids:

1. **The weights do not transfer.** The re-fitted rho of every re-sized bank is nowhere near 1 (e.g. F1.85@tt: 5.37, 2.37, 1.76, 1.72, 1.43, 1.01, 0.82, 1.07; F2.50: 0.83, 0.35, 1.35, 1.15, 1.04, 0.96, 0.94, 1.04). The drawn-length -> effective-weight map is strongly non-linear (bypass-switch Ron and ladder node caps participate), so correcting the drawn ratios does not correct the effective ratios.
2. **The span does not hold.** Designed spans 1.85-2.50x land at 1.09-1.96x; the step lands at 0.03-1.20x nominal. No screened point is inside the half-LSB step band, and none covers the ratified ends (the best, F2.50, reaches 27.1-53.2 MHz at tt against 28.8-67.2).
3. **The carries stay negative on every candidate** (3-4 of 4), and the mid carries (0xBF->0xC0, 0xDF->0xE0) are the stubborn ones: -1.83 to -4.53 % everywhere, because the weight deficit sits in the bit-5/6/7 block that every re-sizing redistributes but cannot linearise.

**The #337 interaction is measured, not assumed:** doubling all 16 bank pass devices (`w2`, the row-4 lever direction) collapses the span to 1.026x, turns all four carries negative and pushes bit 0's weight to 17.6x - wider switches add node capacitance that the small segments cannot overcome. The candidate bank levers compose with NEITHER the current bank nor the #337 variants; within this family they are the same lever, and it moves the wrong way.

**Evidence integrity incident (disclosed):** the first submission round mixed variants inside each `klt sim --batch-set` group and 28 of 342 member reports were silently cross-wired to another variant's testbench (shared `tb_cXX.spice` basenames; tool gap 2AMLogic/klayout-tools#7180). Caught by verifying every report's `environment.netlist_sha256` against the bench provenance; the 28 files are quarantined under `results/20261122T0550Z-screen/reports-quarantined/`, the affected requests were re-run one variant per invocation, and `analyze_screen.py` now refuses any report whose netlist sha does not match its own request. All numbers in this record are from the sha-verified set.

## Full curve of the least-bad candidate (F2.50@tt, 256 codes x the three dense-campaign corners, 768 batch reports)

`results/20261122T0810Z-full-s22-83/analysis/` (sim/trim-dense/analyze.py over the frozen bench, engine ngspice 47 uniform, manifest verified, all three curves valid):

| corner | f(0x00) / f(0xFF) MHz | range ends 28.8 / 67.2 | mean step %/code (x nominal) | steps outside nominal +/- half-LSB (of 255) | worst deviation (LSB) | non-positive steps | DR-0021 carries % |
|---|---|---|---|---|---|---|---|
| tt 27 C 3.3 V | 27.067 / 53.151 | **no / no** | 0.3779 (1.20x) | 65 | 13.6 at 0xDF->0xE0 | 15 | -0.14 -3.76 -3.94 -1.63 |
| ss -40 C 3.0 V | 20.121 / 40.401 | no / no | 0.3953 (1.26x) | 56 | 14.9 at 0xDF->0xE0 | 13 | -0.58 -3.97 -4.37 -2.46 |
| ff 85 C 3.6 V | 37.488 / 71.626 | no / yes | 0.3571 (1.14x) | 69 | 14.4 at 0xBF->0xC0 | 19 | -0.27 -4.19 -3.72 -1.04 |

The negative screen verdict holds at every dense-campaign corner, by every statistic the ratified row states: the mean step is 1.14-1.26x nominal, 56-69 of 255 steps lie outside the half-LSB band (worst 13.6-14.9 LSB at the mid carries), all four carries are negative at all three corners, 9-15 further non-positive steps exist per curve beyond those four (13-19 in total), and neither range end is met on tt or ss.

## Pricing (rows 4 / 5 / 8, rebuilt-layout extraction, `results/20261122T0815Z-pricing/`)

- Row 5/calibration: tt 0xC8 (47.83 MHz), ff 0x70 (47.67); **ss tops out at 42.66 MHz (0xF8) - 48 MHz is not reachable on a slow die**. The span collapse disqualifies the candidate before rows 4/8 are even read.
- Row 4: `ss` 27 C supply span 5.81 pt at the per-die calibration codes (baseline 6.09, `w3r65` 4.68, window 4.9) - no clearance.
- Row 8: running Iq max 638.6 uA at 0xFF, 9/54 cells over 500 uA (baseline 759.0 uA, 15/54): no regression, no clearance.

## Decision

Recorded as the negative result #460's step 5 defines; nothing in the spec or the design changes.

1. **No re-sizing of the committed binary 8-bit ladder - at any span, at either compensation corner, with or without doubled switches - meets the ratified row 2** (step, monotonicity or range) on the P3 extraction. The failure is structural: the effective bit weights are set by the switch/ladder interaction, not by the drawn segment lengths, so the ladder cannot be corrected by drawing it differently.
2. **The next structural option is a segmented upper bank (thermometer-coded)**: a small binary low nibble (whose in-band steps are tolerated by the half-LSB) plus a thermometer-coded upper bank, which removes the upper carries by construction (each code closes exactly one more unit - monotone independent of weight error) and cuts the weight-ratio precision the bank must hold from 2^7-scale matching to unit-scale matching. A unit-resistor/thermometer re-build is a schematic-and-layout change and is OUT of this record's scope; it needs its own issue.
3. The #337 adopt-or-close ruling is not pre-empted: this record only hands it one more measured fact - inside this family the bank-switch lever degrades row 2 monotonically (w2: all carries negative, span 1.026x).
4. The ratified step, range and half-LSB are unchanged; the measured step is not recorded as the design's resolution.

## Verification

- `python3 -I -m pytest -p no:cacheprovider sim/row2-trimsize/test_toolchain.py` (7 offline tests: variant edits exactly the nine ladder lines, row45 switch doubling, exact LS recovery, binary-exact synthetic fit reproduces the DR-0021 carry sign, ratio-rule floor).
- `sim/check-append-only.sh <base> HEAD` passes (new files only, no exceptions needed).
- Reproduction: the READMEs of the three run directories list the exact commands; the `ctrl` variant reproduces the committed #87 `ext_tt` numbers (f 0x00 = 28.652 MHz, 0x7F->0x80 = -9.40 %), which ties the screen to the frozen campaign.
- `signoff/signoff-report.json` statuses are unchanged; no schematic, netlist-of-record or layout file changes.
