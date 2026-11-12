# 0033: Rows 4 and 5 stage-level attribution on the DR-0028 netlist: `ss` supply span is the trim-bank charge path, `ff` hot / low-V skew is comparator H

- **Status**: proposed — attribution and candidate proposal only. Changes no ratified row, window or value, keeps the per-die
  calibration basis of [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md), adds no per-corner trim, and
  leaves [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched.
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #314), pending operator ratification

## Context

DR-0032 left two cells failing on the per-die basis, neither attributed below the whole-oscillator level: row 4 at `ss`
(0 % yield, span 5.51-6.69 points against 4.9) and row 5 at `ff` (92.6 %, 85 C / 3.0 V, worst +11.04 % against +8.8 %).

## Method

`sim/row45-attribution/gen_stage_requests.py` writes a probed copy of the DR-0028 netlist (sha256 `7afa433a...` in `dut.txt`;
the only change is probe pins on `.SUBCKT`, each tied to an internal net through 1 mOhm; no device edited). One `klt sim`
request per (process, VDD) runs the three temperatures at that process's DR-0032 median-die calibration code (tt 165, ff 78,
ss 212), 27 points, submitted with `--batch-set --wait-for-capacity 600` (nothing run locally in the evidence). The bench
records the six oscillator events (vc rises through vh, cmph_out, clk rise, vc falls through vl, cmpl_out, clk fall). Their
gaps are the stage delays and sum to the period (residual 0.0000 % of T over all 27 points). `stage_attribution.py` turns a
delay change into frequency points exactly: `eps = -sum_s (d_s - d_s,ref)/T`. The charge stage is split with
`t_chg = tau * ln((VDD - v0)/(VDD - vh))` into a threshold-ratio term, an RC term and a cross term. Reference is the same die at
3.3 V / 27 C. The recommended "freeze one stage at a time" sweep was not used: the event decomposition measures every stage in
the same transient, is exact rather than approximate (freezing leaves an interaction residual) and needs one grid, not one per stage.

Evidence: `sim/row45-attribution/results/20261112T070000Z/` (`stage_attribution.md` has all tables, including the other
cells and the bias gate voltages). Reproduces DR-0032's median dies: `ss` span 6.13 (6.08), `ff` 85 C / 3.0 V +6.88 % (+6.90).
The 20-period `fosc` measurement agrees with the 3-edge period to 0.058 % of T.

## Row 4: `ss`, 27 C, supply term (points of frequency, span = eps(3.6 V) - eps(3.0 V))

| stage | 3.0 V | 3.6 V | span | share |
|---|---|---|---|---|
| charge: RC term (trim-bank R incl. switch Ron, C) | -1.60 | +1.43 | **+3.03** | 49 % |
| comparator H | -0.41 | +0.48 | +0.89 | 15 % |
| comparator L | -0.40 | +0.26 | +0.65 | 11 % |
| latch set / reset | -0.52 / -0.19 | +0.45 / +0.14 | +0.97 / +0.33 | 16 / 5 % |
| discharge | -0.21 | +0.10 | +0.31 | 5 % |
| charge: threshold ratio (bias) / cross | -0.04 / 0.00 | -0.11 / 0.00 | -0.07 / 0.00 | -1 % |
| **sum = measured** | -3.38 | +2.75 | **+6.13** | |

Residual: 0.00 pt against the period, 0.03 pt against `fosc`. The bias ratio term is negligible (vh/VDD = 0.6662 to 0.6668
over every process): the supply span is not a threshold problem. Controls: `tt` span 3.51 (RC 1.53) and `ff` 1.55 (RC 0.89) pass,
and the RC term scales with process slowness (0.89, 1.53, 3.03) as an overdrive-limited switch would. The need is 0.61 pt for the
narrowest die, 1.18 for the median and 1.79 for the widest (6.69). DR-0032's "about 1.2 points ... to fit the narrowest die" is the
median figure; passing the 99 % yield target needs the widest-die figure.

What the RC term is, and what is inferred: the PDK `cap_mim_1f0fF` model has `c_tc1 = 1.3e-5`/C and `c_vcr1 = 6e-6`/V (at most 0.1
point over the range), and `ppolyf_u_1k` has `r_vc1 = r_vc2 = 0`, so neither the capacitor nor the poly ladder has a supply
dependence in the model. The supply-dependent part of the RC term is therefore the trim-bank pass gates' on-resistance (gate drive
is VDD, so Ron rises as VDD falls, worst at `ss`). That is an inference from the model, not a measured Ron split; the candidate
below starts by measuring it.

