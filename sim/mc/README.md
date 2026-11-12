# sim/mc — item-6 Monte Carlo campaign (issue #202)

The T1 item-6 evidence for the statistical spec rows 2, 4 and 5 (DR-0019
claims S1-S3): `klt sim` `monte_carlo` campaigns on the batch fleet, graded
with `klt yield`. Result and its limits: **row 4 fails at `ss`, row 5 fails at
`ff`, and the negative controls are incomplete, so the passing cells carry no
verdict.** Item 6 grades `unmet` (`negative_control_not_detected`). The
ratified spec is untouched; the record is
[DR-0030](../../spec/decision-records/0030-item-6-monte-carlo-campaign-results-s2-ss-and-s3-ff-fail-controls-incomplete.md).
`results/` is append-only.

```
sim/mc/
  gen_campaign.py        writes the benches, requests and limits below (offline; tests: test_gen_campaign.py)
  run-campaign.sh        copies them into a NEW results/<runid>/ and submits each as a sharded `klt sim` batch request
  grade.sh, analyze.py   klt yield-samples + klt yield per (process, row set), control summary -> results/<gradeid>/
  tb_<case>.spice        per-die bench: P3 extracted DUT with the DR-0022 injection inlined
  request_<case>.json    the klt sim requests (cases: main_<p>, inflated_<p>, zero_<p>, sens1_tt, sens10_tt, senszero_tt)
  limits_main.json       klt yield limits: ratified rows, target yield 0.99, 95 % confidence, min 500 samples
  mismatch-manifest.json the injected terms (instance, sigma at scale 1): the evidence the body injection is live
  results/20261106T051700Z/  raw reports: main_tt/ff/ss (500 samples each), inflated_tt (500)
  results/20261106T061800Z/  raw reports: inflated_ff/ss (500), zero_tt/ff/ss (3 draws)
  results/20261106T070700Z/  raw reports: sens1_tt, sens10_tt (100 each), senszero_tt (3)
  results/20261106T072000Z/  graded: sampleset_<p>.json, yield_<p>_row{2,4,5}.json, summary.md, sources.txt
  results/20261106T052000Z/, 20261106T052500Z/, 20261106T053000Z/   pipeline validation (below)
```

