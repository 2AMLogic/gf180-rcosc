# spec — ratified spec + decision records

The ratified target spec table lives in the top-level
[`README.md`](../README.md#target-specification-ratified-2026-08-20-see-issues-1-and-3).
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
| [0002](decision-records/0002-target-spec-ratification.md) | Target spec ratification — frequency, trim, and PVT accuracy budget | Ratified (process spread, trim range/resolution, post-trim accuracy, and Iq rows superseded by 0003) |
| [0003](decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md) | PDK-sourced process spread, temperature drift, and Iq — superseding four rows of 0002 | Ratified |

A record is never deleted or rewritten once ratified — a later change
supersedes it with a new record rather than editing history in place (same
append-only convention as `sim/`, see [`sim/README.md`](../sim/README.md)).
A record that supersedes only *part* of an earlier one leaves that record's
own Status field alone (0002 is still "Ratified" in its own file) and is
annotated here in the index instead — `TEMPLATE.md`'s Status field models
supersession as all-or-nothing, and rewriting it would violate the
append-only rule above.
