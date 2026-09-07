# layout

**Status: full `rcosc_top` hierarchy (issues #13 + #27).** This directory
carries a DRC-clean, LVS-matched GDS for all four of `rcosc_top`'s
sub-blocks -- the bias generator (`rcosc_bias`), the trim bank
(`rcosc_trim_bank`), the comparator (`rcosc_comparator`, instantiated twice
as `XXCMPH`/`XXCMPL`) -- plus the `rcosc_top` top-level composition itself
(the inline SR latch, `MDISCH`, the `CTIMING` MiM cap, and the wiring that
instantiates the three sub-cells as real GDS sub-cells, not redrawn
geometry) -- all reproducible from one committed build script. The
post-layout (PEX-extracted) PVT re-verification this schematic-level layout
enables is tracked separately, issue #28.

## What's checked in

```
layout/
  gen_lib.py           Composer: klt gen -> place -> wire -> pin-label -> GDS
  netlist_parse.py      tiny parser reading device geometry out of
                         design/netlist/rcosc_top.spice (never hand-retyped)
  build_cells.py        builds layout/cells/*.gds + layout/lvs_ref/*.spice
  run_checks.sh          regen-netlist + build + DRC + extract + LVS, writes
                         layout/reports/*.json
  cells/
    rcosc_bias.gds
    rcosc_trim_bank.gds
    rcosc_comparator.gds
    rcosc_top.gds          instantiates the other three as sub-cells
  lvs_ref/               hand-authored-but-generated LVS reference netlists
    rcosc_bias.spice     (see "LVS reference netlists" below for why these
    rcosc_trim_bank.spice are not the schematic netlist verbatim)
    rcosc_comparator.spice
    rcosc_top.spice
  reports/                committed evidence -- DRC/extract/LVS JSON, fresh
    rcosc_bias.{drc,extract,lvs}.json
    rcosc_bias.extracted.spice
    rcosc_trim_bank.{drc,extract,lvs}.json
    rcosc_trim_bank.extracted.spice
    rcosc_comparator.{drc,extract,lvs}.json
    rcosc_comparator.extracted.spice
    rcosc_top.{drc,extract,lvs}.json
    rcosc_top.extracted.spice
```

## Reproducing

```bash
layout/run_checks.sh
```

Regenerates `design/netlist/` (so layout always builds against the current
schematic), rebuilds all four GDS from `klt gen` primitives (plus, for
`rcosc_top`, sub-cell instantiation of the other three), and re-runs
`klt drc` / `klt extract` / `klt lvs` for each cell, asserting `status ==
"clean"` / `"match"` and failing loudly otherwise. `layout/build_cells.py
--check` (no `design/regen-netlist.sh` re-run) verifies the committed GDS +
reference netlists are byte-identical to a fresh rebuild, without touching
them — the same "derived, not hand-written, and reproducible on change"
convention `design/regen-netlist.sh` documents for the schematic netlists.

## Approach: `klt gen` primitives, composed by hand

Every resistor is one `klt gen res_array` call (`num=1` — these are not a
*matched* array, each has its own binary-weighted length per "Trim bank
sizing" in `design/README.md`) and every switch/diode-connected transistor
is one `klt gen mos_array` call. Both generators produce DRC-clean gf180mcu
geometry (contacts, enclosures, spacing) already — no active-device geometry
in this directory is hand-drawn from scratch (the one exception, the MiM
timing capacitor, is called out below). `layout/gen_lib.py`'s `Composer`
imports each generated cell into one composing `klayout.db` layout, places
it at a computed offset, and wires ports together with plain Manhattan
metal rectangles.

`rcosc_bias`/`rcosc_trim_bank` (issue #13) are single-finger, planar-in-
metal1 cells: two rows per cell (a resistor chain, and a row of
switches/bias-transistor above it), wired with `wire_segment`/`wire_l`/
`wire_z` so each cross-row jog stays inside its own resistor's private
x-window rather than sharing a routing channel. `rcosc_comparator`/
`rcosc_top` (issue #27) needed three things those two cells did not:

- **Multi-finger devices.** `rcosc_comparator`'s `MTAIL` is `nfet_03v3
  W=16u nf=8` — one folded 8-finger `mos_array` call
  (`finger_topology: "parallel"`, the default), not eight separate devices.
  `klt extract` correctly reports it as 8 parallel `W=2u` `nfet`s; `klt
  lvs`'s `options.combine_devices: ["nfet"]` folds them back into the
  reference's single `W=16u` card (see `run_checks.sh`) — scoped to `nfet`
  specifically so it can never quietly merge an unrelated series-resistor
  pair. Two independent `mos_array` calls are used for the `MINP`/`MINN`
  input pair rather than `klt gen diff_pair`'s common-centroid layout: the
  comparator's offset is a second-order contributor to this design's
  accuracy budget (dominated by R/C spread and trim resolution, DR-0003),
  so `diff_pair`'s mandatory guard ring — which would need cutting open on
  both sides to route four terminals out — was not judged worth it here.
- **A two-layer channel router** (`gen_lib.Channel`, used by `build_cells.py`'s
  `Row`/`Channel` helpers). `rcosc_comparator`'s `dn` net has to cross `dp`'s
  own run to the output buffer, which metal1 alone cannot route without a
  short; `rcosc_top`'s wiring between its four sub-blocks is denser still.
  One horizontal track per net in a channel above a row of blocks, reached
  by one vertical column per terminal below it (metal1 columns, metal2
  tracks) makes an arbitrary, non-planar netlist routable.
- **A shared n-well group** (`Composer.draw_nwell` / `klt gen well_island`).
  `rcosc_comparator`'s three PMOS devices share one drawn n-well with a
  `well_island` tap on `vdd` — without it every PMOS body extracts as an
  anonymous floating net and LVS cannot match a `vdd`-bodied reference.
- **A hand-drawn MiM capacitor** (`Composer.add_mim_cap`). `klt gen
  cap_array` has no gf180mcu plate-layer configuration (see "Known `klt`
  gaps" below) — `CTIMING` is the one device in this design drawn from base
  layers (Metal4 bottom plate, inset FuseTop top plate with `CAP_MK`/
  `MIM_L_MK`, `Via4` up to `Metal5`) rather than a `klt gen` primitive,
  sized to clear `mim.enclosing.fusetop.1`/`mim.space.1` with margin.

See `gen_lib.py`'s and `build_cells.py`'s module docstrings for the exact
floorplan and geometric constants (`ROW_GAP_UM`, `TRACK_PITCH_UM`, etc.) of
each cell.

## Known `klt` gaps this build works around (filed upstream)

Each is a genuine `klt gen`/`klt lvs` capability gap for this PDK, not a
design-specific issue — filed per `CLAUDE.md`'s friction protocol against
`2AMLogic/klayout-tools`, kept generic there (the last two entries below are
included for completeness — one worked as documented, needing no new issue):

- **[klayout-tools#1550](https://github.com/2AMLogic/klayout-tools/issues/1550)**:
  `klt gen res_array`'s gf180mcu support has only one resistor flavor
  (`"generic"`, the base `ppolyf_u`, ~350 Ω/sq) — no way to select the
  PDK's high-sheet-rho `ppolyf_u_1k`/`2k`/`3k` flavors `klt extract`'s own
  gf180mcu deck already recognizes. This design's timing/trim/threshold
  resistor is `ppolyf_u_1k` (DR-0003 sec 5.1/6.1 — the only poly flavor
  gf180mcu publishes TCR data for). Worked around in `gen_lib.py`'s
  `Composer.patch_high_sheet_resistors()`: after generating each resistor,
  draw the gf180mcu `Resistor` (62/0) high-sheet-rho marker over its
  `RES_MK` footprint by hand — the one drawn layer `res_array`'s flavor
  table is missing for gf180mcu. Verified this is load-bearing, not
  cosmetic: before the patch, `klt extract` recognized a `res_array`
  resistor as the base `ppolyf_u` class at ~350 Ω/sq — a >2.5x resistance
  misrecognition, not a naming difference.
- **[klayout-tools#1551](https://github.com/2AMLogic/klayout-tools/issues/1551)**:
  `klt gen res_array --deck gf180mcu` draws a 219 nm (not the required
  220 nm minimum) end contact at `length_um=1.4965` exactly — reproduced in
  isolation, and *only* at that one value (every neighboring length and
  every other resistor length this design uses is clean); looks like a
  half-nanometre grid-tie rounding bug in the generator's own contact-size
  math (`1.4965 um = 1496.5 nm` sits exactly on a 1 nm grid boundary).
  `R1`'s schematic value is exactly `1.4965 um`
  (`design/rcosc_trim_bank.sch`) — worked around in `build_cells.py`
  (`_R1_LENGTH_NUDGE_UM`) by drawing it at `1.4966 um` instead (a 0.1 nm /
  <0.007% resistance nudge, disclosed at the call site and in the LVS
  reference's tolerated-parameter delta below), not a schematic change.
- **(no issue filed, workaround only)** `klt lvs`'s `reference.form:
  "subckt-call"` normalizer (`klayout_tools.netlist_normalize`) only
  converts MOS device calls (anything carrying an `l`/`w` parameter) —
  a resistor `X` call (`r_length`/`r_width` parameters) passes through
  unchanged, so it is never actually converted to a comparable
  plain-element device, and `klt lvs` cannot compare it against the
  layout's real extracted resistor. Worked around by writing this design's
  LVS reference resistors directly in the plain-element `R` form `klt
  extract` itself writes (`R$RBA vdd vh vsubs 50000 ppolyf_u_1k`), computed
  from the same parsed `r_length`/`r_width` (`build_cells.py`'s
  `_res_r_ohm`) rather than retyped. Not filed as a third issue: this is
  the same underlying gap as klayout-tools#1550 (resistor support is a
  second-class citizen throughout this part of `klt`'s gf180mcu tooling),
  documented here rather than opening a duplicate.
- **[klayout-tools#1555](https://github.com/2AMLogic/klayout-tools/issues/1555)**:
  `klt gen cap_array` rejects the `gf180mcu` PDK family outright
  (`"PDK family 'gf180mcu' has no MiM capacitor plate layers configured --
  supported families: sky130, sg13g2"`). This is the specific gf180mcu
  follow-on issue #1117 (the issue that first added `cap_array`, sky130-only)
  explicitly anticipated splitting out as separate work, and that #1455 later
  filed and closed for `sg13g2` — but no equivalent gf180mcu issue existed
  before this repo hit the gap, so #1555 is that missing follow-on, not a
  duplicate. Worked around by hand-drawing `CTIMING` from base layers
  (`Composer.add_mim_cap`, see "Approach" above) instead of `cap_array` —
  DRC-clean and LVS-matched against `klt extract`'s existing `mim_cap`
  deck-option flavour selection (see below), just without `cap_array`'s
  row-layout/`matched_group_id` conveniences (moot here: `CTIMING` is a
  single fixed-size capacitor, not a matched array).
- **(worked, not a gap)** `klt extract --deck-option
  mim_cap=cap_mim_1f0_m4m5_noshield` (`rcosc_top`'s `DECK_OPTIONS` in
  `run_checks.sh`) correctly selects this design's `cap_mim_1f0fF` MiM
  density (as opposed to the deck's `cap_mim_2f0_m4m5_noshield` default) —
  this is klayout-tools#1151's `--deck-option` mechanism, already merged
  upstream by the time this issue started; confirmed working as documented,
  not a new gap to file.

## LVS reference netlists (`layout/lvs_ref/`)

Not the schematic's own `X...ppolyf_u_1k...`/`X...nfet_03v3...` subckt-call
text verbatim (beyond the resistor-conversion gap above, there is a second,
more fundamental reason): `klt`'s curated gf180mcu extraction deck has no
distinct substrate-tap layer, so it unconditionally ties *every* NMOS body
and resistor bulk terminal to one synthesized global net (`vsubs`),
regardless of what — if anything — is drawn (`klayout_tools/decks/
gf180mcu.py`; `klayout_tools/lvs.py`'s `_body_net_warnings` docstring calls
this "structurally unverified" for gf180mcu specifically, `deck.tap is
None`). This design's schematic ties every resistor's third terminal and
every relevant transistor's body to the real `vss` signal net (both a
substrate tie *and* a real circuit node here) — comparing that literally
against the layout's `vsubs` pseudo-net is an unconditional, unfixable-by-
better-layout net split. `layout/lvs_ref/*.spice` therefore rewrites just
that one terminal's net name to `vsubs` to match the deck's own model
(`rcosc_trim_bank`'s reference additionally drops the now-unused `vss` pin
from its `.SUBCKT` line for the same reason) — the **schematic itself is
unchanged**, only the LVS bookkeeping's substrate-tie modeling. This mirrors
`gf180-temp-por`'s own `lvs_reference.py` precedent on this exact PDK
("the third (bulk) node is always rewritten to SUBSTRATE_NET ... regardless
of what the schematic names there").

`rcosc_comparator`'s three PMOS bulk terminals are **not** rewritten to
`vsubs`: unlike the NMOS bodies and resistor bulks above, this cell draws a
real n-well tap (`klt gen well_island`) tying the shared PMOS well to `vdd`,
so the layout genuinely reports those bodies on the `vdd` net and the
schematic's own `vdd` bulk connection compares directly, no accommodation
needed. Its `MTAIL` is written `W=16u nf=1` (the same total-width device,
respelled — `klt`'s reference normalizer rejects `nf>1`) with the layout's
eight drawn fingers folded back together by `klt lvs`'s
`options.combine_devices: ["nfet"]` (see "Known `klt` gaps" above).

`rcosc_top`'s reference is written hierarchically (`XXBIAS`/`XXTRIM`/
`XXCMPH`/`XXCMPL` subcircuit calls, reading like the schematic) but compared
with `options.flatten_reference: true`, since `klt extract` always emits the
layout side flat — the sub-block `.SUBCKT` bodies in
`layout/lvs_ref/rcosc_top.spice` are byte-identical to the three per-cell
references above, so the hierarchy is verified against exactly what each
cell was already verified against on its own.

`rcosc_trim_bank`'s and `rcosc_top`'s LVS runs additionally opt into
`options.parameter_tolerance: 0.001` (klt's disclosed, opt-in relative
tolerance, `klayout_tools/lvs.py` issue #589) to absorb the sub-0.1% grid-
rounding deltas the `--check`-verified GDS's 1 nm database unit introduces
against the reference's directly-computed `sheet_rho * r_length/r_width`
values (plus `R1`'s deliberate 0.1 nm nudge above) — every tolerated
parameter difference is disclosed in each cell's `reports/*.lvs.json`
`device.parameter_tolerated` entries (both original values), not silently
absorbed. `rcosc_bias` and `rcosc_comparator` need no tolerance (`status:
"match"`, 0 mismatches, 0 tolerated deltas).

## gf180mcu geometry notes

**The LSB trim-bank segment DRC risk `design/README.md` previously flagged
is resolved, empirically, not just asserted**: `rcosc_trim_bank.gds`'s `R0`
(`0.7482 um`, the shortest segment) is DRC-clean as drawn; `klt`'s curated
gf180mcu deck has no resistor minimum-*length* rule at all (only
`poly2.width.1`, a minimum *width* — i.e. perpendicular-to-current-flow —
of `0.18 um`, which every segment's `r_width=2u` clears trivially). The
only DRC issue any trim-bank segment length actually hit was `R1`'s
half-nm-grid-tie generator bug above, unrelated to segment shortness (`R0`,
shorter still, is clean).
