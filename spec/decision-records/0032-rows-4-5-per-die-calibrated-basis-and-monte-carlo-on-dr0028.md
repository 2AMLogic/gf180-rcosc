# 0032: Rows 4 and 5 on the per-die-calibrated basis: Monte Carlo on the DR-0028 netlist still fails row 4 at `ss` and row 5 at `ff`

- **Status**: proposed — records the grading basis and simulation evidence. Changes no ratified row, window or value, adds no
  per-corner trim, and leaves [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched.
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #236), pending operator ratification

## Context

[0031](0031-row45-cause-attribution-process-offset-dominates.md) attributed the fixed-code failure of rows 4 and 5 to process
offset and showed the deterministic corners pass on the DR-0017 per-die basis (21/21 and 63/63). What it could not say is
whether the **Monte Carlo** campaign still passes on the current netlist: [0030](0030-item-6-monte-carlo-campaign-results-s2-ss-and-s3-ff-fail-controls-incomplete.md)
(row 4 `ss` 0 % yield, row 5 `ff` 60.4 %) measured the pre-[0028](0028-comparator-h-output-stage-fix.md) P3 netlist.

## Basis (authority: operator ruling 2026-11-11, `/fleet:decide` round 20261111-r14 q35, option a)

Rows 4 and 5 are graded **per die**: each die is calibrated once, at 27 C / 3.3 V, by bisecting the 8-bit trim code to the
frequency nearest 48.000 MHz; that code is then **held fixed across supply and temperature**. There is **no per-corner trim**.
This narrows the "fixed trim code" reading of the 2026-11-10 ruling (r12-q60) to *fixed per die, not one code for all dies*,
for rows 4 and 5 only. The windows are the ratified ones (row 4 -2.9 % / +2.0 %, row 5 -10.8 % / +8.8 %) and are unchanged. The
existing `sim/mc/` harness already works this way, so only the DUT changed: `gen_campaign.py --dut`.

## Evidence

- DUT: `sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, sha256 `7afa433a227b9e8fc94f0bfa17e9ae8e10a244092769885a25719b0a9d72aeb3`
  (the DR-0028 netlist; recorded in `sim/mc/results/20261112T025135Z/dut.txt` and the mismatch manifest).
- Run: `sim/mc/results/20261112T025135Z/` (`main_{tt,ff,ss}` and `inflated_{tt,ff,ss}`, 500 samples each; `zero_{tt,ff,ss}`, 3 draws),
  seed `20261008`, `klt sim` on the batch fleet. Graded by `klt yield` (`klayout-tools[yield]==0.8.0`, 95 % confidence, target
  yield 99 %) against the unchanged `limits_main.json` in `sim/mc/results/20261112T060000Z/`.
- The first `main_ss` submit lost 50 of 500 dies to a Spot interruption (shards never recovered through two `--resume` calls);
  it is kept as `report_main_ss.attempt1.json` and the case was resubmitted in full to the batch fleet (500/500, all `pass`).
  Nothing was run locally.

## Results

| process | row 2 (S1: residual, headroom) | row 4 (S2, 27 C, 3.0-3.6 V) | row 5 (S3, -40..85 C, 3.0-3.6 V) |
|---|---|---|---|
| `tt` | 100 % (lower bound 99.26 %) | 100 % (99.26 %) | 100 % (99.26 %) |
| `ff` | 100 % (99.26 %) | 100 % (99.26 %) | **92.6 % (lower bound 89.94 %), fails** |
| `ss` | 100 % (99.26 %) | **0 % (0 %), fails** | 100 % (99.26 %) |

Per-die detail (500 dies per corner, from `report_main_*.json`):

| process | code min / median / max | calibration residual p99 | row 4 span at 27 C (median, range) | row 5 span (median, range) | worst error |
|---|---|---|---|---|---|
| `tt` | 161 / 165 / 168 | 0.271 % | 3.45 (2.86-3.92) | 7.52 (7.10-8.17) | +3.75 / -4.70 % |
| `ff` | 73 / 78 / 83 | 0.213 % | 1.56 (0.42-2.18) | 11.77 (8.63-16.24) | **+11.04** / -5.44 % |
| `ss` | 210 / 212 / 215 | 0.356 % | **6.08 (5.51-6.69)** | 7.15 (6.74-7.51) | +3.57 / -4.49 % |

No die calibrates within 7 codes of a rail (`s1_headroom` passes everywhere), `hold_gap_hz` is 0 for all dies, and `tt` row 1 residual
is far inside its limit (p99 0.27 % against 0.757 %).

- **Row 4 at `ss` is a deterministic span miss, again.** Every one of 500 dies has a supply span (5.51-6.69 points) wider than the
  4.9-point ratified window; 500 exceed +2.0 % (3.6 V, median +2.76 %) and 498 fall below -2.9 % (3.0 V, median -3.34 %). Per-die
  calibration places the die at 0 % at 3.3 V but cannot narrow the span. It needs about 1.2 points (22 %) less supply
  sensitivity at `ss` just to fit the narrowest die.
- **Row 5 at `ff` fails at one cell: 85 C / 3.0 V.** 37 of 500 dies exceed +8.8 % there (median +6.90 %, worst +11.04 %). The other
  eight cells are inside on every die; the cold end reaches only -5.44 %. The span itself (median 11.77, max 16.24) fits the 19.6-point
  window, so the miss is an upward skew at hot / low-V `ff`, not a lack of width. The frequency rising when the supply falls
  from 3.3 V to 3.0 V at 85 C (+5.12 % to +6.90 %) is the opposite of the sign at 27 C (+0.01 % to -0.76 %).
- Compared with 0030 (pre-DR-0028): row 5 `ff` yield 60.4 % -> 92.6 % and its low-side failure (17 % of dies) is gone; row 4 `ss`
  is unchanged at 0 %, with a slightly wider median span (5.44 -> 6.08 points).

## Controls (DR-0019 section 2), and what the cells therefore claim

| control | outcome |
|---|---|
| zero mismatch (plumbing) | draws identical at all three corners. `tt`: code 0xA4 and 47.886 MHz, equal to DR-0029's calibration point. `analyze.py` marks all three "NO" only because it compares against the **P3** grid (0xA9 / 0x59 / 0xD7); it has no DR-0028 reference for `ff` / `ss`, so those two are unverified, not failed |
| inflated 3x | `klt yield` reports the degradation as **detected for `tt` row 4 and `ff` row 5 only**; not detected for the other ten measurement rows |
| injected-term sensitivity (`sens1`, `sens10`) | **not re-run** here; the DR-0030 result (partial) stands for the injector, which this issue did not change |

Per DR-0019 section 2 a cell whose negative control is not detected carries no verdict: every "100 %" above is a point estimate,
not a pass claim. The two failing cells are claims in the other direction. `ss` row 4 does not depend on the mismatch sigmas (the
span is set by process and supply); `ff` row 5 is detected by its control (the `inflated` run degrades it further). DR-0022 section 3
is not amended here. The sigmas remain the flagged assumption `A_R = A_C = 1.0 %.um`.

## Outcome and proposed design change (not built here)

On the per-die basis the Monte Carlo campaign on the DR-0028 netlist **still fails rows 4 and 5**, at one process corner each. The
remainder is supply and temperature residual that per-die calibration does not remove:

1. **Row 4, `ss`:** reduce the frequency's supply slope at `ss` by at least 1.2 points over 3.0-3.6 V (about 22 % of today's
   6.1 points), for example by biasing or regulating the timing-path current from a supply-insensitive reference. [0017](0017-low-side-comparator-pmos-respin-supply-slope.md)
   already took the low-side comparator's supply span down 24x; the remaining term is in the other delay and charge-current paths and has
   not been attributed at the stage level on the DR-0028 netlist.
2. **Row 5, `ff`:** remove about 2.3 points of the hot / low-supply upward skew at 85 C / 3.0 V (worst die +11.04 % against +8.8 %).
   The sign reversal against 27 C points at a delay term that changes with temperature and supply together, so stage attribution at
   `ff` / 85 C / 3.0 V comes first. Any temperature-compensation lever collides with DR-0004 and would have to cite the 2026-11-10 ruling and
   state what it narrows.

No row is relaxed and no per-corner trim is added. The change proposal is filed as a separate issue at `loom:triage`.

## Not decided here

Control sufficiency (the DR-0022 section 3 amendment, LSB-transition timing), rows 2 and 8 design fixes, ratification of 0019 /
0022 / 0023, the `signoff/` re-grade, layout and PEX. The by-product current measurement named in DR-0019 section 5 was again not taken;
row 8 (already failing at ff / 85 C / 3.6 V, DR-0029) is neither measured nor gated by this run.

## Reproduce

```
sim/mc/run-campaign.sh --dut sim/cmph-fix/rcosc_top_p3_cmphfix.spice <runid> main_tt main_ff main_ss inflated_tt inflated_ff inflated_ss zero_tt zero_ff zero_ss
sim/mc/grade.sh <gradeid> <results/runid dir>   # then: python3 -I sim/mc/analyze.py <grade dir> <run dir> > <grade dir>/summary.md
```

`grade.sh` stops at its final `analyze.py` step when the `sens*` reports are absent; the yield reports are written before that point, and
`summary.md` above was produced by running `analyze.py` directly. Its header text and zero-mismatch reference still describe the P3 DUT.
