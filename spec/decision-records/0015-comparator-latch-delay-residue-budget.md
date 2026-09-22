# 0015: Comparator/latch delay residue measured and budgeted — superseding DR-0003's post-trim accuracy rows

- **Status**: Ratified — supersedes Row 3 (post-trim PVT accuracy, both
  sub-rows a and b) of
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md). DR-0003's Rows 1, 2,
  and 4 stand unchanged, as does every other row of 0002/0003.
  [0004](0004-no-active-tc-compensation-runtime-discipline.md) is untouched:
  no compensation is added here — this record **budgets** the delay term, it
  does not compensate it. The schematic, netlist, and layout are unchanged
  by this record (lever (b) of issue #51; see "Alternatives considered" for
  why lever (a) — the circuit change — was evaluated and rejected on
  quantified grounds).
- **Date**: 2026-09-22
- **Decided by**: Builder agent, issue #51

## Context

After DR-0012 removed the current-reference share and DR-0014 removed the
trim-bank phantom share, the two post-trim accuracy rows remained **not met**
(−7.14% / +4.62% at the calibration point and −14.53% / +7.00% over the full
temperature range, surrogate-calibrated codes, campaign
`sim/pvt/results/20260921T173529Z/`) and DR-0014 re-attributed the remainder
to the comparator/latch propagation delay — a term DR-0003's post-trim
derivation never carried. DR-0003's at-calibration budget table quantized
four lines (quantization, mismatch, offset, supply drift), of which the
supply line assumed "a reasonably supply-independent bias per 0001" at
±0.300%; nothing in the arithmetic represented propagation delay at all.
DR-0003's own Consequences pre-authorized exactly this record: its at-cal
±1.1% was flagged against ST's shipped `ACC_HSI48` = −2.8%/+2.9% with
"Schematic-phase work must either justify beating ST's 25 °C figure or
trigger a further superseding record."

Issue #51 offered two levers: (a) a comparator/latch architecture change, or
(b) a re-derivation of the budget arithmetic to explicitly carry the delay
term, backed by fresh measurement. This record selects **(b)**, on the
evidence below.

## Measured evidence

**New instrumentation**: `sim/pvt/delay_probe.py` (run
`sim/pvt/results/20260922T004823Z/`, 138 points, 0 failed) decomposes
steady-state cycles at both per-corner calibrated-code sets (surrogate and
ratified, read from the 20260921T173529Z manifest) across the full
7-process × 3-temperature × 3-supply factorial, plus DR-0014's switchprobe
code pairing (`0x80`/`0x9D`/`0xCF`/`0xEF`) at `ss`/27 °C. Methodology: the
transient (`tran 100p`) is dumped with `wrdata` and crossings are extracted
by interpolation with cycle alignment by timestamp proximity — edge-*index*
matching across nodes is unusable (startup glitch counts desynchronize node
indices by whole cycles; observed and documented in the driver). The
standard campaign was also re-run at the same netlist
(`sim/pvt/results/20260922T010039Z/`, same schematic at git `bd57830` —
schematics/netlist unchanged since the `bfeb95d` sizing the original
campaign froze) as a same-schematic reproduction; the probe's
period-derived frequencies agree
with the campaign's 20-period-average figures at shared cells to within
0.1%.

Findings, each a measured table row in the probe's `summary.md`:

- **F1 — the delay is paid once per crossing, not ≈3×.** The decomposition
  `period = charge + (t_cmp_h + t_lat_h) + t_fall + (t_cmp_l + t_lat_l)`
  closes to better than 20 ps at every one of the 138 probed cells. DR-0012's
  "period pays ~3 × t_delay" prose overstated the mechanism: the `vh`
  overshoot (measured 100–205 mV, ≈ charge slope × high-side latency) costs
  no period, because `MDISCH` resets `vc` to ≈0 V every cycle — the
  overshoot is a *symptom* of the high-side latency, not a period term of
  its own.
- **F2 — the delay sum is large.** `dsum = t_cmp_h + t_lat_h + t_cmp_l +
  t_lat_l` runs 3.4–7.4 ns at the per-corner calibrated codes (15–28% of the
  period at 27 °C/3.3 V), reaching 8.4 ns (34% of the period) at the worst
  probed cell (`ss`/−40 °C/3.0 V, code `0xCF`).
- **F3 — the delay term dominates the supply span.** Across the 3.0→3.6 V
  span at 27 °C, per-corner calibrated codes, `dsum` carries **62–82%** of
  the period span (surrogate codes: tt 73%, ff 68%, ss 75%, fs 62%, sf 82%,
  rc_f 75%, rc_s 69%). The remaining **16–36%** is a charge-path supply term
  (the transmission-gate shunts' `R_on(VDD)` and/or the divider's loaded
  threshold ratio) — itself previously unbudgeted, first separated here.
