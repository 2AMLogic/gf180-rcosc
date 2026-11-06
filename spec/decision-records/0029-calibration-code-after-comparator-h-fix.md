# 0029: Re-centre the calibration code from 0xA9 to 0xA4 after the comparator-H output-stage fix

- **Status**: proposed
- **Date**: 2026-11-06
- **Decided by**: Loom Builder (issue #235), pending operator ratification

## Context

[DR-0023](0023-recentre-timing-ladder-for-extracted-parasitics.md) set the tt / 27 C / 3.3 V calibration code to
0xA9 on the P3 netlist (48.05 MHz, +0.10 %). [DR-0028](0028-comparator-h-output-stage-fix.md) narrowed the comparator-H
pull-down so the oscillator starts at fs / -40 C; the revised stage shifts the oscillator up, and 0xA9 now gives 49.142 MHz
(+2.38 %), so ratified row 1 (+/-1.1 % at the calibration point) fails where it passed. DR-0028 left the re-centring to a
follow-up. The ratified row is not relaxed; the code moves instead. DR-0023 is not edited in place; this record amends it.

## Decision

The calibration code is **0xA4**. Rule: the probed code nearest 48.000 MHz at tt / 27 C / 3.3 V on the DR-0028 netlist
(single-corner probes `sim/cmph-fix/calib/`, confirmed by the 21-point batch grid):

| code | f (MHz) | error |
|---|---|---|
| 0xA3 | 47.647 | -0.74 % |
| **0xA4** | **47.886** | **-0.24 %** |
| 0xA5 | 48.145 | +0.30 % |
| 0xA6 | 48.384 | +0.80 % |
| 0xA7 | 48.635 | +1.32 % |

0xA4 and 0xA5 both pass row 1; 0xA4 is nearer. The batch campaign `sim/item5/results/20261106T071555Z/` reproduces the
0xA4 and 0xA5 numbers exactly (47.886 / 48.145 MHz). Nothing else changes: no netlist, ratified row, corner list or
DR-0019 limit is edited. `sim/item5/gen_requests.py` and `report_rows.py` take 0xA4 (LSB neighbour 0xA5) as their default.

## Alternatives considered

- **0xA5** (+0.30 %): also inside row 1. Over the full grid it is not clearly better for rows 4/5 (both give 7/21 and 26/63
  points inside the ratified windows; worst error +30.75 % / +37.91 % against +29.99 % / +37.33 % for 0xA4), so the
  nearest-code rule stands.
- **Keep 0xA9 and relax row 1**: forbidden.
- **Re-tune the design to bring 0xA9 back**: that is the #229 / #234 scope, rejected here.

## Consequences

- Item-5 re-run on the revised netlist at 0xA4 (15 batch envelopes, `sim/item5/results/20261106T071555Z/`): **row 1 passes**
  (-0.24 %), rows 7 and 10 pass (0 no-clock points, fs / -40 C now reports a frequency), and rows 4 and 5 are re-derived on 0xA4 and
  re-graded with the ratified limits (-2.9 / +2.0 % and +8.8 / -10.8 %): both **still FAIL** (7/21 and 26/63 points inside; one code
  held across process corners, worst ff corners). Rows 2 (LSB 0.539 %/code) and 8 (559.4 uA at ff / 85 C / 3.6 V) still FAIL.
- Item 5 stays `unmet`. The Monte Carlo remainders of rows 2/4/5 stay declared gaps (DR-0019).
- The pre-fix evidence (`sim/item5/results/20261106T051832Z/`, 0xA9) and `sim/cmph-fix/results/` (0xA9 on the revised netlist) are unchanged.
