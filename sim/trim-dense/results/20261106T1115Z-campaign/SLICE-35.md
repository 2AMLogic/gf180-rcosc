# Slice 35 (#87, `Part of #87`)

Ran `run_batch.py --limit 36` (concurrency cap 2) in the foreground (bounded in-turn poll) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`) against the bench regenerated with the manifest's
netlists and `--capacity-wait-s 1200`; its `provenance.json` hash was `d1d24253...`, identical to
`manifest.json:provenance_sha256`. No local process of this run is left running.

Result: ledger now holds 720 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 36 done, 0 not done (`ext_tt_27C_3p3V` c(AC..CF)). Throughput was ~45 s/job at concurrency 2.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts are committed; no existing receipt was rewritten.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

816 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
