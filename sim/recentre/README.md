# sim/recentre - re-centre of the oscillator for extracted parasitics (issue #66)

Evidence for decision record
[0023](../../spec/decision-records/0023-recentre-timing-ladder-for-extracted-parasitics.md)
(status `proposed`). Append-only: new run ids only; nothing under another `sim/` directory is
edited. No ratified spec row is touched.

| path | role |
|---|---|
| `pexlib.py` | loads the committed extracted netlist, classifies its parasitic cards by schematic net, builds ablated / re-sized variants, runs ONE ngspice transient at a time |
| `attribute.py`, `report_attribution.py` | AC 1: attribution of the 19-37 % slow-down; `results/attribution/<runid>/{results.csv,attribution.md,manifest.json,rcosc_top.devices_only.spice}` |
| `explore.py`, `report_explore.py` | AC 2/3 prep: single-corner probes of re-sized candidates (range endpoints, 48 MHz calibration, T/V extremes); `results/explore/<runid>-<mode>/`, collated in `results/summary/<runid>/summary.md` |
| `gen_requests.py`, `p3/` | AC 3: the 27-point `klt sim` corners requests (3 x 9 corners) and the proposed-sizing netlist `p3/rcosc_top_p3.spice` |
| `results/p3-27pt/<runid>/` | batch submission record - **failed** (fleet runner klt 0.5.0 vs client 0.7.0, #2851); no 27-point numbers exist |
| `corners/` | raw ngspice logs of every single-corner run above |

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
python3 -I sim/recentre/report_attribution.py sim/recentre/results/attribution/<runid>
python3 -I sim/recentre/explore.py curve|calibrate|points <NAME:RSCALE:CFF|WxL> ... [--corner p:T:V] [--tie] [--points ...]
python3 -I sim/recentre/report_explore.py sim/recentre/results/summary/<new-runid>   # dir must exist
python3 -I sim/recentre/gen_requests.py
KLT_SIM_BACKEND=batch klt sim sim/recentre/p3/request_<tt|ff|ss>.json -o OUT --format json
```

Every ngspice invocation here is one process, one corner, one trim code, run serially (shared host:
no pool, no `&`, no grid). The 27-point grid is the `klt sim` request, which is what failed to run.

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
  and code gave 48.048 MHz (explore) vs 48.058 MHz (`klt sim`), 0.02 %.
* Iq here is mean `i(VDD)` over the 20 measured periods of the frequency transient, not the
  `sim/iq` metric of ratified row 9.
