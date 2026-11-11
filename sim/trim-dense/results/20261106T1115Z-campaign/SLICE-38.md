# Slice 38 (#87, `Part of #87`)

Ran `run_batch.py` twice (`--limit 14`, then `--limit 16`; concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`) against the bench regenerated with the manifest's
netlists and `--capacity-wait-s 1200`; its `provenance.json` hash was `d1d24253...`, identical to
`manifest.json:provenance_sha256`. Both runs were foreground; no local process of this run is left running.

Result: ledger now holds 822 of 1536 jobs (822 distinct tags), all `done`, all submitted with `--backend batch`.
This slice: 30 done, 0 not done (`sch_ff_85C_3p6V` c18..c35).
All three `ext` curves (768 jobs) are complete; `sch` has 54 of 768 jobs.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts are committed; no existing receipt was rewritten.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

714 jobs remain (`sch` only), then `analyze.py --manifest` and the verdict DR (0030, renumber if taken).
`test_harness.py` was not re-run (no code changed).
