# 0006: Post-#16-resize PVT campaign — trim range and post-trim accuracy still unmet, ratified spec unchanged

- **Status**: Ratified — records simulation evidence. Does **not** supersede
  any row of [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md),
  [0004](0004-no-active-tc-compensation-runtime-discipline.md), or
  [0005](0005-pvt-campaign-frequency-shortfall-spec-unchanged.md). The
  ratified target-spec table in `README.md` stands unchanged.
- **Date**: 2026-09-06
- **Decided by**: Builder agent, issues #16 / #18

## Context

Issue #16 (PR #19) root-caused the ~2.3× frequency shortfall and
compressed trim-bank ratio DR-0005 found in the pre-#16 schematic
(comparator/latch propagation delay and the discharge switch's
faster-than-comparator on-resistance invalidating the `f ≈ 1/(R·C·ln 3)`
closed form — see `design/README.md` "Root cause of the pre-#16
frequency/trim-range shortfall") and re-sized `design/rcosc_bias.sch`'s
`RBIAS` and `design/rcosc_trim_bank.sch`'s `RFIX`/`R0..R7` from real,
simulated reference-corner transient data. PR #19 validated the resize at
the reference corner only; the full process×temperature×supply PVT
campaign was deferred to follow-up issue #18 for shared-build-host-load
reasons (see PR #19's description and #18's Problem Statement).

This record is that deferred campaign, run against the issue #16 resize
exactly as landed on `main` (git sha `af1cf30c`, unchanged by this
record): 7 process corners (`tt`/`ff`/`ss`/`fs`/`sf` plus the
resistor/MIM-cap-only `rc_f`/`rc_s` split) × 3 temperatures
(−40/+27/+85 °C) × 3 supplies (3.0/3.3/3.6 V) — 63 points per pass,
pre-trim and two post-trim methodologies, 278 unique operating points
total, **0 failed measurements**, 15.0 minutes wall clock at 14 parallel
jobs. Full evidence: `sim/pvt/results/20260906T030219Z/{results.csv,manifest.json,summary.md}`,
raw logs under `sim/pvt/corners/20260906T030219Z/`. This evidence
directory is new and additive — the issue #12 evidence
(`sim/pvt/results/20260905T211140Z/`) is unmodified.

This run also completes issue #18's identical scope (#18 was filed
specifically to track this campaign in case #16 itself did not get to it
first — see #18's "Note on issue #16's own status"); this record and its
citing PR close both issues rather than duplicating the evidence.

## Decision

**No ratified spec figure is superseded.** The findings, row by row
against `README.md`'s target-spec table (all figures from
`sim/pvt/results/20260906T030219Z/summary.md`):

| Row | Ratified | Simulated (this campaign) | Disposition |
|---|---|---|---|
| Free-running, untrimmed, process spread (fixed T=27 °C/V=3.3 V) | ±35% first-order (−27.7%/+47.6% exact) | −28.73% / +46.53% | **Met** — within the ratified bound, consistent with DR-0005's confirmation of this row and unaffected by the resize (this row's derivation does not depend on the timing R/C absolute sizing). |
| Output frequency | 48.000 MHz | Max reachable at the reference corner: 65.9204 MHz at code `0xFF`; the realized trim curve spans 29.5072–65.9204 MHz, bracketing the 48.000 MHz target well inside the range (unlike DR-0005's pre-resize finding, where the target was unreachable at *any* corner/code). | **Met.** |
| Trim range | ±40% (28.8–67.2 MHz) | ±38.16% (29.5072–65.9204 MHz realized at the reference corner); trim-bank endpoint ratio 2.2340 realized vs. 2.3333 intended | **Not met — but close.** A large improvement over DR-0005's 1.2058 realized ratio; the resize gets to 96% of the intended endpoint ratio and 95% of the ratified ±40% window, not the ~35%-of-target shortfall DR-0005 recorded. |
| Post-trim, at calibration point | ±1.1% | −34.83%/+53.97% (single global code `0xBF`, calibrated against the ratified 48.000 MHz target) or −16.28%/+15.24% (per-corner code, calibrated against the surrogate target `f(tt,27°C,3.3V,0x80)=42.0678` MHz) | **Exceeds, both methodologies.** |
| Post-trim, full temperature range | +8%/−9% | −42.43%/+62.77% (global code) or −25.74%/+21.18% (per-corner code) | **Exceeds, both methodologies.** |

Two things distinguish this from DR-0005's finding rather than simply
repeating it:

1. **The trim bank is no longer saturated.** DR-0005's post-trim rows were
   dominated by every process corner's calibration search pinning at code
   `0xFF` (zero headroom left to correct anything) because the ratified
   48.000 MHz target was unreachable at any corner. This campaign's
   calibration table shows only one corner (`ss`) saturates against the
   ratified target, and none saturate against the surrogate target — the
   trim bank now has real headroom at every corner. Despite that, the
   post-trim accuracy rows are still exceeded by a wide margin under both
   calibration methodologies.
2. **The surrogate-target (per-corner, "trim every die at test") residual
   barely moved.** DR-0005 measured −23.48%/+21.20% under this
   methodology (pre-resize, still partially saturation-limited); this
   campaign measures −25.74%/+21.18% (post-resize, not saturation-limited
   for this methodology at all). The residual this methodology is meant to
   isolate — process/temperature/supply sensitivity *after* accounting for
   trim saturation — is essentially unchanged by fixing the trim-bank
   sizing. This means the accuracy shortfall DR-0005 attributed largely to
   saturation was, in fact, only partially a saturation artifact: a
   comparable residual survives once saturation is removed, driven by
   temperature and supply sensitivity in the comparator/bias path itself
   (see the per-corner ΔT-coefficient and supply-sensitivity tables in
   `summary.md`, e.g. `tt` at +1576 ppm/K and `ss` at +22.11% over
   3.0→3.6 V — both far larger than the timing resistor's own −1200 ppm/K
   TCR that DR-0003's post-trim accuracy derivation was based on).

The top-code non-monotonicity DR-0005 flagged (`0xF0` → `0xFF`: 22.2197 →
21.3761 MHz, a ~4% drop, pre-resize) **does not reproduce** in this
campaign's trim curve: `0xF0` → `0xFF` is now 64.0718 → 65.9204 MHz, a
further +2.9% *increase* — monotonically consistent with every other step
in the curve. This was checked directly against the raw `results.csv`
`trim_curve` pass (not just the summary table) at the same `tstop=1200 ns`
window issue #16 already reduced to match the resized schematic's faster
free-running frequency (25 measured edges comfortably fit in that window
at every code in this curve, so this is not a re-run at a longer window —
the anomaly is simply absent at the resized operating point, not marginally
resolved by more settling time). Two much smaller (~0.1%, opposite-sign-of-
trend) dips remain at `0x10` (vs. `0x00`) and `0x90` (vs. `0x80`) — two
orders of magnitude smaller than the pre-resize anomaly and consistent with
ordinary simulation/measurement noise at this resolution, not flagged as a
new instance of the same effect.

## Alternatives considered

- **Ratify a narrower trim range or looser post-trim accuracy figures
  matching these numbers.** Rejected, for the same reason DR-0005
  rejected it: CLAUDE.md prohibits relaxing the ratified spec to make
  results pass. The ±40% trim range and post-trim accuracy budgets remain
  anchored to external precedent and gf180mcu's own published device data
  (DR-0002/0003), independent of this schematic's specific sizing.
- **Treat the trim-range shortfall (±38.16% vs. ±40%, a 2-point-of-
    percentage miss) as effectively met and round up.** Rejected — CLAUDE.md
  and this repo's decision-record discipline draw the verdict from the
  simulated number, not from how close it looks; the same discipline that
  requires recording DR-0005's much larger miss requires recording this
  smaller one exactly as measured. The `summary.md` table's own generated
  verdict already says "not met," and this record does not override it.
- **Conclude the post-trim accuracy rows are permanently unreachable by
  this topology on gf180mcu and file a spec-relaxation proposal.**
  Rejected as premature. The comparator/bias path's temperature and
  supply sensitivity (point 2 above) has not itself been the subject of
  any resizing attempt — issue #16 resized only the timing R/C, not the
  comparator or bias-generator's own PVT sensitivity. Concluding the
  target is unreachable would require a schematic revision aimed at that
  specific sensitivity and a further PVT campaign against it, neither of
  which this record's evidence covers.
- **Leave the discrepancy undocumented, noted only in the PR
  description.** Rejected — same evidence-discipline requirement DR-0005
  cites.

## Consequences

- `README.md`'s target-spec table is **unchanged** by this record.
- `design/README.md`'s "Full PVT-corner re-verification" section is
  updated to cite `sim/pvt/results/20260906T030219Z/` and this record,
  replacing its prior "in progress" language.
- Issues #16 and #18 are both closed by the PR carrying this record: #16's
  own acceptance criteria (root cause, resize, and full PVT re-campaign)
  are now all satisfied, and #18's identical scope is satisfied by the
  same evidence rather than a duplicate run.
- **A new, more specific follow-up is now warranted**: unlike DR-0005 (where
  the dominant, single mechanism was trim saturation against an
  unreachable target), this record's finding is that the comparator/bias
  path's own temperature and supply sensitivity — not budgeted by
  DR-0003's timing-resistor-TCR-only derivation of the post-trim accuracy
  figure — is the dominant residual once saturation is removed. A future
  schematic-revision issue that wants to close the remaining post-trim
  accuracy gap should target that sensitivity specifically (e.g. the bias
  generator's supply/temperature dependence, not further timing-R/C
  retuning), rather than repeating issue #16's approach. This record does
  not file that issue — it is future scope, consistent with CLAUDE.md's
  decomposition discipline.
- **What is not invalidated**: the relaxation-oscillator topology
  ([0001](0001-relaxation-oscillator-topology.md)), the decision not to add
  active TC compensation ([0004](0004-no-active-tc-compensation-runtime-discipline.md)),
  the free-running untrimmed process-spread figure
  ([0003](0003-pdk-sourced-process-spread-tcr-and-iq.md) Row 1, reconfirmed
  above), and DR-0005's own findings (superseded in effect, not in record,
  by this campaign's evidence against the now-resized schematic) all
  stand.
- If a future schematic revision targeting the comparator/bias-path
  sensitivity shows the ratified trim-range or post-trim accuracy rows
  genuinely cannot be met by any realizable implementation of this
  topology on gf180mcu, that finding must be recorded in its own
  superseding decision record — not folded into this one.
