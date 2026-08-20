# spec — ratified spec + decision records

The ratified target spec table lives in the top-level
[`README.md`](../README.md#target-specification-ratified-2026-08-20-see-issue-1).
This directory holds the **decision records** that justify each ratified
value and any future change to it: per CLAUDE.md, spec changes go through a
decision record here — agents do not relax the ratified spec to make
results pass.

```
spec/
  README.md               this file
  decision-records/
    TEMPLATE.md            copy this to start a new record
    NNNN-<slug>.md          one decision per record, numbered sequentially
```

## Decision records

One page per decision: the context that forced it, the decision itself
(stated as a concrete spec change), alternatives considered, and
consequences. See [`decision-records/TEMPLATE.md`](decision-records/TEMPLATE.md)
for the format and the numbering rule (next unused `NNNN`, checked against
every filename in this directory on `main`, including superseded records).

| Record | Title | Status |
|---|---|---|
| [0001](decision-records/0001-relaxation-oscillator-topology.md) | Relaxation-oscillator topology for the trimmable RC core | Ratified |
| [0002](decision-records/0002-target-spec-ratification.md) | Target spec ratification — frequency, trim, and PVT accuracy budget | Ratified |

A record is never deleted or rewritten once ratified — a later change
supersedes it with a new record rather than editing history in place (same
append-only convention as `sim/`, see [`sim/README.md`](../sim/README.md)).
