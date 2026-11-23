# sim/trim-dense - dense trim-step request generator and analyzer (offline)

Issue #98, the offline-preparation subset of #87. **The dense campaign ran (1536 jobs, `results/20261106T1115Z-campaign/`, #87) and
its analysis is committed in `results/20261120T2330Z-verdict/`, read in decision
record 0049.** This directory holds the tooling and tests; `results/` may hold the
frozen campaign, the #378 engine A/B, a Step 0 fleet-gate record and that one verdict
directory, the only place analyzer outputs are permitted (see
`test_no_measured_artifacts_in_tree`). `analyze.py --engine-ab <comparison.json>` accepts a
version-mixed campaign only against a committed paired A/B. Every curve in
`test_harness.py` is a labeled synthetic fixture. The verdict
is decision record 0049; no ratified row, existing result, design
file or DR-0021 is changed by this directory.

| file | role |
|---|---|
| `prepare.py` | writes `klt sim` batch requests + testbenches for codes 0x00..0xFF, `provenance.json`, `manifest.template.json`; `--engine-version-expected` with a real version also pins `engine_version` per request |
| `analyze.py` | validates `klt sim` reports and produces ordered frequency/step tables, extrema, carry transitions and the ratified-resolution comparison |
| `compare_engine.py` | paired engine-version A/B (issue #378): per-code `fosc` deltas between two report sets + bench attestation (requests identical to a frozen campaign once the pin key is removed) |
| `test_harness.py` | synthetic-fixture tests (no simulator, no process launched) |
| `test_compare_engine.py` | offline tests for `compare_engine.py` (synthetic reports only) |

## Grid

Variants (explicit, hashed input netlists; both must define
`.subckt rcosc_top clk t0 .. t7 vdd vss`, the alphabetical order `klt extract`
writes, because the testbench instance line is positional):

- `sch`: `--schematic-netlist` (e.g. `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice`)
- `ext`: `--extracted-netlist` (a `klt extract` output; `netlist_source: extracted`)

Corners (default; override with repeated `--corner PROC:TEMP_C:VDD_V`, values
must lie on the `sim/pvt/pvt_sweep.py` grid `PROCESS_CORNERS` / `TEMPS_C` /
`VDDS_V`):

| corner tag | process (fets/res/mimcap + `cap_mim`) | T | VDD | why |
|---|---|---|---|---|
| `tt_27C_3p3V` | tt | 27 C | 3.3 V | nominal |
| `ss_m40C_3p0V` | ss | -40 C | 3.0 V | bounding corner, as in `sim/supply-transient` |
| `ff_85C_3p6V` | ff | 85 C | 3.6 V | bounding corner, also the DR-0017 Row-4 guardrail cell |

Per (variant, corner): 256 requests, one per code, so 2 x 3 x 256 = 1536
single-corner requests by default. The trim code is not a `klt sim` axis and
the frequency `.meas` threshold (VDD/2) is fixed at authoring time, so
code and supply are baked into each testbench (static `VT<i>` sources at
`VDD * bit`, not B-source decode, per the repeatability notes in
`sim/mc-groundwork/README.md`). Frequency measurement is identical to
`sim/pvt-postlayout/klt-pex/gen_requests.py`: 20 periods after skipping 5
edges. The default `tran` stop is 2000n (not 1200n) so low codes at slow
extracted corners still reach edge 25; it is configurable.

Layout of the output directory: `<variant>/<corner>/{rcosc_top_<variant>.spice,
tb_cXX.spice, request_cXX.json}`; request tag `<variant>_<corner>_cXX`.

## Solver settings and repeatability

`--reltol --abstol --vntol --tstep --tstop --skip-edges --periods
--timeout-s --capacity-wait-s --engine-version-expected` are configurable;
they are written into every testbench (`.options`), `provenance.json` and the
manifest template. Defaults are ngspice's own (`reltol=1e-3`, matching the
committed `sim/pvt` campaigns). `sim/mc-groundwork/README.md` shows `reltol`
moves frequency by about 0.2 %; on simulator versions, that bench measured the
ngspice **42→46** move at ~0.4 % on one trim code (~2.5× the half-LSB), while
the paired **46→47** A/B (`results/20261115T160955Z-engine-ab/`, issue #378)
measured median +0.0000 %, max |delta| 0.1328 %, 0/47 pairs over the half-LSB
— verdict recorded there: immaterial, per-curve version treatment defensible.
#87 must freeze `reltol` and the
simulator version before the run; `analyze.py` rejects a manifest whose
solver settings differ from the generated ones, and a run whose reports mix
simulator versions or differ from the manifest.

Setting `--engine-version-expected` to a version (`"MAJOR"` or
`"MAJOR.MINOR"`) additionally emits a request-level `engine_version` pin in
every request (klayout-tools#3041): `klt sim` fails the run with code
`engine_version_unmet` when the runner's reported version disagrees — checked
after the run, since the batch backend has no pre-submit probe. The default
`unspecified` emits no pin and leaves every request byte unchanged, which is
what keeps a frozen campaign (`run_batch.py`'s `provenance_sha256` preflight)
submittable across prepare.py changes.

## Step and resolution formulas

```
step[c]  = 100 * (f[c+1] / f[c] - 1)   [%]     c = 0 .. 254   (signed)
nominal  = 80 / 255 = 0.313725 %/code            (DR-0003, Row 2)
half-LSB = 40 / 255 = 0.156863 %
deviation[c] = step[c] - nominal   [percentage points]
dnl[c]       = step[c] / nominal - 1   [LSB]
```

Reported per curve: worst positive step (largest step > 0), worst negative
step (most negative step < 0), smallest/largest signed step, every
non-positive transition (`step <= 0`; a flat step is not monotone), the carry
transitions 0x7F->0x80, 0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0, the span, the mean
step `100*(f[255]/f[0]-1)/255` (the same arithmetic convention as 80 %/255),
and the steps whose `|deviation|` exceeds half-LSB (outside
0.156863..0.470588 %). This comparison is descriptive; whether results meet a
ratified row is decided in #87, not here.

## Validation

A curve needs exactly one entry per code 0..255. Unordered entries are
normalized by code. Missing and failed/errored entries make the curve
`INCOMPLETE`; duplicate, non-finite, non-positive, non-numeric or
out-of-range-code entries make it `INVALID`. No value is imputed, and an
invalid curve carries a problem list instead of a table or summary, so it can
never be read as a passing measurement. Report-level checks: report status,
exactly one corner matching the request process/temperature, corner status,
exactly one passing `fosc` measurement, and (when present) the report's
`netlist_sha256` against the generated testbench.

## Offline commands

```
python3 -I sim/trim-dense/prepare.py \
    --schematic-netlist sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice \
    --extracted-netlist <klt extract output .spice> --out /tmp/trim-dense-bench

# synthetic-fixture smoke of the analyzer (reports labeled "synthetic": true):
python3 -I sim/trim-dense/analyze.py --bench-dir /tmp/trim-dense-bench \
    --reports-dir <dir of report_<tag>.json> --outdir /tmp/trim-dense-res --synthetic

python3 -m pytest -p no:cacheprovider sim/trim-dense/test_harness.py
```

`--out` and `--outdir` must be new or empty directories. Output of
`analyze.py`: `results.json`, `steps.csv` (ordered code/frequency/step table),
`summary.md`. Fixture runs (`--synthetic`, or any report with
`"synthetic": true`) carry `SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE` in all
three. Exit status is 0 only if every curve is valid and provenance is
complete (it says nothing about monotonicity).

## Provenance (follows the #65 convention)

`manifest.template.json` lists the fields to fill at execution: `git_sha`,
`git_dirty`, `klt_version`, `engine`, `engine_version`, `pdk`,
`pdk_revision` (40-hex open_pdks commit, or exactly `"unknown"` plus
`pdk_revision_reason`; see `sim/pdk_provenance.py`), `pdk_revision_source`,
`model_dir`, `backend`, `executed_utc`, `provenance_sha256` (sha256 of the
bench's `provenance.json`), and the `solver` block. For a non-synthetic run
`analyze.py` fails explicitly when `--manifest` is absent, still the template,
has a missing/null field, a mismatching provenance hash or solver block, or
when any report lacks `environment.remote`. This offline subset does not
import or depend on #65's code.

## Campaign handoff (#87, batch only)

Not part of this issue and not to be run from this directory. Once
`2AMLogic/klayout-tools#2851` is resolved and a batch preflight succeeds:
generate the bench into a new directory, run each request with
`klt sim <request> --backend batch -o <outdir> --format json` (the flag must
be explicit; `klt` keeps single-corner units local by default), save each
report as `report_<tag>.json`, fill the manifest, then run `analyze.py
--manifest`. Hand-launched local `ngspice` grids are forbidden on the dispatch
hosts; a refused or failed submission is reported, never replaced by a local
fallback. The evidence directory, decision record and any verdict are #87's.

## Resumable batch driver (`run_batch.py`, #87)

```
python3 -I sim/trim-dense/run_batch.py --bench-dir <prepare.py out> \
    --out-dir sim/trim-dense/results/<UTC-stamp> [--limit N] [--only TAG] [--retry-failed]
```

Submits each `request_cXX.json` with `klt sim --backend batch -o <out>/jobs/<tag> --format json`
(never local), saves `reports/report_<tag>.json`, and appends one line per
submission (job id, receipt state, report status) to `ledger.jsonl`. Concurrency
is hard-capped at 2 (host rule). Re-running skips requests whose
`batch-receipt.json` is `done`; failed/errored ones are reported and only
re-submitted with `--retry-failed`. `--limit` lets a session run a bounded
slice. Tested with a fake `klt` (`test_harness.py`); no fleet job was run for the
driver itself. The 1536-job campaign (~32 s per job, 2 at a time) is still to run.
