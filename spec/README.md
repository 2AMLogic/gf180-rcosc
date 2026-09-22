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
| [0003](decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md) | PDK-sourced process spread, temperature drift, and Iq — superseding four rows of 0002 | Ratified (Row 3 — post-trim PVT accuracy — superseded by 0016; Rows 1, 2, 4 stand) |
| [0004](decision-records/0004-no-active-tc-compensation-runtime-discipline.md) | No active temperature-coefficient compensation — rely on runtime discipline | Ratified |
| [0005](decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md) | PVT campaign confirms a frequency/accuracy shortfall in the current schematic — ratified spec unchanged | Ratified (records evidence; supersedes nothing) |
| [0006](decision-records/0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md) | Post-#16-resize PVT campaign — trim range and post-trim accuracy still unmet, ratified spec unchanged | Ratified (records evidence; realized trim-curve figures superseded by 0008) |
| [0007](decision-records/0007-quiescent-current-exceeds-target-post-resize.md) | Post-#16 quiescent current exceeds DR-0003 Row 4's target — ratified spec unchanged | Ratified (records evidence; Row 4 verdict superseded by 0008) |
| [0008](decision-records/0008-iq-metric-correction-and-bias-rebalance.md) | Bias re-balance brings Iq under DR-0003 Row 4 — and the `.op` figure 0007 used is not the quantity Row 4 names | Ratified (supersedes 0007's Row 4 verdict and 0006's trim-curve figures; supersedes no ratified target; `RBIAS` sizing and trim-curve figures superseded by 0009, metric finding not) |
| [0009](decision-records/0009-running-iq-metric-basis-and-partial-trim-range-recovery.md) | Row 4's verdict basis moves to the running Iq metric — `RBIAS` re-derived, partial trim-range recovery | Ratified (supersedes 0008's `RBIAS` sizing and trim-curve figures, not its metric finding; supersedes no ratified target) |
| [0010](decision-records/0010-postlayout-pex-pvt-frequency-shift.md) | Post-layout (PEX-extracted) PVT re-verification — layout parasitics shift frequency further below the schematic-level model, ratified spec unchanged | Ratified (records evidence; supersedes nothing; post-layout figures for the post-#39 schematic superseded by 0013 — 0010 remains valid for the pre-#39 GDS pair) |
| [0011](decision-records/0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md) | Quiescent-current PVT-corner factorial — DR-0003 Row 4 met at the reference corner, exceeds off-reference (fast process corner, hot, high supply); ratified spec unchanged | Ratified (records evidence; supersedes nothing) |
| [0012](decision-records/0012-comparator-bias-path-pvt-revision.md) | Comparator/bias-path PVT revision — self-biased current reference, post-trim residuals re-measured, ratified rows unchanged | Ratified (records evidence; supersedes no ratified row; its "layout consequence" paragraph retired by 0013) |
| [0013](decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md) | Bias-cell layout re-spin against the post-#39 schematic + post-layout (PEX) PVT re-verification — parasitic shift deepens (−11.24 % … −41.42 %), ratified rows unchanged | Ratified (records evidence; supersedes 0010's post-layout figures for the post-#39 schematic) |
| [0014](decision-records/0014-trim-bank-pass-switch-restructure.md) | Trim-bank pass-switch restructure — per-position transmission-gate shunts with locally inverted pfet gates, trim range restored (±51.36 %, first `met` since DR-0005), residual supply sensitivity re-attributed | Ratified (records evidence; supersedes no ratified row; its "layout consequence" paragraph retired by 0015) |
| [0015](decision-records/0015-trim-bank-respin-postlayout-pex-reverification.md) | Trim-bank layout re-spin against the post-#43 schematic + post-layout (PEX) PVT re-verification — parasitic shift deepens on the mean (−17.46 % … −40.92 %, mean −27.32 %), ratified rows unchanged | Ratified (records evidence; supersedes 0010's and 0013's post-layout figures for the post-#43 schematic — 0013 remains valid for the post-#39, pre-#43 GDS pair) |
| [0016](decision-records/0016-comparator-latch-delay-residue-budget.md) | Comparator/latch delay residue measured and budgeted — the delay term (62–82% of the post-trim supply span) enters the post-trim accuracy arithmetic; schematic unchanged | Ratified (supersedes 0003 Row 3: at-calibration −9.2%/+6.5%, full-range +13.4%/−17.1%; circuit-side follow-up is #57) |

A record is never deleted or rewritten once ratified — a later change
supersedes it with a new record rather than editing history in place (same
append-only convention as `sim/`, see [`sim/README.md`](../sim/README.md)).
A record that supersedes only *part* of an earlier one leaves that record's
own Status field alone (0002 is still "Ratified" in its own file) and is
annotated here in the index instead — `TEMPLATE.md`'s Status field models
supersession as all-or-nothing, and rewriting it would violate the
append-only rule above.
