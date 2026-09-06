# 0007: Post-#16 quiescent current exceeds DR-0003 Row 4's target — ratified spec unchanged

- **Status**: Ratified — records simulation evidence. Does **not** supersede
  any row of [0002](0002-target-spec-ratification.md),
  [0003](0003-pdk-sourced-process-spread-tcr-and-iq.md),
  [0004](0004-no-active-tc-compensation-runtime-discipline.md),
  [0005](0005-pvt-campaign-frequency-shortfall-spec-unchanged.md), or
  [0006](0006-post-resize-pvt-campaign-trim-range-and-accuracy-still-unmet.md).
  The ratified target-spec table in `README.md` stands unchanged.
- **Date**: 2026-09-06
- **Decided by**: Builder agent, issue #20

## Context

Issue #16 (PR #19) re-sized `design/rcosc_bias.sch`'s `RBIAS` from
`L = 200 µm` to `L = 25 µm` (~8x higher comparator tail current) to reduce
comparator propagation delay, one of the two root-cause mechanisms behind
the frequency/trim-range shortfall DR-0005 found. PR #19 explicitly flagged,
in `design/README.md`'s "Non-goals" section, that this resize's effect on
quiescent current (Row 4 of the ratified target-spec table, `< 500 µA`
running — DR-0003) was **not** re-verified.

This record is that re-verification. Issue #20 extended
`design/smoke_test.sch`'s existing `.op` analysis to compute the total DC
current drawn from `vdd` (`i(vdd)`, which by KCL already sums every branch
hung off the supply — both `rcosc_bias` legs, both `rcosc_comparator`
tail-current mirrors, and the trim bank's charging current) at the
reference corner (`tt`, 27 °C, VDD = 3.3 V) and the smoke test's existing
representative trim code (`0x80`). Full evidence, including an independent
hand-estimate sanity check that corroborates the simulated figure:
`sim/iq/results/20260906T032927Z/README.md`.

**Result: 914.99 µA — 1.83x the ratified `< 500 µA` target.**

## Decision

**No ratified spec figure is superseded.** DR-0003 Row 4's `< 500 µA`
quiescent-current target stands unchanged — it is anchored to ST `DS9826`'s
shipped crystal-less-USB part (312 µA typ / 350 µA max) with explicit
headroom for gf180mcu's older 180 nm node, and nothing in this
measurement shows that target is unreachable on this process; it shows
*this specific implementation's* post-#16 bias-current choice overshoots
it.

The overshoot is accepted as a recorded, open gap for now — **not** fixed
by this record or by issue #20, which is scoped to measurement only (per
its own Suggested Scope: "that's a decision-record discussion... not a
silent spec relaxation," explicitly not "re-size the bias generator"). A
follow-up issue is required before this gap can be closed (see
"Consequences").

## Alternatives considered

- **Loosen DR-0003 Row 4 to match the as-simulated figure (e.g. `< 1000 µA`
  or `< 950 µA`).** Rejected outright — this is exactly "relax the ratified
  spec to make results pass," which `CLAUDE.md` prohibits. The 500 µA
  figure is anchored to a real shipped precedent (ST `DS9826`) with a
  deliberate, reasoned headroom multiplier (DR-0003: "~1.43x ST's max and
  ~1.60x ST's typ... with headroom for a node roughly two generations
  older"); loosening it to fit this specific, unbalanced bias-current
  choice would launder an implementation shortfall into a claimed
  requirement change, the same failure mode DR-0003 itself rejected when
  considering the opposite direction (tightening to `< 400 µA`).
- **Revert issue #16's `RBIAS` resize in this issue to bring Iq back under
  500 µA.** Rejected as out of scope for issue #20 (a measurement-only
  issue per its own Suggested Scope) and as premature: reverting the resize
  would re-open the frequency/trim-range shortfall DR-0005/DR-0006 already
  quantified and that issue #16 was filed specifically to fix. Any
  re-balancing of `RBIAS` must jointly consider both the Iq budget and the
  comparator-delay/frequency-range fix it was sized for — a
  single-parameter, single-issue fix in either direction (this record or
  #16) would trade one ratified-spec gap for another. This is exactly the
  kind of joint re-derivation that needs its own issue, not a fold-in here.
- **Treat the ~1.83x overshoot as "close enough" and note it only in
  `design/README.md`'s prose, no decision record.** Rejected — `CLAUDE.md`'s
  evidence discipline requires a decision-record artifact whenever
  simulation contradicts a ratified figure (the same reasoning DR-0005 and
  DR-0006 both state), and issue #20's own acceptance criteria explicitly
  require this record if the target is exceeded.
- **Silently reduce scope of the Iq target's applicability (e.g. call it a
  "trimmed-only" or "per-branch" figure the current sum doesn't map onto).**
  Rejected — DR-0003 Row 4 states the target as `< 500 µA (running)` for
  the block's total supply current, which is exactly what `i(vdd)` measures
  by KCL; reinterpreting the target's scope after the fact to avoid a
  failing verdict is a subtler form of the same relaxation the alternative
  above rejects.

## Consequences

- `README.md`'s target-spec table (Row 4, Iq `< 500 µA`) is **unchanged**
  by this record.
- `design/README.md`'s "Non-goals" section's Iq bullet is resolved by this
  issue: the gap is no longer "not re-verified" — it is now "verified and
  found failing," which is a materially different (and more actionable)
  status. The bullet is updated to state the result and point here, per
  issue #20's acceptance criteria.
- **A follow-up issue is required** to re-balance the bias generator's
  sizing so that both the frequency/trim-range fix issue #16 delivered and
  DR-0003 Row 4's Iq target can be met simultaneously — for example, by
  restoring some of `RBIAS`'s length (trading back some of the comparator
  bandwidth issue #16 bought) while re-checking whether the resulting
  comparator delay still keeps the trim-range/frequency rows DR-0006
  reported at "met"/"close," or by reducing the comparator tail mirror
  ratio instead of the reference current itself (changing the *ratio*
  between the diode-connected reference device and each comparator's tail
  device, rather than `RBIAS`, so the reference-branch current used
  elsewhere is undisturbed) — either avenue (or another) is for that
  follow-up issue to evaluate with its own simulation evidence, not decided
  here. Filed as issue #22 (`loom:triage`), separate from this record.
- This record does **not** invalidate DR-0005's or DR-0006's frequency/
  trim-range/accuracy findings, DR-0004's no-active-TC-compensation
  decision, or DR-0001's topology choice — all stand unchanged.
- If the follow-up re-balancing work shows the ratified Iq and
  frequency/trim-range targets are jointly unreachable by *any* realizable
  sizing of this topology's bias generator on gf180mcu (as opposed to this
  specific first-cut choice), that finding must be recorded in its own
  superseding decision record — not folded into this one.
