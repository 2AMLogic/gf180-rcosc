# Slice 46 (#87, `Part of #87`)

Ran `run_batch.py --limit 224` (concurrency cap 2) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`, `KLT_SIM_BACKEND=batch`; requests carry
`batch.capacity_wait_s=1200`) against the bench regenerated from the frozen
inputs exactly as in slices 44/45 (`sch` netlist recovered at `258e5e76...`
from commit `affc8a64`, `sim/pvt/pvt_sweep.py` at `acfc7ff5...` from
`2e166a59^`, `ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice` unchanged at
`7afa433a...`). The regenerated bench's `provenance.json` hashed
`d1d24253...`, byte-identical to `manifest.json:provenance_sha256`; the
driver's preflight printed `manifest preflight: OK`.

Result: **14 submitted and done**, then the slice was stopped in-session
(SIGTERM to the driver and its two in-flight `klt` clients; both verified gone,
no local process of this run outlived the session, no local ngspice was run).
Fleet-side throughput was capacity-degraded the whole time (~110-145 s per job
wall clock end to end at concurrency 2, vs ~26 s/job in slice 9), so the full
remaining curve did not fit the session; same saturation slice 45 hit.

**State after this slice:** ledger holds **1326 of 1536 jobs, all `done`,
all `report_status: pass`, 1326 distinct tags** (no duplicates). Five of six
curves complete (all three `ext` 768, `sch_ff` 256, `sch_ss` 256). `sch_tt_27C_3p3V`
is now 46/256: done codes `0x00..0x24` and `0x26..0x2E`; **210 remain**:
`0x25`, `0x2F`, `0x30..0xFF`. This slice's 14 done: `0x1F`, `0x21..0x24`,
`0x26..0x2E`.

## Interrupted submits at the stop (disclosure)

| tag | fleet job id | state at stop | disposition |
|---|---|---|---|
| `sch_tt_27C_3p3V_c25` | `klt-sim-f741e4908b83` | `pending` (queued; read-only `--job-status` check at 20:47Z) | partial job dir removed; the driver's resume will resubmit it as a new job. The queued fleet job completes unused (~32 s sim, negligible waste). |
| `sch_tt_27C_3p3V_c2F` | none (no receipt written; client was killed mid-launch) | never submitted | partial job dir removed; resubmitted on resume. |

No existing receipt, report or ledger row was rewritten or removed; the ledger
is append-only (one line per finished submission, 14 appended this slice).

## Audit over the 14 new reports

Every report `status: pass` and carries `environment.remote`
(aws-batch-fleet, spot, `runner_klt_version: 0.9.0`,
`client_klt_version: 0.9.0`, `runner_compatibility: match`); 46/46 done
receipts have distinct fleet job ids; every report's
`environment.netlist_closure` contains the frozen manifest `sch` DUT hash
`258e5e76...`; `models_lib_sha256` uniform (`f6f4a96e...`, the manifest's PDK
models). All 14 are ngspice-47, consistent with the rest of `sch_ss`/`sch_tt`.

New fact for the verdict DR / manifest readers (manifest itself stays frozen,
unedited): the runner image now exposes the open_pdks stamp in each report at
`environment.worker_environment.pdk.stamp_text` =
`open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (plus `stamp_sha256`
`4ca10280...`). The manifest's `pdk_revision: unknown` reason ("runner-side
open_pdks SOURCES not exposed to the client") no longer holds for new jobs;
the campaign-wide PDK revision can be cited from the reports when the verdict
DR is written, if the stamp is uniform across curves.

`test_harness.py` passes (39/39, pytest via `uvx --with pytest`); no code
changed. `sim/check-append-only.sh` passes against the merge base
`4faa04f2`. Supersedes the counts in `README.md` and earlier `SLICE-*.md`
(append-only, left unedited).

Next slice: resume with the same bench-regeneration recipe; 210 jobs remain
(all `sch_tt`), then `analyze.py --manifest`, the summary and the verdict DR
(next free number 0047 at `4faa04f2`; renumber if taken at merge). Only the PR
carrying the final analysis plus verdict DR may `Closes #87`.
