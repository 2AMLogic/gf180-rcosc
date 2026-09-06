# 0008: Bias re-balance brings Iq under DR-0003 Row 4 — and the `.op` figure DR-0007 used is not the quantity Row 4 names

- **Status**: Ratified — records simulation evidence and a sizing change.
  **Supersedes [0007](0007-quiescent-current-exceeds-target-post-resize.md)'s
  verdict on DR-0003 Row 4** (Iq: *exceeds* → **met**) as a statement about
  the current schematic, and supersedes
  [0006](0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md)'s
  realized trim-curve figures for the same reason. It supersedes **no
  ratified target**: the target-spec table in `README.md` — including Row
  4's `< 500 µA` — stands unchanged, as do
  [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md),
  [0004](0004-no-active-tc-compensation-runtime-discipline.md) and
  [0005](0005-pvt-campaign-frequency-shortfall-spec-unchanged.md).
- **Date**: 2026-09-06
- **Decided by**: Builder agent, issue #22

## Context

Issue #16 (PR #19) re-sized `RBIAS` from `L = 200 µm` to `L = 25 µm` (~8×
higher comparator tail current) to cut comparator propagation delay, fixing
part of the frequency/trim-range shortfall DR-0005 found. Issue #20 then
measured the resulting quiescent current at **914.99 µA**, 1.83× DR-0003
Row 4's ratified `< 500 µA`, and DR-0007 recorded that overshoot as an open
gap requiring a joint re-derivation of the bias sizing — explicitly *not* a
spec relaxation, and explicitly deferred to a follow-up issue. This record
is that follow-up (issue #22).

Two things came out of it, and they are separable.

### Finding 1 — the `.op` figure overstates the running current by ~1.8×

DR-0003 Row 4 reads `< 500 µA` **(running)**, and its anchor is ST
`DS9826`'s `IDDA(HSI48)` (312 µA typ / 350 µA max) — a datasheet supply
current for an oscillator that is *oscillating*. The figure DR-0007 quoted
is `-1e6*i(vdd)` evaluated at an ngspice `.op` point. A relaxation
oscillator has no stable DC operating point by construction, so that solve
converges on the unstable equilibrium. Measured directly at that point and
printed into every raw log (`sim/iq/corners/20260906T062311Z/`), the
charge-complete comparator `XCMPH` sits pinned at its own output inverter's
trip point on a 3.3 V rail — `XCMPH.dp = 1.4783 V`, and its buffered output
`cmph_out = 1.4230 V`, itself mid-rail — so both that output buffer *and*
the SR-latch NOR gate it drives are held in full crowbar conduction. (The
discharge-complete comparator `XCMPL` is resolved at this point:
`XCMPL.dp = 3.2993 V`, `cmpl_out ≈ 0 V`.) The running circuit passes
through that mid-rail state on every edge but never rests in it, which is
why the DC figure and the running figure differ so widely.

The two metrics, measured side by side at the **same** (pre-#22) sizing:

| code | `iq_op` (µA) | `iq_run` (µA) | ratio |
|---|---|---|---|
| `0x00` | 914.40 | 470.40 | 1.94× |
| `0x80` | 914.99 | 502.31 | 1.82× |
| `0xFF` | 914.99 | 605.50 | 1.51× |

The `.op` figure is also all but **code-independent** (914.40 … 914.99 µA
across the full trim range) where the running figure varies by 29% with
code, because higher frequency means more dynamic switching current. A
metric blind to the block's dominant current-vs-frequency trade-off is not
measuring the running quantity Row 4 names.

### Finding 2 — a joint re-derivation meets the target on *both* metrics

The bias budget is `ibias × (1 + 2M)`: one reference branch plus two
comparator tails at `M` times `ibias` each, for `M` the mirror ratio
between `rcosc_bias.sch`'s `MBIASD` and each `rcosc_comparator.sch`
`MTAIL`. At any fixed total, a larger `M` puts a larger share of that total
into comparator tail current — where it buys the bandwidth issue #16 was
after — instead of into the reference leg, where it buys nothing. So the
two knobs DR-0007 named are not alternatives; they are complementary, and
were swept as a 2-D grid (`sim/iq/`, and the scratch grid tabulated under
"Alternatives considered") rather than one at a time.

## Decision

**1. Both Iq metrics are measured and reported, always together, and
neither may be quoted alone.** `design/smoke_test.sch` now prints `iq_ua`
(the `.op` figure, unchanged, for continuity with DR-0007) *and*
`iq_run_ua` (`-i(vdd)` averaged over 20 whole periods, rising edges 5..25,
the same startup-skipping window `sim/pvt/pvt_sweep.py` uses).
`sim/iq/iq_sweep.py` + `run-iq-sweep.sh` produce both across trim codes and
across both sizings as append-only evidence.

**2. The bias generator is re-sized on both knobs jointly:**

| device | pre-#22 (issue #16) | ratified here | effect |
|---|---|---|---|
| `rcosc_bias.sch` `RBIAS` | `W = 2 µm`, `L = 25 µm` | `W = 2 µm`, **`L = 1000 µm`** | reference current ↓ |
| `rcosc_comparator.sch` `MTAIL` | `W = 4 µm`, `nf = 1` (2:1) | **`W = 16 µm`, `nf = 8`** (8:1) | mirror ratio ↑ |

`MBIASD` (`W = 2 µm`, `nf = 1`) is unchanged and is the mirror's unit
device: `MTAIL`'s 8:1 ratio is drawn as eight `2 µm` fingers, i.e. eight
copies of the reference geometry, not one 8×-wider device. The
threshold divider (`RBA`/`RBB`/`RBC`) and every other block are untouched.

**3. DR-0003 Row 4's verdict changes from *exceeds* to *met*** — on both
metrics, at every simulated trim code. The ratified `< 500 µA` figure
itself is **unchanged**; nothing was relaxed to reach this verdict.

Reference corner (`tt` / 27 °C / 3.3 V), `sim/iq/results/20260906T062311Z/`:

| code | `iq_op` (µA) | vs. target | `iq_run` (µA) | vs. target | f (MHz) |
|---|---|---|---|---|---|
| `0x00` | 467.13 | met | 136.45 | met | 26.5059 |
| `0x80` | 467.18 | met | 157.27 | met | 35.9557 |
| `0xFF` | 467.18 | met | 218.54 | met | 51.9414 |

**The verdict does not depend on which metric is chosen**: at the pre-#22
sizing *both* metrics exceed 500 µA at the representative code (914.99 and
502.31 µA); at the ratified sizing *both* are under it (467.18 and
157.27 µA). That is the point of reporting both — it forecloses the reading
that a more favourable metric was selected to manufacture a pass.

## Alternatives considered

- **`RBIAS` alone, leaving the 2:1 mirror (DR-0007's first suggested
  avenue).** Simulated across `L = 25 … 2000 µm`. `L = 250 µm` gives
  `iq_op = 476.72 µA` with maximum reachable frequency 50.85 MHz;
  `L = 200 µm` gives 497.44 µA — 0.5% margin — at 51.93 MHz. **Rejected**:
  the joint point reaches 51.94 MHz at 467.18 µA (6.6% margin), strictly
  better on *both* axes, precisely because a larger `M` stops spending the
  budget on the reference leg. A single-knob fix leaves that on the table.
- **The mirror ratio alone, leaving `RBIAS` at `L = 25 µm` (DR-0007's
  second avenue).** **Rejected on simulation**: raising `M` at fixed
  `RBIAS` *raises* Iq (`L = 100 µm`, `M = 8` → 981 µA). The ratio knob
  redistributes the budget between reference leg and tails; it does not
  shrink it. Both knobs are required, which is why DR-0007's framing of
  them as two independent options is superseded here.
- **Pushing the mirror ratio past 8:1.** `M = 16` and `M = 32` were both
  simulated at matched Iq (`RBIAS L = 2000 µm`, `M = 16` → 471.49 µA /
  52.11 MHz vs. `L = 1000 µm`, `M = 8` → 467.18 µA / 51.94 MHz).
  **Rejected**: within 0.2% at equal Iq — the knee is at `M ≈ 8` — so a
  higher ratio would add mirror-mismatch risk and resistor area for no
  measurable return. 8:1 is where the evidence stops paying, not an
  arbitrary pick.
- **Sizing against the running metric only, keeping more of issue #16's
  comparator bandwidth.** The running figure has large headroom at the
  ratified point (218.54 µA at the worst code, 44% of target), so this
  would have recovered trim range. **Rejected here**: it would leave the
  `.op` figure well above 500 µA, and both DR-0007's framing and issue
  #22's acceptance criteria state the target against that figure. Meeting
  the *stricter* of two readings costs only trim range — a row that was
  already "not met" before and after — whereas adopting the looser reading
  inside the same record that first argues for it would be indistinguishable
  from relaxing to pass. Deferred to **issue #24**, where the metric change
  is the subject rather than a side effect.
- **Relaxing Row 4 to fit the as-simulated figure.** **Rejected** — this is
  exactly what `CLAUDE.md` prohibits, and DR-0007 already rejected it.
  Note that nothing here loosens Row 4: it is met as written.
- **Folding this into DR-0007 rather than filing a new record.**
  **Rejected** per DR-0007's own "Alternatives considered", which requires
  a superseding record for any change in Row 4's disposition.
- **Recording the metric finding in `design/README.md` prose only, with no
  decision record.** **Rejected** — a verdict flip on a ratified row is
  exactly the artifact `CLAUDE.md`'s evidence discipline requires a record
  for, and the same reasoning DR-0005/0006/0007 each state.

## Consequences

- **DR-0003 Row 4 (Iq) is met** at the reference corner on both metrics at
  every simulated code. DR-0007's failing verdict is superseded as a
  statement about the current schematic; DR-0007 remains the correct record
  of what the *post-#16* schematic measured.
- **Trim range regresses, and this is the price paid.** Full campaign
  `sim/pvt/results/20260906T060104Z/` (271 unique points, 0 failures) vs.
  DR-0006's `20260906T030219Z`:

  | Spec row | DR-0006 (post-#16) | here (post-#22) | verdict change |
  |---|---|---|---|
  | Output frequency (48.000 MHz) | max 65.9204 MHz | max 51.9415 MHz | none — **met** both |
  | Trim range (±40%) | ±38.16% | ±32.42% | none — **not met** both, margin worse |
  | Trim step (0.314 %/code) | 0.4839 %/code | 0.3763 %/code | none — **met** both |
  | Untrimmed process spread (±35%) | −25.60% / +38.71% | −25.46% / +38.54% | none — **within** both |
  | Post-trim, calibration point (±1.1%) | −11.38% / +10.56% | −10.18% / +10.30% | none — **exceeds** both |
  | Post-trim, full temp (−9% / +8%) | −18.00% / +12.91% | −17.38% / +13.46% | none — **exceeds** both |
  | **Quiescent current (`< 500 µA`)** | **914.99 µA — exceeds** | **467.18 µA — met** | **exceeds → met** |

  Row 4 is the only verdict that moves. The trim-range row's *verdict* is
  unchanged (it was already not met), but its margin to ±40% widens from
  1.84 to 7.58 percentage points. That is a real regression against
  DR-0006's finding and is recorded here rather than buried: the ratified
  48.000 MHz output frequency stays reachable with 8.2% headroom, and the
  design remains far from DR-0005's pre-#16 shortfall (31.18 MHz maximum
  reachable at *any* corner or code), but the trim range got worse to buy
  the Iq fix.
- **Trim-curve monotonicity is not degraded.** The `0xE0` → `0xF0` →
  `0xFF` region DR-0006 flagged stays monotonic (48.5043 → 50.7721 →
  51.9415 MHz), and the small LSB-region non-monotonicity is marginally
  smaller than DR-0006's (−0.09% vs. −0.11% at `0x10`).
- **Issue #24 is filed** to re-derive the sizing against the running metric
  and determine how much of the lost trim range is recoverable while still
  meeting Row 4 as worded. If that work shows the recovery is negligible,
  that is equally a finding and needs its own record.
- **Testbench changes**: `design/smoke_test.sch`'s transient window goes
  400 ns → 1200 ns to fit the 20-period averaging window; its `rise=1` /
  `rise=2` measurements are unchanged, so issue #16's evidence line stays
  comparable. New driver `sim/iq/iq_sweep.py` + `sim/iq/run-iq-sweep.sh`,
  and `sim/iq/corners/<runid>/` joins `sim/pvt/corners/` as a raw-log tree.
- **Not re-verified here**: Iq across the PVT factorial. Every Iq figure in
  this record is the single reference corner (`tt` / 27 °C / 3.3 V), as
  DR-0007's was. A corner sweep for Iq remains a possible future increment;
  the 6.6% `.op` margin is thin enough that a corner campaign could plausibly
  move it, whereas the running metric's 56% margin at the *worst* simulated
  code (218.54 µA at `0xFF`) is not seriously in doubt.
- DR-0001's topology, DR-0004's no-active-TC-compensation decision, and
  DR-0005's pre-#16 evidence are all untouched.
