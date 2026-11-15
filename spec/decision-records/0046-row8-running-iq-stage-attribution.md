# 0046: Row 8: the running-Iq excess at the ff corners is carried by comparator-H (static, temperature-driven) and by the trim bank (code-driven); a candidate lever and its price are named

- **Status**: proposed - measurement and attribution only. Changes no schematic, netlist or layout
  file, no ratified row and no Iq metric basis ([0009](0009-running-iq-metric-basis-and-partial-trim-range-recovery.md)
  untouched); records the stage attribution the row-8 failure (#337's trade input,
  [0045](0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md)'s
  open question 2) was missing.
- **Date**: 2026-11-15
- **Decided by**: Loom Builder (issue #347), pending operator ratification

## Context

Row 8 (DR-0003 Row 4 "< 500 uA running"; the issue text calls it row 8) fails and no open issue
owned it: 16 of 108 cells exceed 500 uA on the extraction of the rebuilt layout, max 759.0 uA at
`ff` / `0xFF` / 3.6 V / 85 C ([0044](0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md)),
and the item-5 campaign reads 559.4 uA on the calibration code at the same corner
(`sim/item5/results/20261106T071555Z/summary.md`). DR-0045's open question 2 asks whether the
`0xFF` Iq cost of the `w3r65` candidate is acceptable -- unanswerable without knowing where the
current goes. This record measures it.

**Basis** (stated once, and on every reported figure): the DR-0009 / DR-0044 `iq_run` basis --
supply charge integrated on 1 nF over 20 whole oscillation periods (clk rising edges 5 -> 25) -- on
a probed copy of DR-0044's exact DUT, per stage, in one transient per cell. Evidence:
`sim/iq-attribution/` (`results/20261115T030058-iq-attribution/table.md`, control
`...-control-l1/table.md`); all `klt sim --backend batch --wait-for-capacity 600`, receipts
committed. Every corner's probed total reproduces DR-0044's committed figure for the same cell
within +0.00..+0.27 % (back-to-back gate, +/-1 %), and the per-stage sum tracks the measured total
to |residue| <= 0.009 uA at all 33 cells. The timing MiM and the discharge device draw exactly
0 A -- no `vdd` terminal, zero by construction, asserted in the committed stage map.

These figures are **not** comparable to item-5's row-8 numbers (its bench integrates a fixed
200-1200 ns window on a different netlist); 559.4 uA and this campaign's 555.8 uA at
`ff` / 3.6 V / 85 C / `0xA4` land close by coincidence. Reconciling the two bases is out of scope
and untouched.

## Findings (the attribution)

Per-cell tables in `sim/iq-attribution/results/20261115T030058-iq-attribution/table.md`. Stages:
bias, comparator-H, comparator-L, latch (+clk drive), trim bank; timing and discharge zero.

- **Comparator-H carries the largest single share of the ff-hot excess.** It is the largest stage
  at the shipping-code failing cell (211.6 of 555.8 uA at `ff` / 3.6 V / 85 C / `0xA4`, 38 %) and
  at every ff cell of the grid; it grows steeply with temperature and supply (`0xFF`, ff 3.6 V:
  177.0 uA at -40 C -> 218.7 at 85 C; bias and comparator-L scale the same direction, ~2x from
  -40 to 85 C) and is almost **code-flat**: +3 % from `0xC0` to `0xFF` (212.3 -> 218.7 uA at
  ff / 3.6 V / 85 C). Comparator-L and bias behave the same way at roughly 2/3 and 1/3 of
  comparator-H's level. This is why even low-code ff-hot cells fail: at `0x80` / ff / 3.6 V / 85 C
  the comparator pair + bias already sum to 421 uA and the cell reads 527 uA.
- **The trim bank carries the code scaling.** At ff / 3.6 V / 85 C: 58.9 (`0x80`) / 83.9 (`0xA4`) /
  108.7 (`0xC0`) / 252.8 uA (`0xFF`) -- a 2.3x step from `0xC0` to `0xFF` with the rest of the
  oscillator flat. Mechanically: at high codes the ladder's series resistance is lowest, so the
  RC node swings deeper and the oscillator runs faster (the window is 20 *periods*, so current
  scales with charge-per-cycle x frequency); the same direction DR-0045 priced in reverse
  (lowering series resistance further raised `0xFF` Iq 18-28 %). The latch (+clk drive) carries a
  smaller frequency-scaled term (38-74 uA).