## Row 5: `ff`, 85 C, 3.0 V (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at 85 C)

| stage | T step (85 C) | V step (3.0 V) | total |
|---|---|---|---|
| **comparator H** | +3.38 | +2.84 | **+6.27** |
| charge: RC term | +2.85 | -0.67 | +2.23 |
| charge: threshold ratio | +0.13 | +0.01 | +0.15 |
| latch set / reset | -0.57 / -0.21 | -0.34 / -0.16 | -0.93 / -0.37 |
| comparator L | -0.41 | +0.10 | -0.31 |
| discharge | -0.07 | -0.09 | -0.16 |
| **sum = measured** | +5.10 | +1.70 | **+6.88** |

Residual 0.00 pt against the period, 0.05 pt against `fosc`. The sign reversal DR-0032 saw (up when the supply falls at 85 C,
down at 27 C) is comparator H alone: its delay is 1.84 ns at 3.3 V / 27 C, 1.17 ns at 3.3 V / 85 C and **0.61 ns** at 3.0 V / 85 C
(2.0 ns at -40 C), the other stages move the other way. The charge path moves with the usual temperature sign and its supply step
is negative. Controls: `tt` 85 C / 3.0 V +1.00, `ss` -2.31, `ff` -40 C / 3.0 V -4.88 (limit -10.8), all inside.

## Candidates (proposals; none built here)

1. **Row 4, `ss`: reduce the trim-bank switch on-resistance's supply dependence.** Lever: widen the bank pass gates and/or raise
   their effective gate overdrive so Ron stops tracking VDD. Narrows the supply span at slow process only; it is a supply-slope
   change like [0017](0017-low-side-comparator-pmos-respin-supply-slope.md), not a temperature-compensation mechanism, so DR-0004
   and the 2026-11-10 ruling are not engaged. Expected reduction: removing 40-60 % of the RC term's 3.03-point supply span gives
   **1.2-1.8 points**, which reaches the median-die need (1.18) and at its upper end the widest-die need (1.79). It is only as good as
   the Ron inference above, so the first step is a measurement of Ron against VDD, T and code. Costs to check: ladder total R
   (the nine ladder resistors were scaled x0.70 in DR-0023 to place the range), trim LSB size, switch parasitic C, row 8 current.
2. **Row 5, `ff`: stop comparator H's delay collapsing at hot / low supply.** Lever: make the comparator-H output-stage trip (the
   MBUFN/MBUFP ratio and the stage that DR-0028 touched) track the supply instead of the threshold, so the delay at 85 C / 3.0 V stays
   near its 3.3 V value. This is a **supply-slope** lever (the 2.84-point V step) and only needs part of the temperature step. If a
   temperature-dependent element is used instead, it collides with DR-0004 and must cite the 2026-11-10 ruling; it narrows the
   `ff` hot end only. Expected reduction: the V step alone is 2.84 points, against the need of 2.2 (worst die +11.04 % to +8.8 %), i.e.
   **about 2.3-2.8 points** at the failing cell. Cold end: `ff` -40 C is -5.44 % against -10.8 %, so up to 5 points of added
   downward shift are tolerable; a lever that is inactive at cold does not worsen it. Costs to check: the `ss` / `tt` hot cells
   (`ss` 85 C / 3.0 V is -2.31 against -10.8) and row 4 at `ff` (+1.55 span), where this stage is -0.14.

The candidate netlist change is filed as a separate `loom:triage` issue (#317).

## Not decided here

The 500-die campaign was not re-run (the failures are systematic; DR-0032 shows `ss` row 4 does not depend on the mismatch sigmas).
Deterministic zero-mismatch dies only; mid-rail event thresholds define the comparator and latch delays. Control sufficiency, rows 2 and
8, ratification, layout and PEX are untouched. No row is relaxed.

## Reproduce

```
python3 -I sim/row45-attribution/gen_stage_requests.py sim/row45-attribution/results/<runid>
cd sim/row45-attribution/results/<runid> && klt sim --batch-set request_*.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art
python3 -I sim/row45-attribution/stage_attribution.py sim/row45-attribution/results/<runid> sim/row45-attribution/results/<runid>/stage_attribution.md
```
