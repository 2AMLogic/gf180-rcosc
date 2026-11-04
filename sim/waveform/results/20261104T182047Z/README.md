# Waveform campaign preflight (issue #213) -- FAILURE RECORD, no measurements

Informational evidence only. **No pulse-width, duty, rise/fall or period
measurement exists from this run**; none is claimed.

## What was run

One batch submission (the preflight in #213's guidance), from
`preflight/`:

```
klt sim request_v33_tt.json --backend batch -o out --format json
```

`request_v33_tt.json` / `tb_v33_tt.spice` / `rcosc_top_schematic.spice` are
unmodified copies of the committed files in `sim/waveform/` (`models.pdk` is
still `gf180mcuC`). Run 2026-11-04 (client submit 18:21:03Z). A first attempt
the same minute never reached the fleet: the netlist's
`.include rcosc_top_schematic.spice` was missing from my copy (client-side
refusal, my staging error, fixed by copying the include). Only the second
attempt counts.

## Result

| Field | Value |
|---|---|
| Job id | `klt-sim-d4811d4414d4` (`environment.remote`) |
| Fleet | aws-batch-fleet, us-east-1a, m7i.4xlarge spot |
| Client klt | `0.8.1.dev1317+ga2804ab99263` |
| Runner klt | `0.8.0`, `runner_compatibility: match` |
| Request features | `options.ngspice_init` supported, none missing |
| State | `failed`, job exit code 1, 5 s, before any ngspice run |
| Corners | 3 submitted, 3 errored (`batch_job_failed`), 0 passed |

Runner error (verbatim core): *no supported-layout PDK install providing
variant 'gf180mcuC' was found. Searched PDK_ROOT (/opt/pdk), ~/.ciel, ~/.volare,
~/pdks, /usr/local/share/pdk, /usr/share/pdk, ~/share/pdk.*

This is the same failure as `sim/mc-groundwork/results/20261017T202900Z/`
(2026-10-17, klt 0.7.0): the batch image has not been backfilled with
`gf180mcuC`. Closing klayout-tools#2851/#2882 did not change that.

## Per-point status (27-point grid)

Only the v=3.3 V / tt group was submitted (one preflight, per the issue).
Its three points errored; the other 24 points were **not submitted** because
the preflight failed, and none was run locally (host rule; no `--backend local`).

| Supply | Corner | -40 C | 27 C | 85 C |
|---|---|---|---|---|
| 3.3 V | tt | errored (`batch_job_failed`) | errored | errored |
| 3.3 V | ss, ff | not submitted | not submitted | not submitted |
| 3.0 V | tt, ss, ff | not submitted | not submitted | not submitted |
| 3.6 V | tt, ss, ff | not submitted | not submitted | not submitted |

## Not done (blocked on the same cause)

Convergence check, `analyze.py` table, decision record, and the stochastic-noise
assessment all need a successful batch run. Unblock = operator backfill of
`gf180mcuC` into the batch image (2AMLogic/2am `infra/aws/`), then re-run.
`models.pdk` and the requests were not altered.

Raw artifacts: `preflight/submit.json` (klt envelope), `preflight/stderr.txt`,
`preflight/out/batch-receipt.json`.
