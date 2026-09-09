# 0011: Quiescent-current PVT-corner factorial — DR-0003 Row 4 met at the reference corner, exceeds off-reference; ratified spec unchanged

- **Status**: Ratified — records simulation evidence. Does **not** supersede
  any row of [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md),
  [0007](0007-quiescent-current-exceeds-target-post-resize.md),
  [0008](0008-iq-metric-correction-and-bias-rebalance.md), or
  [0009](0009-running-iq-metric-basis-and-partial-trim-range-recovery.md).
  The ratified target-spec table in `README.md` stands unchanged, including
  Row 4's `< 500 µA` (running) figure.
- **Date**: 2026-09-09
- **Decided by**: Builder agent, issue #35

## Context

Every quiescent-current (Iq) figure recorded before this issue — DR-0007,
DR-0008, DR-0009 — was measured at exactly one operating point: the
reference corner (`tt` / 27 °C / 3.3 V). `sim/pvt/pvt_sweep.py` has run the
full process × temperature × supply factorial for **frequency** since
issue #12, but `sim/iq/iq_sweep.py` never grew the matching axis for Iq —
`design/README.md`'s Non-goals bullet and DR-0009's own "Consequences"
section both named this a standing gap. DR-0009's own sizing margin
(~6.3% headroom on `iq_run` at the worst *simulated* code, but only ever
checked at one corner) was exactly the kind of thin, unstress-tested margin
that gap made possible: Iq in a relaxation oscillator rises with
frequency, and the PVT campaign's own data
(`sim/pvt/results/20260907T090653Z/summary.md`) already showed the `ff`
process corner running the block dramatically faster than the reference
corner at temperature/supply extremes — the exact condition that should
also draw the most current.

Issue #35 extends `sim/iq/iq_sweep.py` with the same 7-process ×
3-temperature × 3-supply factorial `sim/pvt/pvt_sweep.py` uses —
`PROCESS_CORNERS`, `TEMPS_C`, `VDDS_V`, `corner_include()` are imported
from `sim/pvt/pvt_sweep.py` directly, not re-typed, so the two campaigns'
corner definitions cannot drift apart — at codes `0x00`, `0x80`, `0xC0`
(the post-#24/DR-0010 single-code post-trim calibration code, the code the
block would actually ship at), and `0xFF`, for the as-committed schematic
sizing only (see "Alternatives considered" for why `pre-22` is not part of
the grid).

Full evidence: `sim/iq/results/20260909T225306Z/{README.md,results.csv,
manifest.json}`, 252 raw ngspice logs under
`sim/iq/corners/20260909T225306Z/` (63 grid points × 4 codes, 0 failed
measurements, 2.7 minutes wall clock at 6 parallel jobs, gf180mcuC,
ngspice-46).

## Decision

No ratified spec-table row's disposition changes — per CLAUDE.md ("agents
do not relax the ratified spec to make results pass"), Row 4's `< 500 µA`
target is unchanged. This record's sole purpose is to state the
PVT-corner finding with numbers, as issue #35's acceptance criteria
require, and to place it in the same evidence lineage as DR-0007 through
DR-0009.

**Finding: Row 4 is met at the reference corner and at every corner
`tt`/`ss`/`fs`/`sf`/`rc_s` carries, but exceeds at the fast corners
(`ff`, `rc_f`) once temperature and supply move toward their hot/high-VDD
extreme, at every simulated trim code.** The worst-case grid point at
every code is `ff` / 85 °C / 3.6 V — the fastest process corner at its
hottest, highest-supply condition, exactly the direction a relaxation
oscillator's current is expected to move with frequency:

| code | reference corner (`tt`/27 °C/3.3 V) `iq_run` | worst-case corner (`ff`/85 °C/3.6 V) `iq_run` | Row 4 verdict, full grid |
|---|---|---|---|
| `0x00` | 345.34 µA — met | 531.18 µA — **exceeds** | **exceeds** (2 of 63 grid points) |
| `0x80` | 372.27 µA — met | 572.67 µA — **exceeds** | **exceeds** (5 of 63 grid points) |
| `0xC0` | 400.87 µA — met | 623.68 µA — **exceeds** | **exceeds** (8 of 63 grid points) |
| `0xFF` | 451.91 µA — met | 713.68 µA — **exceeds** | **exceeds** (21 of 63 grid points) |

