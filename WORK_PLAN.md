# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#473**: sim(row2-trimsize): row-2 trim-bank sizing screen is negative at every corner; DR-0048 names the thermometer upper bank as next option

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5
- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) and comparator-H hot/low-V delay collapse (ff)
- **#460**: Row 2: name a trim-bank sizing that meets 0.314 %/code with monotonic carries (simulation only, bounded screen)
- **#461**: T1 item 6: define and prove a known-bad negative control per statistical row set (rows 2, 4, 5 x tt/ff/ss); the 3x-inflated control is detected in 2 of 12 cells

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout

## In Progress

Issues currently being built (`loom:building`).

- **#452**: Plan-region guard: anchor the tag suffix match to end-of-line so an issue title cannot false-positive
- **#460**: Row 2: name a trim-bank sizing that meets 0.314 %/code with monotonic carries (simulation only, bounded screen)
- **#461**: T1 item 6: define and prove a known-bad negative control per statistical row set (rows 2, 4, 5 x tt/ff/ss); the 3x-inflated control is detected in 2 of 12 cells

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#449**: sim: matched-die calibrated-code Iq for w3r65/w2.5r75 - 0 of 1500 dice at 0xFF, penalties collapse at calibrated codes, row-8 code applicability returns to the operator (DR-0048)
- **#466**: signoff: anchor plan-region suffix check to the end-of-line run

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#473**: sim(row2-trimsize): row-2 trim-bank sizing screen is negative at every corner; DR-0048 names the thermometer upper bank as next option

## Proposed

Issues carrying `loom:curated`.

- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)*
- **#204**: Move layout geometry pin klt 0.4.0 → 0.8.0 and regenerate committed cells/reports *(curated)*
- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption *(curated)*
- **#452**: Plan-region guard: anchor the tag suffix match to end-of-line so an issue title cannot false-positive *(curated)*
- **#460**: Row 2: name a trim-bank sizing that meets 0.314 %/code with monotonic carries (simulation only, bounded screen) *(curated)*
- **#461**: T1 item 6: define and prove a known-bad negative control per statistical row set (rows 2, 4, 5 x tt/ff/ss); the 3x-inflated control is detected in 2 of 12 cells *(curated)*

## Proposed (Architect / Hermit)

- **#487**: Call the row-4 generator directly and share its trim-bank sizing rule *(hermit)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 2 |
| Approved PRs awaiting merge | 1 |
| Curated | 6 |
| Architect / Hermit proposals | 1 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
