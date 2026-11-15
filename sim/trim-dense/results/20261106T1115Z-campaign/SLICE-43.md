# Slice 43 (#87, `Part of #87`)

Ran `run_batch.py --limit 128` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; requests carry `batch.capacity_wait_s=1200`).
The run's preflight line: `manifest preflight: OK (provenance_sha256 d1d24253..., netlists {ext=7afa433a...,
sch=258e5e76...})`. Result: 128 submitted, 128 done, 0 not done (exit 0, ~78 min wall). No local ngspice was run
and no process of this run outlived the session.

**Bench regenerated from the frozen netlists, not from `main`:** the `sch` input was again recovered from git
history by its manifest hash (`258e5e76...`, commit `affc8a64`; `main`'s DR-0039-regenerated copy is
`2ccc184e...`); `ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` is unchanged (`7afa433a...`). The regenerated
bench's `provenance.json` hashed `d1d24253...`, byte-identical to `manifest.json:provenance_sha256`.

Result: ledger now holds 1152 of 1536 jobs (1152 distinct tags, no duplicates), all `done`, all submitted with
`--backend batch`. This slice: 128 done (`sch_ss_m40C_3p0V` codes 0x00..0x7F). All three `ext` curves (768),
`sch_ff_85C_3p6V` (256) and `sch_ss` through 0x7F are complete. Audit over all 128 new reports: every report
carries `environment.remote` (aws-batch-fleet, 128 distinct job ids, receipts on disk), every report's
`environment.netlist_closure` contains the variant's frozen manifest DUT hash, and `models_lib_sha256` is
uniform (`f6f4a96e...`, the manifest's PDK models). No existing receipt was rewritten; `check-append-only.sh`
passes.

**Fleet engine drift (finding, not introduced here):** the runner image's ngspice moved 46 -> 47 mid-campaign.
Per committed reports: all 768 `ext` jobs and `sch_ff`'s first 180 jobs are ngspice-46; `sch_ff`'s last 76 jobs
(slice 42) and this slice's 128 `sch_ss` jobs are ngspice-47. Same PDK models hash throughout. Consequence:
`analyze.py --manifest` over the current tree reports `run_errors` ("mixed simulator versions across reports:
['46','47']" and "report engine_version ['46','47'] != manifest engine_version '46'"), so `all_curves_valid`
is False today and the final verdict PR cannot produce a clean manifest-level analysis as things stand. Each
individual curve is version-homogeneous except `sch_ff` (180x46 + 76x47). This predates slice 43 (first fired
in slice 42's 76 jobs); slice 43 continues on the current runner and does not widen the split beyond what
slice 42 started. Resolution (re-run policy, per-curve treatment, or a properly frozen successor decision) is
a campaign-level call for the issue's next revision; no unilateral change to the frozen manifest was made.

384 jobs remain (`sch_ss_m40C_3p0V` codes 0x80..0xFF: 128, `sch_tt_27C_3p3V`: 256), then `analyze.py
--manifest` and the verdict DR (next free number; renumber if taken at merge). No step or carry claim is made
here; that is for `analyze.py` once the curves are complete and the version question is resolved. Supersedes
the counts in `README.md` and earlier `SLICE-*.md` (append-only, left unedited).
