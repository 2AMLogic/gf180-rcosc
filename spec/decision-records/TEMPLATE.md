# 0000: <short title>

<!--
Copy this file to spec/decision-records/NNNN-<slug>.md and fill it in.
Use the next unused NNNN (zero-padded 4 digits). One decision per record;
keep it to one page. A decision record is required for every spec change
(see CLAUDE.md). Do not delete or rewrite a ratified record — supersede it
with a new one.

Numbering rule: before picking NNNN, check every filename already in this
directory on `main` (including superseded records) and use one greater than
the highest number found — never guess or reuse a number, and re-check if
another record may have landed concurrently, to avoid a collision.

Index rule: after copying this template to NNNN-<slug>.md, add the record's
row to the `## Decision records` table in `spec/README.md`, in numeric order:
`| [NNNN](decision-records/NNNN-<slug>.md) | <title> | <status> |`.
`.github/workflows/doc-citations.yml` runs
`signoff/verify-decision-record-index.py` on every PR and fails CI if that
row is missing, duplicated, misdirected, or out of order.
-->

- **Status**: proposed | ratified | superseded by NNNN
- **Date**: YYYY-MM-DD
- **Decided by**: <name / role>

## Context

What forced this decision? One short paragraph: the constraint, the
measurement, or the conflict that made the current spec inadequate. Link to
the issue, the simulation evidence in `sim/`, or the prior record it revises.

## Decision

The decision, stated as a change to the spec — the parameter and its new
value, or the approach now ratified. Be specific enough that design work can
lock to it without further interpretation.

## Alternatives considered

- **<alternative>** — why it was not chosen.
- **<alternative>** — why it was not chosen.

## Consequences

What follows from this: what becomes possible, what becomes harder, which
testbenches or corner sets change, what work is invalidated or must be
re-run. Include the bad consequences, not just the good ones.
