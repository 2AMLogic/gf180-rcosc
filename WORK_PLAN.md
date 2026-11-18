# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#337**: Row 4 ss span: adopt and verify the DR-0037 w3r65 bank candidate (needs operator ruling on one re-centred change) *(held)*

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout *(held)*
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(held)*
- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) and comparator-H hot/low-V delay collapse (ff) *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#434**: verify_workflow_concurrency()'s completeness check globs only *.yml; a .yaml workflow evades it

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#436**: signoff: completeness check covers *.yml and *.yaml workflows

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)* *(held)*
- **#204**: Move layout geometry pin klt 0.4.0 → 0.8.0 and regenerate committed cells/reports *(curated)* *(held)*
- **#337**: Row 4 ss span: adopt and verify the DR-0037 w3r65 bank candidate (needs operator ruling on one re-centred change) *(curated)* *(held)*
- **#434**: verify_workflow_concurrency()'s completeness check globs only *.yml; a .yaml workflow evades it *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(held)*

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 0 |
| Curated | 4 |
| Architect / Hermit proposals | 0 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