- **Process scaling** at 3.6 V / 85 C / `0xFF`: total 760.7 (`ff`) vs 431.7 (`ss`) -- the trim bank
  252.8 vs 168.3 and comparator-H 218.7 vs 109.2 are the two biggest movers; at `ss` no cell of
  the grid exceeds 500 uA.
- **Not an artifact of the L 0.7 um change**: the L=1U control at the max cell (781.0 uA total)
  shows the same ranking -- trim 262.8, comparator-H 222.5 -- against DR-0044's committed control
  figure 779.4 (+0.20 %).

## Decision

Recorded, not adopted: **at `ff` the row-8 excess has two carriers, and a lever must say which one
it prices.**

1. **Comparator-H** -- static, temperature- and supply-driven, code-flat: it puts ff-hot cells at
   ~520-530 uA before any code dependence, at the shipping code as much as at `0xFF`.
2. **Trim bank** -- code-driven: it is what makes `0xFF` cells reach 590-760 uA; at the shipping
   code `0xA4` it is only 84 uA (15 % of the cell).

**Candidate lever (one, named)**: comparator-H's current is the larger and the code-independent
excess, and the in-repo-proven lever family for it is the comparator sizing lever of
[0036](0036-row5-comparator-h-first-stage-is-the-supply-slope-lever-load-l-and-tail-screen.md) (mirror-load L
/ tail current). **Expected cost to rows 4 and 5** -- this means the *accuracy* rows of
`sim/item5/ROWS.md` (post-trim accuracy at the calibration point and over temperature), **not**
DR-0003's row numbering, where "Row 4" is this Iq row itself: DR-0036/DR-0038 measured deterministic
+/-0.1 um mirror-load steps at +0.69..+2.48 pt hot and L 1.1 um at +10.4 pt on row 5, and any
comparator sizing move re-centres the calibration code, moving rows 4 and 5 together. A current
reduction sized only at `0xFF` would overstate its benefit at the shipping code: comparator-H
carries 211.6 uA at `0xA4` but the trim-bank lever's price is code-dependent in DR-0045's measured
direction (+18.4..+28.1 % Iq at `0xFF`, within +3 % at codes <= `0xC0`) -- so the `w3r65` question
(DR-0045 open question 2) is answered "not acceptable as priced": the candidate widens the
code-driven excess the oscillator already fails with, for a row-4 gain the attribution now shows
does not touch the dominant ff-hot term at all.

No row, window, basis or design file is changed by this record. Adoption of any lever is a
separate, ratification-bearing decision with its own measurement campaign.

## Alternatives considered

- **Pricing a lever at `0xFF` only** -- rejected: the code dependence above makes `0xFF`-only
  pricing wrong at `0xA4` (the graded basis) in both directions.
- **Freeze-one-stage-at-a-time attribution** -- rejected in
  [0033](0033-rows-4-5-stage-attribution-and-candidate-levers.md) for delay (interaction
  residual, one grid per stage); the same objection applies to current, and the per-stage
  integrator measures every stage in one transient instead.
- **`klt extract --hierarchical-cells` for real stage boundaries** -- rejected by design in
  combination with `--parasitics` (klayout-tools #2916); the committed per-block rosters + the
  coordinate-registered stage map close the partition exactly (99/99, both DUTs).

## Consequences

- #337's ruling now has its input: the `w3r65` candidate's Iq cost lands on the code-driven term
  (trim bank), the ff-hot static excess (comparator-H) predates it and is untouched by it.
- A comparator-current lever, if pursued, must budget the DR-0036/DR-0038 row-5 price and a
  re-centre; a trim-ladder lever must budget the row-4 `ss` span (DR-0034's Ron confound).
- `sim/iq-attribution/` is the reusable attribution bench: the map rebuilds for any flat
  extraction of this layout, and the probed-DUT method extends to any stage set.