At code `0xC0` — the code the block would actually ship at, per the
DR-0010 post-layout campaign's own single-code methodology — the 8
exceeding grid points are all at `VDD = 3.6 V`, split between the `ff`
process corner (all 3 temperatures: 570.33 / 604.42 / 623.68 µA at
−40/27/85 °C) and the `rc_f` process corner (525.60 / 553.21 / 562.77 µA
at −40/27/85 °C) — the two fastest process corners in the campaign
(`sim/pvt/results/20260907T090653Z/summary.md`'s "Untrimmed / free-running
spread" table), consistent with Iq tracking oscillation frequency. Every
`ss`/`fs`/`sf`/`rc_s`/`tt` grid point, and every `ff`/`rc_f` point at
3.0 V or 3.3 V, remains met at every code — the failure is confined to the
fastest corners' hottest, highest-supply condition, not spread uniformly
across the grid.

`iq_op` (continuity metric only, not Row 4's verdict basis per DR-0009)
shows non-monotonic variation across some grid points — e.g.
`tt`/−40 °C/3.3 V/`0x80` reads 216.54 µA against neighboring cells in the
600–900 µA range. This is consistent with, not contradictory to, DR-0007's
finding that the `.op` solve lands on an *unstable* DC equilibrium: which
of several possible crowbar-conduction states that solve converges to can
depend on corner-specific bias-point sensitivity. `iq_run` — the actual
verdict basis — has no such discontinuities: for every (process,
temperature, code) combination in this run's data, `iq_run` increases
monotonically as supply sweeps 3.0 → 3.3 → 3.6 V (verified directly
against `results.csv`, 0 of 84 such groupings out of order), exactly the
smooth, physically-expected behavior of an averaged running current.

## Alternatives considered

- **Running the `pre-22` (issue #16) sizing across the full corner grid
  as well, for a like-for-like before/after comparison.** Rejected: it
  would double this driver's simulation cost (504 vs. 252 ngspice
  invocations) for a comparison the corner campaign does not need — the
  `pre-22` sizing was already superseded at the reference corner in
  DR-0008 (`sim/iq/results/20260906T062311Z/README.md`), and Row 4 is now
  evaluated against the `as-committed` sizing going forward. `pre-22`
  remains available in `sim/iq/iq_sweep.py`'s history (issue #22's commit)
  but is not part of the corner-grid driver as extended by this issue.
- **Re-sizing `RBIAS`/the tail mirror now, to close the off-reference
  gap this record finds.** Rejected as out of scope for this issue, per
  issue #35's explicit "Out of scope" list — the follow-on is filed
  separately (see "Consequences") with this record's numbers in hand, the
  way issue #22/#24 followed issue #20's finding.
- **A `--subset endpoints` (tt/ff/ss × 3T × 3V, 27 points/code) run as the
  committed record, instead of the full 7-corner grid.** Rejected for the
  committed evidence — issue #35's acceptance criteria require the full
  grid. `--subset endpoints` remains available as a fast pre-commit check
  (used during this issue's own development, see `sim/iq/iq_sweep.py`
  `--help`) but every number in this record comes from the full-grid run.
- **Treating the worst-case-corner finding as grounds to change DR-0003
  Row 4's target itself.** Rejected — prohibited by `CLAUDE.md`, and not
  what this record does: the ratified `< 500 µA` figure, and its ST
  `DS9826`/`IDDA(HSI48)` anchor, are unchanged; this record states where
  the current design stands against that unchanged target, corner by
  corner.

## Consequences

- **DR-0003 Row 4 is no longer unconditionally "met."** It is met at the
  reference corner and across most of the grid, but **exceeds** at the
  fast-process/hot/high-supply corner at every simulated code — a real,
  previously unmeasured finding, not a regression introduced by this
  issue. `design/README.md`'s "No PVT factorial for Iq" Non-goals bullet
  is marked resolved, pointing at this record and the new run id;
  `docs/chipalooza/challenge-5-proposal.md`'s Iq row (added by issue #14)
  is re-qualified the same way the frequency-accuracy rows already are —
  reference-corner figure and full-grid worst case, both stated, neither
  substituting for the other.
- **A re-sizing follow-on is now well-defined, not speculative.** Unlike
  DR-0009's "Consequences" section, which could only say a corner sweep
  "remains a future increment," this record gives the exact corner
  (`ff`/85 °C/3.6 V), the exact margin needed at each candidate code, and
  the fact that the failure is confined to `ff`/`rc_f` at 3.6 V — enough
  to scope a `RBIAS`/tail-mirror re-derivation without further
  measurement. That re-derivation is filed as a separate follow-on issue,
  per issue #35's explicit "Out of scope" list (re-sizing is not done
  here).
- **`sim/pvt/pvt_sweep.py`'s own frequency campaign is unaffected.** This
  issue only imports its corner-definition constants and helper function;
  no line of `pvt_sweep.py` changed, and its own CLI/output are unchanged
  (verified: `git diff` against this record's branch touches no file under
  `sim/pvt/`).
- **The corner grid is schematic-level only, same scope boundary as every
  prior PVT campaign.** Post-layout (PEX-extracted) Iq, a post-layout Iq
  PVT factorial, and Monte Carlo/mismatch evidence for Iq are all still
  absent — explicitly out of scope for this issue, tracked as open gaps
  the same way DR-0010's post-layout frequency finding is.
- **`iq_op`'s corner-to-corner non-monotonicity is now visible in
  committed evidence, not just asserted in prose.** This does not change
  Row 4's basis (still `iq_run`, per DR-0009) — it is recorded here as an
  observation, not a new finding requiring action, since DR-0007 already
  explained why the `.op` figure is an unstable-equilibrium artifact
  rather than a physical running-current measurement.
