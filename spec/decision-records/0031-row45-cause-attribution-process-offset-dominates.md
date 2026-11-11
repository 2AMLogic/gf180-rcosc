# 0031: Rows 4 and 5 at the fixed calibration code: process offset, not supply or temperature, is the dominant cause; no supply or TC candidate can close them

- **Status**: proposed
- **Date**: 2026-11-11
- **Decided by**: Loom Builder (issue #236), pending operator ratification

## Context

The 2026-11-10 operator ruling on #236 says: change the design, keep ratified rows 4 and 5, grade at the fixed calibration
code with no per-corner trim. [DR-0029](0029-calibration-code-after-comparator-h-fix.md) grades both rows at one code (0xA4)
across seven process corners and finds 7/21 (row 4) and 26/63 (row 5) points inside, worst +29.99 % / +37.33 % at ff. The
ruling names the `ss` supply span and the `ff` temperature spread as the causes to attack. This record attributes the failure
from existing data (no new simulation): `sim/item5/results/20261106T071555Z/`, tabulated by
`sim/row45-attribution/attribute.py` -> `sim/row45-attribution/results/20261111T0000Z/attribution.md` (reproduces DR-0029's
7/21, 26/63, +29.99 %, +37.33 %).

## Decision (attribution; no ratified row, window or code is edited)

**Dominant cause of both failures: the absolute process offset of the oscillator frequency at the fixed code.** At 0xA4,
tt / 27 C / 3.3 V, f at the other corners is: ff +28.7 %, rc_f +24.4 %, ss -20.3 %, rc_s -17.2 % against 48 MHz. Row 4's window
is -2.9 / +2.0 % and row 5's is -10.8 / +8.8 %, so a fixed code leaves ff and ss outside both before any supply or
temperature move. The binding points (+29.99 % row 4, +37.33 % row 5, both ff) are that offset plus a few points:

| term (at 0xA4) | ss | ff | other corners |
|---|---|---|---|
| process offset at 27 C / 3.3 V | -20.3 % | +28.7 % | rc_f +24.4, rc_s -17.2, fs +1.3, sf -2.0, tt -0.2 |
| supply term, 3.0 / 3.6 V (row 4) | -2.35 / +1.92 % | -0.96 / +1.01 % | worst -1.90 / +1.55 (tt) |
| temperature term, -40 / 85 C (row 5) | -2.31 / +1.73 % | -2.83 / +4.98 % | worst -3.32 / +6.54 (fs, rc_f) |

So the `ss` supply span (4.27 points, below the 4.9-point window width) and the `ff` temperature term (7.8 points) are small next
to a 49-point process spread of the fixed-code frequency. Row 4's `ss` failure at the fixed code is -22.2 % at 3.0 V, of which
-2.35 points is supply.

**Upper bound for the lever classes the ruling names** (exact removal, which no circuit achieves), against the unchanged windows:

| idealisation | row 4 in-window | worst | row 5 in-window | worst |
|---|---|---|---|---|
| as graded (DR-0029) | 7/21 | 29.99 % | 26/63 | 37.33 % |
| supply term removed exactly (row 4); temperature term removed exactly (row 5) | 9/21 | 28.69 % | 27/63 | 29.99 % |

Perfect supply regulation / tracking bias moves row 4 from 7 to 9 of 21; perfect temperature compensation moves row 5 from 26
to 27 of 63. Neither closes a row, so **no candidate of the supply-regulation, tracking-bias or RC/comparator-delay
temperature-compensation class can pass rows 4 or 5 under a single fixed code.** Closing them needs process tracking of the
absolute frequency to about +/-5 % across ff/ss/rc, a change of oscillator architecture (for example a process-ratiometric
reference), not a trim-scheme, supply or TC tweak.

**Basis mismatch to resolve.** [DR-0017](0017-low-side-comparator-pmos-respin-supply-slope.md) derived the ratified windows on
"per-corner ratified-calibrated codes" (each die calibrated at 27 C / 3.3 V, error against its own calibration). On that basis
the same data gives 21/21 (row 4, worst 2.35 %) and 63/63 (row 5, worst 8.57 %): both rows pass on the DR-0028 netlist at the
deterministic corners. The failure is therefore a property of the fixed-code grading, not of the supply or temperature behaviour
the windows were derived for. The Monte Carlo ss span (5.44 points median vs 4.9 allowed, DR-0030) is a separate, unaddressed
finding on the DR-0017 basis.

**Not addressed here:** the Monte Carlo ss span (DR-0030); row 2 and row 8 failures; any DR-0004 question (no TC mechanism is
proposed, so DR-0004 is untouched).

## Alternatives considered

- **Build a supply-regulation or TC candidate netlist and re-grade**: not done. The bound above shows the best case still fails
  (9/21, 27/63; worst +28.7 % / +30 %); a fleet campaign would spend budget to confirm what the existing corner data fixes.
  The issue allows stopping at the best result and the remaining gap.
- **Relax rows 4/5 or add per-corner trim**: ruled out by the issue and the operator ruling.
- **Process-ratiometric redesign**: the only class the data supports; larger than #236 and an architectural decision, so it is
  left to the operator.

## Consequences

- Rows 4 and 5 stay FAIL at the fixed code; no ratified value changes. No `design/` change; no candidate DUT exists.
- Operator decision needed: (a) confirm the fixed-code basis and commission a process-tracking architecture study, or
  (b) state that rows 4/5 are graded on the DR-0017 per-die-calibrated basis, where they pass deterministically.
- Evidence is append-only under `sim/row45-attribution/`; no existing result is edited.
