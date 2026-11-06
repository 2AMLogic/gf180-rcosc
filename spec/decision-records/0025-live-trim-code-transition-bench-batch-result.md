# 0025: Live trim-code transition bench - batch result is partial; no runt/missing edge, but settle violations and an unsimulated lsb_first skew

- **Status**: proposed (evidence record; the ratified spec is **not** changed)
- **Date**: 2026-11-06
- **Decided by**: Builder agent, issue #103

## Context

[0021](0021-runtime-discipline-trim-resolution-sof-loop-model.md) models a disciplining loop that rewrites the 8-bit trim code every SOF frame, assuming the update does not corrupt the clock. Issue #103 added `sim/trim-transition/` (PWL-driven select lines, +/-1 steps at a non-carry code and at the 0x3F/0x7F/0xBF carries, four phases, three skews, nine tt/ss/ff x 3.0/3.3/3.6 V corners). The nine requests ran through `klt sim` on the batch fleet (runner klt 0.9.0, launch template v11, open_pdks `f6eeac7`) into `sim/trim-transition/results/20261106T050454Z/`; method and tables in `sim/trim-transition/README.md`.

## Decision

Nothing in the ratified spec is changed or relaxed. The finding is recorded:

1. **No runt pulse and no missing/extra edge** in any of the 576 events simulated (`none` and `msb_first` skews, all nine corners).
2. **22 events fail the "never settles" screen** (17 ff/3.6 V, 4 ff/3.3 V, 1 tt/3.3 V; carries 0x3F<->0x40 and 0x7F<->0x80, plus two non-carry downs at ff/3.6 V). Several have excursions under 1 %, so a slow tail or a screen artefact of the steady-window definition is likelier than a glitch; unresolved.
3. **249 FLAGs**, concentrated at the major carries; the 0x7F->0x80 up step reaches 31 % period excursion (msb_first, ff, 3.0 V). This is largely the known non-monotone carry of DR-0021 (the steady periods themselves differ by 6-7 %), not new injection.
4. **The `lsb_first` skew has no batch evidence**: all nine corners aborted in ngspice (`timestep_too_small`, at 30.7 us in every corner) although the 2026-10-09 local tt/3.3 V probe completed. Not debugged and not rerun locally (host rule: grids go to the fleet; bench generator out of scope).

**Verdict.** DR-0021's no-glitch-on-update assumption is *not confirmed* for all skews and corners, and not refuted either: no glitch-class failure was seen where simulation completed.

## Alternatives considered

- **Rerun `lsb_first` locally** - rejected: host rule forbids local grids; the abort is deterministic across corners.
- **Loosen the settle tolerance to clear the 22 violations** - rejected: would relax a screen to make results pass.

## Consequences

- Follow-ups: (a) make the `lsb_first` bench converge (stimulus/solver options) and rerun on the fleet into a new `results/<runid>/`; (b) decide whether the ff/3.6 V settle tail is real (longer steady window or denser sampling); (c) post-layout PEX only if (b) shows a real effect.
- DR-0021 follow-ups cross-reference this record.
