# sim/mc-groundwork — item-6 Monte Carlo groundwork (issue #77)

Design-independent groundwork for T1 item 6 (DR-0019): (1) can the gf180mcuC
ngspice models be sampled for mismatch through a `klt sim` `monte_carlo`
request, and (2) a bench that does the **per-sample trim-code selection**
DR-0019 section 2 requires. **No yield is run or claimed.** The campaign and
every yield number still wait for #66 (DR-0019 section 4). No ratified spec
row is touched; the tolerances below are harness criteria, not spec values.

```
sim/mc-groundwork/
  gen_bench.py                 writes the benches and requests below (DUT inlined from design/netlist/pvt_tb.spice)
  run-groundwork.sh            cold start: gen_bench.py, then the three requests into a NEW results/<runid>/
  tb_trimsel_nomm.spice        per-sample trim-selection bench, sw_stat_mismatch=0
  tb_trimsel_mm.spice          same bench, sw_stat_mismatch=1
  tb_fixedcode.spice           fixed-code reference (code decoded from one DC source)
  request_*.json               the `klt sim` requests
  results/20261008T235620Z/    the committed run (append-only)
```

Run: engine ngspice 42 (this host), `klt 0.7.0+g4cbdfa769875`, `gf180mcuC`,
open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`,
`sm141064.ngspice` sha256 `6edba54d…1b77b1aa`, MC seed `20261008` (DR-0019).

## Feasibility verdict: mismatch-capable PARTIALLY (MOS yes; resistor and MIM capacitor no)

| device family in the design | per-instance (local) mismatch in the vendored models | evidence |
|---|---|---|
| `nfet_03v3` / `pfet_03v3` (comparator, bias mirrors, trim switches) | **Yes.** `delvto='mis_vth*sw_stat_mismatch'`, `mulu0='1-mis_k*sw_stat_mismatch'`, both drawn with `agauss` per instance | `results/20261008T235620Z/model-mismatch-evidence.txt`; five samples differ (below) |
| `ppolyf_u_1k` (bias divider and the **trim ladder**) | **No.** The subcircuit never references `sw_stat_mismatch`; its only statistical terms are the global `mc_rsh_*`/`mc_dw_*`/`mc_rt_*`, gated by `sw_stat_global` and drawn once per run (common to every instance, so a corner-like shift, not a matching error). The `(1+mis_r*sw_stat_mismatch)` hook exists only in `nplus_u`/`npolyf_u`/`pplus_u`/`ppolyf_u`, with `mis_r` defaulting to 0 and its sigma formula commented out | same file |
| `cap_mim_1f0fF` (timing capacitor) | **No.** Only the global `mc_c_cox_1p0fF` (gated by `sw_stat_global`, one draw per run). No local term | same file |

What this means for the DR-0019 claims. The comparator-offset term of the
DR-0003 Row 3 budget and the bias/switch mismatch can be sampled. The
**trim-DAC element mismatch (+/-0.300 %) and any timing-C mismatch cannot be
sampled from the PDK models**: a `monte_carlo` run with `vary: "mismatch"`
varies only MOS devices, and `sw_stat_global=1` would move all resistors
together rather than relative to each other. Statistical rows 2, 4, 5 (S1-S3)
therefore need a stated, design-owned matching model for the ladder resistors
(and the capacitor) injected into the netlist (e.g. per-segment Pelgrom
multipliers drawn from `mc_mismatch_seed`) with the assumption recorded in a
decision record, or the campaign must say that its MC covers MOS mismatch only.
That choice is the campaign's, not made here, and nothing here relaxes a row.

`klt sim` itself expresses the MOS case correctly: `monte_carlo` seeds
`.options seed=` per sample, and `sw_stat_mismatch=1` set in the netlist body
takes effect (the body's `.param` overrides the model default). A caveat: its
`family_mismatch` report classifies the design's resistors and capacitor as
`other` / `capacitor` with `active: null` ("not verified"), so it does not
reveal that they have no mismatch hook — filed as klayout-tools#2898. And the
mismatch seed is keyed on the corner index, so one `sample_index` is a
different die at each corner (klayout-tools#2899).

## The per-sample trim-selection bench

`klt sim` runs one analysis per corner (klayout-tools#2482), but per-die
calibration needs ~10 dependent solves against the *same* sampled devices.
The bench therefore carries a `.control` block in the netlist body (against
the documented "no `.control` in the body" convention; the gap is the reason)
that, inside one ngspice session:

1. binary-searches the 8-bit code (`alter` VT0..VT7, one 1200 ns transient
   per probe, f from edges 5..25 exactly as `sim/pvt`) for the code nearest
   48.000 MHz at 27 C, 3.3 V,
2. holds that code and re-measures it,
3. exposes `code_sel`, `f_sel_hz`, `f_hold_hz`, `resid_pct`, `hold_gap_hz` as
   `set` variables that `klt sim` harvests with `measurements[].expr`
   (`analysis.kind: "op"`; the real analysis is the body's transients).

Mismatch parameters are drawn once when ngspice expands the netlist, so they
persist across the `alter`/`tran` re-runs: every probe of a sample sees one
die. Each `tran` makes a new current plot, so the search state lives in a
`setplot new` plot and is bridged with `set`. The search is a bisection over
`[-1, 256]` with virtual rails, so a saturated search ends on a rail code.
Like `sim/pvt`'s `calibrate`, it assumes monotonic f(code); the committed
trim curve has local dips (e.g. 0x7F -> 0x80), so the pick can be locally
suboptimal.

**Scope limits, stated.** The bench calibrates at the corner it is given
(temperature from `.temp`, supply fixed at 3.3 V); holding the code at *other*
temperatures/supplies inside the same die (S2/S3) needs the body to restore
the corner temperature, which it cannot see — that is the multi-step gap on
#2482 (comment added) plus #2899 for cross-corner same-die. The run below is
the calibration point only.

## Smoke results (`results/20261008T235620Z/`)

Fixed-code reference, mismatch off, `tt`/27 C/3.3 V (`report_ref_codes.json`,
file-scope `.meas`, the independent measurement path):

| code | 160 | 161 | 162 | 163 | 164 | 165 |
|---|---|---|---|---|---|---|
| f (MHz) | 47.4143 | 47.6504 | 47.9294 | 48.1755 | 48.4741 | 48.7830 |

Zero-mismatch control (`report_control_nomm.json`, `sw_stat_mismatch=0`,
3 `monte_carlo` draws, `vary: "mismatch"`):

| check | observed | pass |
|---|---|---|
| draws identical (sigma = 0) | all three: code 162, f 47.9845 MHz | yes |
| chosen code = the reference sweep's nearest-to-48 MHz code | 162 (-0.148 %) vs 163 (+0.366 %) | yes |
| held f vs fixed-code reference at the same code, within 0.25 % | +0.115 % (47.9845 vs 47.9294 MHz) | yes |
| re-measure at held code reproduces the search value | `hold_gap_hz` = 0 | yes |

Mismatch smoke, 5 samples (`report_smoke_mm.json`, `sw_stat_mismatch=1`),
smoke only, **not a yield**:

| sample | code | f_hold (MHz) | residual |
|---|---|---|---|
| mc0 | 163 | 48.0342 | +0.071 % |
| mc1 | 161 | 48.0844 | +0.176 % |
| mc2 | 163 | 48.0241 | +0.050 % |
| mc3 | 163 | 48.1363 | +0.284 % |
| mc4 | 162 | 47.8561 | -0.300 % |

The control's tolerance (0.25 %) is set from the repeatability measured here,
not from the spec. The same circuit and code (0xA2) measured three ways gives
47.9294 (B-source-decoded code, `klt sim` `.meas`), 47.9503 (static sources,
`repeatability/`), and 47.9845 MHz (in-session, after earlier probes): a
0.116 % spread, about 0.37 LSB (0.314 %/code). Tightening the solver moves
the value too (`repeatability/`, static 0xA2): `reltol` 1e-3 -> 47.9503,
3e-4 -> 48.0450, 1e-4 -> 48.0498 MHz, i.e. the default-`reltol` figure is
about 0.2 % low. This matters for the campaign: that noise is comparable to
the half-LSB (0.157 %) the residual is judged against, and the committed
`sim/pvt` figures were produced with default `reltol` on ngspice 46 (this
host's ngspice 42 reads the same code 0.4 % apart: 0xA3 is 47.98186 MHz in
`sim/pvt/results/20260923T030125Z` and 48.1755 MHz here). The campaign should
fix `reltol` and the simulator version before it quotes residuals. This is
recorded, not acted on: no committed result is changed.

## Batch fleet: not usable on 2026-10-08 (reported, not worked around)

The three requests are expressed as `klt sim` requests and would go to the
Spot fleet on a host exporting `KLT_SIM_BACKEND=batch`. They did not run
there:

- `klt 0.7.0` (the host tool): after one `BATCH_MAX_CONCURRENT_INSTANCES=8`
  capacity refusal the job was refused, exit 87, "fleet runner runs klt 0.5.0
  but the submitting client is 0.7.0"
  (`results/20261008T235620Z/batch-attempts/report_ref_codes.klt0.7.0-refused.*`).
- `uvx --from klayout-tools==0.6.0 ... --backend batch`: the job failed with
  exit 1 in ~4 s, no usable report, with the DUT inlined into one netlist
  (`batch-attempts/report_ref_codes.klt0.6.0-batch-failed.json`). The job log
  was not retrievable with this host's credentials. This matches
  klayout-tools#2882 (open); data point added there.

Because the bench and its two requests (3 and 5 samples) are a smoke run,
they were run on this host with `--backend local` (serial). The six-code
fixed-code reference is a six-corner grid of one short solve each; it was
also run locally (12 s), which is more than "single unit" — flagged for the
reviewer. An earlier attempt of the same six-code grid with `uvx
klayout-tools==0.5.0` also ran locally (that version ignores
`KLT_SIM_BACKEND`); its output is not committed, and it reproduced the same
six values. The 500-sample campaign must not be run until the fleet accepts
a client that supports `monte_carlo` and `expr`.

## Friction filed or extended at 2AMLogic/klayout-tools

- #2898 (new): `family_mismatch` reports the PDK's poly-resistor and MIM
  subcircuits as `other`/`active: null`.
- #2899 (new): mismatch seed keyed on `corner_index`; no same-die-across-corners option.
- #2482 (comment): per-sample dependent solves; body `.control` stop-gap and its costs.
- #2882 (comment): fleet failures observed for this request shape.
- #2892 (existing): relative `-o` makes ngspice never start; hit and worked around with an absolute path.
