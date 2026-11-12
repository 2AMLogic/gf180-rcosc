# 0034: Row 4 `ss` supply span: bank pass-gate Ron is real but only part of the RC term; doubling the pass-gate widths cuts the span 0.69 pt (target >= 1.2) and costs the trim top end

- **Status**: proposed - measurement and a refuted candidate lever only. Changes no ratified row, window or value, keeps the
  per-die calibration basis of [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md), adds no per-corner trim,
  leaves [0004](0004-no-active-tc-compensation-runtime-discipline.md) untouched. **No design change is proposed by this record
  and none is merged**: the committed schematics and netlists are unchanged.
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #317), pending operator ratification

## Context

[0033](0033-rows-4-5-stage-attribution-and-candidate-levers.md) attributed 3.03 of the 6.13 pt `ss` supply span (27 C) to the
charge RC term and *inferred* bank transmission-gate Ron as its cause (the PDK has no supply dependence in MiM / poly). #317
asks to measure that, then make one netlist change that cuts the span by >= 1.2 pt (6.13 -> <= 4.9).

## Measurement (`sim/row4-ron/`, batch fleet, nothing run locally)

Schematic `rcosc_trim_bank` at `ss`, 50 mV across the bank with its low pin held at VDD/3, VDD/2 and 2VDD/3, six codes, three
supplies, three temperatures. `ron_table.md` subtracts a ladder-only reference (each TG replaced by 1 mOhm / 1 GOhm by code bit).

- **Ron rises as VDD falls, and the ladder R does not move.** At `ss`, 27 C, code 0xD4 (the `ss` per-die code), node at 2VDD/3:
  Ron 7.5 kohm at 3.0 V, 5.9 kohm at 3.3 V, 4.8 kohm at 3.6 V (bank total 37.9 kohm at 3.0 V, 35.0 kohm at 3.6 V), ladder-only R identical at all three supplies. Ron(3.0 V)/Ron(3.6 V) = 1.20 / 1.39 / 1.57 at the VDD/3, VDD/2,
  2VDD/3 node levels. The hypothesis in 0033 is **confirmed qualitatively**.
- Switch width scaling (`sim/row4-ron/results/20261112T083000Z-w1.5`, `-w2`, `-w3`): the 3.0 V -> 3.6 V swing of the bank at 2VDD/3 falls from
  2905 ohm to 2039 / 1572 / 1080 ohm at 1.5x / 2x / 3x W (-30 / -46 / -63 %).

## Stage re-run of the candidate (2x W on every pass device)

`sim/row45-rerun/` applies 2x W to the extracted DR-0028 netlist as text (layout not re-extracted). At 2x the oscillator is
*slower* at a fixed code (`ss` 0xD4 47.95 -> 45.56 MHz, `tt` 0xA5 48.14 -> 46.40 MHz: the extra gate capacitance on the timing node
outweighs the lower Ron), so the per-die codes were re-derived by calibration scans: tt 171, ff 80, ss 218. Same 27 points,
same stage split:

| quantity | committed (0033) | 2x W | target |
|---|---|---|---|
| `ss` 27 C supply span, 3.6 V - 3.0 V (pt) | 6.13 | **5.44** | <= 4.9 |
| `ss` charge RC term span (pt) | 3.03 | 2.41 | |
| `tt` 27 C span (pt) | 3.51 | 3.16 | |
| `ff` 27 C span (pt) | 1.55 | 1.28 | |
| `ff` 85 C / 3.0 V total error (pt) | +6.88 | +7.48 | row 5 (window +8.8) |
| `ff` -40 C / 3.0 V total error (pt) | -4.88 | -5.10 | |

**The lever does not meet the criterion**: -0.69 pt (not -1.2), although it cuts the bank's own Ron swing by 46 %. Ron therefore
explains only about 1.3 pt (0.62 pt RC-term cut / 0.46) of the 3.03 pt RC term; the remaining ~1.7 pt is another supply-dependent part of "bank R, Ron, C"
that this measurement did not isolate (candidates, not measured: voltage-dependent switch junction / gate capacitance on the
timing node, bias-current-dependent charge). 3x W would extrapolate to roughly -0.9 pt, still short, with more timing-node load.

**Trim range is regressed**: endpoints (27 C, 3.3 V, 0x00 / 0xFF) go from 28.65 / 76.42 MHz to 27.97 / 66.22 MHz at `tt`
(DR-0003 Row 2 range 28.8-67.2 MHz: the top end no longer reaches it) and from 22.62 / 61.18 to 22.09 / 53.38 MHz at `ss`.
`ff` 37.72 / 98.20 -> 36.80 / 84.74 MHz.

## Decision

Do **not** adopt the 2x-W pass-gate lever. Row 4's `ss` span stays at the DR-0032 / DR-0033 figures. The measurement is the
deliverable: Ron is confirmed as a *contributor* (about 45 % of the RC term), so a Ron-only fix cannot reach 4.9 pt.

## Not done in this record (open, tracked on #317)

- Row 5 comparator-H output-stage change and its stage re-run (criterion 3).
- The 500-die Monte Carlo campaign (criterion 5): there is no adopted change to run it on; it would repeat DR-0032 unchanged.
- `design/check-netlist-consistency.py` is unaffected (no schematic change); layout / LVS impact: none.
- Next measurement for row 4: isolate the non-Ron ~1.7 pt (switch parasitic C vs supply; bias current vs supply in the charge
  path) before choosing another knob. Rejected as before: relaxing windows, per-corner trim, active TC compensation (0004).

## Alternatives considered

- **3x W** - extrapolates to about -0.9 pt, still below 1.2 pt, and the 2x run already shows the timing-node load cost.
- **Gate overdrive boost** - needs a supply-independent drive above VDD (charge pump), out of proportion for an RC canary block.
- **Retuning the ladder R to restore the top end** - a second knob in the same change; DR-0014 / DR-0023 evidence is pinned to the
  current map, and it would not recover the missing span.
