# sim/iq-attribution - row 8 per-stage running-Iq attribution (issue #347)

Where does the running supply current go, stage by stage, on DR-0044's DUT (the extraction of the
rebuilt layout, `sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice`),
at the cells over 500 uA in DR-0044's 108-cell table, at the calibration code `0xA4` cells row 8 is
actually graded on (`sim/item5/ROWS.md` row 8), at tt / 27 C / 3.3 V for reference, and on the
L=1U control extraction at one cell. Append-only: new run ids only; DR-0044's results directory is
read, never edited.

## Method

Both netlists in play are flat parasitic extractions with no stage hierarchy and no instance names,
so the device-to-stage map cannot be read off the netlist text:

- **`stage_map.py`** builds the map from the committed per-block rosters
  (`layout/reports/rcosc_{bias,comparator,comparator_p,trim_bank}.extracted.spice`): each block's
  devices carry in-block placement coordinates (`* device instance $N r0 *1 X,Y class`), so a single
  translation per block registers the block's devices 1:1 onto the flat extraction's 99 devices by
  (class, L, W) signature + coordinates. The 10-device remainder is assigned from
  `design/netlist/rcosc_top.spice`'s top-level devices: the timing MiM (only cap_mim device), the
  discharge nfet (only W=20U nfet) and the eight latch devices as one group. The VDD parasitic
  network is the union-find component of `vdd` over the extraction's star resistors
  (`Rvdd_tK vdd__tK vdd ...`); every device terminal landing in that component is a supply-entry
  point of its stage. Nothing is guessed: unresolved devices are listed (and fail the build unless
  `--allow-unresolved`). The committed map for the main DUT is **`stage_map.json`** (99/99 devices:
  bias 16, comparator-H 14, comparator-L 18, latch 8, trim bank 41, timing 1, discharge 1; 41
  devices / 62 terminals on the VDD network) -- the conservation assertion lives in
  `stage_map.check_conservation` and is re-run by `iq_report.py` on every report.
- **`gen_stage_iq_requests.py`** writes a **probed copy** of the DUT (no device edited beyond
  net renaming): each current-bearing stage's vdd-side terminals are re-terminated onto an internal
  `vdd_<stage>` node, 0 V sources tie that node back to the original nets (an ideal short; every
  parasitic star resistor stays in circuit, so the operating point and transient are unchanged --
  exact, unlike a 1 mOhm probe), and each stage's feed is integrated on 1 nF INSIDE the subckt
  (a source inside a subckt cannot be referenced from a bench-level B source, and an external
  ammeter would leave the internal vdd network as a parallel feed path). Only the per-stage
  integrator nodes are exposed, as pins `pq_<stage>`. The bench is DR-0044's integrator bench
  unchanged for the total (`iq_run`, clk rising edges 5 -> 25 = 20 whole periods, the DR-0009
  basis). The timing MiM and the discharge device have no vdd terminal: no source, no integrator --
  zero by construction. `dut.txt` records the sha256 of the source DUT, the probed copy and the map.
