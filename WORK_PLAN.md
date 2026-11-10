# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#225**: feat(sim): simulated 63-point startup factorial (61/63 pass, pre-re-centre design) and DR-0020 ratified
- **#237**: sim(mc): item-6 Monte Carlo campaign on the P3 netlist, graded with klt yield (rows 4 and 5 fail, controls incomplete)

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#82**: Run startup-time PVT factorial on batch fleet and close row 10 (follow-up to #78/PR #80)
- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b)
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#225**: feat(sim): simulated 63-point startup factorial (61/63 pass, pre-re-centre design) and DR-0020 ratified
- **#237**: sim(mc): item-6 Monte Carlo campaign on the P3 netlist, graded with klt yield (rows 4 and 5 fail, controls incomplete)

## Proposed

Issues carrying `loom:curated`.

- **#82**: Run startup-time PVT factorial on batch fleet and close row 10 (follow-up to #78/PR #80) *(curated)*
- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b) *(curated)*
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)*
- **#204**: Move layout geometry pin klt 0.4.0 → 0.8.0 and regenerate committed cells/reports *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 2 |
| Very important | 0 |
| Important | 1 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 2 |
| Curated | 4 |
| Architect / Hermit proposals | 0 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
