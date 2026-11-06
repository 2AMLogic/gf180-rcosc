# #87 trim-dense campaign run directory (PARTIAL: frozen manifest + live driver check only)

Append-only run directory for the 1536-request dense campaign (256 codes x 3 corners x {sch, ext}).
**Only 2 of 1536 jobs have run** (`ext_ff_85C_3p6V_c00`, `_c01`), as the live `--limit 2` check of
`run_batch.py`. No trim-step, monotonicity or carry claim follows; the campaign and the verdict DR are still open.

- `manifest.json`: frozen execution manifest (netlist hashes, solver settings, simulator version, `provenance.json`
  hash). Later slices append into this directory with the same bench; never overwrite a `done` job.
- Netlists: `ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` (P3, MBUFN W=1u). `sch` =
  `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice` is **pre-P3 trim sizing** (MBUFN W=1u but not DR-0023 P3), so
  `sch` carry verdicts are for that named netlist only; no post-fix P3 schematic variant was traced.
- `pdk_revision` is `unknown` (runner-side open_pdks SOURCES not exposed to the client); `models_lib_sha256` is in each report.
- Driver check: receipts (`jobs/<tag>/batch-receipt.json`), `reports/report_<tag>.json` and `ledger.jsonl` match the
  layout `analyze.py --reports-dir reports --manifest manifest.json` reads (it accepted the manifest; the 6 curves
  are INCOMPLETE as expected). Both reports carry `environment.remote` (job ids in `ledger.jsonl`).
- Client: `uvx --from klayout-tools==0.9.0 klt` (matches runner 0.9.0). Raw per-corner dirs are git-ignored.
- Resume: `python3 -I sim/trim-dense/run_batch.py --bench-dir <prepare.py out, same netlists> --out-dir <this dir> --klt 'uvx --from klayout-tools==0.9.0 klt' --limit N`
  (bench regenerated with `prepare.py --schematic-netlist ... --extracted-netlist ...` and default settings; its
  `provenance.json` must hash to `manifest.json:provenance_sha256`).
