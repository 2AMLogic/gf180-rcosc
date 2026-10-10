# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs stuck under a `loom:operator` merge-risk hold — implementation work is done, only a human merge decision is missing.

_None._

## Operator Priority

Issues the operator starred (`loom:operator-priority`); land these first.

_None._

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#107**: CI guard: offline consistency check between pvt_tb.spice, rcosc_top.spice and the per-bench DUT netlist copies
- **#115**: Validate the layout builder Python runtime against the geometry toolchain pins

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#116**: CI guard: offline netlist consistency check (#107)

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#91**: Characterize clk output pulse width and period jitter (unspecified quantities the discipline model assumes) *(curated)*
- **#107**: CI guard: offline consistency check between pvt_tb.spice, rcosc_top.spice and the per-bench DUT netlist copies *(curated)*

## Proposed (Architect / Hermit)

- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b) *(architect)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Tier | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Operator priority | 0 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 0 |
| Curated | 2 |
| Architect / Hermit proposals | 1 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
