# Slice 45 (#87, `Part of #87`)

Attempted the whole remaining `sch_tt_27C_3p3V` curve in one session:
`run_batch.py --limit 256` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; requests carry
`batch.capacity_wait_s=1200`). The run's preflight line: `manifest preflight: OK
(provenance_sha256 d1d24253..., netlists {ext=7afa433a..., sch=258e5e76...})`.
Result: **32 submitted and done, then the slice was stopped in-session** at
fleet-capacity saturation; 224 requests remain. No local ngspice was run and no
process of this run outlived the session.

**Bench regenerated from the frozen inputs** exactly as in slice 44 (same two
recoveries from git history; both restored to HEAD before committing — only
campaign-dir files changed in this PR):

- `sch` netlist `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice`
  recovered at the frozen `258e5e76...` from commit `affc8a64` (main's
  DR-0039-regenerated copy `2ccc184e...` does not match). `ext` =
  `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` unchanged (`7afa433a...`).
- `sim/pvt/pvt_sweep.py` recovered at the frozen `acfc7ff5...` (main's copy
  changed in `2e166a59` to `db478e2b...`).

The regenerated bench's `provenance.json` hashed `d1d24253...`, byte-identical
to `manifest.json:provenance_sha256`.

**Why stopped:** the first 16 jobs ran at ~39 s/job; from ~14:25Z the shared
fleet's vCPU budget saturated (other sweeps competing) and throughput degraded
to ~5 min per job, with `capacity_wait_s=1200` absorbing queue waits. At that
rate the remaining 224 jobs needed ~18 h of wall — beyond one session. The
32nd done job is 14:46:39Z; the driver and its two in-flight `klt` clients were
stopped cleanly (SIGTERM) and verified gone before committing.

**State after this slice:** ledger holds **1312 of 1536 jobs, all `done`**
(1312 distinct tags, no duplicates). Remaining: `sch_tt_27C_3p3V` codes 0x1F
and 0x21..0xFF (224 jobs). Done codes this curve: 0x00..0x1E and 0x20. The two
interrupted submits (`c1F` mid-flight, `c21` never started) have no done
receipt, no report and no ledger row; their partial job dir was removed and the
driver's resume (`is_done` + attempted-set checks) will resubmit them on the
next run. **Five of six curves are complete** (all three `ext` 768, `sch_ff`
256, `sch_ss` 256); `sch_tt` is 32/256.

Audit over all 32 new reports: every report is `status: pass` and carries
`environment.remote` (aws-batch-fleet, 32 distinct job ids, receipts on disk),
every report's `environment.netlist_closure` contains the frozen manifest `sch`
DUT hash, and `models_lib_sha256` is uniform (`f6f4a96e...`, the manifest's PDK
models). All 32 are ngspice-47, so `sch_tt` is (so far) uniformly 256-job-47.
Per committed reports the campaign version split is now: all 768 `ext` jobs on
46; `sch_ff` mixed (180x46 + 76x47); `sch_ss` 256x47; `sch_tt` 32x47 so far.
Same PDK models hash throughout. No existing receipt was rewritten;
`check-append-only.sh` passes against the merge base; `test_harness.py` still
passes (36 tests).

**The campaign-level question recorded in SLICE-44 is unchanged and now
gating:** the campaign is version-mixed across curves, so
`analyze.py --manifest` over the full tree reports `run_errors` (mixed
simulator versions vs manifest `engine_version: 46`) and labels the output
`PROVENANCE INCOMPLETE - NOT USABLE AS EVIDENCE` — under the frozen tooling no
verdict DR can be written from this tree as-is. Resolution (re-run policy for
`sch_ff` — or a full successor campaign on 47 — per-curve treatment, or another
properly frozen successor decision) remains a campaign-level call for the
issue's next revision; no unilateral change to the frozen manifest was made.

Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only,
left unedited).
