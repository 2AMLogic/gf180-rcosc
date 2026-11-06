# Slice 3 (#87, `Part of #87`)

Ran `run_batch.py --limit 20` on the batch fleet (`uvx --from klayout-tools==0.9.0 klt`, concurrency 2) against a bench
regenerated with the manifest's netlists; its `provenance.json` hashed to `manifest.json:provenance_sha256`
(`d1d24253...`). Wall time 11.4 min for 20 jobs (~34 s/job, so the full 1536 is ~14 h of fleet time).

Result: ledger now holds 62 of 1536 jobs (`ext_ff_85C_3p6V_c00..c61`), all submitted with `--backend batch`; this slice:
20 done, 0 not done. Supersedes the counts in `README.md` and `SLICE-02.md` (append-only, left unedited). No step,
monotonicity or carry claim follows; 1474 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
