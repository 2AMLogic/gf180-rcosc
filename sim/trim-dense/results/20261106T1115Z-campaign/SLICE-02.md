# Slice 2 (#87, `Part of #87`)

Ran `run_batch.py --limit 40` on the batch fleet (`uvx --from klayout-tools==0.9.0 klt`, concurrency 2) against a bench
regenerated with the manifest's netlists; its `provenance.json` hashed to `manifest.json:provenance_sha256`
(`d1d24253...`). Wall time 19 min for 40 jobs (~28 s/job, so the full 1536 is ~12 h, not the ~7 h PR #241 estimated).

Result: ledger now holds 42 of 1536 jobs (`ext_ff_85C_3p6V_c00..c41`), all `state: done`, `report_status: pass`.
`README.md` in this directory still says "2 of 1536" (written before this slice; append-only, left unedited): this
file supersedes it. No step, monotonicity or carry claim follows; 1494 jobs remain, then `analyze.py --manifest` and the
verdict DR (0030).
