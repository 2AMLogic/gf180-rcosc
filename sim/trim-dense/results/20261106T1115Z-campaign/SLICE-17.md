# Slice 17 (#87, `Part of #87`)

Ran `run_batch.py --limit 16` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` was byte-identical to the committed one (`d1d24253...`,
`manifest.json:provenance_sha256`). Wall time 8m46s (~33 s/job). No local process of this run is left running.

Result: ledger now holds 401 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 16 done, 0 not done (`ext_ss_m40C_3p0V_c81..c90`, hex codes 0x81..0x90; every report status `pass`,
every report carries `environment.remote`).
`ext_ss_m40C_3p0V` now covers `c00..c90`. No step or carry claim is made here; that is for `analyze.py` once the
curve is complete. No resubmissions in this slice.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

No step, monotonicity or carry claim follows; 1135 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
