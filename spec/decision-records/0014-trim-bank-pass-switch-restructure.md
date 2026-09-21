# 0014: Trim-bank pass-switch restructure — transmission-gate shunts with locally inverted pfet gates, trim range restored, per-code supply sensitivity re-attributed

- **Status**: Ratified — records simulation evidence. Does **not** supersede any
  row of [0002](0002-target-spec-ratification.md)/[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md);
  does not reopen [0004](0004-no-active-tc-compensation-runtime-discipline.md).
  This is the DR-0012-sanctioned follow-up record (issue #43), fixing the
  mechanism DR-0012 isolated as *out of scope there*.
- **Date**: 2026-09-21
- **Decided by**: Builder agent, issue #43

## Context

DR-0012 isolated and deferred a second, distinct mechanism: the trim-bank
pass switches (`SW0..SW7`, pre-#43 one `nfet_03v3 W=4u L=0.5u` per bit,
gate = `t_i`, bulk = `vss`) lose their shunt effectiveness as the timing node
rises toward `vh = 2/3·VDD`, because each switch's effective
`V_GS = t_i − v(low node)` collapses into the body-effected subthreshold
region exactly where the RC charge time concentrates. The campaign evidence
(`20260921T075822Z`): mid-block codes near-dead (`0x00`→`0x10` measured
+0.03% against a ~+5% ideal-block step), a PVT-dependent "phantom" series
resistance on every ON code (`ss`@`0xEF` supply sensitivity ~+20.0%, vs
~+11.0% at `ss`@`0x80`), calibration saturation at the slow corners
(`ss`/`rc_s` clamped at `0`, the ratified 48.000 MHz target unreachable at
every corner), and the trim-range row not met since DR-0005
(±34.42% realized vs. ±40% ratified).

Issue #43 fixed this mechanism with an explicit guardrail: only the switches;
the `ppolyf_u_1k` segment values `RFIX`/`R0..R7` frozen at the issue-#16
derivation.

## Decision

**Each trim segment's shunt is restructured from a single NFET pass switch to
a transmission gate with a locally inverted pfet gate; no resistor value is
re-tuned and no ratified spec figure is superseded.**

`design/rcosc_trim_bank.sch` changes (issue #43):

- **`SW<i>` (nfet, gate = `t_i`, bulk = `vss`) stays, and a new `PW<i>`
  (pfet, gate = `tb_i`, bulk = `vdd`) is added in parallel across the same
  node pair.** The nfet serves the low-node end of the shunt's node swing;
  the pfet serves the high-node end, where its `|V_GS|` grows with node
  voltage: the pair tiles the full 0..VDD range with no drive-dead region.
  A pure per-position re-size of the old NFET cannot do this: for the
  upper-ladder segments the switch's low node rides near VDD the whole
  charge phase, where an NFET gate driven from `VDD` has no overdrive at
  any width.
- **A per-bit CMOS inverter (`NINV<i>` 2u / `PINV<i>` 4u, `L=0.5u`) generates
  `tb_i`** on a new `vdd` pin (wired in `rcosc_top.sch`), because trim bits
  at the cell boundary are single-ended (`t_i`), and changing their polarity
  would break the ratified code→R mapping and every campaign tool. Trim bits
  are quasi-DC, so the inverters draw no static current and DR-0003 Row 4 is
  unaffected by them.
- **Pass devices run at `L=0.28u`** — the DRM 7.7 `PL.2` gate-poly minimum
  for the 3.3V column and the `sm141064` model's own `nfet_03v3`/`pfet_03v3`
  default `l` — with per-position widths gridded from transient data, not
  closed form: `SW<i>=PW<i> = 24/16/12/8/6/5/4/3 µm` for `i=0..7`. The
  taper's logic: the timing node is a ~270 fF capacitor, and a shunt's
  on-channel gate capacitance loads it in proportion to its width where the
  ladder couples it — worst at the m-adjacent position (bit 7), least at the
  top (bit 0, decoupled through ~100 kΩ of segment). The width floor rises
  with the ladder's segment sizes falling toward the LSB end: bit 0 must
  beat a 374 Ω segment, bit 7 a 47.9 kΩ segment. The gridded compromise:
  endpooints preserved (`f(0x00)` 27.30 vs 27.67 pre-fix), fast end freed
  (`f(0xFF)` 84.94 vs 56.71), no measured oscillation failure anywhere on
  the grid incl. `ff`/−40 °C/3.6 V at `0xFF` (117.8 MHz).
- **`sim/pvt/pvt_sweep.py` is updated** (the campaign-update case issue #43's
  curation explicitly anticipated): trim-curve sampling now includes the
  seven block-boundary codes so the boundary behavior is first-class
  evidence; a `posttrim_ratif` pass now holds per-corner codes calibrated to
  the *ratified* 48.000 MHz target (impossible pre-#43 — every corner
  saturated below it); a `switchprobe` pass re-measures the issue's own
  acceptance pairing (`ss`/27 °C supply sensitivity, `0x80` vs `0xEF`); and
  two prose claims that pre-#43 evidence had made *vacuously* true are
  made conditional on the data: the "monotonically non-decreasing by
  construction" calibration premise and the "ratified target unreachable at
  every corner" surrogate-target explanation.

**Post-#43 PVT campaign: `sim/pvt/results/20260921T173529Z/`** (full
7-corner × 3-T × 3-V factorial, 361 unique points, 0 failed measurements,
`tran 200p 1200n` average-over-20-periods methodology), against the ratified
target-spec table row by row. The first interim run on this branch
(`20260921T164939Z`, pre-driver-fix) is committed append-only for the record
trail and superseded within this same issue — its summary carries the two
stale prose notes this record describes, so its numbers are not to be cited
as final.

| Row | Ratified | pre-#43 (20260921T075822Z) | **post-#43 (20260921T173529Z)** | Disposition |
|---|---|---|---|---|
| Trim range | ±40% (28.8–67.2 MHz) | ±34.42% (27.6659–56.7060, `not met` since DR-0005) | **±51.36% (27.2955–84.9384 MHz, ratio 3.1118)** | **met** — first campaign since DR-0005 to cover the ratified 28.8–67.2 window from both sides |
| Output frequency | 48.000 MHz | max reachable 56.7060 (`ss`/`rc_s` saturated below 48) | max reachable **84.9384**; **48.000 reached inner-range at all seven corners** (tt `0x9D`, ff `0x4C`, ss `0xCF`, fs `0x9B`, sf `0xA3`, rc_f `0x58`, rc_s `0xBE`) — **no corner saturates** | met — stronger: the ratified target is now trim-reachable on every process corner, not just the fast ones |
| Trim step | 0.314 %/code | 0.4116 %/code (endpoint-share average; mid-block codes dead: `0x00`→`0x10` +0.03%) | 0.8282 %/code (endpoint-share); **`0x00`→`0x10` block step +5.03%** (≈0.31 %/code, on the ratified per-code figure), every sampled 16-code block step positive | met — the previously-dead mid-block steps are live at ≈ their binary weights |
| Post-trim, at calibration point (per-corner code, surrogate target) | ±1.1% | −11.65% / +8.32% | **−7.14% / +4.62%** | **exceeds** — improved ~4.5/3.7 pt, still outside ±1.1% |
| Post-trim, full temperature range (per-corner code, surrogate target) | +8% / −9% | −20.15% / +13.03% | **−14.53% / +7.00%** | **exceeds** — upper side now inside +8%; lower side improved 5.6 pt, still outside −9% |
| Post-trim, at calibration point (per-corner code, **ratified** 48.000 target — pass new in #43) | ±1.1% | unmeasurable (no corner reached the target) | −8.13% / +5.79% | **exceeds** — measurable for the first time; same verdict class |
| Post-trim, full temperature range (**ratified** target) | +8% / −9% | unmeasurable | −15.49% / +7.78% | **exceeds** — upper side inside +8%, lower outside −9% |
| ΔT coefficient spread (per-corner calibrated codes, surrogate) | ≈ +1177 ppm/K budget basis | +774…+1003 ppm/K | **+559…+756 ppm/K** | all seven corners now below the arithmetic's budgeted basis |
| Supply sensitivity, slow-corner calibrated codes (ss / sf / rc_s) | ~0 (ratiometric ideal) | +20.05% / +12.02% / +13.70% | **+11.76% / +7.73% / +6.09%** | roughly halved — the phantom's share removed; the remainder re-attributed below |
| Free-running untrimmed process spread | ±35% (−27.7/+47.6 exact) | −26.11% / +39.90% | −23.72% / +34.56% | within the ratified bound |
| Quiescent current (running, Row 4) | < 500 µA | `0x00`/`0x80` met across the whole factorial (worst 459–498 µA); `0xC0`/`0xFF` exceed at ff/85 °C/3.6 V (541.85 / 614.87 µA, DR-0012) | Iq PVT factorial `sim/iq/results/20260921T181049Z/`, 252 points, 0 failed: `0x00` worst 460.06 µA (**met**), `0x80` worst 498.76 µA (**met**, 1.24 µA of margin at ff/85 °C/3.6 V), `0xC0` worst **550.20** µA (`exceeds`), `0xFF` worst **724.42** µA (`exceeds`) | **verdict classes unchanged; values aggravated at the fast-hot high-code cells** — the restored fast-end frequency carries the per-cycle timing-cap charge with it; see below |

**On the two acceptance rows that did not come back clean:**

- **Block-boundary local dips (characterized, not fixed by sizing).** With the
  frozen R map, every `0xkF → 0x(k+1)0` code pair has only ~1 LSB-R
  (~374 Ω, `R_maxbit` minus the sum below it) of ideal-switch monotonicity
  margin. A realizable shunt's trip-weighted residual exceeds that at slow
  corners — all of bit 7's devices sit directly on the timing-capacitor node —
  so those specific adjacent pairs can dip a few percent locally **at every
  shunt sizing that preserves the endpoints** (gridded exhaustively during
  this issue: uniform, per-position-tapered, and bit-7-width sweeps; the dip
  reappears at every width that does not break `f(0x00)`). Measured at tt:
  `0x7F`→`0x80` −6.40%, `0xBF`→`0xC0` −3.21%, `0xDF`→`0xE0` −1.72%,
  `0xEF`→`0xF0` −0.42%; at ss/85 °C/3.0 V the `0x7F`/`0x80` dip is −4.82%.
  Every sampled 16-code block step is positive at every corner, and the
  calibration picks codes whose own f is re-simulated and reported. The
  pre-#43 "monotone by construction" claim held only because the dead
  mid-block switches flattened the curve; the campaign driver now says all
  of this explicitly instead of asserting vacuous monotonicity. Fixing the
  margin itself would mean re-tuning the frozen R map — explicitly out of
  scope here.
- **Per-code supply sensitivity at the ss corner (`switchprobe`).**
  `0x80`: +11.0…+11.3% pre-#43 → **+8.34%** post-#43. `0xEF`:
  +20.0…+20.8% pre-#43 → **+18.78%** post-#43. The named acceptance
  ("no longer materially worse at high codes") is **met at `0x80`, not met
  at `0xEF`**, and the campaign's own rows re-attribute the residue: the
  supply sensitivity grows monotonically as the code's in-chain trim mass
  falls (+8.34% at 58.5 kΩ, +10.5% at 46 kΩ, +13.9% at 28 kΩ, +18.8% at
  15.3 kΩ), which is the signature of the comparator/latch delay term paid
  ≈3× into the charge phase (DR-0012's own measurement) whose period-share
  grows as the RC term shrinks. The switch residual's own 3.0→3.6 V
  contribution at these codes is bounded ≈1–3 points by direct arithmetic on
  the frozen map (its R-share at `0xEF` is ~6–8% of in-chain mass, and a
  pass-device overdrive ratio moves that share by <±25%). The measured gap
  is ~10 points. **Conclusion: the remaining high-code supply sensitivity
  is dominated by the comparator/latch delay residue, not the switch
  phantom** — revising the DR-0012 attribution, which credited the phantom
  with the slow-corner calibrated-code residual. That mechanism was already
  named as the *other* residual of DR-0012; it is filed as its own follow-up
  (issue #51) carrying this campaign's quantification.

## Alternatives considered

- **Wider NMOS-only per-position re-sizing (the issue's "wider W" option).**
  Rejected on physics: for the upper-ladder segments the switch's low node
  rides near VDD through the whole charge phase, where an NFET with its gate
  at VDD has zero overdrive — at any width. Gridded (W=8/16/32 µm) before
  the TG was adopted: mid-block steps stay dead.
- **PMOS gate driven directly by `t_i` (no inverter).** Rejected: wrong
  polarity — a PMOS is ON when its gate is LOW, but the ratified code
  semantics ("bit = 1 shorts the segment", DR-0003) and every campaign tool
  require active-high. Adding the per-bit local inverter preserves the
  cell-boundary interface one-to-one.
- **Stacked-device shunts.** Rejected: series stacking raises, not lowers,
  the effective threshold barrier per device; it does not tile the node
  swing the way a complementary pair does.
- **Fixing the block-boundary margins by nudging the R map.** Rejected:
  the issue's own guardrail freezes `RFIX`/`R0..R7` at the issue-#16
  derivation; one issue, one mechanism. The dips are characterized
  (campaign evidence, driver prose) instead of absorbed.
- **Silently keeping the pre-#43 campaign's monotonicity and unreachability
  prose.** Rejected: both claims were made true pre-#43 *by the defect being
  fixed* (flat mid-block staircase; saturation below 48 MHz). The driver now
  derives them from the data instead of asserting them.
- **Do nothing and record the phantom as permanent.** Rejected: DR-0012
  explicitly warranted this targeted repair attempt, and the trim-range row
  has been `not met` since DR-0005.

## Consequences

- `README.md`'s target-spec table is **unchanged** by this record.
- `design/rcosc_trim_bank.sch` carries the restructured shunts; the
  comparator, bias, `rcosc_top` nets, and trim code semantics are
  functionally unchanged (top gains the wired `vdd` pin for the inverters);
  `design/netlist/*` regenerated; `design/README.md` "Trim bank sizing"
  documents the switch restructure; `sim/README.md`'s campaign index gains
  the new run rows.
- **The trim-range row is met for the first time since DR-0005**, and the
  ratified 48.000 MHz target is reached inner-range at all seven process
  corners. The two post-trim accuracy rows remain **not met**: the
  phantom-residual share is removed, and the remaining excess is now
  attributed, with campaign evidence, to the comparator/latch delay
  residue (the other named follow-up from DR-0012). No result is rounded
  up to "met" and no ratified row is relaxed.
- **Quiescent row 4 is honestly worse at the fast-corner hot/free-running
  cells** (`0xC0`/`0xFF` at ff/85 °C/3.6 V, now 550.20 / 724.42 µA vs
  541.85 / 614.87 pre-#43): the restored fast-end frequency carries the
  per-cycle timing-cap charge with it. The row was already `exceeds`
  there pre-#43; the per-code verdict classes are unchanged (`0x00`/`0x80`
  met everywhere, `0x80` with only 1.24 µA of margin at its worst cell).
  Re-opening the bias/Iq budget is deliberately not done here (one issue,
  one mechanism).
- **Layout consequence (acknowledged, not executed here):** the committed
  `layout/` cells and the post-layout PEX evidence now describe the
  **pre-#43** trim bank. (DR-0012 had left the bias cell describing
  pre-#39, but during this branch's final rebase-onto-`main` the bias
  cell's re-spin landed as #48 and its record took the 0013 slot
  ([DR-0013](0013-bias-cell-respin-postlayout-pex-reverification.md)) —
  this record was renumbered 0013 → 0014 accordingly — so the trim cell
  and the top-composition re-verification are what now remain stale below.)
  The trim-bank cell's GDS + LVS-reference re-spin — including the cell's
  new `vdd` pin and the TG devices in `build_cells.py` — is filed as its
  own follow-up issue (#50), and DR-0010's / DR-0013's post-layout figures
  must not be quoted against the post-#43 trim tree until that
  re-verification lands.
- If a later revision wants to fix the ~374 Ω block-boundary margins, the
  calibration-granularity trade, or the delay residue, each gets its own
  record with new evidence — not a silent edit of this one.
