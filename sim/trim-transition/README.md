# sim/trim-transition - live trim-code transition bench (issue #103)

Changes the trim code **while the oscillator runs** and measures `clk` across the
change: shortest/longest period in the three cycles around it, runt pulses,
missing/extra edges, and cycles to settle at the new code's steady period.
Every committed trim result before this was steady-state at a fixed code; the
runtime-discipline claim (DR-0004, DR-0021) assumes a code rewrite does not
corrupt the clock. This bench tests that assumption. Schematic level only, no
design change.

**Status (2026-11-06): COMPLETE. The nine-corner batch campaign ran on the v11
runner (runner klt 0.9.0) into `results/20261106T055733Z/`: all nine jobs `pass`,
864 events (3 skews x 9 corners x 32). No runt pulse and no missing/extra edge in
any event. 30 events fail the "never settles" screen, which is noise-limited at the
fast corners (see "Verdict").** Decision records:
`spec/decision-records/0027-live-trim-code-transition-bench-nine-corner-result.md`
(this run) and `0026-...-batch-result.md` (the earlier partial run
`results/20261106T050454Z/`, kept as is). Nothing here changes a ratified spec row.

```
sim/trim-transition/
  prepare.py            offline bench + `klt sim` request generator (no simulator, no cloud)
  analyze.py            klt sim report analyzer -> results.json / results.csv / summary.md
  run-transition.sh     regenerate + `klt sim` each request into a NEW results/<runid>/
  test_harness.py       synthetic-fixture + request tests (24 tests, run in CI)
  provenance.json       GENERATED: positions, skew modes, settings, DUT hash (not evidence)
  rcosc_top_schematic.spice   GENERATED: DUT extracted from design/netlist/pvt_tb.spice
  tb_/request_/schedule_v{30,33,36}_{none,lsb_first,msb_first}.*   GENERATED: nine benches
  batch-attempts/       failed batch submissions (kept, not hidden)
  results/<runid>/      append-only evidence (see sim/README.md)
```

## Commands

```
python3 -I sim/trim-transition/prepare.py                      # regenerate the nine benches
python3 -I sim/trim-transition/prepare.py --out /tmp/p --probe tt:3.3:lsb_first   # one-corner request
sim/trim-transition/run-transition.sh                          # klt sim (host default backend = batch)
python3 -I sim/trim-transition/analyze.py v33_none=<report.json> ... --outdir sim/trim-transition/results/<runid>/analysis
python3 -I -m pytest -p no:cacheprovider sim/trim-transition/test_harness.py   # offline, pytest only
```

CI: `.github/workflows/offline-suites.yml` (matrix entry `trim-transition-offline`) runs the offline suite
(synthetic fixtures; no PDK, klt, ngspice or batch credentials).

## Bank weighting (checked against the schematic, asserted by a test)

`rcosc_trim_bank` stage `i` is a `ppolyf_u_1k` resistor of length
`0.7482 um x 2^i` shunted by a pass switch gated by `t<i>` (`t<i>=1` shorts the
stage). The bank is plain **binary, t0 = LSB, t7 = MSB**, higher code = lower R =
higher f. `n -> n+1` flips `k+1` bits, `k` = trailing ones of `n`.

| step | bits flipped |
|---|---|
| `0xA2 <-> 0xA3` (non-carry; brackets the tt calibration code `0xA3`) | 1 |
| `0x3F <-> 0x40` | 7 |
| `0x7F <-> 0x80` (major carry) | 8 |
| `0xBF <-> 0xC0` | 7 |

