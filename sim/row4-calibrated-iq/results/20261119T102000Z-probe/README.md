# 20261119T102000Z-probe - draw-matching and engine-semantic probes (sim/row4-calibrated-iq, issue #337)

Three local single-deck ngspice runs (`probe_*.spice`, one at a time) and two evidence pieces for the
ngspice-46 -> 47 fleet-image change.  No batch campaign in this directory; the probe decks are also the
record of why the campaign's injector sigmas are folded to single literals.

## Draw matching (`probe_*.csv`, wrdata columns: f/iq repeats then the d__91 draw as the last odd column)

`.options seed=<S>` + the identical 98-X-card / 28-injected-param draw sequence in both DUT texts means die i's
realization is identical on candidate and control; `wrdata probe.csv iq1 iq2 d91v` exposes the integrator Iq
(20-period window, twice - the `.ic` integrator re-zeros per tran, iq1 == iq2 everywhere) and the injected X$91
draw through a probe-only behavioral source (`BD91 p91 0 V='d__91'` - a `.param` is not a control-space vector).

| deck | DUT | seed | iq1 = iq2 (A) | d__91 (V) | d__91 / sigma |
|---|---|---|---|---|---|
| probe_cand_w3r65 | rebuilt extraction + w3r65 | 1316784515 | 3.91230e-4 | 3.30478e-3 | **1.30742** (sigma 0.0025277861590801785) |
| probe_ctrl_l1 | `sim/cmph-fix/` (L=1u control) | 1316784515 | 3.74628e-4 | 2.66440e-3 | **1.30742** (sigma 0.0020379663547086) |
| probe_ctrl_alt | `sim/cmph-fix/` (L=1u control) | 1316784516 | 3.57154e-4 | 2.65222e-3 | 1.30191 (different seed, different draw) |

Same seed -> the same unit normal (1.30742) scaled by each device's own sigma (ratio 0.80622 = sqrt(7.82509/12.0386),
the X$91 length ratio of `w3r65`); seed + 1 -> an unrelated draw.  That is the matched-draw contract of the phase-2
control decks, verified before the campaign.

## ngspice-47 sigma semantics (`fleet-sigma-probe.spice`, run on the batch fleet, `fleet-sigma-probe-stdout.bin`)

The batch fleet image now runs **ngspice-47** (stdout banner; DR-0032's 2026-11-12 reports record ngspice-46).
On ngspice-47 an `agauss(0, <expr>, 1)` sigma draws **0 and consumes no RNG** unless `<expr>` is a single folded
literal: `agauss(0,mm_scale*0.0025,1)` -> 0, `agauss(0,var,1)` -> live, `agauss(0,0.0025,1)` -> live,
`agauss(0,1.0*0.0025,1)` -> 0 (the injector's literal-scale path is still an expression).  Single-parameter sigmas
(the PDK's per-instance `agauss(0,var_k,1)`) draw live.

## DR-0032 reproduction check (`dr32-tb_main_tt-reseed0-local.spice`, `dr32-reseed0-check.txt`)

The committed `sim/mc/tb_main_tt.spice`, run locally on ngspice-47 with DR-0032 sample 0's derived seed
(1316784515) and the tt model sections:

| sigma form | code_sel | fhold (MHz) | committed DR-0032 sample 0 |
|---|---|---|---|
| symbolic (`mm_scale*...`, as committed) | 168 | 47.8915 | **163 / 47.9425** |
| folded literal | 170 | 47.8918 | |

Neither form reproduces the committed sample: the 46 -> 47 image change shifted the realization itself, so the
DR-0032 committed population cannot be re-drawn bit-for-bit on today's fleet.  The campaign keeps DR-0032's
seed / draw-identity bookkeeping (same seed 20261008, same derived per-sample seeds, request shape) and folds the
injected sigmas so the DR-0022 injected ladder/MIM terms are actually live on the engine that runs it; candidate
and control carry the identical folded treatment, so the matched-draw comparison is unaffected.
