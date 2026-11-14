# Slice 41 (#87, `Part of #87`)

Ran `run_batch.py` as three sequential foreground calls of `--limit 14` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; each request carries `batch.capacity_wait_s=1200`).
The bench was regenerated with the manifest's netlists; its `provenance.json` hash was `d1d24253...`, identical to
`manifest.json:provenance_sha256`.

Result: ledger now holds 948 of 1536 jobs (948 distinct tags, no duplicates), all `done`, all submitted with
`--backend batch`. This slice: 42 done, 0 not done (`sch_ff_85C_3p6V`, codes after slice 40's c89, through cB3).
All three `ext` curves (768 jobs) are complete; `sch` has 180 of 768 jobs. No existing receipt was rewritten and no
local ngspice process was run. No step or carry claim is made here; that is for `analyze.py` once the curves are complete.
Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).

588 jobs remain (`sch` only), then `analyze.py --manifest` and the verdict DR (next free number; renumber if taken at merge).
`test_harness.py` was not re-run (no code changed).
