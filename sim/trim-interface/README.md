# sim/trim-interface - trim-pin DC selection and static-current harness (issue #106)

Offline harness that prepares a schematic-level characterization of the trim
pins `t0..t7`: where the bank is functionally low-selected / high-selected as a
function of the pin voltage, and what static current the pin draws. It supports
a host-compatibility assessment; it produces **no measured silicon guarantee
and no ratified interface row**.

**Status: generator, analyzer, synthetic tests, documentation and CI only.**
Nothing here launches a simulator, `klt sim`, a cloud operation or a batch
submission. The campaign that executes the generated requests, and the decision
record built from its results, are a later increment.

```
sim/trim-interface/
  prepare.py        extracts rcosc_trim_bank, writes DC benches + batch klt sim requests + provenance
  analyze.py        klt sim report analyzer -> results.json / results.csv / summary.md
  test_harness.py   SYNTHETIC fixtures + request tests (run in CI; no PDK, simulator, credentials, network)
```

Generated files (benches, requests, `provenance.json`) are written to a
directory you choose and are not committed here. Synthetic fixtures exist only
inside `test_harness.py` / pytest temporary directories and are kept out of
append-only simulation evidence (`sim/*/results/`).

## Commands

```
python3 -I sim/trim-interface/prepare.py --out /tmp/trim-interface-req
python3 -I sim/trim-interface/analyze.py v33_t3_bg1_m50=<report.json> ... \
    --bench-dir /tmp/trim-interface-req --outdir sim/trim-interface/results/<runid>
python3 -I -m pytest -p no:cacheprovider sim/trim-interface/test_harness.py   # offline, pytest only
```

CI: `.github/workflows/trim-interface-offline.yml`.

## Case matrix (1296 cases)

8 target pins x 2 held backgrounds x 3 bank bias points x 27 PVT points.

- PVT: process `tt/ss/ff` (section mapping imported from `sim/pvt/pvt_sweep.py`),
  -40/27/85 C, VDD 3.0/3.3/3.6 V.
- The trim bank is instantiated **alone**: `vss=0`, ideal `vdd` source. The
  `rcosc_trim_bank` subcircuit is extracted verbatim from
  `design/netlist/pvt_tb.spice` (device parameters untouched). A missing,
  duplicated, unterminated or structurally changed definition is rejected; no
  hand-written device model is substituted.
- For each target pin, the other seven pins are held first all at 0, then all at
  VDD (backgrounds `bg0`, `bg1`).
- The target source `VTIN` sweeps 0 to VDD in steps of 0.01 VDD, **both
  endpoints included** (101 points).
- Bank terminal `p = VDD`; terminal `m` at 0.25, 0.50, 0.75 VDD. These are
  disclosed static operating-point samples, not exhaustive oscillator
  trajectories.
- One netlist/request per (VDD, pin, background, m) = 144 requests, each with
  9 process x temperature corners. Request tag `v<VDDx10>_t<pin>_bg<0|1>_m<pct>`,
  e.g. `v33_t3_bg1_m50`. Case id
  `<proc>_T<temp>_V<vdd>_pin<N>_bg<B>_m<frac>`, e.g. `tt_T27_V3.3_pin3_bg1_m0.50`.
- Observed: `v(xbank.tb<pin>)` (target inverter output), `v(t<pin>)`, `i(VP)`
  (bank terminal p), `i(VTIN)` (target input source). Requests use the batch
  backend and `waveforms: true`. The raw-file signal names are the intended
  convention; the analyzer also accepts `v(tb<pin>)` and `vp#branch` aliases and
  fails a case when a signal is absent or ambiguous. The names are confirmed
  only when the campaign runs.

## Equations

Let `x` be the swept pin voltage, `VDD` the supply.