(DR-0021's other non-monotone carries `0xDF`/`0xEF` are not in this first set.)

## Stimulus

Per (supply, skew mode) one netlist, one 3-corner request (process tt/ss/ff at
27 C): 3 supplies x 3 skew modes = 9 requests = the nine tt/ss/ff x 3.0/3.3/3.6 V
corners, each under three skew modes. Supply and trim select lines are PWL
sources (VDD and the high bits ramp 0 -> VDD in 1 us, as in `sim/startup`).
One transient holds all code changes in sequence so each runs on a settled,
free-running oscillator:

- Four blocks (one per step above). A block starts with an excluded *setup*
  change to the block's low code, 1.5 us settle, then 8 events 700 ns apart:
  up, down, up, down, ... = 4 "phases" x 2 directions. Each phase pair is
  offset by 5.25 ns (~T/4 at 48 MHz). 32 events per netlist, ~31 us.
- Select edges: 0 -> VDD in 1 ns. **Skew modes**: `none` (all bits together),
  `lsb_first` (bit i starts i x 1 ns late, total 7 ns), `msb_first` (bit i starts
  (7-i) x 1 ns late). At a carry these produce the two worst transient codes
  (momentarily too-low and too-high code).
- Same bench settings as `sim/waveform` except `tstep/tmax = 100p` (a 200p max
  step leaves ~0.2 % solver edge-time noise on single periods, larger than the
  settle tolerance; 40p aborted with "timestep too small" at a PWL edge).
- Each select PWL source drives its trim pin through `drv_ohm` = 50 ohm. With ideal
  0-ohm sources the `lsb_first` benches aborted `timestep_too_small` at 30.7167 us at
  every corner, whatever `itl4` / `method=gear` / `tmax` was used (DR-0027).
- No extra `clk` load, ideal rails, schematic netlist, no mismatch. The trim
  code is *not* the per-process calibrated code: the carry codes are fixed by the
  bit pattern, the same for every process (periods differ, see results).
- **Phase caveat**: the oscillator is free-running, so the phase at which a
  select edge lands cannot be fixed by the schedule; it is *measured* (`phase_in_cycle`,
  fraction of the cycle that has elapsed at the first select edge) and reported
  per event. Coverage per step is whatever the offsets produce (the probe
  spans 0.4-1.0 at some steps and 0-1 at others); it is not claimed uniform.

## Metrics (analyze.py; full definitions in its docstring)

Level = 50 % of nominal VDD, linear interpolation. Window = the cycle before,
the cycle containing the first select edge, and the next (extended to the cycle
containing the last select edge for skewed changes). Per event: min/max period in
the window; `P_old`/`P_new` = mean of 8 steady cycles before / just before the
next change; **excursion** = how far window periods leave
`[min(P_old,P_new), max(P_old,P_new)]` in % of `P_old`; **runt** = any window
high/low width below 0.5 x its steady width, or an incomplete swing (not reaching
90 % / 10 % of VDD); **missing/extra edge** = any window period > 1.5 x or
< 0.5 x the steady periods; **settle cycles** = cycles from the change cycle until
all following periods stay within 0.1 % of `P_new` (0 = the change cycle already
is; "never" is a failure). Explicit failures (no metrics) for missing reports,
errored corners, short runs, rail off nominal, or steady windows that overlap a
neighbouring change.

Verdict screens - **bench screening thresholds, not ratified spec rows**:
VIOLATION = runt, missing/extra edge, or never settles; FLAG = excursion > 5 % or
settle > 3 cycles; PASS otherwise. The verdict table (`summary.md`) has one row
per corner x step x direction x skew, aggregated over the four phases
(min of min P, max of max P, any runt, max settle).

## Batch status and the one local probe

- `batch-attempts/klt0.7.0_request_v33_none.report.json`: `klt sim` 0.7.0 with
  `KLT_SIM_BACKEND=batch` submitted `request_v33_none.json`; job
  `klt-sim-5e591c92fa97` failed on the fleet with `batch_runner_version_mismatch`
  (runner klt 0.5.0, client 0.7.0), the same refusal as `sim/startup/batch-attempts/`.
  Not worked around by a local multi-corner run. A runner image update (or a
  compatible client) is needed before the campaign can run.
- `batch-attempts/*_klt0.9.0_runner/` (the 2026-11-05 attempt directory): re-run of
  `run-transition.sh --backend batch` on the eda-batch-runner v10 image (runner klt
  0.9.0, `runner_compatibility=match`). All nine requests (27 units) ended
  `batch_job_failed`, exit 1: "no supported-layout PDK install providing variant
  'gf180mcuC' was found" (`/opt/pdk` and the other search roots empty on the
  runner). Job ids are in each `report_*.json` (e.g. `klt-sim-e9c43a8073a7`). No
  local fallback was run. Tracked at 2AMLogic/klayout-tools#4947. Re-run once the
  runner image ships the PDK.
- `results/20261009T152100Z/`: the single-corner debug probe
  (tt, 3.3 V, 27 C, `lsb_first`, `klt sim --backend local`, ~90 s). Preliminary and
  one corner of 27; the rows, not these notes, are the record.

### What the single probe shows (tt, 3.3 V, lsb_first only)

No runt pulse, no missing/extra edge, every event settles; 23 PASS, 9 FLAG of 32.
FLAGs: the 0x7F -> 0x80 *down* and 0xBF -> 0xC0 *down* steps (ripple order passes
through a transient code with many bits already at the target, momentarily
shifting the period by 10-19 % / 6-7 % beyond the old/new envelope for one
cycle; the 7-ns skew exceeds a third of a cycle, so this is an extreme skew), and
one 0x3F -> 0x40 *up* event that takes 14 cycles to come within 0.1 % of the new
period (a small slow tail, 3.3 % excursion). Whether the other 26 corner x skew
combinations change this is unknown until the campaign runs; extrapolating from
one corner is not claimed.