- **F4 — the low-side comparator is the dominant single stage.** At
  `ss`/27 °C, `t_cmp_l` = 3.81 ns at 3.0 V vs 1.90 ns at 3.6 V — a 1.92 ns
  span, 87% of that corner's `Δdsum` (2.21 ns) — while the high-side
  comparator is nearly supply-flat (2.55 → 2.45 ns) and the two latch paths
  together contribute ≈0.1–0.2 ns of span. Mechanism: `XCMPL` compares
  `vl` (= VDD/3) against `vc` ≈ 0 — its input pair sits at a near-ground
  common mode where overdrive is marginal, degrading worst exactly at
  slow-cold-low-supply (`t_cmp_l` = 5.0 ns at `ss`/−40 °C/3.0 V).
- **F5 — the delay's own ΔT is second-order.** Holding the charge term at
  its 27 °C value, `dsum`'s temperature move shifts frequency by only
  −1.23%…+0.38% on the cold leg and −0.03%…+2.10% on the hot leg across all
  seven corners. The PDK-worst TCR line (+1200 ppm/K equivalent) over-bounds
  the realized ΔT at every corner, so no separate delay-ΔT budget line is
  needed (checked per-corner, below).
- **F6 — the code-monotonicity is a fixed-Δdsum signature.** At `ss`/27 °C,
  `Δdsum` over the supply span is ≈2.2 ns nearly independently of code
  (`0x80` 2.22, `0x9D` 2.21, `0xCF` 2.20, `0xEF` 2.17 ns) while the period
  span grows (2.69 → 3.29 ns) as the code's in-chain trim mass falls —
  confirming DR-0014's re-attribution by mechanism: the delay's *absolute*
  supply dependence is fixed; its *share* grows as the RC term shrinks.

## Decision

**DR-0003's Row 3 is superseded. The post-trim accuracy rows are
re-derived to explicitly carry the measured comparator/latch delay residue
(and its charge-path minority share); the other three lines of the
at-calibration table are carried forward unchanged.**

Row 3(a) — at the calibration point (T = 27 °C, process, VDD ±10%):

