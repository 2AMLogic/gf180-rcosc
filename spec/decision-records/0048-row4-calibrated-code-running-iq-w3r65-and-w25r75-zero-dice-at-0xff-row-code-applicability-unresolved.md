# 0048: Row 4 running Iq at per-die calibrated codes: `w3r65` and `w2.5r75` measured over the DR-0032 population; 0 of 1 500 dice calibrate at `0xFF`; the row's trim-code applicability is unresolved and returns to the operator

- **Status**: proposed - measurement only. Changes no ratified row or window, no schematic, netlist or layout file; per-die basis
  ([0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md)) unchanged; no per-corner trim; [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched.
- **Date**: 2026-11-20
- **Decided by**: Loom Builder (issue #337, operator ruling q178), pending operator ruling

## Context

Ruling q178 (2026-11-18) measured the two bank candidates' running-Iq penalties only at `0xFF` - a code no die in the
population uses - and asked for the current at **each die's own calibrated code** before any adopt-or-close decision:
`w3r65` ([0045](0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md):
`ss` span 4.68 pt, `0xFF` Iq +18.4..+28.1 %) and `w2.5r75` ([0047](0047-row4-no-bank-variant-in-the-w-r-family-clears-ss-span-without-the-0xff-iq-rise.md):
`ss` span 4.84 pt, `0xFF` Iq +12.09..+19.20 %). Evidence: `sim/row4-calibrated-iq/` (README has commands, run ids and the sharding/resume history).

## Evidence

Method: the DR-0032 population re-drawn on each candidate DUT (500 mismatch draws per process, seed 20261008, derived-seed parity
with `sim/mc/results/20261112T025135Z` verified 500/500 on all six reports, engine 47 both sides); each die bisects to its
nearest-48.000 MHz code at 27 C / 3.3 V, holds it across 3.0/3.3/3.6 V x -40/27/85 C; the DR-0044 L=1 um control runs the
**same draw at the same code** (deck carries the candidate report's derived seed and calibrated code). Delta = (candidate -
control) / control, per matched die/code/supply/temperature; 4 500 matched points per process per variant. Calibrated-code
occupancy: `w3r65` tt `0x7F`/`0xA5`-`0xA9`, ff `0x48`-`0x4F`, ss `0xD3`-`0xD6`; `w2.5r75` tt `0xA4`-`0xA9`, ff `0x49`-`0x50`,
ss `0xD3`-`0xD6`. **Dice at `0xFF`: 0 of 1 500 baseline (re-counted from the DR-0032 reports: tt 161-168, ff 73-83, ss 210-215
decimal), 0 of 1 500 for each candidate.** The `0xFF` penalties on record remain [0045](0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md) (+18.4..+28.1 %, max 918.9 uA) and [0047](0047-row4-no-bank-variant-in-the-w-r-family-clears-ss-span-without-the-0xff-iq-rise.md) (+12.09..+19.20 %, max 868.3 uA).

Matched-die delta vs control, and the absolute row (ratified "< 500 uA (running)"), per process (full distributions, worst
dice and code occupancy in `results/20261119T220503Z-analysis-*/table_vs_control.md`):

| variant | process | delta % (min..max) | DR-0044 band -4.57..+0.18 % | cand cells >= 500 uA (of 4 500) | control cells >= 500 uA | worst absolute (uA) |
|---|---|---|---|---|---|---|
| `w3r65` | tt | +1.11..+3.02 | outside | 0 | 0 | 427.1 (die 313, `0xA6`, 3.6 V, 85 C) |
| `w3r65` | ff | -0.20..+1.16 | outside | 387 | 363 | 537.9 (die 370, `0x48`, 3.6 V, 85 C; control 539.0, -0.20 %) |
| `w3r65` | ss | **+3.90..+7.08** | outside | 0 | 0 | 375.8 (die 370, `0xD3`, 3.6 V, 85 C) |
| `w2.5r75` | tt | +0.68..+1.88 | outside | 0 | 0 | 426.1 (die 370, `0xA4`, 3.6 V, 85 C) |
| `w2.5r75` | ff | -0.35..+0.98 | outside | 384 | 374 | 537.5 (die 370, `0x49`, 3.6 V, 85 C; control 539.3, -0.35 %) |
| `w2.5r75` | ss | **+2.75..+5.42** | outside | 0 | 0 | 371.2 (die 370, `0xD3`, 3.6 V, 85 C) |

Worst increases: `w3r65` ss die 463 `0xD6` 3.0 V 27 C +7.08 % (control 231.4 uA); `w2.5r75` ss die 385 `0xD6` 3.0 V 27 C
+5.42 % (control 229.8 uA). Reading of the table:

1. **At the codes dice actually use, both candidates' penalties are far below their `0xFF` penalties** - worst process
   (`ss`) +7.08 % (`w3r65`) / +5.42 % (`w2.5r75`) against +18..+28 % / +12..+19 % at `0xFF`. The `0xFF` figure is a code the
   population never calibrates to; it is a recorded fact, not a population exposure.
2. **The DR-0044 no-regression band (-4.57..+0.18 %) is still not met at calibrated codes** - every process of both variants
   sits above +0.18 % at its minimum. The band is a base-vs-variant nominal-cell delta, not the ratified row itself.
3. **On the absolute ratified figure, tt and ss are met with margin** (max 427.1 / 375.8 uA); ff carries 387/384 cells
   >= 500 uA against the control's 363/374 - the pre-existing fast-corner hot/high-V failure of the row
   ([0011](0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md), [0044](0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md)),
   to which the candidates add 24 / 10 cells of 4 500. `w2.5r75` is uniformly the lower-current candidate, as ruling q136 anticipated.

## The row's trim-code applicability (ruling q178 item 2)

The ratified texts name **no trim code**: README table - "Quiescent current (Iq) - < 500 µA (running)";
[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md) Row 4 - "Ratified: < 500 µA (running)." The practices on record:
[0011](0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md) graded the row at **every** simulated code
(`0x00`/`0x80`/`0xC0`/`0xFF`, full 63-point grid; the row already exceeds at the fast corners at every code);
[0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md) ratified the per-die calibrated-code basis for the
**accuracy** rows only (its rows 4-5: -2.9/+2.0 % and -10.8/+8.8 % windows), not for the Iq row; item 5's single calibration
code across corners likewise graded accuracy; [0044](0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md)
explicitly calls its own band "a base-vs-variant delta, not a verdict on Row 4". No record establishes a calibrated-code-only
reading for the Iq row. Under ruling q178 item 4 the interpretation is therefore **returned to the operator** with these numbers.

## Disposition

No adoption decision is made here. Both candidates still hold row 4 `ss` span <= 4.9 pt (4.68 / 4.84, [0045](0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md) / [0047](0047-row4-no-bank-variant-in-the-w-r-family-clears-ss-span-without-the-0xff-iq-rise.md)),
but neither meets the DR-0044 band at calibrated codes, and the row's code applicability is unruled. Per the ruling, `loom:operator`
is restored on #337 and no `design/*` file is touched. The operator decides with this record: (a) the row applies at every code -
neither candidate is adoptable (and the row already fails at baseline ff), pointing to a no-knob close-out; (b) the row applies at
calibrated codes - then `w2.5r75` (uniformly lower current) is the candidate, its residual ss penalty (+2.75..+5.42 % vs the L=1
control) priced against the absolute 500 uA figure it still clears, and the schematic/layout/extraction steps of #337 proceed;
(c) neither reading accepts the cost - close with the measured floor already on record in [0047](0047-row4-no-bank-variant-in-the-w-r-family-clears-ss-span-without-the-0xff-iq-rise.md).

## Consequences

- The `0xFF` population exposure question that blocked `w3r65` in ruling q136 is answered: zero dice, both populations.
- Any adoption still needs the schematic, netlist, layout, DRC/LVS and re-extraction steps listed on #337; this record does not start them.
- `sim/row4-calibrated-iq/` is the reusable harness for calibrated-code Iq (any variant), including the fleet sharding lesson:
  a 500-deck request must be sharded (`--max-units-per-job 15`), or the batch job hits the fleet's 3600 s cap.