- **`iq_report.py`** tabulates per cell: total `iq_run`, each stage's `iq_<stage>`, the sum of
  stages and the residue (total - sum, per cell, never bounded once), asserts the back-to-back
  check (probed total vs DR-0044's committed figure, +/-1 %) and the sum check (+/-1 %), states the
  integration window (and that these figures are NOT comparable to item-5's fixed 200-1200 ns
  window figures such as 559.4 uA), and reports the timing/discharge stages as exactly zero.

## Runs

```
python3 -I sim/iq-attribution/stage_map.py <flat deck> <out.json> --roster bias=... --roster cmp_h=... --roster cmp_l=... --roster trim=...
python3 -I sim/iq-attribution/gen_stage_iq_requests.py sim/iq-attribution/results/<runid>
cd sim/iq-attribution/results/<runid> && klt sim --batch-set request_cFF_v33.json request_cFF_v36.json --backend batch --format json --wait-for-capacity 600 -o $PWD/art   # wave 1: the back-to-back gate
python3 -I sim/iq-attribution/iq_report.py sim/iq-attribution/results/<runid>/art sim/iq-attribution/results/<runid>/table.md
```

- `results/20261115T030058-iq-attribution/`: the main campaign (8 requests, 33 corners, all
  receipts committed under `art/`). **Wave order is the Test Plan's gate**: the two requests
  carrying the back-to-back cells (`cFF_v33`: tt / 27 C / 3.3 V / 0xFF; `cFF_v36`:
  ff / 85 C / 3.6 V / 0xFF) were submitted and checked FIRST; the remaining six requests went out
  only after both cells reproduced DR-0044 within +0.22 % (table `table.md`, back-to-back section).
  Grid: the 16 DR-0044 over-500 cells (all `0xFF`/`0xC0`/`0x80` ff cells incl. tt 3.6 V, over
  -40/27/85 C), `0xA4` at ff x -40/27/85 C x 3.3/3.6 V (the item-5 failing cells and their
  neighbours), tt / 27 C / 3.3 V reference, ss at 3.6 V (process scaling), plus ff at 3.0 V.
  **Bench-validation probes, disclosed**: before any fleet submission, two single-corner debug
  runs of the same benches were run LOCALLY (`--backend local`, the host rule's sanctioned
  single-corner debug probe, `/tmp` scratch only, no committed receipt): tt/27/3.3/0xFF and
  ff/85/3.6/0xFF. They validated deck convergence and the measurement set; the committed
  back-to-back evidence is the wave-1 batch run.
- `results/20261115T030058-iq-attribution-control-l1/`: the L=1U control (DR-0044's control
  extraction `sim/cmph-fix/rcosc_top_p3_cmphfix.spice`) at one cell (ff / 85 C / 3.6 V / 0xFF).
  Its own stage map (`stage_map_control_l1.json`, built with the pre-rebuild comparator roster
  extracted from git `affc8a64` -- see `rosters/`) registers 99/99 devices the same way; its total
  is compared against DR-0044's committed control figure (779.4 uA) via `iq_report.py --control`.

## Result

`results/20261115T030058-iq-attribution/table.md` (per-cell tables, back-to-back and sum checks);
control: `results/20261115T030058-iq-attribution-control-l1/table.md`. Reading:

- Back-to-back: every corner's probed total sits within **+0.00 % .. +0.27 %** of DR-0044's
  committed figure for the same cell; the sum of stages tracks the measured total to
  |residue| <= 0.009 uA at all 33 cells. The split is trustworthy.
- **Comparator-H carries the largest single share of the ff-hot excess**: it is the largest stage
  at the shipping-code failing cell (211.6 of 555.8 uA at ff / 3.6 V / 85 C / `0xA4`, 38 %) and
  grows steeply with temperature (ff 3.6 V / `0xFF`: 177.0 at -40 C -> 218.7 at 85 C) -- while
  being almost code-flat (+3 % from `0xC0` to `0xFF`).
- **The trim bank carries the code scaling**: 58.9 / 67.6 / 87.0 / 252.8 uA at ff / 3.6 V / 85 C
  for `0x80` / `0xA4` / `0xC0` / `0xFF` -- a 2.3x step from `0xC0` to `0xFF` that the rest of the
  oscillator does not share. This is the same direction DR-0045 priced in reverse (lowering the
  ladder series resistance raised `0xFF` Iq by 18-28 %).
- The latch (+clk drive) and bias stages are 38-77 uA everywhere in the grid; the timing MiM and
  the discharge device draw exactly 0 A (no vdd terminal).
- The L=1U control at the max cell shows the same ranking (trim 262.8, cmp-H 222.5 of 781.0), so
  the attribution is not an artifact of the L 0.7 um change.

Decision record: `spec/decision-records/0046-row8-running-iq-stage-attribution.md` (proposed).

## Tests

`python3 -m pytest sim/iq-attribution` -- offline unit tests for the map builder (offset
registration incl. the ambiguous-signature case, conservation, zero-by-construction assertion,
unresolved-not-guessed) and the report script (sum/residue math, back-to-back gate, sum-check
failure surfacing). The `klt sim` grids themselves are evidence, not tests.
