# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#183**: ci: fold five offline-suite workflows into offline-suites matrix

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#66**: design: re-centre the oscillator for extracted parasitics and size a trim range that covers them (T1 item 5; operator ruling 2026-10-08)
- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#182**: Consolidate five remaining offline-suite workflows into offline-suites.yml matrix
- **#186**: T1 item 6: wire the DR-0022 mismatch injector into the MC bench, prove a klt yield envelope end to end, and declare the statistical row set

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#183**: ci: fold five offline-suite workflows into offline-suites matrix
- **#189**: docs(signoff): record item-6 Monte Carlo groundwork status and open gaps

## Proposed

Issues carrying `loom:curated`.

- **#66**: design: re-centre the oscillator for extracted parasitics and size a trim range that covers them (T1 item 5; operator ruling 2026-10-08) *(curated)*
- **#91**: Characterize clk output pulse width and period jitter (unspecified quantities the discipline model assumes) *(curated)*

## Proposed (Architect / Hermit)

- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b) *(architect)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 0 |
| Important | 2 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 2 |
| Curated | 2 |
| Architect / Hermit proposals | 1 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
