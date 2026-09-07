# 0009: Row 4's verdict basis moves to the running Iq metric — partial trim-range recovery

- **Status**: Ratified — records simulation evidence, a metric-basis change,
  and a sizing change. **Supersedes [0008](0008-iq-metric-correction-and-bias-rebalance.md)'s
  sizing** (`RBIAS L = 1000 µm`) and its trim-range figures, but **not**
  DR-0008's Finding 1 (the `.op` figure is not the quantity DR-0003 Row 4
  names) — this record acts on that finding rather than revising it. It
  supersedes **no ratified target**: `README.md`'s target-spec table,
  including Row 4's `< 500 µA`, stands unchanged, as do
  [0001](0001-relaxation-oscillator-topology.md)–[0006](0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md).
- **Date**: 2026-09-07
- **Decided by**: Builder agent, issue #24

## Context

DR-0008 (issue #22) re-balanced `RBIAS` and the comparator tail-mirror
ratio to bring quiescent current under DR-0003 Row 4's ratified `< 500 µA`
target, and in doing so established that Row 4 names the **running**
current (`iq_run`: `-i(vdd)` averaged over 20 whole oscillation periods,
startup skipped) — anchored to ST `DS9826`'s `IDDA(HSI48)`, a datasheet
figure for an oscillator that is *oscillating* — not the `.op` figure
(`iq_op`) issue #20 introduced, which is a DC-equilibrium artifact: a
relaxation oscillator has no stable operating point, so that solve parks
the charge-complete comparator at its own output inverter's trip point in
full crowbar conduction, a state the running circuit passes through but
never rests in.

Despite identifying this, DR-0008 sized against `iq_op` anyway — the
**stricter** of the two readings — because issue #22's acceptance criteria
were written against `iq_op`, and DR-0008 judged that changing the metric
basis inside the same record that first identified the discrepancy would
be indistinguishable from relaxing a spec row to make results pass. That
choice cost trim range: realized reference-corner trim range dropped from
DR-0006's ±38.16% to DR-0008's ±32.42%, widening the gap to the ratified
±40% row (already "not met" before and after). At the DR-0008 sizing, the
running metric has large headroom: 221.59 µA of the 500 µA target at the
worst simulated code (`0xFF`) — see
`sim/iq/results/20260906T062311Z/README.md`. DR-0008 explicitly deferred
re-deriving the sizing against `iq_run` to this issue (#24), naming it as
its own likely outcome ("negligible recovery" included as an equally valid
finding).

## Decision

**1. DR-0003 Row 4's verdict is now stated against `iq_run`, not `iq_op`.**
This is the metric-basis change DR-0008 declined to make under issue #22's
narrower scope. `iq_op` is still always measured and reported alongside
`iq_run` (`sim/iq/iq_sweep.py`, `design/smoke_test.sch` — unchanged
instrumentation) — neither may be quoted without the other — but `iq_op`
is no longer a second acceptance gate; it is reported for continuity with
DR-0007's original methodology only. The two metrics are no longer
expected to agree on verdict at every sizing, and as this record's own
data shows, they now do not.

**2. `RBIAS` is re-derived again, on the same single knob, against the
new verdict basis:**

| device | DR-0008 (post-#22) | **ratified here (post-#24)** | effect |
|---|---|---|---|
| `rcosc_bias.sch` `RBIAS` | `W = 2 µm`, `L = 1000 µm` | `W = 2 µm`, **`L = 210 µm`** | reference current ↑ |
| `rcosc_comparator.sch` `MTAIL` | `W = 16 µm`, `nf = 8` (8:1) | **unchanged** | — |

The mirror ratio `M` was **not** re-opened as a free knob. DR-0008 already
found `M ≈ 8` at the saturation knee for the `.op` metric (`M = 16`/`32`
land within 0.2% of `M = 8` at equal Iq). This issue re-checked that
finding against `iq_run` specifically: a 1-D grid over `RBIAS L` was run
at `M = 4:1`, `M = 8:1`, and `M = 16:1` (each swept to its own
`iq_run(0xFF) = 500 µA` boundary), using the *same* op-then-tran deck
methodology `sim/iq/iq_sweep.py` uses (not a bare transient — see
"Alternatives considered" for why that distinction matters). At matched
~5–7% margin to the 500 µA boundary, the three ratios recover comparable
trim range (`M = 8`: ±35.50%; `M = 16` and `M = 4` each land within about
a percentage point of that figure at their own matched-Iq boundary `L`).
`M = 8:1` is kept: it requires no `rcosc_comparator.sch` change at all,
and the alternative ratios buy no measurable trim-range advantage over it
at this current budget.

**3. Sizing point and margin.** A 1-D grid over `RBIAS L` at fixed `M = 8:1`
(`210u` sizing point through `25u`) locates the `iq_run(0xFF) = 500 µA`
boundary between `L = 185 µm` (502.61 µA, exceeds) and `L = 190 µm`
(495.58 µA, met, < 1% margin — too thin to be a safe operating point).
`L = 210 µm` is chosen, giving a DR-0008-comparable ~6.3% margin
(468.61 µA at the worst simulated code, `0xFF`) — see
`sim/iq/results/20260907T090639Z/README.md`.

## Evidence

Reference corner (`tt` / 27 °C / 3.3 V), `sim/iq/results/20260907T090639Z/`:

| sizing | code | `iq_op` (µA) | verdict | `iq_run` (µA) | verdict (Row 4 basis) | f (MHz) |
|---|---|---|---|---|---|---|
| `as-committed` (post-#24) | `0x00` | 754.82 | exceeds | 359.74 | met | 28.0769 |
| `as-committed` (post-#24) | `0x80` | 754.90 | exceeds | 387.09 | met | 39.1203 |
| `as-committed` (post-#24) | `0xFF` | 754.90 | exceeds | 468.61 | met | 58.9870 |
| `pre-22` (issue #16) | `0x00` | 914.40 | exceeds | 470.39 | met | 29.5123 |
| `pre-22` (issue #16) | `0x80` | 914.99 | exceeds | 502.23 | exceeds | 42.0390 |
| `pre-22` (issue #16) | `0xFF` | 914.99 | exceeds | 605.57 | exceeds | 65.9332 |

**Row 4 is met at every simulated code on its actual verdict basis
(`iq_run`)**, at a sizing that draws visibly more current on the `.op`
figure than DR-0008's (754.90 vs. 467.18 µA at code `0x80`) — this is
expected and intentional, not a regression: `iq_op` is not, and was never,
the quantity being targeted here.

Full PVT campaign at this sizing, `sim/pvt/results/20260907T090653Z/`
(277 unique points, 206 recorded rows, 0 failures, 4.0 minutes wall
clock at 8 jobs), against DR-0006 (post-#16) and DR-0008 (post-#22):

| Spec row | Ratified | DR-0006 (post-#16) | DR-0008 (post-#22) | **here (post-#24)** |
|---|---|---|---|---|
| Quiescent current | `< 500 µA` (running) | 914.99 µA `.op` (only metric then measured) | 467.18 µA `.op` / 157.27 µA running — met both | 754.90 µA `.op` (not verdict basis) / **468.61 µA running — met** |
| Output frequency | 48.000 MHz | max 65.9204 MHz | max 51.9415 MHz | max **58.9870 MHz** — met |
| Trim range | ±40% (28.8–67.2 MHz) | ±38.16% | ±32.42% | **±35.50%** (28.0769–58.9870 MHz) — not met, margin narrower than DR-0008's |
| Trim step | 0.314 %/code | 0.4839 %/code | 0.3763 %/code | **0.4317 %/code** — met |
| Untrimmed process spread | ±35% | −25.60% / +38.71% | −25.46% / +38.54% | **−26.34% / +42.68%** — within |
| Post-trim, calibration point (per-corner code) | ±1.1% | −11.38% / +10.56% | −10.18% / +10.30% | **−11.50% / +13.19%** — exceeds |
| Post-trim, full temperature (per-corner code) | +8% / −9% | −18.00% / +12.91% | −17.38% / +13.46% | **−19.41% / +27.85%** — exceeds, worse than both priors |

Per-corner-code figures use each process corner's own calibration code
(binary search against the design's own realized frequency at
`tt/27 °C/3.3 V/0x80`, the surrogate target — the ratified 48.000 MHz
target is unreachable at every corner, per DR-0005/0006); see
`sim/pvt/results/20260907T090653Z/summary.md` for the ratified-target
(global-code) figures too.

**Trim range: recovered ~54% of DR-0008's loss.** `(35.50 − 32.42) /
(38.16 − 32.42) = 53.7%`. The gap to DR-0006's pre-#22 figure narrows from
5.74 to 2.66 percentage points; the gap to the ratified ±40% narrows from
7.58 to 4.50 points. This is a **partial**, not full, recovery — the
answer this issue's acceptance criteria explicitly allowed ("even if the
answer is negligible"), and 54% is not negligible, but it is also not
complete: `iq_run`'s headroom at the DR-0008 point (44%) does not map
1:1 onto trim-range headroom, because trim range is set by comparator
propagation delay relative to the *fastest* trim code's period, and that
relationship saturates well before the Iq budget does (see "Alternatives
considered").

**A genuine regression, not buried**: the post-trim, full-temperature,
per-corner-code residual is **worse** here (+27.85%) than both DR-0006
(+12.91%) and DR-0008 (+13.46%). Root cause: at this sizing, the `fs`
process corner's own per-corner calibration search converges to code
`0x80` — coincidentally the same code the "untrimmed / free-running
spread" section already measures at every corner — because `fs`'s
frequency curve near mid-code already sits close to the surrogate target
at that corner's own 27 °C/3.3 V point. `fs` also carries the highest
measured temperature sensitivity of any corner at this sizing
(+1923 ppm/K, vs. 856–1373 ppm/K elsewhere — see
`sim/pvt/results/20260907T090653Z/summary.md` "Isolated sensitivities"),
so its post-trim temperature excursion is effectively its *untrimmed*
excursion, and that excursion is the campaign's new full-temperature
maximum. This is a property of where this sizing's frequency map places
the `fs` corner's calibration code, not a simulation artifact, and it was
already "exceeds" in every prior campaign — the verdict does not change,
but the margin does, and that is recorded here rather than omitted.

## Alternatives considered

- **A bare `tran`-only deck (no leading `.op`) for the grid search, to
  avoid the `.op` solve's cost.** Tried first, and rejected after direct
  comparison: at the same sizing and code, a `tran`-only deck measures
  `iq_run` ~4% lower than the official op-then-tran deck
  `sim/iq/iq_sweep.py` and `design/smoke_test.sch` both use (383.34 vs.
  398.27 µA at the DR-0008 sizing, code `0x80`) — the leading `.op` solve
  measurably shifts which point on the oscillator's periodic orbit the
  transient settles into before the skip-5/average-20 window starts. The
  final sizing boundary and margin in this record were re-verified with
  the official op-then-tran methodology; a bare-`tran` scratch grid was
  used only for the initial coarse search, not as evidence.
- **Also re-opening the mirror ratio `M`.** Simulated (`M = 4:1` and
  `M = 16:1`, each swept to its own `iq_run(0xFF) = 500 µA` boundary — see
  "Evidence"). **Rejected**: both land within about a percentage point of
  `M = 8:1`'s recovered trim range at matched margin, confirming DR-0008's
  saturation finding holds under the running metric too. `M = 8:1`
  requires no `rcosc_comparator.sch` edit, so it is preferred on economy of
  change alone once the alternatives buy nothing measurable.
- **A thinner margin (`L = 190–195 µm`, ~1–2% margin) for slightly more
  trim range (~35.8–36.0% vs. 210 µm's 35.50%).** **Rejected**: the gain is
  well under one percentage point of trim range for an order-of-magnitude
  thinner safety margin against a metric with no PVT-corner
  re-verification (see "Consequences" — Iq is still reference-corner-only).
  DR-0008's own accepted margin was ~6.6%; `L = 210 µm`'s ~6.3% margin is
  deliberately kept comparable rather than spent on a small further
  trim-range gain.
- **Relaxing Row 4 or the ±40% trim-range row to fit as-simulated
  figures.** **Rejected** — prohibited by `CLAUDE.md`, and not what this
  record does: Row 4's ratified `< 500 µA` figure is unchanged, and the
  trim-range row is unchanged and still "not met," as it has been in every
  campaign since DR-0005.
- **Treating the running-metric re-derivation as a spec relaxation because
  `iq_op` now exceeds 500 µA at the chosen point.** **Rejected**: DR-0008
  already established `iq_op` is not the quantity Row 4 names, independent
  of and prior to this record's sizing choice. Accepting an elevated
  `iq_op` at a sizing chosen against the metric Row 4 actually names is the
  correct implication of DR-0008's own finding, not a new judgment call
  made to pass.

## Consequences

- **DR-0003 Row 4 (Iq) remains met**, now on an unambiguous, correctly-named
  basis (`iq_run`) at every simulated code, with `iq_op` demoted to a
  continuity figure rather than a second gate.
- **Trim range improves but remains "not met"**: ±35.50% vs. the ratified
  ±40%, up from DR-0008's ±32.42% and still short of DR-0006's ±38.16%.
  Output frequency and trim step both remain "met," with more headroom
  than DR-0008 (58.9870 MHz max vs. 51.9415 MHz, 22.9% above the ratified
  48.000 MHz target).
- **The post-trim, full-temperature, per-corner-code residual gets worse**
  (+27.85% vs. DR-0008's +13.46%), driven by the `fs` corner's calibration
  code landing on the same code as its own untrimmed reference at this
  sizing (see "Evidence"). The verdict ("exceeds") does not change — it
  was already "exceeds" in every prior campaign — but the margin does, and
  this is the real price of this record's sizing choice, not a
  free recovery.
- **No PVT factorial for Iq, still.** Every Iq figure in this record, like
  DR-0007's and DR-0008's, is the single reference corner
  (`tt` / 27 °C / 3.3 V). The chosen point's ~6.3% margin on `iq_run` is of
  the same order as DR-0008's ~6.6% margin on `iq_op`, which a corner
  sweep did not exist to stress-test either; this remains a standing gap
  (`design/README.md` "Non-goals"), not newly introduced here.
- **`sim/iq/iq_sweep.py`'s generated evidence README no longer asserts that
  `iq_op` and `iq_run` verdicts agree** (they did, coincidentally, at the
  DR-0008 sizing, and do not at this one) — the generator's prose was
  corrected as part of this change so future runs describe the actual
  relationship between the two metrics rather than a stale invariant.
- **Environment note, not a design finding**: the host this record's
  simulations ran on exhibits severe ngspice performance degradation (and,
  transiently, corrupted `iq_run` results) under concurrent multi-threaded
  ngspice invocations, traced to ngspice's own default OpenMP thread count
  (one instance's threads alone match the host's core count) causing
  8–48× oversubscription once more than one `ngspice -b` process runs at
  once. `set num_threads=1` (via a local `~/.spiceinit`, not a repo change)
  fully resolves it. This is a local environment tuning note, not a
  finding about the design or a change to any committed tool.
- DR-0001's topology, DR-0004's no-active-TC-compensation decision, and
  DR-0005's/DR-0006's pre-#22 evidence are all untouched.
