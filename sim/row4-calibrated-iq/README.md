# sim/row4-calibrated-iq - running Iq at per-die calibrated codes for w3r65 / w2.5r75 (issue #337, ruling q178)

Sim-only measurement. Both bank candidates (DR-0037 `w3r65`, DR-0047 `w2.5r75`, applied as netlist text to the
extraction of the rebuilt layout, `sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice`)
are measured over the DR-0032 population: 500 mismatch draws per process (`tt`/`ff`/`ss`, `seed 20261008`,
`vary: mismatch` - klt's derived per-sample seeds reproduce DR-0032's `sim/mc/results/20261112T025135Z` draws
sample-for-sample; `tables.py check` asserts it). Each die calibrates inside one ngspice session (`.control`
bisection, the `sim/mc/gen_campaign.py` method) for the code nearest 48.000 MHz at 27 C / 3.3 V, then holds it
across the DR-0044 grid 3.0/3.3/3.6 V x -40/27/85 C, measuring frequency and running Iq at every point. Running
Iq is the DR-0044 integrator (`-i(VDD)` on 1 nF, window = clk rising edges 5..25); probes stop at 1200 n like
every established extraction probe (`gen_calib_requests.py`, `gen_stage_requests.py`) - the window is
edge-indexed, so the stop time does not move it.

The control is DR-0044's L=1 um same-recipe extraction of the previous layout (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`),
run as a `klt sim` **deck list**: deck `k` carries `.options seed=<derived seed of the candidate's k-th sample>`
(read from the candidate report) and that die's calibrated code, so every delta is matched on draw, code, supply
and temperature. Draw matching was verified three ways before the full grid (pilot run dirs): derived-seed parity
with DR-0032, bit-identical inline-vs-`.include` RNG behaviour, and identical 14-term DR-0022 injector manifests
across all three DUTs. All SPICE `klt sim --backend batch --wait-for-capacity 600`; nothing runs locally.
Append-only.

```
run.sh RUNID [pilot]                                    # full driver (cand + ctl, batch fleet)
python3 -I sim/row4-calibrated-iq/gen.py cand w3r65 OUTDIR [N]          # benches + MC requests
python3 -I sim/row4-calibrated-iq/gen.py ctl OUTDIR CANDRUNDIR [N]      # control deck list from a cand run
python3 -I sim/row4-calibrated-iq/tables.py check CANDDIR CTLDIR        # draw-identity checks
python3 -I sim/row4-calibrated-iq/tables.py TAG CANDDIR CTLDIR OUTDIR   # distribution / delta tables
```

Run dirs (append-only, under `results/`):

- `*-pilot-*` - n=2 fleet pilots for both variants and the control deck path (seed parity, RNG equivalence,
  `$PDK_ROOT` deck resolution).
- `*-cand-w3r65`, `*-cand-w25r75` - the n=500 Monte Carlo campaigns (3 requests each).
- `*-ctl-w3r65`, `*-ctl-w25r75` - the control deck lists (3 deck requests, 500 decks each; `codes.json` maps
  sample_index -> seed + calibrated code). Per-unit `dut_control.spice` and deck copies are stripped from the
  collected trees before committing (byte-identical to the request-side files; each unit's `unit.json` keeps the
  deck sha256); `stdout.bin` / `stderr.bin` / `unit.json` are the evidence.
- `*-analysis-*` - `tables.py` output (`table_vs_control.md`, `summary.json`).

Outcome: `spec/decision-records/0048-*.md`.
