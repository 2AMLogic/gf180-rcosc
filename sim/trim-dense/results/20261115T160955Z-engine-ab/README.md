# #378 engine A/B run directory (COMPLETE: 47 paired jobs, verdict recorded)

Paired ngspice-46 vs ngspice-47 measurement for the version-mixed dense campaign
(`20261106T1115Z-campaign`, issue #87; the drift is tracked and resolved by
issue #378). **Append-only evidence directory.** Every A/B request is
byte-identical to the frozen campaign's request for the same tag once the
`engine_version` pin is removed, so the runner's simulator binary is the only
changed input. This directory makes no step, carry or monotonicity claim —
those belong to #87's `analyze.py` verdict.

## Verdict: (a) immaterial

The paired 46→47 `fosc` effect is bounded below the ratified half-LSB
(40/255 = 0.156863 %, DR-0003 Row 2), so per-curve version treatment of the
mixed campaign is defensible on measurement. Overall over 47 paired codes:
median **+0.0000 %**, mean **+0.0044 %**, min **−0.0889 %**, max **+0.1328 %**,
**0/47 pairs exceed the half-LSB**. Per curve (`comparison.json` has every pair):

| curve | n | median | mean | min | max | \|delta\| > half-LSB |
|---|---|---|---|---|---|---|
| `ext_tt_27C_3p3V`  | 16 | +0.0000 % | +0.0000 % | +0.0000 % | +0.0000 % | 0/16 |
| `ext_ss_m40C_3p0V` | 16 | +0.0000 % | +0.0012 % | +0.0000 % | +0.0192 % | 0/16 |
| `sch_ff_85C_3p6V`  | 15 | +0.0031 % | +0.0124 % | −0.0889 % | +0.1328 % | 0/15 |

- The extracted-netlist curves are numerically almost untouched: 31/32 codes
  reproduce bit-identically (delta exactly 0.0000 %); the one exception is
  `ext_ss` 0xE0 at +0.0192 %.
- `sch_ff` (schematic netlist, ff/85 C/3.6 V) shows small solver-path shifts,
  12/15 within ±0.07 % (13/15 within ±0.09 %); the three outside ±0.07 % are
  +0.1328 % (0x10), +0.1088 % (0xB2) and −0.0889 % (0x20).
  The max is 0.85× the half-LSB — below it, but this single point is why the
  verdict says "bounded below", not "zero": the campaign caveat for `sch_ff`
  should carry that number.
- Scale reference: `sim/mc-groundwork/README.md` measured **~0.4 %** for the
  ngspice **42→46** move on a different bench (~2.5× the half-LSB). The
  measured **46→47** effect is ~3× smaller again and never crosses the
  half-LSB. The campaign-level three-way choice does not need to be escalated:
  no re-run or successor campaign is justified by this measurement, and no
  follow-up decision issue is filed (the #378 acceptance criterion for verdict
  (b) does not trigger).

**`singular_matrix` deconfound (the `ext_ss` arm's purpose):** the v47 `ext_ss`
sample carries **0** `singular_matrix` diagnostics and 12/16 reports carry
`nonconvergence` — exactly matching the v46 reports for the same 16 codes
(12/16; the v46 full curve runs 216/256 `nonconvergence`, 0
`singular_matrix`). ngspice-47 on the same cell/corner does **not**
introduce the new warning class, so the `sch_ss` `singular_matrix` cluster is
not attributable to the simulator version alone — the cell/corner combination
(`sch` + ss) remains the differing factor. Diagnosis of that class is separate
work (#378 out of scope).

## Sample

16 codes per curve at a 0x10 stride across 0x00..0xF0 (`0x00, 0x10, …, 0xF0`;
spread, not one contiguous nibble), plus `sch_ff` boundary codes 0xB1, 0xB2,
0xB3 — 47 jobs total:

- `ext_tt_27C_3p3V` (16) and `ext_ss_m40C_3p0V` (16): all-ngspice-46 curves in
  the frozen campaign; the `ext` netlist is unchanged on `main`
  (`7afa433a…`), no recovery needed.
- `sch_ff_85C_3p6V` (15, all within the v46 half 0x00..0xB3): the one
  internally-split curve; the `sch` netlist was recovered at the frozen
  `258e5e76…` from commit `affc8a64` (main's DR-0039 copy `2ccc184e…` does not
  match).

## Method and provenance

- Bench: `prepare.py` with **`--engine-version-expected 47`**, which emits the
  request-level `engine_version: "47"` pin (klayout-tools#3041) into every
  request; `klt sim` checks it against the runner's reported version after the
  run (there is no pre-submit probe for batch). All 47 reports carried
  `engine_version: 47` — no `engine_version_unmet`.
- **Paired-design attestation** (`compare_engine.py attest`, run twice — for
  the generation-time bench and the submitted bench): all **1536** bench
  requests hash identically to the frozen campaign's
  `20261106T1115Z-campaign/provenance.json` requests once the pin key is
  removed; all 1536 testbench hashes identical. Bench regenerated from the
  canonical repo paths (recovered inputs above + `sim/pvt/pvt_sweep.py`
  recovered at `acfc7ff5…` from `2e166a59^`); `manifest.json:provenance_sha256`
  = `5f7e0196…` freezes that bench.
- Report audit (`compare_engine.py attest --ab-reports`): n=47, uniform
  `engine_version=47`, uniform `engine_build.binary_sha256 =
  39ca1adb826660324c3626f72bd946ec40704f0f3fc8e243c623f76e24b3eee2`, uniform
  `models_lib_sha256 = f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24`
  (the campaign's PDK models — PDK inputs unchanged), 47 distinct
  `environment.remote` job ids (aws-batch-fleet), all `status: pass`.
- Comparison: `compare_engine.py compare` (this repo) → `comparison.json`
  (per-code pairs, stats, half-LSB counts, per-curve diagnostic tallies).
- Driver: `run_batch.py --backend batch` per tag (one invocation per sampled
  tag; the substring `--only` filter is not repeatable), client
  `uvx --from klayout-tools==0.9.0 klt`, concurrency cap 2,
  `batch.capacity_wait_s=1200` in every request. No local ngspice was run and
  no process of this run outlived the session.
- Execution window: 2026-11-15T16:10:07Z … 17:39:53Z (~90 min wall, ~1–3.5
  min/job). 46 jobs ran under a sequential background driver; it was reaped by
  the session sandbox after 38 jobs (mid-`sch_ff` 0x70, no partial state) and
  the remaining 8 finished as foreground per-tag invocations — the driver's
  resume logic (ledger + receipts) deduplicated everything; no job was
  submitted twice (`attest` verifies 47 distinct job ids).
- Client klt 0.9.0 already supports the pin (verified before the run); the
  campaign's frozen manifest needed no change. Every A/B stderr carries the
  known multi-install `gf180mcuC` PDK-root warning (recorded in the issue; out
  of scope, and `models_lib_sha256` is uniform as in the campaign).

## Files

- `manifest.json` — frozen at `engine_version: "47"` (fills `manifest.template.json`
  conventions; `git_sha` = the commit carrying the #378 tooling used to
  generate the bench and run the jobs).
- `provenance.json` — the bench's generation provenance (1536 requests; only
  the 47 sampled tags were submitted).
- `jobs/<tag>/` — batch receipts + stderr; `reports/report_<tag>.json` — the
  47 reports; `ledger.jsonl` — one row per submission.
- `comparison.json` — the paired delta table and stats (machine-readable;
  `compare_engine.py compare --out-json` refuses to overwrite, so it is a
  single-shot artifact).

Resume (should more codes ever be needed): regenerate the bench per the recipe
above, then
`python3 -I sim/trim-dense/run_batch.py --bench-dir <bench> --out-dir <this dir> --klt 'uvx --from klayout-tools==0.9.0 klt' --only <tag>`.
