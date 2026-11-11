# Slice 39 (#87, `Part of #87`)

Ran `run_batch.py` (`--limit 60`, concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; each request carries
`batch.capacity_wait_s=1200`) against the bench regenerated with the manifest's netlists; its
`provenance.json` hash was `d1d24253...`, identical to `manifest.json:provenance_sha256`.
The foreground session hit the tool's time limit and the run was stopped after 42 of the 60 requested jobs
(resumable by design; no local process of this run is left running).

Result: ledger now holds 864 of 1536 jobs (864 distinct tags), all `done`, all submitted with `--backend batch`.
This slice: 42 done, 0 not done (`sch_ff_85C_3p6V` c36..c5F).
All three `ext` curves (768 jobs) are complete; `sch` has 96 of 768 jobs.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts are committed; no existing receipt was rewritten.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

672 jobs remain (`sch` only), then `analyze.py --manifest` and the verdict DR (next free number; 0031 is taken at merge time of this slice).
`test_harness.py` was not re-run (no code changed).

Interrupted in flight when the run was stopped: `sch_ff_85C_3p6V_c60` (submitted as batch job
`klt-sim-19c6ad0c70ab`, no result read) and `_c61` (no receipt). Neither is in the ledger or counted; their
untracked job dirs were removed, so the next slice resubmits both.
