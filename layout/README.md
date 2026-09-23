# layout

**Status: full `rcosc_top` hierarchy, re-spun current with the post-#57
schematic (issues #13 + #27 + #44 + #50 + #57).** This directory carries a
DRC-clean, LVS-matched GDS for all of `rcosc_top`'s sub-blocks -- the bias
generator (`rcosc_bias`), the trim bank (`rcosc_trim_bank`), the two
comparators (`rcosc_comparator` for `XXCMPH`, and since issue #57 the
complementary PMOS-input `rcosc_comparator_p` for `XXCMPL`) -- plus the
`rcosc_top` top-level composition itself (the inline SR latch, `MDISCH`,
the `CTIMING` MiM cap, and the wiring that instantiates the four sub-cells
as real GDS sub-cells, not redrawn geometry) -- all reproducible from one
committed build script. The post-layout (PEX-extracted) PVT re-verification
this schematic-level layout enables was tracked separately as issue #28,
re-run against the bias re-spin as part of issue #44, and re-run against
the trim re-spin as part of issue #50; the post-#57 pass against the new
comparator cell is the pending follow-up in that series.

**Current with the post-#57 schematic (issue #57's re-spin):** `rcosc_bias`
was re-spun minimally (one new `pb` pad above P1's gate column, its GDS
otherwise byte-for-byte the #44 geometry) to export the beta-multiplier's
PMOS gate bus for the new cell's 4:1 tail mirror; `rcosc_comparator_p` is
new (one-row-plus-`Channel`, the load/buffer NMOS first, the five PMOS --
tail, input pair, both buffer pfets -- sharing one drawn n-well with its
`well_island` tap); `rcosc_top` recomposes with `XXCMPL` as the new cell
and routes the new `pb` net. `rcosc_trim_bank.gds` and
`rcosc_comparator.gds` are byte-for-byte unchanged from #50/#27 (reproced
identically by the pinned toolchain). Two verification-apparatus repairs
shipped with the re-run, both pre-existing on `main`: `run_checks.sh` now
**pins klt 0.4.0** (0.5.0's generators draw different geometry and would
silently rewrite every committed cell), and `erc-supply-spec.json`'s tie
uses the **32/0 tap marker layer** because klt erc 0.4.0 ignores
`tap_requires` (upstream klayout-tools#2358) -- the old 22/0 spelling
merged every in-well diffusion into the supply net and reported vdd/vss
shorted on the untouched pre-#57 GDS too. The hierarchy re-verified end to
end -- DRC clean, LVS matched, supply-ERC one island per supply for all
five cells.

**Current with the post-#43 schematic (issue #50's re-spin):** the
`rcosc_trim_bank` cell geometry was re-drawn against the
transmission-gate shunt restructure issue #43 put on `main`
([DR-0014](../spec/decision-records/0014-trim-bank-pass-switch-restructure.md))
-- per-position `SW<i>`/`PW<i>` pairs at `L=0.28u` (widths
24/16/12/8/6/5/4/3 µm) with per-bit 2u/4u `L=0.5u` complement inverters,
a new `vdd` pin, and `vss` back as a real routed net. The restructure is
not planar in metal1 (`tb<i>` must cross every c-node column; the rails
cross the `t<i>` columns), so the cell moved from issue #13's two-row
planar shape to the same one-row-plus-`Channel` discipline the comparator
(#27) and the re-spun bias cell (#44) use, with all sixteen PMOS sharing
one drawn n-well + `well_island` tap on `vdd`. The recomposed `rcosc_top`
also fixes a latent pad-mapping bug the new pin exposed (two trim pins
land on the top's `vdd`; the pad table is collision-safe now). The
hierarchy was re-verified end to end -- DRC clean, LVS matched,
supply-ERC one-island-per-supply -- and the post-layout (PEX) PVT
re-verification re-run against the re-spun GDS: see
[DR-0015](../spec/decision-records/0015-trim-bank-respin-postlayout-pex-reverification.md),
which supersedes
[DR-0010](../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)'s
and
[DR-0013](../spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md)'s
figures for the post-#43 schematic (the parasitic frequency shift
deepened on the mean: −17.46 % … −40.92 %, mean −27.32 %, always
slower). The bias cell was re-spun current earlier per #44; the
comparator and its evidence are byte-for-byte the pre-re-spin cell
(verified against this toolchain's own reproducibility check over the
unmodified builders).


## What's checked in

```
layout/
  gen_lib.py           Composer: klt gen -> place -> wire -> pin-label -> GDS
  netlist_parse.py      tiny parser reading device geometry out of
                         design/netlist/rcosc_top.spice (never hand-retyped)
  build_cells.py        builds layout/cells/*.gds + layout/lvs_ref/*.spice
  run_checks.sh          regen-netlist + build + DRC + extract + LVS
                         + supply ERC, writes layout/reports/*.json
  erc-supply-spec.json  klt erc spec for the T1 item-11 supply-island read
                         (see "Supply ERC (T1 item 11)" below; every
                         stackup/via/label field is justified in its
                         _comment block)
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
  reports/                committed evidence -- DRC/extract/LVS ERC JSON,
                         fresh
    rcosc_bias.{drc,extract,lvs}.json
    rcosc_bias.extracted.spice
    rcosc_trim_bank.{drc,extract,lvs}.json
    rcosc_trim_bank.extracted.spice
    rcosc_comparator.{drc,extract,lvs}.json
    rcosc_comparator.extracted.spice
    rcosc_top.{drc,extract,lvs}.json
    rcosc_top.extracted.spice
    rcosc_top.erc.json     T1 item 11 structural power-delivery evidence
                           (supply islands; input content-hash pinned to
                           the committed GDS)
```

## Reproducing

```bash
layout/run_checks.sh
```

Regenerates `design/netlist/` (so layout always builds against the current
schematic), rebuilds all four GDS from `klt gen` primitives (plus, for
`rcosc_top`, sub-cell instantiation of the other three), and re-runs
`klt drc` / `klt extract` / `klt lvs` for each cell, asserting `status ==
"clean"` / `"match"` and failing loudly otherwise — then the block-level
`klt erc` supply-island check of the section below. `layout/build_cells.py
--check` (no `design/regen-netlist.sh` re-run) verifies the committed GDS +
reference netlists are byte-identical to a fresh rebuild, without touching
them — the same "derived, not hand-written, and reproducible on change"
convention `design/regen-netlist.sh` documents for the schematic netlists.

**Which `klt` reproduces which artifact (recorded here because it is
load-bearing, and discovered the hard way on issue #44's re-spin):** every
per-cell DRC/extract/LVS report in `layout/reports/` records the toolchain
that produced the committed cells — `klt 0.4.0` with `klayout 0.30.12` —
and byte-identical cell reproduction (and the re-spin's own bias/top
evidence) holds under exactly that pair, while `klt erc` and `klt signoff`
grading require the newer pinned build (`klt 0.5.0+g2b1e55e51bb8…`, the
same version string `reports/rcosc_top.erc.json` records). `klt gen`'s
drawn output is **not stable across `klayout-tools` versions**: the
0.5.0-era generators render `res_array` footprints and an output grid
that differ from the 0.4.0 era, so under a newer `klt` alone
`layout/build_cells.py --check` reports the *unchanged* cells as stale —
reproduce layout GDS with the 0.4.0-era toolchain the reports record
(filed upstream per the friction protocol as
[klayout-tools#2246](https://github.com/2AMLogic/klayout-tools/issues/2246);
see [DR-0013](../spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md)'s
toolchain provenance note).

## Supply ERC (T1 item 11)

`erc-supply-spec.json` + `reports/rcosc_top.erc.json` are this block's
structural power-delivery evidence for klayout-tools design-evidence-tiers
T1 item 11 (added 2026-09-17, klayout-tools#2025), whose analog/custom
branch reads: *"`klt erc` supply spec reports one island per supply and
zero `missing_tie`; LVS reference includes the supply nets (already true
for SPICE references)"*.

What the committed report says, and on what each part rests:

- **One island per supply.** `vdd` and `vss` are declared `kind:
  "supply"`; in the committed report zero `erc.unconnected_net` and zero
  `erc.supply_short` (and zero `erc.multiply_driven_net`) findings name
  either — which is exactly the one-island verdict: `erc.unconnected_net`
  fires on zero *and* on more-than-one island, so its absence plus no
  supply short is "each supply is one connected rail", not merely a
  missing check. The stackup covers the layers the supplies actually
  route on, measured on this GDS: Metal1–Metal2 (intra-block device tabs
  and channel-router columns/tracks) and Metal3–Metal4 (long top-level
  tracks and `CTIMING`'s MiM bottom plate, which `XCTIMING` wires to
  `vss`). `label_layer` is 36/10 (Metal2 pin text) only — verified
  against the stream: that is the one layer this merged GDS puts `vdd` /
  `vss` (and every other pin) text on.
- **`erc.missing_tie` is computed, and clean: zero findings.** The spec
  declares one `ties[]` entry — the upstream deck's own gf180mcu tap
  boolean (an `Nplus`-covered `Comp` shape inside `Nwell`, wired to
  `Metal1`, net `vdd`; the `tap_nplus` derivation of klayout-tools#1084,
  spelled with the optional `tap_requires` intersection key the #2169
  fix added) — so the committed report's zero is graded evidence:
  `erc_coverage` lists `erc.missing_tie:["nwell_vdd_tap"]` under
  `checked`, and every merged n-well polygon (the comparator's PMOS
  group, the top-level latch-PMOS group, the bias core's `P1`/`P2`
  mirror-pair well since issue #44's re-spin, and — since issue #50's
  re-spin — the trim bank's sixteen-pfet group, each with its
  `well_island` tap routed to the `vdd` track) carries a tap that reaches
  the `vdd` net. **Coverage caveat, kept visible rather than papered
  over:** this grades the *drawn-well* half only. gf180mcu has no drawn
  p-tub/substrate layer, so per `klt erc`'s own contract a substrate tie
  "cannot be declared at all: `well_layer` requires drawn geometry, so
  only the drawn-well half of such a design is graded" — and klt
  extract's gf180mcu deck likewise synthesizes body/well ties
  (`vsubs`) rather than geometrically verifying drawn taps (see "LVS
  reference netlists" below). The p-substrate half of the question is
  outside what this run can ask; device-level body verification stays
  with item 4's full-connectivity LVS, matching with `VDD`/`VSS` in
  `net_correspondence` as pins. (Why `ties[]` was previously omitted and
  why that is obsolete under the pinned grader: the pre-#2169 model
  collapsed routed layouts into one island — see the gaps list below;
  the pinned grader ships the fix, and `klt signoff`'s item 11 now
  *requires* a declared tie — "an uncomputed check is not a clean one".)
- **The report's overall `status` is `"violations"`, and item 11 does
  not grade that.** Its findings (60 on the current, issue-#50 re-spun
  GDS; 36 on the #44 re-spin; 32 pre-re-spin) are all `erc.floating_gate`, the
  disclosed artifact of omitting the `Contact` (33/0) vias entry: the
  bias generator's resistor ladder is drawn poly straight across the
  rails (`vdd→vh→vl→vss`, plus the trim chain
  `vdd→vc` and — on the re-spun core — `n2s→vss`'s degeneration
  resistor), and `klt erc` has no device recognition, so with
  `Contact` declared those resistor bodies conduct the two supplies into
  one island and report a false `erc.supply_short`. Omitting `Contact`
  keeps the supply verdict about the metal power delivery —
  measured both ways on this GDS — at the cost of reporting every real,
  contacted gate as floating (klayout-tools#2183; item 11's own text
  pre-declares antenna-verdict and floating-gate findings non-blocking,
  klayout-tools#1994). Antenna verdicts themselves are all `"unchecked"`:
  the run passes no `--pdk`, and `klt erc`'s antenna-ratio table covers
  sky130 only.
- **Freshness is pinned, not asserted.** The report's
  `provenance.input.content_hash` is the sha256 of
  `cells/rcosc_top.gds` and `provenance.spec.content_hash` is the
  sha256 of the spec — `run_checks.sh` re-verifies the first on every
  run, and the signoff verifier re-verifies both (plus the manifest's
  item-11 pins) in CI, so a regenerated-but-stale pair fails the check.

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

Every cell in the hierarchy is now channel-routed on
`gen_lib.Channel`'s two-layer discipline (metal1 columns, metal2 tracks —
the top level one layer pair higher): `rcosc_comparator` and `rcosc_top`
adopted it at issue #27, `rcosc_bias` at issue #44's re-spin (the PMOS
gate bus is not planar in metal1), and `rcosc_trim_bank` at issue #50's
re-spin (the `tb<i>` inverter buses and the two rails cross the c-node and
`t<i>` terminal runs). Issue #13's two-row planar trim bank — a resistor
chain with a row of shunt switches above it, wired with
`wire_segment`/`wire_l`/`wire_z` so each cross-row jog stayed inside its
own resistor's private x-window — survives only in history: it was
planar precisely because pre-#43 every shunt was one nfet, which the
transmission-gate restructure ended. The bias cell's own re-spin (#44)
forced the same move for its own reason ("the PMOS gate bus `pb` must
reach five terminals across the cell and `vl` must reach `SEED`'s gate
across them"), so it too shares the comparator's row-plus-`Channel` and
n-well constructions verbatim (one row of blocks, `P1`/`P2` sharing a
drawn n-well with a `well_island` tap on `vdd`). What
`rcosc_comparator`/`rcosc_top` (issue #27) additionally needed:

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
- **[klayout-tools#2169](https://github.com/2AMLogic/klayout-tools/issues/2169)**
  (*fixed* in the pinned grader): `klt erc`'s pre-fix `ties[]` model
  registered the whole well layer as a conductor and shared its graph
  with `gates[]`, so a declared tie collapsed a real routed layout into
  one electrical island and reported a **false** `erc.supply_short`
  (reproduced four ways in `gf180-drone-fc`'s FRICTION F-034). Hit here
  while building the T1 item-11 supply spec ("Supply ERC" above):
  originally worked around by committing the spec without `ties[]`;
  the pinned grader (`0.5.0+g2b1e55e51bb8`) ships the fix — a declared
  well is never a conductor, a tie contributes only its `tap_requires`
  tap sites, and `ties[]` runs in an extraction that cannot alter any
  other rule — so the spec now declares the tie (`Comp` intersected
  with `Nplus`, per the deck's own tap definition) and grades
  `erc.missing_tie` instead of omitting it. Regenerating the report
  with the tie declared reproduced the guarantee on this GDS: still
  exactly 32 `erc.floating_gate` findings, zero supply findings,
  byte-comparable `gates[]` and `coverage`.
- **[klayout-tools#2183](https://github.com/2AMLogic/klayout-tools/issues/2183)**:
  `klt erc` registers no device recognition, so a drawn resistor body is
  indistinguishable from a wire — any block whose topology deliberately
  spans two declared supplies through an on-chip resistor (this block's
  bias ladder and trim chain are exactly that) reports a **false**
  `erc.supply_short` with a spec that declares `Contact`, and likewise a
  MiM cap's top-plate `Via4` reads as a metal-to-metal short across the
  dielectric. Worked around here by omitting `Contact` and `Via4` from
  the supply spec's `vias[]` (each omission justified in the spec's
  `_comment`, measured both ways on this GDS — see "Supply ERC" above):
  the supply-island verdict stays about the metal rails, and the cost —
  every real gate reported as `erc.floating_gate`, 32 findings — is
  disclosed and pre-declared non-blocking by item 11's own text. The
  LVS-side companion of this gap is this file's "LVS reference netlists"
  note: `klt extract`, which *does* recognize device bodies, is what
  keeps device-level connectivity honest.

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
(pre-#50, `rcosc_trim_bank`'s reference additionally dropped the then
bulk-only `vss` pin from its `.SUBCKT` line for the same reason; since
issue #50's re-spin the pin is back — the per-bit inverter nfets' sources
are a real routed `vss` net) — the **schematic itself is
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
`options.combine_devices: ["nfet"]` (see "Known `klt` gaps" above). The
re-spun `rcosc_bias` (issue #44) carries the same two accommodations for
the same reasons: its `P1`/`P2` pair shares a drawn n-well with a
`well_island` tap on `vdd` (bodies compare on `vdd` directly), and its
8-finger `N2` is respelled `W=16u nf=1` and folded at compare time by the
`options.combine_devices: ["nfet"]` its own LVS run carries
(`layout/run_checks.sh`).

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
