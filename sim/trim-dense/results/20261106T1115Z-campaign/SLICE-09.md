# Slice 9 (#87, `Part of #87`)

Ran `run_batch.py --limit 40` as a single invocation (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` hashed to `manifest.json:provenance_sha256` (`d1d24253...`).
Wall time 17m34s (~26 s/job).

Result: ledger now holds 261 of 1536 jobs, all `done`, 261 distinct tags, all submitted with `--backend batch`.
This slice: 40 done, 0 not done. The `ext_ff_85C_3p6V` curve is now complete (`c00..cFF`, 256 codes); the
`ext_ss_m40C_3p0V` curve has started (`c00..c04`). Supersedes the counts in `README.md` and earlier `SLICE-*.md`
(append-only, left unedited).

No step, monotonicity or carry claim follows; 1275 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run this slice (no code changed).
