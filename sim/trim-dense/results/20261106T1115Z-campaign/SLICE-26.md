# Slice 26 (#87, `Part of #87`)

Ran `run_batch.py --limit 16` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists; its
`provenance.json` was byte-identical to the committed one (`d1d24253...`, `manifest.json:provenance_sha256`).
The run hit the 10-minute session cap after 14 of the 16 requested jobs (~42 s/job this slice) and was stopped by the
harness; no local process of this run is left running, and the two unsubmitted requests stay pending for the next slice.

Result: ledger now holds 541 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 14 done, 0 not done (`ext_tt_27C_3p3V_c0F..c1C`). `ext_tt_27C_3p3V` now covers c00..c1C.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts for all 14 are committed in this slice.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete. No resubmissions.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

995 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