- Bank current into `p`: `I_p = -I(VP)` (the source's positive terminal drives p).
- Bank effective conductance `G(x) = I_p / (V(p) - V(m))`, in siemens. This is
  the complete bank response **including the parallel poly resistor**; it is not
  the isolated switch conductance.
- `G0 = G(0)`, `G1 = G(VDD)`; selection `s(x) = (G(x) - G0) / (G1 - G0)`.
  Valid only if `G1 - G0 > max(1e-12 S, 1e-6 * max(|G0|, |G1|))`, otherwise the
  case is invalid ("endpoint conductance unresolved").
- Nonmonotone: `s` falling more than 0.01 below its running maximum is rejected.
- Low-selected `s <= 0.10`; high-selected `s >= 0.90`. Raw low boundary = linear
  interpolation of the 0.10 crossing (upper edge of the low-selected region
  connected to 0); raw high boundary = the 0.90 crossing (lower edge of the
  high-selected region connected to VDD). Each level must be crossed exactly
  once, else the case is invalid (unresolved/ambiguous).
- Screening margin 0.05 VDD inward: `low bound = max(0, raw_low - 0.05 VDD)`,
  `high bound = min(VDD, raw_high + 0.05 VDD)`.
- Inverter diagnostic: the unique interpolated `v(tb<pin>) = 0.5 VDD` crossing
  (`inverter_trip_v`). It is reported, never substituted for either functional
  bound.
- Input current: **`I_in = -I(VTIN)`, amperes, positive into the DUT** (the
  voltage source's positive terminal drives the pin), reported with its absolute
  value at 0, 0.25, 0.50, 0.75, 1.0 VDD, plus the maximum absolute current and
  its bias. This is model-reported static pin current, distinct from supply
  current and inverter crowbar current. A zero model current is not a hardware
  guarantee; the harness does not invent leakage.
- Per-supply aggregate: minimum `low bound` and maximum `high bound` over all
  pins, backgrounds, m biases, processes and temperatures, with the limiting
  case ids, and the maximum `|I_in|` with its case.

The 10 % / 90 % selection levels and the 0.05 VDD margin are configurable,
recorded **characterization screens pending later ratification** (in
`provenance.json` `settings.screens` and the analyzer `params`). Outputs are
named *characterized* low/high bounds. They are not guaranteed VIL/VIH.

## Outputs (schema)

`provenance.json` (prepare.py) top-level keys: `kind`, `evidence`
("NOT EVIDENCE"), `issue`, `git_revision`, `source_dirty`, `grid`,
`process_library_mapping`, `models`, `dut` (source path and SHA-256, extracted
file and SHA-256), `settings` (screens, leak biases, tolerances, sign
convention, units), `requests` (tag, request, netlist, sweep, per-request case
ids), `execution`.

`results.csv` (analyze.py), one row per case, units V / A / S / C:
`id`, `tag`, `process`, `temp_c`, `vdd_v`, `pin`, `background`, `m_frac`,
`valid`, `status` (`OK` or `FAIL: <reason>`), `g0_s`, `g1_s`, `raw_low_v`,
`raw_high_v`, `raw_low_frac`, `raw_high_frac`, `low_bound_v`, `high_bound_v`,
`low_bound_frac`, `high_bound_frac`, `inverter_trip_v`, `inverter_trip_frac`,
`i_in_<bias>_a` and `abs_i_in_<bias>_a` for bias in `000, 025, 050, 075, 100`
(percent of VDD), `max_abs_input_current_a`, `max_abs_input_current_bias_frac`.

`results.json` holds `label`, `synthetic`, `params`, `conventions`, `reports`,
`n_rows`, `n_expected`, `complete`, `aggregate` (per supply: `complete`,
`verdict`, `n_expected`, `n_ok`, `missing`, `duplicate`, `unexpected`,
`failed`, `min_low_bound_v`, `min_low_bound_frac`, `min_low_bound_case`,
`max_high_bound_v`, `max_high_bound_frac`, `max_high_bound_case`,
`max_abs_input_current_a`, `max_abs_input_current_case`,
`max_abs_input_current_bias_frac`) and `cases`. `summary.md` is the
readable table. The analyzer refuses to overwrite an existing results directory.

## Failure handling

Missing or duplicate cases, unexpected case ids, non-`pass` report or corner
status, missing waveform or signal, nonfinite samples, out-of-order or short
sweeps, off-grid endpoints, unresolved endpoint conductance, missing or multiple
threshold crossings and nonmonotone selection all produce an explicit
`FAIL: ...` row and make the affected supply **INCOMPLETE**. An incomplete
aggregate cannot be reported as complete; there is no PASS verdict at all, only
`CHARACTERIZED` (all 432 cases per supply valid) or `INCOMPLETE`. The analyzer's
exit status is nonzero unless every supply is complete.

## Limitations and deferred work

- Schematic model only: ideal supply, no layout extraction, no ESD structure,
  no pad or package. Model leakage may be unrealistically small or zero.
- Static samples at three `m` biases; the oscillator's own `p/m` trajectory is
  not swept.
- Pin capacitance, dynamic edges / slew behavior, ESD and 1.8 V host
  compatibility guarantees are **deferred** (not characterized here).
- No design, spec, decision-record or existing result is changed.

Later campaign procedure (separate approved item): run `prepare.py`, execute
each request through `klt sim` with the batch backend (no local-grid fallback;
preserve and report failures), analyze into a NEW `results/<runid>/`, then
prepare a decision record from the actual results. Ratification of any
interface row happens there, not here.

Test fixtures are **SYNTHETIC** and never measured evidence.
