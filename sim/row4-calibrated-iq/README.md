# sim/row4-calibrated-iq - running Iq at per-die calibrated codes for the `w3r65` / `w2.5r75` bank candidates (issue #337, operator ruling 2026-11-18 q178)

The DR-0045/DR-0047 Iq evidence for both bank candidates was taken at fixed codes (0x00 / 0x80 / 0xC0 / 0xFF), and the DR-0032
population calibrates at none of the codes where the candidates' Iq rise was measured (`ss` dice at 0xD2-0xD7, `tt`/`ff` at or
below 0xA8, 0 of 1500 at 0xFF). This campaign measures row 8 running Iq at the code each die actually calibrates to, per
operator ruling q178: for `w3r65` and `w2.5r75`, the DR-0032 population (500 draws per process, seed 20261008, derived
seeds) is re-realized on the candidate DUT, each die's nearest-to-48.000 MHz code is derived at 27 C / 3.3 V (the DR-0032
bisection rule), the code is held across the DR-0044 grid (3.0 / 3.3 / 3.6 V x -40 / 27 / 85 C), and the same die i - same
derived seed, therefore the same mismatch realization - is measured on the DR-0044 L = 1 um control at the same held code.
Sim-only; no `design/*` file touched. All SPICE `klt sim --batch-set ... --backend batch --wait-for-capacity 600`.
Append-only.

```
python3 -I sim/row4-calibrated-iq/gen.py cand  OUTDIR w3r65|w2.5r75 tt|ff|ss          # phase-1 bench + request
python3 -I sim/row4-calibrated-iq/gen.py ctrl  OUTDIR w3r65|w2.5r75 tt|ff|ss REPORT   # phase-2 control decks (25/request)
python3 -I sim/row4-calibrated-iq/gen.py probe OUTDIR SEED                            # draw-matching probe decks (local)
python3 -I sim/row4-calibrated-iq/tables.py --cand RUNDIR --ctrl RUNDIR/phase2 --out RUNDIR/tables   # summary tables
```

Draw identity, and the engine change behind the sigma folding: see `results/20261119T102000Z-probe/README.md`.
In short - the batch fleet image moved to ngspice-47 since DR-0032, on which an `agauss` sigma that is any expression
(including the injector's symbolic `mm_scale*` and literal-scale `1.0*` forms) draws 0 and consumes no RNG; the campaign
folds every injected sigma to a single literal (same 1x values, the form ngspice-47 actually draws) in BOTH the candidate
and control decks, so the matched-die comparison is unaffected. The DR-0032 committed population itself does not re-draw
bit-for-bit on ngspice-47 (probe `dr32-reseed0-check.txt`: sample 0 gives code 170 folded / 168 symbolic against the
committed 163); the campaign keeps DR-0032's seed / draw-identity bookkeeping (same seed 20261008, same derived
per-sample seeds, request shape) so each die is one fixed realization across candidate, control and grid.

Results and disposition: `spec/decision-records/0048-*.md`.
