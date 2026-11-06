# 0027: Live trim-code transition bench - all nine corners x three skews simulated; no runt or missing edge; "never settles" screen is noise-limited at fast corners

- **Status**: proposed (evidence record; the ratified spec is **not** changed)
- **Date**: 2026-11-06
- **Decided by**: Builder agent, issue #103

## Context

[0026](0026-live-trim-code-transition-bench-batch-result.md) recorded a partial batch result: the three `lsb_first` benches aborted in ngspice (`timestep_too_small` at 30.7167 us, every corner) and 22 events failed the "never settles" screen. This record is an addendum with the follow-up run `sim/trim-transition/results/20261106T055733Z/` (nine `klt sim` batch jobs, runner klt 0.9.0, `runner_compatibility=match`, 3 corners per job, all nine jobs `pass`). 0026 is not rewritten.

## Findings

1. **`lsb_first` convergence.** A single local tt/3.3 V probe (host rule: one corner may run locally) reproduced the abort at the identical instant. It was insensitive to `itl4=100`, `method=gear` and `tmax` 100p -> 80p, so it is a hard solver singularity in the state at that instant, not a step-grid or iteration-limit effect. A finite driver impedance (`drv_ohm = 50` ohm in series with each ideal select PWL source, `prepare.py`) lets the run complete. The same instant still produces two zero-length duplicate time points in ngspice's output; `analyze.py` now collapses exact-duplicate timestamps (out-of-order time still fails). The bench changes for all skews (the `none` and `msb_first` benches are re-simulated with the resistor too).
2. **No runt pulse and no missing/extra edge in any of 864 events** (3 skews x 9 corners x 32 events).
3. **Verdicts** (bench screens, not spec rows): `none` 182 PASS / 92 FLAG / 14 VIOLATION; `lsb_first` 202 / 78 / 8; `msb_first` 134 / 146 / 8; 0 FAIL. The `none` and `msb_first` totals match the 0026 run (22 violations) event for event in count.
4. **Worst period excursion** (beyond the old/new envelope): 14 % (`none`), 24 % (`lsb_first`), 41 % (`msb_first`), all at the 0x7F<->0x80 carry at ff; the carry's steady periods themselves differ by 6-7 % (DR-0021's non-monotone carry). Excursions are single-cycle and settle back; they are skew-ordering artefacts of a momentarily wrong code, not charge-injection runts.
5. **The 30 "never settles" rows are a screen artefact, not a slow settle.** The pre-change steady-window period spread of those events is 0.02-0.15 % (median 0.075 %), against a 0.1 % settle tolerance; the 834 non-violating events have a median 0.046 % and up to 0.17 %. The steady period is itself not quieter than the tolerance at fast corners (21 of 30 at ff/3.6 V). The tolerance is **not** loosened.

**Verdict.** DR-0021's no-glitch-on-update assumption holds in all 27 corner x skew benches at schematic level for runt/missing-edge failures; the settle claim (return to within 0.1 % of the new period) cannot be confirmed or refuted at the fast corners with this screen.

## Alternatives considered

- **Loosen `settle_tol` to clear the violations** - rejected: would relax a screen to make results pass.
- **Rerun on a denser grid / longer steady window** - not done; the cause is the steady spread, which a longer window does not reduce. A settle criterion defined relative to the measured steady spread is the better follow-up.

## Consequences

- Follow-up (separate issue if wanted): spread-relative settle criterion; post-layout PEX only if a runt or missing edge appears (none did).
- The 50 ohm driver impedance is a bench modelling choice (realistic digital driver, tau of order ps against a gate load); a 0 ohm ideal source is not simulatable here. Recorded in `sim/trim-transition/README.md` Limitations.
- DR-0021 follow-ups cross-reference this record.
