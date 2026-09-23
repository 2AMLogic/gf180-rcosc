# 0018: Comparator PMOS re-spin post-layout (PEX) PVT re-verification — DR-0017's guardrails hold post-layout; DR-0010/0013/0015 superseded for the post-#60 hierarchy, ratified rows unchanged

- **Status**: Ratified — records post-layout verification evidence, no
  layout change. Supersedes the post-layout *figures* of
  [0010](0010-postlayout-pex-pvt-frequency-shift.md),
  [0013](0013-bias-cell-respin-postlayout-pex-reverification.md) and
  [0015](0015-trim-bank-respin-postlayout-pex-reverification.md) **for the
  post-#60 (DR-0017) hierarchy**: DR-0010 remains the valid post-layout
  characterization of the pre-#39 `rcosc_bias` GDS, DR-0013 of the
  post-#39/pre-#43 pair, DR-0015 of the post-#43/pre-#57 pair, and none of
  the three may be quoted against the post-#60 schematic. Does not
  supersede any ratified spec-table row of
  [0002](0002-target-spec-ratification.md)/[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md);
  confirms — does not relax or re-derive — DR-0017's two issue-#57
  guardrails against the extracted netlist, and retires the
  post-layout-deferral paragraph of
  [0017](0017-low-side-comparator-pmos-respin-supply-slope.md) (this issue,
  #61).
- **Date**: 2026-09-23
- **Decided by**: Builder agent, issue #61

## Context

DR-0017 (PR #60, `7383d62`) re-referenced the low-side comparator `XCMPL`
to the new complementary-PMOS cell `rcosc_comparator_p`, re-budgeted its
tail 8:1 → 4:1, and recomposed `rcosc_top` — and explicitly deferred the
post-layout (PEX) re-verification to a separate pass, per this repo's
re-spin convention (#28/#44/#50 → DR-0010/0013/0015). Until this record,
the newest committed post-layout run
(`sim/pvt-postlayout/results/20260922T004322Z/`) predated PR #60 and so
described the pre-#57 NMOS-only comparator hierarchy: **no post-layout
figure existed for the new cell, and both of DR-0017's issue-#57
guardrails (the Row-4 guardrail cell's f, and the trim range) were
verified against the un-extracted schematic netlist only.**

## Decision

**The post-#60 hierarchy is re-verified post-layout — 27-point
corner-endpoint subset × 2 sides, 0 failed runs — and both DR-0017
guardrails hold against the parasitic-annotated netlist. No ratified
spec-table row's disposition changes** (the ±1.1% calibration-point budget
remains unmeetable from layout parasitics alone, exactly the standing
DR-0010-class finding, re-quantized against the new hierarchy).

Evidence: `sim/pvt-postlayout/results/20260923T152954Z/` (+ raw logs under
`corners/20260923T152954Z/`), run at issue #28's flow with one additive,
opt-in extension — `pex_pvt_sweep.py --guardrails` (issue #61) — which
measures the guardrail cell and the per-process trim calibration on both
sides *inside the same run*, so every guardrail comparison below is
in-run. Provenance: `klt 0.4.0` (the `layout/run_checks.sh` toolchain pin,
built per its own documented `uv venv` recipe — the host's default `klt`
0.5.0 was deliberately not used for extraction), `ngspice-46`,
`gf180mcuC` @ `~/.volare` (Linux; prior PEX passes ran on macOS hosts
under ngspice-47 — the in-run schematic-side cross-check against the
committed DR-0017 campaign bounds host/run variance at **0.00%** at
matched points, so neither difference moves any figure below), fixed
post-trim code `0xA3` (auto-read from DR-0017's own campaign
`sim/pvt/results/20260923T030125Z/`, selected explicitly via
`--baseline-runid` because the newest `sim/pvt/results/` run
(`20260923T030905Z`) is DR-0017's delay-probe campaign, whose manifest
carries no calibration table). 54 subset runs, 0 failed, 166.3 s at 8
jobs.

- **Schematic-vs-extracted, 27-point subset at the fixed `0xA3`**: the
  re-spun layout still runs **slower than the schematic at every point:
  −18.78 % … −36.86 % (mean −25.65 %)**, worst at `ff`/−40 °C/3.6 V —
  the same always-slower sign and the same ff-cold-high-VDD worst-corner
  signature DR-0010/0013/0015 reported. Shallower on the mean than the
  pre-#57 pass (DR-0015: −17.46 % … −40.92 %, mean −27.32 %), though the
  two runs sit at different codes (`0xA3` vs `0x9D` — different trim-shunt
  populations load the timing ladder differently) and different
  hierarchies, so the means are not a like-for-like comparison; the class
  is unchanged. DR-0010's mechanism stands: first-order lumped RC adds
  real capacitance to an RC-timed core's switching nodes.
- **DR-0017 guardrail 1 — f must not increase at the Row-4 guardrail cell
  (`0x80`/`ff`/85 °C/3.6 V): holds.** Extracted side 38.0790 MHz vs
  DR-0017's campaign basis 55.3154 MHz — **31.16 % below** (and below the
  55.42 MHz delay-probe basis by a like margin). The in-run schematic side
  reproduces the campaign basis exactly (55.3154 MHz, 0.00 %), so the
  guardrail margin is not host noise. Post-layout, the knife-edge cell
  moves deeper under its limit, in the safe direction; the Iq half of
  DR-0017's Row-4 evidence remains schematic-level by this issue's own
  scope (the issue's guardrail wording is the free-running f).
- **DR-0017 guardrail 2 — trim range must not regress: holds.** Per-process
  single-point calibration at 27 °C/3.3 V against the ratified 48.000 MHz
  target, run on both sides with the same binary search
  `sim/pvt/pvt_sweep.py`'s `calibrate` performs:

  | process | side | f(0x00) | f(0xFF) | cal code | f at code | saturated |
  |---|---|---|---|---|---|---|
  | `tt` | schematic | 26.34 | 83.23 | `0xA3` | 47.982 | no |
  | `tt` | extracted | 20.81 | 60.58 | `0xD9` | 48.025 | no |
  | `ff` | schematic | 35.41 | 108.61 | `0x59` | 48.046 | no |
  | `ff` | extracted | 25.63 | 72.53 | `0xB3` | 48.016 | no |
  | `ss` | schematic | 20.46 | 66.05 | `0xCD` | 47.878 | no |
  | `ss` | extracted | 17.35 | 50.28 | `0xF7` | 48.019 | no |

  (MHz; schematic-side codes reproduce DR-0017's campaign codes `0xA3` /
  `0x59` / `0xCD` exactly, and its `tt` f(0xFF) = 83.23 matches the
  campaign's own `trim_curve` endpoint — two more 0.00 % in-run
  consistency checks.) Every extracted-side corner calibrates inner-range,
  none saturated — DR-0017's own criterion — with each landing within
  +0.052 % of the target (worst: `tt` at 48.025 MHz). The confirmation is
  scoped to the PEX subset's three processes (`tt`/`ff`/`ss`); the
  7-process factorial remains the schematic campaign's `sim/pvt/` job,
  per issue #28's subset definition.

**The one materially tightened margin**: post-layout, `ss` trims at
`0xF7` — 8 LSBs from the `0xFF` rail, with f(0xFF) = 50.28 MHz leaving
only ≈ **+4.7 % frequency headroom** above the target at the slow corner
(schematic basis: `0xCD` with 38 % headroom). The trim range does not
regress by DR-0017's criterion, but any further parasitic deepening at
`ss` — a future re-spin, or a finer extraction model that grows the
slow-corner penalty — could saturate it. That is the trim math this
record exists to state.

## Alternatives considered

- **Quoting DR-0015 as-is and skipping the re-verification.** Rejected:
  DR-0017 explicitly deferred its post-layout pass to this issue;
  DR-0015's figures describe the pre-#57 GDS pair and are void against
  the post-#60 schematic.
- **Verifying the guardrails from the fixed-`0xA3` subset alone.**
  Rejected: the guardrail cell is code `0x80`, not the calibration code,
  and trim-range confirmation requires actual per-corner searches on the
  extracted side — the issue's test plan explicitly requires the guardrail
  cell *in* the extracted-vs-schematic comparison with its margin stated,
  not an aggregate.
- **Hard-coding DR-0017's 55.32 MHz as the comparison basis.** Rejected:
  sourced instead from the baseline campaign's own `pretrim` row at the
  cell (which is exactly that figure), so the anchor is citable evidence,
  not a transcribed constant.
- **`klt pex` request-JSON verbatim.** Standing rejection, unchanged since
  issue #28 (no `--deck-option`/`--pins` passthrough — it cannot select
  this design's non-default MiM-cap density and would silently invalidate
  every delta); see `sim/pvt-postlayout/README.md`.
- **Relaxing or re-rounding a ratified row to absorb the parasitic
  penalty.** Rejected (CLAUDE.md): a contradiction is reported as a
  contradiction.

## Consequences

- **Quote this record and
  `sim/pvt-postlayout/results/20260923T152954Z/` for post-layout figures
  of the post-#60 hierarchy from now on**; DR-0010/0013/0015 are
  superseded for it (and remain valid for their own GDS pairs). The
  status paragraphs in `README.md`, `sim/README.md`'s campaign index,
  `sim/pvt-postlayout/README.md`'s run table, and the challenge-5
  proposal's post-layout divergence note are updated accordingly.
- DR-0017's deferred "post-layout (PEX) PVT re-verification is not part of
  this record" consequence is retired: both its guardrails are confirmed
  against the extracted netlist, and its ratified post-trim rows
  (−2.9/+2.0 % at-cal, −10.8/+8.8 % full-temp) stand as **schematic-basis**
  figures — post-layout, the same-code re-simulation runs −18.78 %…
  −36.86 % slower, so closing the post-trim accuracy gap must budget a
  **≈ −25.65 % mean** layout-parasitic frequency penalty (slightly
  shallower than the ≈ −27 % DR-0015 left, same class) on top of the
  schematic-level residuals DR-0017 leaves.
- The `ss` trim-headroom finding above is the named risk this record adds:
  8 LSBs / ≈ +4.7 % at the slow corner post-layout. Any layout compaction,
  extraction-model refinement, or re-spin touching the slow-corner
  parasitic path should re-run this campaign's `--guardrails` pass before
  claiming the trim range still holds.
- `sim/pvt-postlayout/pex_pvt_sweep.py` gains the opt-in `--guardrails`
  pass (default path byte-identical to issue #28's flow); its baseline
  auto-pick now has a documented caveat — the newest
  `sim/pvt/results/<runid>` may be a probe campaign without a calibration
  manifest, in which case pass `--baseline-runid` explicitly (this run
  did).
- Issue #5's T1 rollup gains this post-layout evidence for the DR-0017
  re-spin, but this record does not itself address #5's item-5
  signoff-manifest citation gap or item-7 `klt pex` grader-format gap
  (out of scope by this issue's own list).
