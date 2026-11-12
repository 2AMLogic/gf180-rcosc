# 0037: Row 4 `ss` supply span: the whole charge-RC supply term is the bank pass gates, not parasitic C; DR-0034's 0.69 pt was a code-shift artefact; a re-centred 3x-W bank meets 4.9 pt in simulation

- **Status**: proposed - measurement and a candidate only. Changes no ratified row, window or value; per-die calibration basis of
  [0032](0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md) unchanged; no per-corner trim; [0004](0004-no-active-tc-compensation-runtime-discipline.md)
  untouched. **No design change is merged**: committed schematics / netlists are unchanged (layout not re-extracted for the candidate).
- **Date**: 2026-11-12
- **Decided by**: Loom Builder (issue #320), pending operator ratification

## Context

[0034](0034-row4-pass-gate-width-lever-insufficient-ron-is-part-of-the-ss-rc-term.md) found that 2x pass-gate W cut the `ss` span only
0.69 pt (needs >= 1.2) and concluded Ron explains about 1.3 pt of the 3.03 pt charge-RC term, leaving ~1.7 pt "not isolated". #320 asks
to isolate that remainder and cut the span to <= 4.9 pt.

## Measurement (`sim/row4-nonron/`, batch fleet; `ss`, 27 C, same bench and attribution as 0033)

`tau = t_chg / ln((VDD-v0)/(VDD-vh))`; span = eps(3.6 V) - eps(3.0 V), pt. Control reproduces 0033 exactly (RC term +3.03, total +6.13).

1. **Parasitic C is not the cause.** Removing all bank-switch junction C (`nojb`), the discharge-device junction C (`nojd`), both, or
   adding 200 fF of linear C on the timing node (`capx`) leaves tau(3.0 V)/tau(3.6 V) at 1.042-1.045 (control 1.0440) and the RC-term span
   at +2.89 .. +3.18 pt. Candidate "voltage-dependent switch/gate C on the timing node" is refuted. The poly resistor model has
   `r_vc1 = r_vc2 = 0` (no voltage coefficient) and there is no bias current in the charge path (VDD -> R -> bank -> vc).
2. **Replacing the 16 pass devices by ideal switches removes the supply term.** At the same code 212: tau(3.0)/tau(3.6) 1.0440 -> 1.0037,
   RC-term span +3.03 -> +0.24 pt (codes 0 / 255: +0.43 -> +0.37 and +4.33 -> -0.03). The RC term follows the number of closed
   switches in series (committed span 0.43 / 3.03 / 4.33 pt at 0 / 4 / 8 closed bits). **There is no ~1.7 pt non-Ron remainder; the 0034 split was
   wrong.** The DC small-signal Ron table of 0034 under-states the transient effect (the switch carries the charging current, node levels vary).
3. **Why 0034's 2x W looked weak: the code moved.** At a fixed code (no re-calibration), 2x W gives span 4.91 (-1.22 pt), 4x W 3.99 (-2.14 pt):

   | W scale | tau 3.0 V (ps) | tau 3.6 V | RC-term span | total span | f(3.3 V) MHz |
   |---|---|---|---|---|---|
   | 1x | 13792 | 13210 | +3.03 | +6.13 | 47.95 |
   | 2x | 14586 | 14193 | +1.95 | +4.91 | 45.58 |
   | 4x | 16882 | 16589 | +1.29 | +3.99 | 40.41 |

   Wider switches slow the oscillator (extra timing-node C; `nojb` is 3 % faster), 0034 re-calibrated the `ss` code 212 -> 218, which closes one more
   series switch (0xD4 -> 0xDA: 4 -> 5 bits set) and gave back most of the gain.

## Candidate (simulation only): 3x W with the fixed base resistor re-centred (`w3r65`)

Pass devices at 3x W and the base resistor (`X$91`, VDD -> bank, 12.0386 um x 2 um poly) shortened to 65 % so code 212 stays at about 48 MHz
(re-centring points: 2x W / 75 %, 85 %: 5.20 / 5.00 pt at 49.06 / 47.60 MHz; 3x W / 70 %: 4.64 pt at 47.00 MHz; 4x W / 55 %, 65 %: 4.43 / 4.32 pt at
46.66 / 45.13 MHz; 2x W cannot reach 4.9 once re-centred).

| quantity (`ss`, 27 C, code 212) | committed | `w3r65` | target |
|---|---|---|---|
| f at 3.3 V (MHz) | 47.95 | 47.78 | |
| eps at 3.0 V / 3.6 V (pt) | | -2.60 / +2.13 | |
| supply span (pt) | 6.13 | **4.73** | <= 4.9 |
| charge RC-term span (pt) | 3.03 | 1.62 | |

Trim range, 27 C / 3.3 V, code 0x00 / 0xFF (MHz): `tt` 28.15 / 75.08 (committed 28.65 / 76.42; row-2 window 28.8-67.2 still covered both ends),
`ss` 22.26 / 60.65 (22.62 / 61.18), `ff` 37.01 / 95.95 (37.72 / 98.20). Unlike 2x W without re-centring, the top end is not lost.

**Not shown (open):** the `tt` / `ff` supply spans and all temperature points at the candidate's per-die codes (needs `tt` / `ff` calibration
scans; row 5 `ff` 85 C / 3.0 V margin in particular), and the 500-die campaign. Also this is **two** edits (W and base R) - the base-R
re-centring is what keeps the oscillator at its operating frequency, but it is not literally "one knob" and 0034 rejected a ladder retune as a
second knob; the operator should decide whether it counts as one re-centred switch-sizing change.

## Decision

Do not adopt in this record. Row 4 `ss` span stays at the DR-0032 / DR-0033 figures until the open items above are measured and the
operator ratifies. 0034's attribution ("Ron ~45 % of the RC term, ~1.7 pt elsewhere") is **superseded by this record**; its
"do not adopt 2x W alone" outcome stands.

## Layout / LVS / checks

Adoption needs the 16 bank pass devices at 3x W (a per-device layout change: the pass-gate strip grows) and `X$91` shortened to 65 %, then
`design/rcosc_trim_bank.sch` + `design/rcosc_top.sch`, `design/regen-netlist.sh`, re-extraction, LVS and every downstream evidence set re-run.
None done here: `design/check-netlist-consistency.py` is unaffected because no schematic changed.

## Alternatives considered

- **2x W, re-centred**: 5.0-5.2 pt, misses 4.9. **4x W**: 4.3-4.4 pt but the oscillator slows to 45-47 MHz at the re-centred points tried and the top end falls further.
- **Ideal-switch style (charge pump gate boost)**: rejected in 0034.
- **Relaxing windows / per-corner trim / active TC compensation**: out of scope.
