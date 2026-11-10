# Slice 37 (#87, `Part of #87`)

Ran `run_batch.py --limit 36` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`) against the bench regenerated with the manifest's
netlists and `--capacity-wait-s 1200`; its `provenance.json` hash was `d1d24253...`, identical to
`manifest.json:provenance_sha256`. The run was a bounded in-turn poll; no local process of this run is left running.

Result: ledger now holds 792 of 1536 jobs (792 distinct tags), all `done`, all submitted with `--backend batch`.
This slice: 36 done, 0 not done (`ext_tt_27C_3p3V` cF4..cFF = 12, then `sch_ff_85C_3p6V` c00..c17 = 24).
All three `ext` curves (768 jobs) are now complete; `sch` has 24 of 768 jobs.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts are committed; no existing receipt was rewritten.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

744 jobs remain (`sch` only), then `analyze.py --manifest` and the verdict DR (0030, renumber if taken).
`test_harness.py` was not re-run (no code changed).
