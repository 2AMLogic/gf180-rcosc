# Slice 8 (#87, `Part of #87`)

Ran `run_batch.py --limit 18` as a single invocation (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` hashed to `manifest.json:provenance_sha256` (`d1d24253...`).
Wall time 8m01s (~27 s/job).

Result: ledger now holds 221 of 1536 jobs (`ext_ff_85C_3p6V_c00..cDC`), all `done`, 221 distinct tags, all submitted
with `--backend batch`; this slice: 18 done, 0 not done. Supersedes the counts in `README.md` and earlier
`SLICE-*.md` (append-only, left unedited).

No step, monotonicity or carry claim follows; 1315 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run this slice (no code changed; `pytest` is not installed on this host).