> **Later run on the DR-0028 netlist (issue #236):** `results/20261112T025135Z/` (reports) and
> `results/20261112T060000Z/` (graded), made with `run-campaign.sh --dut sim/cmph-fix/rcosc_top_p3_cmphfix.spice`.
> Row 4 still fails at `ss` (0 %) and row 5 at `ff` (92.6 %). Record:
> [DR-0032](../../spec/decision-records/0032-rows-4-5-per-die-calibrated-basis-and-monte-carlo-on-dr0028.md).
> The numbers below describe the pre-DR-0028 P3 netlist.

## What was run

* **DUT.** The P3 sizing of [DR-0023](../../spec/decision-records/0023-recentre-timing-ladder-for-extracted-parasitics.md)
  (ladder x0.70) on the committed extracted netlist, `sim/recentre/p3/rcosc_top_p3.spice`:
  the sizing #66 settled. The schematic in `design/` carries the pre-recentre
  sizing and is not used (DR-0019 section 4). **The DUT predates DR-0028**
  (comparator-H output stage, #229/#234), whose change is already in
  `design/netlist/rcosc_top.spice` on `main`: every number here measures a
  superseded netlist and must be re-run on the post-DR-0028 netlist (after
  re-centring) before it describes the current design.
* **Mismatch.** PDK MOS mismatch (`sw_stat_mismatch`) plus the DR-0022 injected
  area-scaled ladder-resistor and MIM-capacitor mismatch, `A_R = A_C = 1.0 %.um`
  (flagged assumption, no public source), through `sim/mc-groundwork/mismatch_inject.py`
  (14 terms: 13 `ppolyf_u_1k` + the MiM). The injector gained two things for
  the extracted netlist: cards with no `m=` (m=1 by default) get one appended,
  and `$` in extracted instance names becomes `_` in the `d_<inst>` parameter.
* **Per die** (one ngspice session, so every solve sees the same draw): bisect
  the 8-bit code to the frequency nearest 48.000 MHz at 27 C / 3.3 V, re-measure it
  (`hold_gap_hz` = 0 for all samples), hold it at 27 C x {3.0, 3.6} V (row 4, S2) and
  -40/27/85 C x {3.0, 3.3, 3.6} V (row 5, S3), and at the two neighbouring codes.
  Temperature is switched in-session with `option temp`; the zero-mismatch
  control reproduces the deterministic grid, so the switch is verified.
* **Seed and size.** Seed `20261008` (DR-0019), 500 samples per process corner;
  requests are sharded 25 units per job (<= 8 jobs in flight) on the Spot fleet,
  client `klt 0.9.2.dev42`, engine ngspice 46. Sharding was checked to be deterministic: the first six dies of
  an 8-sample sharded run equal the unsharded run's (`results/20261106T053000Z/`).
* **Graded measurements** (derived per die, `limits_main.json`): `s1_resid_abs_pct`
  <= 0.757 (0.157 half-LSB + 0.300 trim-DAC + 0.300 comparator offset, the DR-0019
  "half-LSB plus the DR-0003 Row 3 mismatch budget"), `s1_headroom` >= 1 code,
  `s2_margin_pct` >= 0 (the margin to the nearer of the ratified -2.9 / +2.0 %),
  `s3_margin_pct` >= 0 (to -10.8 / +8.8 %). Step sizes are recorded, not gated
  (DR-0022 section 5: DR-0021's carries are non-monotone at 0x).

## Results (`results/20261106T072000Z/summary.md`)

Yield, 95 % Clopper-Pearson lower bound, target 99 %, all `sample_size` verdicts
`sufficient` except `ff` row 5:

| process | row 2 | row 4 | row 5 |
|---|---|---|---|
| `tt` | 100 % (>= 99.26 %) | 100 % (>= 99.26 %) | 100 % (>= 99.26 %) |
| `ff` | 100 % (>= 99.26 %) | 100 % (>= 99.26 %) | **60.4 % (>= 55.96 %), fail** |
| `ss` | 100 % (>= 99.26 %) | **0 %, fail** | 100 % (>= 99.26 %) |

Why the two failures are not noise: `ss` row 4's supply span at the held code
(27 C, 3.0-3.6 V) is 5.44 points median (range 4.89-6.09) against a 4.9-point
ratified window: 498 of 500 dies cannot fit it (the two narrowest, 4.891, fit
by under 0.01 point, below one trim step); `ff` row 5 fails on both sides (26 %
of dies above +8.8 %, 17 % below -10.8 %). Code spread: tt 165-172, ff 82-95,
ss 212-217 (every code at least 38 from a rail).

## Controls, and what they leave unproven

Criteria were fixed before the run (`analyze.py` docstring).

| control | result |
|---|---|
| zero mismatch | **pass**: identical draws; code `0xA9`/`0x59`/`0xD7` and 27 C / 3.3 V frequency within 0.023 % of the 27-point grid |
| inflated 3x (`sw_stat_mismatch=3`: MOS and injected 3x) | **detected only for `ff` rows 4, 5**; not detected for the other 10 of 12 (3x yield stays at the nominal yield, or the nominal is already 0 %) |
| injected-term sensitivity (MOS off, n=100) | MSB step (0x7F->0x80) sigma 9.65x for a 10x scale (band 7-13): **pass**; 0x7E->0x7F step 4.99x: **outside the band**; code spread 0.10 -> 1.44 |

`klt signoff` reads the inflated-control column as
`negative_control_not_detected`. By DR-0019 section 2 a campaign whose controls
do not behave as stated yields no verdict, so the passing cells above are
point estimates, not claims. The 0x7E->0x7F miss is attributed (untested
hypothesis) to the 1x sigma, 4.5 kHz, sitting at the `tran 200p` timing
resolution.

## Honest limits

* The mismatch model is DR-0022's flagged assumption; `klt sim`'s
  `family_mismatch` still reports the resistor and capacitor families
  inactive (klayout-tools#2898), and the manifest above is the evidence the
  injection is live.
* Solver `reltol` is the default (the groundwork measured ~0.2 % dependence);
  the zero control and the deterministic grid used the same setting.
* One seed, one matching-model scale. The yield-vs-`A_R` sensitivity DR-0022
  section 5 allows is not computed.
* Row 1-of-S1 "range covers the spread" is not a Monte Carlo quantity here and
  stays with the corner record (`sim/recentre/results/20261106T044714Z/`: the
  ratified window is covered at only 6 of 27 points).

## Reproduce

```
sim/mc/run-campaign.sh [--dut <netlist>] <new runid> [case ...]     # each case is a klt sim batch request; no local ngspice loop
sim/mc/grade.sh <new gradeid> <run dir> [<run dir> ...]
uv run --no-project --with "klayout-tools==0.8.0" klt signoff --manifest signoff/block-manifest.json --format json > signoff/signoff-report.json
```

## Pipeline validation and attempts kept

* `results/20261106T052000Z/` zero-mismatch tt, 3 draws, on the batch fleet:
  the first run of the in-session temperature/supply hold, matched to the
  27-point grid (two earlier runs of the same bench were discarded before
  commit because ngspice `minimum()`/`maximum()` reduce one vector, not two
  arguments, which corrupted the derived margins; fixed by explicit arithmetic).
* `results/20261106T052500Z/` 6-sample mismatch-on smoke: dies differ, codes 167-170.
* `results/20261106T053000Z/` 8-sample sharded run (determinism check).
* `sim/mc-groundwork/results/20261106T045937Z/`: the #186 injected-pipeline
  smoke on the schematic DUT, now running on the batch fleet (it failed on
  2026-10-17 for want of the `gf180mcuC` runner PDK).
* The first sensitivity attempt ran the "10x" arm at 1x (the injector's default
  `.param mm_scale=1` overrode the bench-header value); it was caught by the
  analysis (ratio 1.00), discarded before commit, and the cases now bake the
  scale into the sigmas (regression test in `test_gen_campaign.py`).

## Tool friction

* Hit again on client `klt 0.9.2.dev42`: the batch whole-job ceiling is checked
  against `options.timeout_s x units`, a worst-case serial bound, so a per-unit
  timeout sized for slow samples cannot be combined with large shards (sizing
  was tuned to the bound, 120 s x 25 units, not to the work). This is
  klayout-tools#4982 (closed); not re-filed because the closed fix did not
  reach this client build.
* Multi-condition per-die evaluation (calibrate, then hold the code across
  conditions on the same sampled die) still needs a body `.control` block
  (klayout-tools#2482, #2899).
