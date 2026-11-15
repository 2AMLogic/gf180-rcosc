# Slice 42 (#87, `Part of #87`)

Ran `run_batch.py --limit 64` (concurrency cap 2) in the foreground on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; requests carry `batch.capacity_wait_s=1200`).
The run's preflight line: `manifest preflight: OK (provenance_sha256 d1d24253..., netlists {ext=7afa433a...,
sch=258e5e76...})`. Result: 64 submitted, 64 done, 0 not done. No local ngspice was run and no process of this
run outlived the session.

**Bench regenerated from the frozen netlists, not from `main`:** DR-0039 (2026-11-12) regenerated the tracked
bench copy `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice` on `main` (now `2ccc184e...`), so the `sch`
input was recovered from git history by its manifest hash (`258e5e76...`, commit `affc8a64`) before running
`prepare.py`; `ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` is unchanged on `main` (`7afa433a...`). The
regenerated bench's `provenance.json` hashed `d1d24253...`, byte-identical to `manifest.json:provenance_sha256`.

**Driver gate landed in this PR** (was left uncommitted by an interrupted session, completed and tested here):
`run_batch.py` refuses to submit anything when the campaign holds a frozen `manifest.json` that the bench no
longer reproduces (netlist sha256 per variant, `provenance.json` hash). 5 new synthetic tests in
`test_harness.py`; full harness `36 passed` (`uv run --with pytest -- python3 -m pytest -p no:cacheprovider
sim/trim-dense/test_harness.py`). The gate's live first fire is this slice's preflight line above.

Result: ledger now holds 1024 of 1536 jobs (1024 distinct tags, no duplicates), all `done`, all submitted with
`--backend batch`. This slice: 64 done (the first 64 pending `sch_ff_85C_3p6V` codes; the interrupted session's
12 jobs cB4..cC0 minus cBE were already on disk and are committed here, audited along with every other report).
`sch_ff_85C_3p6V` is now complete (256/256) and all three `ext` curves are complete (768). Audit over all 1024
committed reports: every report's `environment.netlist_closure` DUT hash equals the variant's frozen manifest
hash, and every report carries `environment.remote`. No existing receipt was rewritten.

512 jobs remain (`sch_ss_m40C_3p0V` 256, `sch_tt_27C_3p3V` 256), then `analyze.py --manifest` and the verdict DR
(next free number; renumber if taken at merge). No step or carry claim is made here; that is for `analyze.py`
once the curves are complete. Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only, left
unedited).
