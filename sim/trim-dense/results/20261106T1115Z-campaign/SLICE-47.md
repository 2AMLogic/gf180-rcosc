# Slice 47 (#87, `Part of #87`) — campaign submission complete: 1536/1536

This slice completed the `sch_tt_27C_3p3V` curve and reconciled a parallel
session, bringing the campaign to **1536 of 1536 jobs done**. All jobs ran on
the Spot batch fleet (`uvx --from klayout-tools==0.9.0 klt`,
`KLT_SIM_BACKEND=batch`, `--backend batch` per request, requests carry
`batch.capacity_wait_s=1200`, concurrency 2). No local ngspice was run and no
process of this run outlived the session.

## What landed here

Two batches of submissions against the same frozen bench, plus the merge
reconciliation:

1. **A parallel builder session in this worktree** (uncommitted until this
   slice; first done `sch_tt_27C_3p3V_c21` 2026-11-15T16:16:55Z, last
   `cF1` 19:09:04Z): 210 done codes `c1F`, `c21..cF1`, plus one
   `no-receipt` attempt on `c23` at 16:39:56Z that a retry then measured
   successfully (both rows are in the ledger, append-only).
2. **This session's final slice** (14 done, `cF2..cFF`, 23:47–23:54:56Z,
   ~34 s/job at concurrency 2; last job `klt-sim-10aa8f81e8f9`).

Both ran `run_batch.py` against the bench regenerated from the frozen inputs
exactly as in slices 44/45/46 (`sch` netlist recovered at `258e5e76...` from
commit `affc8a64`; `sim/pvt/pvt_sweep.py` at `acfc7ff5...` from `2e166a59^`;
`ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` unchanged at `7afa433a...`).
The regenerated `provenance.json` hashed `d1d24253...`, byte-identical to
`manifest.json:provenance_sha256`; the driver's preflight printed
`manifest preflight: OK (...)`.

## Reconciliation with slice 46 (merged from `origin/main` mid-flight)

Slice 46 (PR #394, another session) had already measured 14 of the same
codes (`c1F`, `c21..c24`, `c26..c2E`) from the same 1312-done base. Those 14
tags are therefore **dual-measured**; resolution, append-only throughout:

- `reports/report_<tag>.json`, `jobs/<tag>/batch-receipt.json` and
  `jobs/<tag>/stderr.txt` for the 14 tags keep the **already-landed slice-46
  evidence** (main's job ids); this branch's duplicate submissions for those
  tags are recorded as extra `done` ledger rows only. No existing receipt,
  report or ledger row was rewritten or removed.
- `ledger.jsonl` = slice-46's 1326 rows + this branch's 225 post-base rows,
  chronological: **1551 rows = 1550 `done` + 1 `no-receipt`**, **1536
  distinct done tags**, reports directory == done tags exactly.
- Slice 46's interrupted `c25` (fleet job `klt-sim-f741e4908b83`, queued and
  abandoned) was re-measured here; its done receipt is single (this
  branch's).

## Final campaign state (audited)

- 1536/1536 done; every report `status: pass` and carries
  `environment.remote` (aws-batch-fleet); `models_lib_sha256` uniform
  (`f6f4a96e...`). 14 tags dual-measured as disclosed above.
- Simulator-version tally per curve (the known drift, slice 42+): `ext` all
  768 on ngspice-46; `sch_ff` mixed (180x46 + 76x47); `sch_ss` 256x47;
  `sch_tt` 256x47.
- `sim/check-append-only.sh 20846a3d..HEAD` passes.
- `test_harness.py`: 38/39 pass. The one failure
  (`test_no_measured_artifacts_in_tree`) is caused by the **untracked**
  local-only `results/20261105T080858Z-probe/` directory (a Nov 5 probe with
  no `README.md`, never committed; absent from any clean checkout, so CI is
  unaffected). Not touched by this slice.

## `analyze.py --manifest` status (run to `/tmp`, deliberately NOT committed)

The harness gate (`test_no_measured_artifacts_in_tree`) forbids analyzer
outputs in the tree until the verdict PR adds them deliberately, so the
output was produced for the record only. Banner and run errors, verbatim:

    PROVENANCE INCOMPLETE - NOT USABLE AS EVIDENCE
    - RUN ERROR: mixed simulator versions across reports: ['46', '47']
    - RUN ERROR: report engine_version ['46', '47'] != manifest engine_version '46'

Per-curve, all six curves are individually `OK` (256/256 valid points each);
the only blockers are the two campaign-level version errors above. Analyzer
headline facts (its output, not a verdict): the four DR-0021 carry
transitions appear as negative steps in **all six** curves — `0x7F->0x80`
-5.76..-10.48 %, `0xBF->0xC0`, `0xDF->0xE0`, `0xEF->0xF0` negative
throughout; worst positive steps +1.06..+2.44 % (`0xFB->0xFC` band except
`ext` curves' `0xF9->0xFA`/`0xF5->0xF6`/`0x9F->0xA0`); mean step 2.0-2.7x
the ratified 0.3137 %/code; per-curve `steps.csv`/`summary.md` are in the
`/tmp` output and reproducible from the committed tree with the frozen
tooling.

## What remains (campaign-level call, not made here)

The verdict DR cannot be written from this tree under the frozen tooling
while the mixed-version `run_errors` stand. The measured basis for accepting
per-curve version treatment now exists: the paired ngspice 46 vs 47 engine
A/B (`results/20261115T160955Z-engine-ab/`, issue #378, closed; verdict (a)
immaterial, 0/47 pairs exceed the half-LSB). Ratifying that for #87 — or
choosing a successor campaign — changes the frozen manifest/tooling
expectations and is the issue's next revision to make; no unilateral change
was made here, consistent with slices 43-46.

Supersedes the counts in `README.md` and earlier `SLICE-*.md` (append-only,
left unedited).
