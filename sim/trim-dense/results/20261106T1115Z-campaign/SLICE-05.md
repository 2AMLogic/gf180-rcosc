# Slice 5 (#87, `Part of #87`)

Ran `run_batch.py --limit 40` on the batch fleet (`uvx --from klayout-tools==0.9.0 klt`, concurrency 2) against the bench
regenerated with the manifest's netlists and `--capacity-wait-s 1200`; its `provenance.json` hashed to
`manifest.json:provenance_sha256` (`d1d24253...`). Wall time ~25 min for 40 jobs (~37 s/job).

Result: ledger now holds 117 of 1536 jobs (`ext_ff_85C_3p6V_c00..c74`), all submitted with `--backend batch`; this slice:
40 done, 0 not done. Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).
No step, monotonicity or carry claim follows; 1419 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
