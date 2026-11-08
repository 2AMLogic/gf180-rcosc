# Slice 12 (#87, `Part of #87`)

Ran `run_batch.py --limit 16` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` hashed to `manifest.json:provenance_sha256` (`d1d24253...`).
Wall time 7m03s (~26 s/job). No local process of this run is left running.

Result: ledger now holds 321 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 16 done, 0 not done (`ext_ss_m40C_3p0V_c31..c40`, hex codes 0x31..0x40; every report status `pass`).
`ext_ss_m40C_3p0V` now covers `c00..c40`. No resubmissions in this slice.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

No step, monotonicity or carry claim follows; 1215 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
