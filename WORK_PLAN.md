# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5
- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) and comparator-H hot/low-V delay collapse (ff)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#451**: gitignore gap: daemon-owned .loom/account-ranking.* false-positives check-main-clean
- **#453**: Read trim-bank LVS resistor terminals from the parsed netlist

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#449**: sim: matched-die calibrated-code Iq for w3r65/w2.5r75 - 0 of 1500 dice at 0xFF, penalties collapse at calibrated codes, row-8 code applicability returns to the operator (DR-0048)
- **#454**: fix: derive trim-bank LVS resistor terminals from parsed netlist nodes
- **#455**: gitignore: ignore .loom/account-ranking.* token-pool ranking files

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)*
- **#204**: Move layout geometry pin klt 0.4.0 → 0.8.0 and regenerate committed cells/reports *(curated)*
- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption *(curated)*
- **#451**: gitignore gap: daemon-owned .loom/account-ranking.* false-positives check-main-clean *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 0 |
| Curated | 4 |
| Architect / Hermit proposals | 0 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
