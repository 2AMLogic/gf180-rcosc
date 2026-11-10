# Slice 25 (#87, `Part of #87`)

Ran `run_batch.py --limit 16` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` was byte-identical to the committed one (`d1d24253...`,
`manifest.json:provenance_sha256`). Wall time 9m21s for 16 jobs (~35 s/job). No local process of this run is left running.

Result: ledger now holds 527 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 16 done, 0 not done (`ext_ss_m40C_3p0V_cFF`, then `ext_tt_27C_3p3V_c00..c0E`).
`ext_ss_m40C_3p0V` is now complete (c00..cFF, 256 codes); `ext_tt_27C_3p3V` has started (c00..c0E).
The per-job `reports/report_<tag>.json` files for all 16 are committed in this slice.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete. No resubmissions in this slice.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

1009 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
