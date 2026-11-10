# Slice 27 (#87, `Part of #87`)

Ran `run_batch.py --limit 11` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists; its
`provenance.json` was byte-identical to the committed one (`d1d24253...`, `manifest.json:provenance_sha256`).
All requests carry `capacity_wait_s: 1200`. The run finished inside the session cap; no local process of this run is left running.

Result: ledger now holds 552 of 1536 jobs, all `done`, all submitted with `--backend batch`.
This slice: 11 done, 0 not done (`ext_tt_27C_3p3V` c1D..c27, including c1E). `ext_tt_27C_3p3V` now covers c00..c27.
Per-job `reports/report_<tag>.json` and `jobs/<tag>/` receipts are committed; reports carry `environment.remote`.

Disclosure (resubmission): `ext_tt_27C_3p3V_c1E` was re-run as a new fleet job `klt-sim-b1acb3a2ee0c` (done, pass), as
announced in `SLICE-26.md`. The slice-26 orphaned submission `klt-sim-b49b3afb561b` was never ledgered and its fleet state was
never collected. The driver rewrote `jobs/ext_tt_27C_3p3V_c1E/batch-receipt.json` in place, so the original orphan receipt is
preserved verbatim as `batch-receipt.orphan-klt-sim-b49b3afb561b.json` and the in-place rewrite is listed in
`sim/append-only-exceptions.txt`. The orphan is not counted in the 552.
No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

984 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed).
