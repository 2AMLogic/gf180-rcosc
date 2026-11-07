# Slice 10 (#87, `Part of #87`)

Ran `run_batch.py --limit 40` (concurrency cap 2) on the batch fleet (`uvx --from klayout-tools==0.9.0 klt`) against
the bench regenerated with the manifest's netlists and `--capacity-wait-s 1200`; its `provenance.json` hashed to
`manifest.json:provenance_sha256` (`d1d24253...`).

The invocation was stopped by the host's 10-minute background time limit before reaching `--limit 40`; the driver
was not resumed in this session. No process of this run is left running. Every submission recorded before the stop
is complete in the ledger (appended per job); nothing was resubmitted or overwritten.

Result: ledger now holds 289 of 1536 jobs, all `done`, 289 distinct tags, all submitted with `--backend batch`.
This slice: 28 done, 0 not done (`ext_ss_m40C_3p0V_c05..c20`; 12 of the intended 40 were not run). The
`ext_ff_85C_3p6V` curve is complete (256 codes); `ext_ss_m40C_3p0V` now covers `c00..c20`. Supersedes the counts in
`README.md` and earlier `SLICE-*.md` (append-only, left unedited).

No step, monotonicity or carry claim follows; 1247 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run this slice (no code changed).