| Contributor | DR-0003 basis | This record's basis |
|---|---|---|
| Trim quantization | ±0.157% | unchanged |
| Trim-DAC element mismatch / INL | ±0.300% (flagged assumption) | unchanged (still un-simulated by corner sims) |
| Comparator/reference offset residual | ±0.300% (flagged assumption) | unchanged (still un-simulated by corner sims) |
| Supply drift, VDD ±10% | ±0.300% — *assumed* "reasonably supply-independent bias per 0001" | **−8.4% / +5.8% — measured** worst cells of the post-trim supply span at per-corner calibrated codes (worst across both summary bases: per-corner own-calibration `ss`/`0xCF` −8.40%/+5.47%, and the campaign's nominal-reference table −8.13%/+5.79%, `20260921T173529Z`, reproduced by the same-schematic re-run `20260922T010039Z`; surrogate-calibration basis −7.14% / +4.62%), attributed by the probe as 62–82% comparator/latch delay and 16–36% charge path (F3) |

Linear worst-case sum (same convention as DR-0003):

```
down = -(0.157 + 0.300 + 0.300 + 8.40)% = -9.157%  -> ratified -9.2%
up   = +(0.157 + 0.300 + 0.300 + 5.79)% = +6.547%  -> ratified +6.5%
```

**Ratified: −9.2% / +6.5% at the calibration point** (supersedes ±1.1%).

Row 3(b) — over the full temperature range (−40…+85 °C, VDD ±10%,
single-point trim at 27 °C): DR-0003's TCR legs are retained unchanged on
their PDK basis (−1200 ppm/K resistor TCR + MIM TC over +58/−67 K:
+6.844% / −7.906%), summed linearly with the re-derived Row 3(a):

```
hot  = +6.844 + 6.547      = +12.391% -> ratified +13.4%
cold = -7.906 - 9.157      = -17.063% -> ratified -17.1%
```

**Ratified: +13.4% / −17.1% over the full temperature range** (supersedes
+8% / −9%).

**Bounding check (per-corner, linear stack vs every measured factorial
cell).** The stack `TCR-leg + |supply-span(corner)| + 0.757%` (supply span on the own-calibration basis) over-bounds
that corner's measured worst full-range cell at all seven corners — e.g.
`ss`: stack −17.1% vs measured −14.53% (surrogate) / −15.49% (ratified);
`sf`: −13.5% vs −11.47%; `tt`: −11.9% vs −8.22% — *including* the
cold-leg supply×ΔT interaction (measured `ss`/−40 °C/3.0 V is 2.6 points
worse than the product of its own 27 °C supply span and its 3.3 V ΔT; the
PDK-worst TCR line absorbs this without a separate interaction line). No
measured cell anywhere in either campaign falls outside the ratified
figures.

### Row verdicts, re-evaluated (issue #51 acceptance)

| Row | Basis | Measured | vs superseded (±1.1% / +8%−9%) | vs this record (−9.2/+6.5% / +13.4%−17.1%) |
|---|---|---|---|---|
| At calibration point | surrogate codes | −7.14% / +4.62% | **exceeds** (recorded, superseded basis) | **met** (2.1 / 1.9 pt margin) |
| At calibration point | ratified codes | −8.40% / +5.79% (own-cal / nominal-ref bases: −8.40/+5.47 and −8.13/+5.79) | **exceeds** | **met** (≥ 0.8 / ≥ 0.7 pt margin) |
| Full temperature range | surrogate codes | −14.53% / +7.00% | lower **exceeds** (upper was already within +8%) | **met** (2.6 / 6.4 pt) |
| Full temperature range | ratified codes | −15.49% / +7.78% | lower **exceeds** (upper was already within +8%) | **met** (1.6 / 5.6 pt) |

Both verdict columns are stated together, never one without the other: the
rows are closed against the re-derived (measured-basis) budget and remain
open against the superseded (assumed-basis) one — that is what a superseding
record *is*, and no result here is rounded up to "met".

## Alternatives considered

- **Lever (a): comparator/latch speed-up at unchanged tail current
  (re-sizing within the existing topology).** Rejected on two independent,
  quantified grounds:
  1. *Speed cannot close the row.* Even zeroing `dsum` entirely — physically
     impossible: the two comparator crossings and the latch set/reset are
     structural to the DR-0001 topology, and the latch alone is 0.8–1.3 ns
     per cycle — would leave the charge-path supply share (F3: e.g.
     `ss` ≈ −2.6%/+1.7%) plus the three carried lines ≈ −3.4%/+2.5%, still
     far outside ±1.1%.
  2. *Row 4's knife edge.* DR-0014's Iq factorial leaves probe code `0x80`
     with **1.24 µA (0.25%) of margin** at `ff`/85 °C/3.6 V (498.76 µA vs
     the ratified 500 µA). Any delay cut raises f at fixed code; a 1 ns
     `dsum` cut is a 4–6% f rise at the probe codes' 17–24 ns periods, and
     `iq_run`'s dynamic share then pushes that cell past 500 µA — flipping
     a finally-met Row 4 verdict class. Only cuts ≲0.3 ns survive Row 4,
     worth ≲1 point of supply span: no Iq-neutral sizing path to ±1.1%
     exists.
- **Raising comparator tail current.** Rejected: the bias budget is frozen
  by DR-0009/DR-0012 sizing and Row 4 already exceeds at the fast-hot
  high-code cells (DR-0014). No headroom.
- **A mechanism-level fix that flattens the delay's supply slope at constant
  nominal delay** — e.g. re-referencing the low-side comparison so its input
  pair does not sit at a near-ground common mode (F4), or a discharge-floor
  change. This is the *right* future circuit lever precisely because it
  need not raise f (no Row 4 collision), but it re-opens the
  comparator/bias architecture — and the discharge-floor variant re-opens
  the frozen trim-bank R map — each requiring its own sizing pass and full
  campaign. Out of scope for this one-mechanism issue; filed as follow-up
  issue #57 with F4's measurements as the starting point.
- **Silently relaxing, or re-rounding a measured figure to "met".**
  Rejected (CLAUDE.md: agents do not relax the ratified spec to make
  results pass — the relaxation rides *in* this superseding record, with
  its evidence, or not at all).
- **Leaving the rows "exceeds" and deferring everything to the reserved
  runtime-discipline stage.** Rejected as the disposition for this row: the
  post-trim rows are the *free-running* spec, they are the block's core
  deliverable, and the issue explicitly sanctioned the measured re-derivation.

## Consequences

- `README.md`'s target-spec table rows for post-trim accuracy now cite this
  record; `spec/README.md`'s index annotates DR-0003 as Row-3-superseded by
  this record (DR-0003's file is unchanged, per the append-only convention).
- **The at-calibration figure is now ~3× looser than ST's shipped
  `ACC_HSI48`** (−9.2/+6.5% vs −2.8%/+2.9% at 25 °C) — the exact inversion
  of the credibility flag DR-0003 raised against its own ±1.1%. The
  direction is the expected one for an older node with an unregulated
  asynchronous delay path and a ratiometric-low common-mode comparison, and
  the gap is measured, not asserted. Follow-up #56 is the path back.
- **The runtime-discipline gap widens materially**: from ±1.1% to USB's
  ±0.25% was a ~4.4× gap; from −9.2%/+6.5% it is ~26–37×. DR-0003's note
  that discipline is "the only path to compliance" is strengthened, not
  weakened, by this record.
- **DR-0012's ≈3× paid-in prose is corrected by measurement** (F1), and
  DR-0014's re-attribution of the slow-corner supply sensitivity to the
  delay residue is quantified at 62–82% with a newly-separated 16–36%
  charge-path share — both records stand otherwise; their narratives are
  annotated here rather than edited.
- No schematic, netlist, or layout change rides in this record: the
  committed `layout/` cells and post-layout PEX evidence remain current
  (issue #51's layout acceptance criterion is satisfied trivially — nothing
  went stale). The committed instrumentation (`sim/pvt/delay_probe.py`) and
  its append-only evidence are reusable as-is by follow-up #57's before/
  after comparison.
- If a later revision flattens `dDsum/dVDD` (follow-up #57) or the
  charge-path supply share, this row must be re-derived again by a further
  superseding record — with the same probe methodology, which is now
  committed tooling.
