# Slice 44 (#87, `Part of #87`)

Ran `run_batch.py --limit 128` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; requests carry
`batch.capacity_wait_s=1200`). The run's preflight line: `manifest preflight: OK
(provenance_sha256 d1d24253..., netlists {ext=7afa433a..., sch=258e5e76...})`.
Result: 128 submitted, 128 done, 0 not done (exit 0, ~73 min wall). No local
ngspice was run and no process of this run outlived the session.

**Bench regenerated from the frozen inputs, which now include `sim/pvt/pvt_sweep.py`:**
`main` changed two of the files whose content the frozen `provenance.json` hashes, so both were
recovered from git history before `prepare.py` and the worktree files restored to HEAD before
committing (only campaign-dir files changed in this PR):

- `sch` netlist `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice`: main's
  DR-0039-regenerated copy is `2ccc184e...`; recovered at the frozen `258e5e76...`
  from commit `affc8a64` (same recovery as slice 43). `ext` =
  `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` is unchanged (`7afa433a...`).
- `sim/pvt/pvt_sweep.py`: `main`'s copy changed in `2e166a59` (PR #380) to
  `db478e2b...`; recovered at the frozen `acfc7ff5...` (identical at the manifest
  freeze `d294c6b` and at `affc8a64`). Its sha256 is recorded in
  `provenance.json:pvt_grid_source_sha256`, so a bench regenerated against
  current `main` would no longer reproduce the frozen `provenance_sha256` and
  the driver's frozen-manifest gate would (correctly) refuse the run.

The regenerated bench's `provenance.json` hashed `d1d24253...`, byte-identical to
`manifest.json:provenance_sha256` (provenance embeds every request/testbench
sha256, so byte-identity covers the whole request set).

Result: ledger now holds 1280 of 1536 jobs (1280 distinct tags, no duplicates),
all `done`, all submitted with `--backend batch`. This slice: 128 done
(`sch_ss_m40C_3p0V` codes 0x80..0xFF) — **the `sch_ss` curve is complete**. Five
of six curves are done (all three `ext` 768, `sch_ff` 256, `sch_ss` 256); only
`sch_tt_27C_3p3V` (256 jobs) remains, then `analyze.py --manifest` and the
verdict DR (next free number at merge). Audit over all 128 new reports: every
report is `status: pass` and carries `environment.remote` (aws-batch-fleet, 128
distinct job ids, receipts on disk), every report's `environment.netlist_closure`
contains the frozen manifest `sch` DUT hash, and `models_lib_sha256` is uniform
(`f6f4a96e...`, the manifest's PDK models). No existing receipt was rewritten;
`check-append-only.sh` passes; `test_harness.py` still passes (36 tests).

**Fleet engine drift, updated:** all 128 new reports are ngspice-47, so the
`sch_ss` curve is now uniformly 256x47. Per committed reports the split is now:
all 768 `ext` jobs on 46; `sch_ff` mixed (180x46 + 76x47, split began in slice
42); `sch_ss` and (unless the image moves again) the remaining `sch_tt` on 47.
Same PDK models hash throughout. `analyze.py --manifest` over the current tree
still reports `run_errors` (campaign-level mixed versions; manifest
`engine_version: 46`), so `all_curves_valid` stays False as of this slice. The
situation is narrower than at slice 43: after `sch_tt` lands on the current
image, `sch_ff` would be the only version-mixed curve. Resolution (re-run
policy for `sch_ff`, per-curve treatment, or a properly frozen successor
decision) remains a campaign-level call for the issue's next revision; no
unilateral change to the frozen manifest was made.

Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only,
left unedited).
