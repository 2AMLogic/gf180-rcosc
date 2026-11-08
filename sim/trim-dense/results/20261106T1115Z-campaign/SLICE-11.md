# Slice 11 (#87, `Part of #87`)

Ran `run_batch.py --limit 16` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` hashed to `manifest.json:provenance_sha256` (`d1d24253...`).
Wall time 8m28s (~32 s/job). No local process of this run is left running.

Result: ledger now holds 305 of 1536 jobs, all `done`, 305 distinct tags, all submitted with `--backend batch`.
This slice: 16 done, 0 not done (`ext_ss_m40C_3p0V_c21..c30`, hex codes 0x21..0x30, including the two resubmitted jobs below).
`ext_ss_m40C_3p0V` now covers `c00..c30`.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

## Resubmission of the two slice-10 in-flight jobs

SLICE-10 disclosed `ext_ss_m40C_3p0V_c21` and `_c22` as submitted but never retrieved (receipt `state: null`).
The driver treats a non-`done` receipt as pending, so this slice **resubmitted** both and overwrote their
receipts (`null` -> `done`; narrow exceptions added to `sim/append-only-exceptions.txt`). The superseded
fleet job ids (both observed `done` on the fleet in SLICE-10, outputs never downloaded) were:

| tag | superseded job id | new job id (see receipt) |
|---|---|---|
| `ext_ss_m40C_3p0V_c21` | `klt-sim-ecbbb910a191` | `klt-sim-f363ebb20196` |
| `ext_ss_m40C_3p0V_c22` | `klt-sim-232cc73f7292` | `klt-sim-8ba23351e823` |

So these two tags were each submitted twice; the ledger line is the second submission.

No step, monotonicity or carry claim follows; 1231 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
`test_harness.py` was not re-run (no code changed; `pytest` is not installed on this host).
