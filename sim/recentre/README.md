# sim/recentre - re-centre of the oscillator for extracted parasitics (issue #66)

Evidence for decision record
[0023](../../spec/decision-records/0023-recentre-timing-ladder-for-extracted-parasitics.md)
(status `proposed`). Append-only: new run ids only; nothing under another `sim/` directory is
edited. No ratified spec row is touched.

| path | role |
|---|---|
| `pexlib.py` | loads the committed extracted netlist, classifies its parasitic cards by schematic net, builds ablated / re-sized variants, runs ONE ngspice transient at a time |
| `attribute.py`, `report_attribution.py` | AC 1: attribution of the 19-37 % slow-down; `results/<runid>/{results.csv,attribution.md,manifest.json,rcosc_top.devices_only.spice}` (run `20261011T031527Z`) |
| `explore.py`, `report_explore.py` | AC 2/3 prep: single-corner probes of re-sized candidates (range endpoints, 48 MHz calibration, T/V extremes); `results/<runid>/{results.csv,command.txt}` (mode in both), collated in a `results/<runid>/summary.md` (current: `20261011T035649Z`) |
| `gen_requests.py`, `p3/` | AC 3: the 27-point `klt sim` corners requests (3 x 9 corners) and the proposed-sizing netlist `p3/rcosc_top_p3.spice` |
| `results/20261011T034200Z/` | batch submission record - **failed** (fleet runner klt 0.5.0 vs client 0.7.0, #2851); no 27-point numbers exist |
| `corners/` | raw ngspice logs of every single-corner run above, `corners/attribution-<runid>/` and `corners/explore-<runid>-<mode>/` |

## Source netlist

`sim/pvt-postlayout/results/20260923T152954Z/rcosc_top.pex.spice` (the committed
`klt extract --parasitics` output behind the -18.8 % .. -36.9 % record; layout GDS unchanged since).
Harness: `design/netlist/pvt_tb.spice` with only the embedded `rcosc_top` subckt replaced, the same
substitution `sim/pvt-postlayout/pex_pvt_sweep.py` makes. Measurement: identical to
`sim/pvt/pvt_sweep.py` (edges 5..25 at VDD/2, `tran 200p 1200n`), plus the mean `i(VDD)` over the same
window. The attribution driver reproduces the record's frequencies to the digit
(`ff/-40/3.6` 38.487 MHz, `ss/-40/3.6` 29.377 MHz, `tt/27/3.3` 35.815 MHz at code 0xA3).

## Commands

```
python3 -I sim/recentre/attribute.py                               # 93 serial single-corner runs
python3 -I sim/recentre/report_attribution.py sim/recentre/results/<runid>
python3 -I sim/recentre/explore.py curve|calibrate|points <NAME:RSCALE:CFF|WxL> ... [--corner p:T:V] [--tie] [--points ...]
python3 -I sim/recentre/report_explore.py sim/recentre/results/<new-runid>   # dir must exist
python3 -I sim/recentre/gen_requests.py [--pdk-root DIR]   # pin models.pdk_root on re-submission
KLT_SIM_BACKEND=batch klt sim sim/recentre/p3/request_<tt|ff|ss>.json -o OUT --format json
```

Every ngspice invocation here is one process, one corner, one trim code, run serially (shared host:
no pool, no `&`, no grid). The 27-point grid is the `klt sim` request, which is what failed to run.

Why the attribution and explore runs are local and not a `klt sim` corners request: a corners
request sweeps process / supply / temperature over ONE netlist. The 93 attribution runs are 31
netlist variants x 3 fixed corners (schematic, full extracted, and the cumulative and leave-one-out
parasitic-group ablations, the extracted ones under both substrate models), and the explore probes are re-sized netlists
(ladder R scale, MiM W x L) at a handful of single corners and bisected trim codes. Neither is a
PVT matrix a corners request can express, so each run is one serial single-corner ngspice process;
the one genuine PVT matrix (27 points on the P3 netlist) is expressed as `klt sim` requests.

## Run layout and the raw-log erratum

Every run id is a flat `results/<runid>/` (the repo-wide `sim/<bench>/results/<ts>/` layout that
`signoff/verify-doc-citations.py` resolves). Before the PR #158 review, `explore.py points` named
raw logs `<candidate>_pt_<code>.log` without the corner, so in runs `20261011T032737Z`,
`20261011T032821Z`, `20261011T032843Z`, `20261011T033138Z`, `20261011T033428Z` and
`20261011T033717Z` the points sharing a code overwrote each other's log (27 rows of 44). Those runs
are left as committed with an `ERRATUM.md` that lists each row; every overwritten row was re-run on
its own (one invocation, one ngspice process each) as run ids `20261011T035313Z` ..
`20261011T035616Z`, which reproduced `f_hz` and `iq_a` bit-identically. Logs are now named
`<candidate>_<pt|curve|cal>_<proc>_<T>C_<V>V_0x<code>.log` (minus sign written `m`) and `pexlib.run` refuses to overwrite a log.
Summary `20261011T035649Z` supersedes `20261011T035300Z` (same numbers; adds a `log` column whose
every entry holds the row's own corner).

## Net identification

Hub nodes of the extracted netlist were identified from device connectivity (`pexlib.HUB_NAME`):
`$26` = `vc` (timing node: MiM `C$86`, `MDISCH` drain, comparator inputs, trim-bank output), `$10,$11,$14,$16,$18,$20,$22,$24`
= ladder nodes c1..c8 (between the nine `ppolyf_u_1k` of the trim bank), `$13..$27` odd = the
inverted trim bits, `$32`/`$35` = `cmph_out`/`cmpl_out`, `$36` = `qbar`, `$44`/`$45` = the latch
mid nodes, `$7/$8/$9/$37/$1` = `vh/vl/pb/ibias/n2s`.

## Caveats that apply to every number here

* **Parasitics are lumped at the committed extraction's values.** Re-sizing the ladder resistors does
  not re-extract: a respin changes routing, switch-node diffusion and the MiM plate geometry. That
  re-extraction is the layout follow-up (item 7), not part of this issue.
* **Substrate model.** Model A is the netlist as extracted (`vsubs` held only by the extractor's
  1 Tohm shunt); model B hard-ties `vsubs`. They differ by -6 % .. +7 % in frequency at the
  attribution corners. Filed: 2AMLogic/klayout-tools#3089.
* **MiM.** The extractor writes the MiM as a fixed-value C; the re-sized netlists and the 27-point
  requests use the PDK `cap_mim_1f0fF` subckt (agrees at tt to 0.02 %) so the mimcap corner is
  exercised. Filed: 2AMLogic/klayout-tools#3090.
* **PDK root.** `explore.py` runs resolve the PDK via `klt pdk find` (`~/.volare`); `klt sim` picked
  `~/.ciel` (both `gf180mcuC`, one warning printed). A tt/27/3.3 comparison of the same netlist
  and code gave 48.048 MHz (explore) vs 48.058 MHz (`klt sim`), 0.02 %. On re-submission of the
  27-point requests, regenerate them with `gen_requests.py --pdk-root <root>` so `models.pdk_root`
  is pinned (the committed requests carry no absolute path).
* Iq here is mean `i(VDD)` over the 20 measured periods of the frequency transient, not the
  `sim/iq` metric of ratified row 9.
