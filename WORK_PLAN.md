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

- **#66**: design: re-centre the oscillator for extracted parasitics and size a trim range that covers them (T1 item 5; operator ruling 2026-10-08)
- **#155**: Consolidate remaining importlib loaders in sim analyzers and tests onto _module_loader

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#66**: design: re-centre the oscillator for extracted parasitics and size a trim range that covers them (T1 item 5; operator ruling 2026-10-08) *(curated)*
- **#91**: Characterize clk output pulse width and period jitter (unspecified quantities the discipline model assumes) *(curated)*

## Proposed (Architect / Hermit)

- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b) *(architect)*
- **#131**: Decision record: enable/standby interface for rcosc_top and the start event behind the Startup and Iq rows *(architect)*
- **#153**: CI: preserve started main signoff checks while superseding PR runs *(architect)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Tier | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Operator priority | 0 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 2 |
| Architect / Hermit proposals | 3 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
