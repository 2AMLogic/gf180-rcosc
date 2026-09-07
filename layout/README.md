# layout

**Status: first layout increment (issue #13, partial).** This directory now
carries a DRC-clean, LVS-matched GDS for two of `rcosc_top`'s four
sub-blocks — the bias generator (`rcosc_bias`) and the trim bank
(`rcosc_trim_bank`) — reproducible from a committed build script. It does
**not** yet cover `rcosc_comparator`, the `rcosc_top` composition (SR
latch, `MDISCH`, `CTIMING`, wiring the sub-blocks together), or the
post-layout PVT re-verification — see "Scope and follow-up" below.

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
  lvs_ref/               hand-authored-but-generated LVS reference netlists
    rcosc_bias.spice     (see "LVS reference netlists" below for why these
    rcosc_trim_bank.spice are not the schematic netlist verbatim)
  reports/                committed evidence -- DRC/extract/LVS JSON, fresh
    rcosc_bias.{drc,extract,lvs}.json
    rcosc_bias.extracted.spice
    rcosc_trim_bank.{drc,extract,lvs}.json
    rcosc_trim_bank.extracted.spice
```

## Reproducing

```bash
layout/run_checks.sh
```

Regenerates `design/netlist/` (so layout always builds against the current
schematic), rebuilds both GDS from `klt gen` primitives, and re-runs
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
is one `klt gen mos_array` call (single-finger). Both generators produce
DRC-clean gf180mcu geometry (contacts, enclosures, spacing) already — no
geometry in this directory is hand-drawn from scratch. `layout/gen_lib.py`'s
`Composer` imports each generated cell into one composing `klayout.db`
layout, places it at a computed offset, and wires ports together with plain
Manhattan metal1 rectangles (`wire_segment`/`wire_l`/`wire_z`). See
`gen_lib.py`'s and `build_cells.py`'s module docstrings for the exact
floorplan (two rows per cell — a resistor chain, and a row of
switches/bias-transistor above it — and why each cross-row jog stays inside
its own resistor's private x-window rather than sharing a routing channel).

## Known `klt` gaps this build works around (filed upstream)

Both are genuine `klt gen`/`klt lvs` capability gaps for this PDK, not
design-specific issues — filed per `CLAUDE.md`'s friction protocol against
`2AMLogic/klayout-tools`, kept generic there:

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

`rcosc_trim_bank`'s LVS run additionally opts into
`options.parameter_tolerance: 0.001` (klt's disclosed, opt-in relative
tolerance, `klayout_tools/lvs.py` issue #589) to absorb the sub-0.1% grid-
rounding deltas the `--check`-verified GDS's 1 nm database unit introduces
against the reference's directly-computed `sheet_rho * r_length/r_width`
values (plus `R1`'s deliberate 0.1 nm nudge above) — every tolerated
parameter difference is disclosed in `reports/rcosc_trim_bank.lvs.json`'s
`device.parameter_tolerated` entries (both original values), not silently
absorbed. `rcosc_bias` needs no tolerance (`status: "match"`, 0
mismatches, 0 tolerated deltas).

## Scope and follow-up

This issue's acceptance criteria cover the full `rcosc_top` hierarchy
(bias generator, 2x comparator, trim bank, top-level composition) plus a
post-layout PVT re-verification subset. Drawing and verifying that whole
hierarchy transistor-by-transistor in one pass — while also learning (and
in two cases, working around bugs in) `klt gen`/`klt gen-compose`/`klt
lvs`'s gf180mcu support for the first time in this repo — was assessed as
too large for one PR (builder-complexity.md's decomposition criteria: this
increment alone touched 7 new files and needed real DRC/LVS iteration on 2
of 4 sub-blocks). This increment lands `rcosc_bias` and `rcosc_trim_bank`
DRC-clean and LVS-matched, resolves this file's previously-flagged "LSB
trim-bank segment DRC risk" concretely (see below), and files/documents
every `klt` gap hit along the way so the remaining sub-blocks do not
re-discover them. The remainder (`rcosc_comparator` layout, the `rcosc_top`
composition, and the post-layout PVT re-verification subset) is tracked in
follow-up issue(s) linked from #13.

**The LSB trim-bank segment DRC risk `design/README.md` previously flagged
is resolved, empirically, not just asserted**: `rcosc_trim_bank.gds`'s `R0`
(`0.7482 um`, the shortest segment) is DRC-clean as drawn; `klt`'s curated
gf180mcu deck has no resistor minimum-*length* rule at all (only
`poly2.width.1`, a minimum *width* — i.e. perpendicular-to-current-flow —
of `0.18 um`, which every segment's `r_width=2u` clears trivially). The
only DRC issue any trim-bank segment length actually hit was `R1`'s
half-nm-grid-tie generator bug above, unrelated to segment shortness (`R0`,
shorter still, is clean).
