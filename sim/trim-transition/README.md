# sim/trim-transition - live trim-code transition bench (issue #103)

Changes the trim code **while the oscillator runs** and measures `clk` across the
change: shortest/longest period in the three cycles around it, runt pulses,
missing/extra edges, and cycles to settle at the new code's steady period.
Every committed trim result before this was steady-state at a fixed code; the
runtime-discipline claim (DR-0004, DR-0021) assumes a code rewrite does not
corrupt the clock. This bench tests that assumption. Schematic level only, no
design change.

**Status (2026-10-09): generator, analyzer, offline tests and one single-corner
local probe are committed. The nine-corner campaign has NOT produced results:
the batch submit failed (runner/client version mismatch, below), so the
"committed results for all nine corners" acceptance item is PENDING.** Nothing
here changes a ratified spec row; no decision record is added (see "Verdict").

```
sim/trim-transition/
  prepare.py            offline bench + `klt sim` request generator (no simulator, no cloud)
  analyze.py            klt sim report analyzer -> results.json / results.csv / summary.md
  run-transition.sh     regenerate + `klt sim` each request into a NEW results/<runid>/
  test_harness.py       synthetic-fixture + request tests (23 tests, run in CI)
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

CI: `.github/workflows/trim-transition-offline.yml` runs the offline suite
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

## Verdict (current)

Pending the nine-corner run. If the campaign shows a VIOLATION (runt, missing
edge, never settles) at any corner, add a decision record under `spec/decision-records/`
and a cross-reference in DR-0021's follow-ups; FLAG-only outcomes inform the
discipline model (a skewed update can cost one off-envelope cycle) but do not
alter a ratified row.

## Limitations

Schematic only (post-layout PEX only if a violation appears); ideal digital
sources (no driver impedance, no coupling through routing); no mismatch; edge 1 ns
fixed; skew modes are two orderings, not a Monte Carlo of arrival times; 27 C only;
the phase of each change is measured, not controlled.
