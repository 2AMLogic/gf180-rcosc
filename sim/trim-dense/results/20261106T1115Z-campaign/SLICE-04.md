# Slice 4 (#87, `Part of #87`)

Ran `run_batch.py --limit 15` on the batch fleet (`uvx --from klayout-tools==0.9.0 klt`, concurrency 2) against the bench
regenerated with the manifest's netlists; its `provenance.json` hashed to `manifest.json:provenance_sha256`
(`d1d24253...`). Each request carries `batch.capacity_wait_s = 1200`. Wall time ~9.7 min for 15 jobs (~39 s/job, 4m18s
user CPU on this host for the klt clients).

Result: ledger now holds 77 of 1536 jobs (`ext_ff_85C_3p6V_c00..c4C`), all submitted with `--backend batch`; this slice:
15 done, 0 not done. Supersedes the counts in `README.md`, `SLICE-02.md` and `SLICE-03.md` (append-only, left unedited).
No step, monotonicity or carry claim follows; 1459 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