## Batch campaign `results/20261106T050454Z/` (2026-11-06, v11 runner)

`run-transition.sh --backend batch`; nine `klt sim` jobs (job ids in each
`report_*.json` under `environment.remote`), runner klt 0.9.0, `runner_compatibility=match`,
open_pdks `f6eeac7`, ngspice 46, 3 corners per job. Analysis:
`results/20261106T050454Z/analysis/{summary.md,results.csv,results.json}`
(`analyze.py` over all nine reports, 585 event rows). The raw waveforms
(~1.1 GB) are not committed; benches, requests, schedules, reports and
`corner.cir` decks are.

| skew | corners simulated | events | PASS | FLAG | VIOLATION | FAIL |
|---|---|---|---|---|---|---|
| none | 9/9 | 288 | 172 | 102 | 14 | 0 |
| msb_first | 9/9 | 288 | 133 | 147 | 8 | 0 |
| lsb_first | 0/9 (ngspice abort) | 9 | 0 | 0 | 0 | 9 |
| **all** | 18/27 | 585 | 305 | 249 | 22 | 9 |

- **Runt pulses: none. Missing/extra edges: none** (every simulated event).
- **22 VIOLATION rows, all "never settles" within the 8-cycle steady window**
  (no runt, no missing edge): 17 at ff/3.6 V, 4 at ff/3.3 V, 1 at tt/3.3 V,
  mostly the 0x3F<->0x40 and 0x7F<->0x80 carries, two non-carry 0xA3->0xA2 downs
  at ff/3.6 V. Several have a small excursion (0.006-0.4 %), so this is a slow
  tail past `settle_tol` at the fastest corners rather than a glitch; whether it
  is a real slow settle or a screen artefact of the steady-window definition
  at ff/3.6 V is not resolved here.
- **249 FLAGs** (excursion > 5 % or settle > 3 cycles), concentrated at the
  major carries: the up step 0x7F->0x80 reaches up to 31 % excursion with
  `msb_first` skew (ff, 3.0 V) and 10-14 % without skew.
- **lsb_first aborted at the same instant (30.7 us) in every corner**, while the
  2026-10-09 local probe (tt, 3.3 V, ngspice local) completed the same bench.
  The same-instant abort points at the PWL stimulus/ngspice-version
  interaction, not a corner effect. Not debugged in this run (out of scope:
  no generator change); not retried locally per the batch-only host rule.

## Campaign `results/20261106T055733Z/` (2026-11-06, series-R bench)

`run-transition.sh --backend batch`; nine `klt sim` jobs (all `pass`, runner klt 0.9.0).
Analysis: `results/20261106T055733Z/analysis/{summary.md,results.csv,results.json}`
(864 event rows). Raw waveforms (~1.1 GB) are not committed.

| skew | corners | events | PASS | FLAG | VIOLATION | FAIL | worst excursion |
|---|---|---|---|---|---|---|---|
| none | 9/9 | 288 | 182 | 92 | 14 | 0 | 14 % |
| lsb_first | 9/9 | 288 | 202 | 78 | 8 | 0 | 24 % |
| msb_first | 9/9 | 288 | 134 | 146 | 8 | 0 | 41 % |
| **all** | 27/27 | 864 | 518 | 316 | 30 | 0 | |

- Runt pulses: none. Missing/extra edges: none.
- The 30 VIOLATIONs are all "never settles" (21 at ff/3.6 V). Their pre-change steady
  period spread is 0.02-0.15 % (median 0.075 %) against the 0.1 % settle tolerance,
  and 834 non-violating events have steady spread up to 0.17 %: the screen is
  noise-limited, not evidence of a slow settle. Tolerance not loosened.
- Worst excursions are single-cycle and at the 0x7F<->0x80 carry (ff), the
  non-monotone carry of DR-0021 plus skew-order transient codes.
- `analyze.py` collapses exact-duplicate timestamps (ngspice emits two at the
  30.7167 us instant); out-of-order time still fails.

## Verdict (current)

No glitch-class failure (runt / missing edge) in any of 27 corner x skew benches at
schematic level: DR-0021's no-glitch-on-update assumption holds for that class. The
settle claim is not resolvable with the 0.1 % screen at fast corners; a
spread-relative criterion is the follow-up. Recorded in DR-0027, cross-referenced
from DR-0021; no ratified row is relaxed.

## Limitations

Schematic only (post-layout PEX only if a violation appears); ideal digital
sources behind a fixed 50 ohm driver (no real driver model, no coupling through routing); no mismatch; edge 1 ns
fixed; skew modes are two orderings, not a Monte Carlo of arrival times; 27 C only;
the phase of each change is measured, not controlled.
