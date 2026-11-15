# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#337**: Row 4 ss span: adopt and verify the DR-0037 w3r65 bank candidate (needs operator ruling on one re-centred change)

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout
- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b)
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5
- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) and comparator-H hot/low-V delay collapse (ff)
- **#347**: Row 8: attribute running Iq over 500 uA at the ff corners by stage and name a candidate lever

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#310**: Remove guard-confinement investigation docs: closed, unreferenced, upstream tooling
- **#353**: Split pex_pvt_sweep.py's 585-line main() into the report/record helpers its sibling campaign drivers already have
- **#360**: Collapse the duplicated comparator cell builder in layout/build_cells.py: 39 of 53 body lines identical, differences are pure parameter substitution
- **#361**: Collapse the triplicated local ngspice invocation in the PVT sweep drivers

## In Progress

Issues currently being built (`loom:building`).

- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b)
- **#347**: Row 8: attribute running Iq over 500 uA at the ff corners by stage and name a candidate lever
- **#349**: README status block and maturity-ladder paragraph are stale: #66 is closed and items 5 and 6 have campaigns
- **#359**: Consolidate four duplicated run-writer idioms in sim/ onto evidence_common (#260)
- **#363**: Stop restating the klt pin values in prose: six doc statements still name superseded pins as current

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#366**: refactor(sim): consolidate run-writer idioms (results.csv block, dash closure, prologue, json header) onto evidence_common
- **#374**: sim(trim-dense): run slice 43, 128 sch_ss curve jobs on batch fleet (1152/1536)
- **#376**: docs: refresh README status block and ladder to the graded and post-grade record

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#87**: Dense 256-code freq-vs-code sweep and trim-bank monotonicity verdict (DR-0021 follow-ups a, b) *(curated)*
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)*
- **#204**: Move layout geometry pin klt 0.4.0 → 0.8.0 and regenerate committed cells/reports *(curated)*
- **#337**: Row 4 ss span: adopt and verify the DR-0037 w3r65 bank candidate (needs operator ruling on one re-centred change) *(curated)*
- **#347**: Row 8: attribute running Iq over 500 uA at the ff corners by stage and name a candidate lever *(curated)*
- **#349**: README status block and maturity-ladder paragraph are stale: #66 is closed and items 5 and 6 have campaigns *(curated)*
- **#358**: signoff.yml comment names klt 0.7.0 as the pinned grader; the install step pins 0.8.0 *(curated)*
- **#365**: Collapse four superseded per-campaign PVT sections in design/README.md: a third copy of sim/README.md's run table and the DRs *(curated)*

## Proposed (Architect / Hermit)

- **#365**: Collapse four superseded per-campaign PVT sections in design/README.md: a third copy of sim/README.md's run table and the DRs *(hermit)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`) | 4 |
| In Progress (`loom:building`) | 5 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 0 |
| Curated | 8 |
| Architect / Hermit proposals | 1 |
| Active epics | 1 |
<!-- guide:plan-body:end -->
