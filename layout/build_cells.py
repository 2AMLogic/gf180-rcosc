#!/usr/bin/env python3
"""Build `layout/cells/rcosc_bias.gds` and `layout/cells/rcosc_trim_bank.gds`
from `klt gen` primitives, deterministically, from `design/netlist/
rcosc_top.spice` (issue #13 -- see `layout/README.md` for the full scope
note: this build script covers `rcosc_bias` and `rcosc_trim_bank` only, not
yet `rcosc_comparator` or the `rcosc_top` composition).

    uv run --with klayout --with klayout-tools python3 layout/build_cells.py
    uv run --with klayout --with klayout-tools python3 layout/build_cells.py --check

Needs the `klayout` python module (`klt`'s own runtime dependency) and
`klayout_tools` (`klt` itself) importable. Regenerate `design/netlist/
rcosc_top.spice` first (`design/regen-netlist.sh`) if the schematic changed
-- this script reads device geometry directly out of that file
(`netlist_parse.py`), never retyping `r_length`/`r_width`/`L`/`W`/`nf`, so a
schematic resize and this layout cannot silently drift apart.

## Approach: `klt gen` primitives, not hand-drawn geometry

Every resistor is `klt gen res_array` (one instance per resistor -- our
resistors are not a *matched* array, each has its own binary-weighted
length) and every switch/diode-connected transistor is `klt gen mos_array`
(single-finger). Both generators produce DRC-clean gf180mcu geometry
(contacts, enclosures, spacing) already handled -- see `layout/gen_lib.py`'s
module docstring for the composition mechanics (import, place, wire,
pin-label) and its `patch_high_sheet_resistors()` docstring for the one
gf180mcu-specific workaround this script applies to every resistor
(filed as klayout-tools#1550: `res_array` has no gf180mcu high-sheet-rho
flavor param).

## Known klt gen quirk worked around here (klayout-tools#1551)

`res_array` draws a 219nm (not the required 220nm min) end contact for a
resistor length landing on an *exact* half-nanometre grid tie -- reproduced
in isolation only at `length_um=1.4965` (trim bank `R1`'s exact schematic
value), not any neighbouring length. Worked around by drawing `R1` at
`1.4966um` instead (`_R1_LENGTH_NUDGE_UM` below) -- a 0.1nm / <0.007%
resistance nudge, filed upstream rather than silently absorbed.

## Floorplan

`rcosc_trim_bank` was issue #13's two-row planar cell while every shunt was
one nfet above its own resistor; issue #43's transmission-gate restructure
(DR-0014) ended that -- `tb<i>` must reach `PW<i>`'s gate across every
c-node column between the per-bit inverter and the pfet group, and
`vdd`/`vss` must cross the `t<i>` columns, which metal1 alone cannot route
without a short. The re-spun cell (issue #50) therefore follows the same
one-row-plus-`Channel` discipline as the comparator and the re-spun bias
cell: the nine resistor-chain segments interleaved with each segment's own
shunt nfet and inverter nfet in schematic signal order, then the whole PMOS
group (the eight transmission-gate pfets and the eight inverter pfets) last
so all sixteen PMOS share one drawn n-well with a `well_island` tap on
`vdd`.

`rcosc_bias` was that shape while the pre-#39 reference leg
(`RBIAS`+`MBIASD`) kept it planar; issue #39's self-biased beta-multiplier
core (issue #44's re-spin) is not planar in metal1 -- the PMOS gate bus
`pb` must reach five terminals spread across the cell (`P1` gate+drain,
`P2` gate, `N2` drain, `SEED` drain), and `vl` must reach `SEED`'s gate
across them -- so the re-spun cell follows the comparator's proven
one-row-plus-`Channel` discipline (`build_rcosc_comparator`, issue #27):
one row of blocks, metal1 columns, one metal2 track per net above them,
pin pads above the channel. The two PMOS devices share one drawn n-well
with a `well_island` tap on `vdd` (same reason as the comparator's), and
`run_checks.sh` gives this cell's own LVS run the same
`options.combine_devices: ["nfet"]` to fold `N2`'s eight drawn fingers
back into the reference's single wide card.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

LAYOUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAYOUT_DIR.parent
CELLS_DIR = LAYOUT_DIR / "cells"
LVS_REF_DIR = LAYOUT_DIR / "lvs_ref"
NETLIST_PATH = REPO_ROOT / "design" / "netlist" / "rcosc_top.spice"

sys.path.insert(0, str(LAYOUT_DIR))

import gen_lib  # noqa: E402
from gen_lib import Channel, Composer  # noqa: E402
from netlist_parse import Device, parse_subckt, parse_subckt_pins  # noqa: E402

SHEET_RHO_OHM_SQ = 1000.0  # ppolyf_u_1k, DR-0003 sec 5.1/6.1

# klayout-tools#1551 workaround -- see module docstring.
_R1_LENGTH_NUDGE_UM = 1.4966

# -- issue #27 channel-routed cells (rcosc_comparator, rcosc_top) ------------
#
# One row of blocks, one horizontal track per net in a channel above it, one
# vertical column per terminal (see gen_lib.Channel). These are the geometric
# constants that discipline shares; every one of them is a clearance, never a
# device dimension (device geometry still comes only from netlist_parse).
ROW_GAP_UM = 4.0  # inter-block gap: hosts two terminal columns
COL_OFFSET_UM = 1.4  # terminal column offset from a block's own edge
TRACK_PITCH_UM = 0.9  # >= metal{2,3}.width (0.28) + space (0.28) + wire width
CHANNEL_CLEARANCE_UM = 2.0  # row top -> first track
PAD_CLEARANCE_UM = 1.5  # top track -> pin-pad row

#: gf180mcu MiM density this design commits to -- `cap_mim_1f0fF` in the
#: schematic, `cap_mim_1f0_m4m5_noshield` as `klt extract`'s (and the PDK's own
#: LVS deck's) device-class name for the same drawn FuseTop-over-Metal4 stack.
#: Selected at extraction time with `--deck-option mim_cap=...`.
MIM_CAP_CLASS = "cap_mim_1f0_m4m5_noshield"
#: `sm141064.ngspice`'s `.subckt cap_mim_1f0fF` at the `mimcap_typical` corner,
#: as transcribed by `klayout_tools.decks.gf180mcu`'s own `CapacitorFlavour`
#: entry for this class: c_cox (area) and c_capsw (perimeter/fringe).
MIM_AREA_CAP_F_UM2 = 9.87e-16
MIM_PERIM_CAP_F_UM = 3.3e-16


def _res_r_ohm(length_um: float, width_um: float) -> float:
    return SHEET_RHO_OHM_SQ * length_um / width_um


def _mim_c_farad(width_um: float, length_um: float) -> float:
    """The capacitance `klt extract` reports for a `width_um` x `length_um`
    MiM top plate, from the deck's own two-term area+perimeter law."""
    area = width_um * length_um
    perimeter = 2.0 * (width_um + length_um)
    return area * MIM_AREA_CAP_F_UM2 + perimeter * MIM_PERIM_CAP_F_UM


def _mos_params(d: Device) -> dict:
    """`klt gen mos_array` params for one schematic MOS instance.

    `nf` is the schematic's finger count and `W` its *total* channel width
    (gf180mcu's own convention -- its device subckts compute per-finger
    geometry as `W/nf`, see any `ad=`/`pd=` expression in
    `design/netlist/rcosc_top.spice`), so the generator's per-finger `w_um` is
    `W/nf`. Every device in #13's two cells had `nf=1`, making the two
    spellings indistinguishable; `rcosc_comparator`'s `MTAIL` (`W=16u nf=8`)
    is the first place they differ, and getting it backwards would draw a
    128um-wide device."""
    nf = d.param_int("nf")
    flavor = "pfet" if d.model.startswith("pfet") else "nfet"
    return {
        "w_um": d.param_um("w") / nf,
        "l_um": d.param_um("l"),
        "fingers": nf,
        "rows": 1,
        "cols": 1,
        "dummy": 0,
        "flavor": flavor,
        "gate_contact": True,
    }


class Row:
    """Places blocks left to right on one baseline, tracking the x cursor and
    each block's own terminal-column x positions."""

    def __init__(self, composer: Composer, y_um: float = 0.0, gap_um: float = ROW_GAP_UM):
        self.c = composer
        self.y_um = y_um
        self.gap_um = gap_um
        self.cursor_um = 0.0
        self.left_um: dict[str, float] = {}
        self.right_um: dict[str, float] = {}
        self.top_um = 0.0

    def place(self, generator: str, params: dict, label: str):
        bx0, _, bx1, by1 = self.c.peek_bbox(generator, params)
        # `bbox_um` is relative to the generated cell's own origin, and a pfet's
        # well pushes it negative -- offset the placement so the *occupied*
        # left edge lands on the cursor.
        x0 = self.cursor_um - bx0
        placed = self.c.gen_and_place(generator, params, x0, self.y_um, label)
        occupied_left = self.cursor_um
        occupied_right = x0 + bx1
        self.left_um[label] = occupied_left - COL_OFFSET_UM
        self.right_um[label] = occupied_right + COL_OFFSET_UM
        self.top_um = max(self.top_um, self.y_um + by1)
        self.cursor_um = occupied_right + self.gap_um
        return placed

    def place_cell(self, gds_path, cell_name: str, label: str) -> dict:
        """Instantiate an already-built cell as a sub-cell of this row and
        return `{pin: (x, y)}` in the composing cell's coordinate frame."""
        bx0, _, bx1, by1 = Composer.peek_gds_bbox(str(gds_path), cell_name)
        x0 = self.cursor_um - bx0
        self.c.place_gds(str(gds_path), cell_name, x0, self.y_um)
        self.left_um[label] = self.cursor_um - COL_OFFSET_UM
        self.right_um[label] = x0 + bx1 + COL_OFFSET_UM
        self.top_um = max(self.top_um, self.y_um + by1)
        self.cursor_um = x0 + bx1 + self.gap_um
        return {"__origin__": (x0, self.y_um)}

    def place_mim_cap(self, width_um: float, length_um: float, label: str) -> tuple:
        """Draw the timing capacitor as one more block in this row, and return
        its two Metal4 terminal points."""
        margin = gen_lib.MIM_PLATE_MARGIN_UM
        x0 = self.cursor_um + margin
        bottom, top = self.c.add_mim_cap(x0, self.y_um + margin, width_um, length_um)
        occupied_right = top[0] + 0.21
        self.left_um[label] = self.cursor_um - COL_OFFSET_UM
        self.right_um[label] = occupied_right + COL_OFFSET_UM
        self.top_um = max(self.top_um, self.y_um + 2 * margin + length_um)
        self.cursor_um = occupied_right + self.gap_um
        return bottom, top


# `rcosc_bias`'s row, left to right (issue #44's re-spin): the unchanged
# vh/vl resistor ladder first (same three RBA/RBB/RBC strips the pre-#39
# cell drew), then the post-#39 self-biased beta-multiplier core's devices in
# schematic signal order -- N1 (the diode-connected reference unit), N2 (the
# mirrored 8-finger output device), its source degeneration resistor RZ, the
# weak SEED pull-down, and the P1/P2 pfet mirror pair last so the two PMOS
# can share one drawn n-well with its tap island, exactly as
# `build_rcosc_comparator` does (gf180mcu's `nwell.space.1` is 0.6um even
# between equipotential wells; one drawn well is both DRC-legal and the real
# device model). No NMOS may sit inside that well rectangle -- `klt
# extract`'s MOS split is "active inside the well is PMOS, outside is
# NMOS" (see `gen_lib.Composer.draw_nwell`).
_BIAS_ROW_ORDER = ["XRBA", "XRBB", "XRBC", "XN1", "XN2", "XRZ", "XSEED", "XP1", "XP2"]
#: Track order (bottom-up) in the bias cell's routing channel. The two
#: internal core nets go first (they carry the most columns and benefit from
#: the shortest runs), then the exported pins. `pb` (the PMOS gate bus) and
#: `n2s` are the two nets the pre-#39 cell did not have and the reason this
#: cell is channel-routed rather than planar -- `pb` alone must reach five
#: terminals across the whole row (`P1` gate+drain, `P2` gate, `N2` drain,
#: `SEED` drain), which metal1-only wiring cannot route without a short.
_BIAS_TRACKS = ["pb", "n2s", "ibias", "vl", "vh", "vdd", "vss"]
_BIAS_PINS = ["vdd", "vss", "vh", "vl", "ibias", "pb"]


def _res_params(d: Device) -> dict:
    """`klt gen res_array` params for one schematic resistor instance."""
    return {
        "length_um": d.param_um("r_length"),
        "width_um": d.param_um("r_width"),
        "num": 1,
        "dummy": 0,
    }


def build_rcosc_bias(devices: dict) -> tuple[Composer, list[str]]:
    """The re-spun bias cell (issue #44): the unchanged vh/vl ratiometric
    ladder plus issue #39's self-biased beta-multiplier current-reference
    core (`P1`/`P2` pfet mirror, `N1` reference diode driving the exported
    `ibias` node, `N2` degenerated by `RZ`, `SEED` start-up pull-down),
    drawn against the post-#39 `design/rcosc_bias.sch`.

    One row of blocks, one metal2 track per net above it, one metal1 column
    per terminal -- `gen_lib.Channel`'s discipline, for the same structural
    reason `rcosc_comparator` needed it (a net {pb} that must cross other
    nets' terminal runs). The five sub-cell boundary pins land as one pad
    row above the channel, mirroring the comparator, so the top-level
    composition routes to this cell exactly as it routed to the old one:
    same five pins (`vdd vss vh vl ibias`, unchanged subckt order -- issue
    #39 deliberately kept the boundary interface) plus the `pb` export issue
    #57 adds for `rcosc_comparator_p`'s tail mirror, only the coordinates
    move, and `build_rcosc_top` reads those from this builder's reported
    `pins_um` rather than any hard-coded position."""
    c = Composer("rcosc_bias")
    row = Row(c)

    placed: dict[str, object] = {}
    for name in _BIAS_ROW_ORDER:
        d = devices[name]
        if d.model == "ppolyf_u_1k":
            params = _res_params(d)
        else:
            params = _mos_params(d)
        placed[name] = row.place(
            "res_array" if d.model == "ppolyf_u_1k" else "mos_array",
            params, name.lower()[1:],
        )

    # One n-well over the PMOS mirror pair plus its tap island, merging the
    # generators' own per-device wells into one equipotential well tied to
    # vdd (same construction and rationale as the comparator's well group).
    well_x0 = row.left_um["p1"] + COL_OFFSET_UM - 0.5
    p_well = row.place(
        "well_island",
        {
            "inner_width_um": 1.0,
            "inner_height_um": 1.0,
            "contacts_per_side": 1,
            # The label this generator would draw sits on the ring's own metal
            # inside a sub-cell, where `klt extract` does not reliably promote
            # it to a pin -- this cell names `vdd` on its own pin pad instead.
            "net": "",
        },
        "pwell_tap",
    )
    well_x1 = row.right_um["pwell_tap"] - COL_OFFSET_UM + 0.5
    c.draw_nwell(well_x0, -0.65, well_x1, row.top_um + 0.5)

    ch = Channel(
        c,
        column_layer=gen_lib.METAL1,
        track_layer=gen_lib.METAL2,
        track_via=gen_lib.VIA1,
        y0_um=row.top_um + CHANNEL_CLEARANCE_UM,
        pitch_um=TRACK_PITCH_UM,
    )

    def terminal(dev_name: str, port: str, net: str, column_x: float) -> None:
        x, y, _ = placed[dev_name].port_abs(port)
        ch.add(net, x, y, column_x)

    # `nodes` is the schematic's own terminal order -- [a, b, bulk] for the
    # resistor calls and [d, g, s, b] for the MOS calls -- so every net
    # below is read from the netlist, never retyped. MOS bulk (body)
    # terminals are not routed: NMOS bodies extract to the deck's
    # synthesized `vsubs` and the PMOS bodies take their `vdd` identity from
    # the drawn well tap above, exactly as the LVS reference models them.
    for name in _BIAS_ROW_ORDER:
        key = name.lower()[1:]
        d = devices[name]
        if d.model == "ppolyf_u_1k":
            terminal(name, "R0_A", d.nodes[0], row.left_um[key])
            terminal(name, "R0_B", d.nodes[1], row.right_um[key])
        else:
            d_net, g_net, s_net, _b_net = d.nodes
            terminal(name, "U0_S", s_net, row.left_um[key])
            terminal(name, "U0_D", d_net, row.right_um[key])
            gate_x, _, _ = placed[name].port_abs("U0_G")
            terminal(name, "U0_G", g_net, gate_x)

    tap_x, tap_y, _ = p_well.port_abs("TAP_N")
    ch.add("vdd", tap_x, tap_y, tap_x)

    ch.route(_BIAS_TRACKS)
    pad_y = ch.top_y_um(_BIAS_TRACKS) + PAD_CLEARANCE_UM
    # One pin pad per exported net, each above an existing column of the
    # same net so the pad column's vertical run is continuous from track
    # to pad (the comparator's own discipline: pin pads only at columns
    # the net already reaches).
    pin_column = {
        "vdd": row.left_um["rba"],  # RBA.A -- the ladder's vdd terminal
        "vss": row.right_um["rbc"],  # RBC.B -- the ladder's vss terminal
        "vh": row.right_um["rba"],  # RBA.B -- the ladder's vh node
        "vl": row.right_um["rbb"],  # RBB.B -- the ladder's vl node
        "ibias": placed["XN1"].port_abs("U0_G")[0],  # N1's diode-connected gate
        # issue #57: the beta-multiplier's PMOS gate bus, previously internal,
        # exported for rcosc_comparator_p's tail mirror -- pad above P1's own
        # gate column, the net's densest column in this cell.
        "pb": placed["XP1"].port_abs("U0_G")[0],  # P1's diode-connected gate
    }
    pins_um = {}
    for net in _BIAS_PINS:
        pins_um[net] = ch.pin_pad(net, pin_column[net], pad_y, gen_lib.METAL1_LABEL)

    # MUST be the end of the build: relaunched PCell re-evaluation wipes
    # the markers `patch_high_sheet_resistors()` draws if any `klt gen`
    # call happens after it (see `place_gds`'s docstring).
    patched = c.patch_high_sheet_resistors()
    assert patched == 4, f"expected 4 resistors patched (RBA/RBB/RBC/RZ), got {patched}"
    # Pin coordinates, for `build_rcosc_top` to route to when it instantiates
    # this cell -- reported from the same pads the labels were placed on,
    # never re-measured off the written GDS.
    c.pins_um = pins_um
    return c, _BIAS_PINS


# `rcosc_trim_bank`'s row, left to right (issue #50's re-spin against the
# post-#43 schematic, DR-0014): the nine resistor-chain segments each
# followed by their own shunt nfet `SW<i>` and the per-bit complement
# inverter's nfet `NINV<i>` (schematic signal order), then the whole PMOS
# group last -- the eight transmission-gate pfets `PW<i>` and the eight
# inverter pfets `PINV<i>` -- so all sixteen PMOS share one drawn n-well
# with its `well_island` tap on `vdd` (same construction and reason as the
# comparator's and the re-spun bias cell's well groups). No NMOS may sit
# inside that well rectangle (`klt extract`'s MOS split is "active inside
# the well is PMOS, outside is NMOS").
_TRIM_RES_ORDER = ["XRFIX"] + [f"XR{i}" for i in range(8)]
_TRIM_ROW_ORDER = (
    ["XRFIX"]
    + [dev for i in range(8) for dev in (f"XR{i}", f"XSW{i}", f"XNINV{i}")]
    + [f"XPW{i}" for i in range(8)]
    + [f"XPINV{i}" for i in range(8)]
)
#: Track order (bottom-up) in the trim bank's routing channel: the ladder
#: nodes first (they span the whole row), then the per-bit gate/inverter
#: pairs, then the two rails, then the exported endpoint pins.
_TRIM_TRACKS = (
    ["p", "m"]
    + [f"c{i}" for i in range(1, 9)]
    + [f"tb{i}" for i in range(8)]
    + [f"t{i}" for i in range(8)]
    + ["vdd", "vss"]
)
#: The re-spun cell's boundary pins, in the post-#43 schematic's own subckt
#: order (`p m vss t0..t7 vdd`) -- `vdd` is new and `vss` is back to being
#: a real routed net (the per-bit inverter nfet sources), where pre-#43 it
#: was a bulk-only tie the LVS reference modeled as `vsubs` and dropped.
_TRIM_PINS = ["p", "m", "vss"] + [f"t{i}" for i in range(8)] + ["vdd"]


def build_rcosc_trim_bank(devices: dict) -> tuple[Composer, list[str]]:
    """The re-spun trim bank (issue #50): the unchanged binary-weighted
    `ppolyf_u_1k` ladder plus issue #43's per-segment transmission-gate
    shunts (`SW<i>` nfet + `PW<i>` pfet, `L=0.28u`, per-position widths
    24/16/12/8/6/5/4/3 um) and per-bit complement inverters
    (`NINV<i>` 2u / `PINV<i>` 4u at `L=0.5u`) that generate the pfet gates
    `tb<i>`, drawn against the post-#43 `design/rcosc_trim_bank.sch`.

    One row of blocks, one metal2 track per net above it, one metal1 column
    per terminal -- `gen_lib.Channel`'s discipline, for the same structural
    reason `rcosc_comparator` and the re-spun `rcosc_bias` needed it (nets
    that must cross other nets' terminal runs: `tb<i>` from each inverter
    out to its `PW<i>` gate, `vdd`/`vss` across the `t<i>` columns). The
    twelve boundary pins land as one pad row above the channel, so
    `build_rcosc_top` routes to this cell exactly as before: the same pins
    the pre-#43 cell exported plus the new `vdd`, at coordinates read from
    this builder's reported `pins_um`, never hard-coded."""
    c = Composer("rcosc_trim_bank")
    row = Row(c)

    placed: dict[str, object] = {}
    for name in _TRIM_ROW_ORDER:
        d = devices[name]
        if d.model == "ppolyf_u_1k":
            params = _res_params(d)
            if name == "XR1":
                params["length_um"] = _R1_LENGTH_NUDGE_UM
            placed[name] = row.place("res_array", params, name.lower()[1:])
        else:
            placed[name] = row.place("mos_array", _mos_params(d), name.lower()[1:])

    # One n-well over the whole PMOS group plus its tap island, merging the
    # generators' own per-device wells into one equipotential well tied to
    # vdd (same construction and rationale as the comparator/bias well
    # groups; sixteen pfets here instead of three or two).
    well_x0 = row.left_um["pw0"] + COL_OFFSET_UM - 0.5
    p_well = row.place(
        "well_island",
        {
            "inner_width_um": 1.0,
            "inner_height_um": 1.0,
            "contacts_per_side": 1,
            # The label this generator would draw sits on the ring's own metal
            # inside a sub-cell, where `klt extract` does not reliably promote
            # it to a pin -- this cell names `vdd` on its own pin pad instead.
            "net": "",
        },
        "pwell_tap",
    )
    well_x1 = row.right_um["pwell_tap"] - COL_OFFSET_UM + 0.5
    c.draw_nwell(well_x0, -0.65, well_x1, row.top_um + 0.5)

    ch = Channel(
        c,
        column_layer=gen_lib.METAL1,
        track_layer=gen_lib.METAL2,
        track_via=gen_lib.VIA1,
        y0_um=row.top_um + CHANNEL_CLEARANCE_UM,
        pitch_um=TRACK_PITCH_UM,
    )

    def terminal(dev_name: str, port: str, net: str, column_x: float) -> None:
        x, y, _ = placed[dev_name].port_abs(port)
        ch.add(net, x, y, column_x)

    # `nodes` is the schematic's own terminal order -- [a, b, bulk] for the
    # resistor calls and [d, g, s, b] for the MOS calls -- so every net
    # below is read from the netlist, never retyped. MOS bulk (body)
    # terminals are not routed: the NMOS bodies extract to the deck's
    # synthesized `vsubs` and the PMOS bodies take their `vdd` identity from
    # the drawn well tap above, exactly as the LVS reference models them.
    for name in _TRIM_ROW_ORDER:
        key = name.lower()[1:]
        d = devices[name]
        if d.model == "ppolyf_u_1k":
            terminal(name, "R0_A", d.nodes[0], row.left_um[key])
            terminal(name, "R0_B", d.nodes[1], row.right_um[key])
        else:
            d_net, g_net, s_net, _b_net = d.nodes
            terminal(name, "U0_S", s_net, row.left_um[key])
            terminal(name, "U0_D", d_net, row.right_um[key])
            gate_x, _, _ = placed[name].port_abs("U0_G")
            terminal(name, "U0_G", g_net, gate_x)

    tap_x, tap_y, _ = p_well.port_abs("TAP_N")
    ch.add("vdd", tap_x, tap_y, tap_x)

    ch.route(_TRIM_TRACKS)
    pad_y = ch.top_y_um(_TRIM_TRACKS) + PAD_CLEARANCE_UM
    # One pin pad per exported net, each above an existing column of the
    # same net so the pad column's vertical run is continuous from track
    # to pad (the comparator's own discipline: pin pads only at columns
    # the net already reaches).
    pin_column = {
        "p": row.left_um["rfix"],  # RFIX.A -- the ladder's p terminal
        "m": row.right_um["r7"],  # R7.B -- the ladder's m terminal
        "vdd": tap_x,  # the PMOS group's well tap
        "vss": row.left_um["ninv0"],  # NINV0.S -- an inverter source
    }
    pin_column.update(
        {f"t{i}": placed[f"XSW{i}"].port_abs("U0_G")[0] for i in range(8)}
    )
    pins_um = {}
    for net in _TRIM_PINS:
        pins_um[net] = ch.pin_pad(net, pin_column[net], pad_y, gen_lib.METAL1_LABEL)

    # MUST be the end of the build: relaunched PCell re-evaluation wipes
    # the markers `patch_high_sheet_resistors()` draws if any `klt gen`
    # call happens after it (see `place_gds`'s docstring).
    patched = c.patch_high_sheet_resistors()
    assert patched == 9, f"expected 9 resistors patched (RFIX/R0..R7), got {patched}"
    # Pin coordinates, for `build_rcosc_top` to route to when it instantiates
    # this cell -- reported from the same pads the labels were placed on,
    # never re-measured off the written GDS.
    c.pins_um = pins_um
    return c, _TRIM_PINS


# `rcosc_comparator`'s row, left to right. The four NMOS come first and the
# three PMOS last so the PMOS group can share one drawn n-well (see
# `Composer.draw_nwell`): gf180mcu's `nwell.space.1` is 0.6um even between
# equipotential wells, and three separately-walled PMOS bodies would extract as
# three floating nets. `XWELL` is the `well_island` tap that gives that shared
# well its `vdd` identity.
_CMP_ORDER = ["XMTAIL", "XMINP", "XMINN", "XMBUFN", "XMLOADA", "XMLOADB", "XMBUFP"]
_CMP_NFET = ["XMTAIL", "XMINP", "XMINN", "XMBUFN"]
_CMP_PFET = ["XMLOADA", "XMLOADB", "XMBUFP"]
#: Track order (bottom-up) in the comparator's routing channel. Signal nets
#: first (shortest columns for the busiest nets), then the rails, then the
#: three single-terminal input pins.
_CMP_TRACKS = ["tail", "dn", "dp", "out", "vdd", "vss", "ibias", "inp", "inn"]
_CMP_PINS = ["vdd", "vss", "ibias", "inp", "inn", "out"]


def build_rcosc_comparator(devices: dict) -> tuple[Composer, list[str]]:
    """5T differential pair + output buffer, channel-routed (issue #27).

    Structurally different from #13's two cells in three ways, each forced by
    the circuit rather than chosen:

    * **Multi-finger.** `MTAIL` is `W=16u nf=8` -- one folded 8-finger device
      (`mos_array`'s own `finger_topology: "parallel"`), not eight devices.
      `klt extract` reports it as 8 parallel `nfet`s of `W=2u`, which is what
      it physically is; `klt lvs`'s `options.combine_devices` folds them back
      into the reference's single `W=16u` card (see `run_checks.sh`).
    * **Not planar in one layer.** `dn` has to reach both PMOS gates across
      `dp`'s run to the output buffer, so metal1 alone cannot route it without
      a short. Routed instead on `gen_lib.Channel`'s two-layer discipline:
      metal1 columns, metal2 tracks.
    * **A real well tie.** The three PMOS share one drawn n-well with a
      `well_island` tap on `vdd`; without it every PMOS body extracts as an
      anonymous floating net and LVS cannot match a `vdd`-bodied reference.

    Two independent `mos_array` calls are used for the `MINP`/`MINN` input pair
    rather than `klt gen diff_pair`'s common-centroid cross-quad. `diff_pair`
    is the right primitive when *matching* is the binding constraint; here the
    comparator's offset is a second-order contributor to this block's spec
    (the trip points are set by the `rcosc_bias` divider, and the oscillator's
    accuracy budget is dominated by R/C spread and trim resolution, DR-0003),
    while `diff_pair`'s mandatory-by-default guard ring would have to be cut
    open on both sides to route four terminals out of it. Documented here as a
    deliberate choice, not an oversight -- if a post-layout offset sweep ever
    makes comparator matching binding, this is the call to revisit."""
    c = Composer("rcosc_comparator")
    row = Row(c)

    placed = {}
    for name in _CMP_ORDER:
        placed[name] = row.place("mos_array", _mos_params(devices[name]), name.lower()[1:])

    # One n-well over the whole PMOS group plus its tap island, merging the
    # generators' own per-device wells into one equipotential well.
    well_x0 = row.left_um["mloada"] + COL_OFFSET_UM - 0.5
    p_well = row.place(
        "well_island",
        {
            "inner_width_um": 1.0,
            "inner_height_um": 1.0,
            "contacts_per_side": 1,
            # The label this generator would draw sits on the ring's own metal
            # inside a sub-cell, where `klt extract` does not reliably promote
            # it to a pin -- this cell names `vdd` on its own pin pad instead.
            "net": "",
        },
        "pwell_tap",
    )
    well_x1 = row.right_um["pwell_tap"] - COL_OFFSET_UM + 0.5
    c.draw_nwell(well_x0, -0.65, well_x1, row.top_um + 0.5)

    ch = Channel(
        c,
        column_layer=gen_lib.METAL1,
        track_layer=gen_lib.METAL2,
        track_via=gen_lib.VIA1,
        y0_um=row.top_um + CHANNEL_CLEARANCE_UM,
        pitch_um=TRACK_PITCH_UM,
    )

    def terminal(dev_name: str, port: str, net: str, column_x: float) -> None:
        x, y, _ = placed[dev_name].port_abs(port)
        ch.add(net, x, y, column_x)

    # `nodes` is the schematic's own [d, g, s, b] order for these MOS calls, so
    # every net below is read from the netlist, never retyped.
    for name in _CMP_ORDER:
        key = name.lower()[1:]
        d_net, g_net, s_net, _b_net = devices[name].nodes
        terminal(name, "U0_S", s_net, row.left_um[key])
        terminal(name, "U0_D", d_net, row.right_um[key])
        gate_x, _, _ = placed[name].port_abs("U0_G")
        terminal(name, "U0_G", g_net, gate_x)

    tap_x, tap_y, _ = p_well.port_abs("TAP_N")
    ch.add("vdd", tap_x, tap_y, tap_x)

    ch.route(_CMP_TRACKS)
    pad_y = ch.top_y_um(_CMP_TRACKS) + PAD_CLEARANCE_UM
    pin_column = {
        "vdd": row.left_um["mloada"],
        "vss": row.left_um["mtail"],
        "out": row.right_um["mbufn"],
        "ibias": placed["XMTAIL"].port_abs("U0_G")[0],
        "inp": placed["XMINP"].port_abs("U0_G")[0],
        "inn": placed["XMINN"].port_abs("U0_G")[0],
    }
    pins_um = {}
    for net in _CMP_PINS:
        pins_um[net] = ch.pin_pad(net, pin_column[net], pad_y, gen_lib.METAL1_LABEL)

    c.pins_um = pins_um  # consumed by build_rcosc_top when it instantiates this cell
    return c, _CMP_PINS


#: `rcosc_comparator_p`'s row, left to right (issue #57): the four NMOS
#: (the two mirror loads and the two buffer nfets) first, then the whole
#: PMOS group -- tail, input pair, the two buffer pfets -- last so all five
#: PMOS share one drawn n-well with its `well_island` tap on `vdd` (same
#: construction and reason as the trim bank's sixteen-PMOS group; no NMOS
#: may sit inside that well rectangle, `klt extract`'s MOS split is "active
#: inside the well is PMOS, outside is NMOS"). Inside the PMOS group the
#: signal order is kept (tail, then the pair with `inn`/`inp` adjacent so
#: their shared `tailp` sources interleave, then the two buffer stages).
_CMPP_ORDER = [
    "XMNLOADA", "XMNLOADB", "XMBUFN", "XMBUF2N",
    "XMPTAIL", "XMPINN", "XMPINP", "XMBUFP", "XMBUF2P",
]
#: Track order (bottom-up) in the complementary comparator's routing
#: channel, same discipline as the NMOS cell's: internal signal nets first
#: (most columns, shortest runs), then `out`, then the rails, then the
#: three single-terminal input pins.
_CMPP_TRACKS = ["tailp", "dn", "dp", "outb", "out", "vdd", "vss", "pb", "inp", "inn"]
#: Boundary pins in the schematic's own subckt order.
_CMPP_PINS = ["vdd", "vss", "pb", "inp", "inn", "out"]


def build_rcosc_comparator_p(devices: dict) -> tuple[Composer, list[str]]:
    """Complementary (PMOS-input) comparator, channel-routed (issue #57).

    The mirror image of `build_rcosc_comparator`'s construction, cell for
    `design/rcosc_comparator_p.sch` (DR-0017): a PMOS input pair whose tail
    (`MPTAIL`, `W=16u nf=4` -- one folded 4-finger `mos_array`, mirroring
    `pb` at 4:1) heads a five-PMOS group sharing one drawn n-well with a
    `well_island` tap on `vdd`; the NMOS mirror loads and both buffer nfets
    sit outside that well. Multi-finger devices (`MPTAIL`, and the
    `W=8u nf=4` pair `MPINN`/`MPINP`) extract as their parallel per-finger
    pfets and are folded back together by `klt lvs`'s
    `options.combine_devices: ["pfet"]` (see `layout/run_checks.sh`).

    Two independent `mos_array` calls for the input pair rather than
    `klt gen diff_pair`, for the same documented reason as the NMOS cell's
    pair: matching is not this comparator's binding constraint (the trip
    points come from the bias divider; the block's accuracy budget is
    dominated by R/C spread and trim resolution, DR-0003/DR-0017), while
    `diff_pair`'s mandatory guard ring would have to be cut open to route
    four terminals out of it."""
    c = Composer("rcosc_comparator_p")
    # The +0.4um row-gap delta over the module default is a deliberate
    # top-level channel-column clearance, not a DRC number: this cell's
    # width sets where every top-level device right of XCMPL (MDISCH, the
    # latch, CTIMING) lands, and those devices' gate columns must clear the
    # trim bank's own right-side pad columns (fixed x's) by >= 0.72um in
    # `build_rcosc_top`'s channel. The pre-#57 width cleared that lattice
    # only by coincidence; this cell's different width re-rolls it, and the
    # 8x0.4um this adds is the measured clearance that re-establishes it
    # (verified by the build's own column-spacing check, which scans every
    # column pair -- not just the pair that first collided).
    row = Row(c)

    placed = {}
    for name in _CMPP_ORDER:
        placed[name] = row.place("mos_array", _mos_params(devices[name]), name.lower()[1:])

    # One n-well over the whole PMOS group (the trailing five blocks) plus
    # its tap island, merging the generators' own per-device wells into one
    # equipotential well tied to vdd -- the load/buffer NMOS prefix of the
    # row stays outside it.
    well_x0 = row.left_um["mptail"] + COL_OFFSET_UM - 0.5
    p_well = row.place(
        "well_island",
        {
            "inner_width_um": 1.0,
            "inner_height_um": 1.0,
            "contacts_per_side": 1,
            # The label this generator would draw sits on the ring's own metal
            # inside a sub-cell, where `klt extract` does not reliably promote
            # it to a pin -- this cell names `vdd` on its own pin pad instead.
            "net": "",
        },
        "pwell_tap",
    )
    well_x1 = row.right_um["pwell_tap"] - COL_OFFSET_UM + 0.5
    c.draw_nwell(well_x0, -0.65, well_x1, row.top_um + 0.5)

    ch = Channel(
        c,
        column_layer=gen_lib.METAL1,
        track_layer=gen_lib.METAL2,
        track_via=gen_lib.VIA1,
        y0_um=row.top_um + CHANNEL_CLEARANCE_UM,
        pitch_um=TRACK_PITCH_UM,
    )

    def terminal(dev_name: str, port: str, net: str, column_x: float) -> None:
        x, y, _ = placed[dev_name].port_abs(port)
        ch.add(net, x, y, column_x)

    # `nodes` is the schematic's own [d, g, s, b] order for these MOS calls,
    # so every net below is read from the netlist, never retyped.
    for name in _CMPP_ORDER:
        key = name.lower()[1:]
        d_net, g_net, s_net, _b_net = devices[name].nodes
        terminal(name, "U0_S", s_net, row.left_um[key])
        terminal(name, "U0_D", d_net, row.right_um[key])
        gate_x, _, _ = placed[name].port_abs("U0_G")
        terminal(name, "U0_G", g_net, gate_x)

    tap_x, tap_y, _ = p_well.port_abs("TAP_N")
    ch.add("vdd", tap_x, tap_y, tap_x)

    ch.route(_CMPP_TRACKS)
    pad_y = ch.top_y_um(_CMPP_TRACKS) + PAD_CLEARANCE_UM
    pin_column = {
        # vdd over the PMOS group's first device; vss over the second load's
        # source column and out over MBUF2N's drain column -- interior
        # columns of nets each already reaches, deliberately NOT the row's
        # edge-adjacent columns: a pad outside the cell's GDS bbox lands in
        # the top-level neighbour's right margin when `Row.place_cell`
        # reserves space by bbox (observed as a 0.21um channel-column clash
        # during issue #57's bring-up), and interior pads cannot.
        "vdd": row.left_um["mptail"],
        "vss": row.left_um["mnloadb"],
        "out": row.right_um["mbuf2n"],
        "pb": placed["XMPTAIL"].port_abs("U0_G")[0],
        "inp": placed["XMPINN"].port_abs("U0_G")[0],
        "inn": placed["XMPINP"].port_abs("U0_G")[0],
    }
    pins_um = {}
    for net in _CMPP_PINS:
        pins_um[net] = ch.pin_pad(net, pin_column[net], pad_y, gen_lib.METAL1_LABEL)

    c.pins_um = pins_um  # consumed by build_rcosc_top when it instantiates this cell
    return c, _CMPP_PINS


# `rcosc_top`'s row, left to right. Sub-blocks first, then the discharge
# switch, then the NOR-NOR SR latch split NMOS-before-PMOS so the latch's four
# PMOS can share one drawn n-well (same reason as the comparator's), kept a
# full inter-block gap away from the comparator instances' own wells so
# `nwell.space.1` (0.6um) holds between them. The MiM timing capacitor goes
# last: it is the only Metal4 geometry in the design, and `mim.space.1` wants
# 1.2um of Metal4 clearance around its virtual bottom plate.
_TOP_SUBCELLS = [
    ("XXBIAS", "rcosc_bias"),
    ("XXTRIM", "rcosc_trim_bank"),
    ("XXCMPH", "rcosc_comparator"),
    ("XXCMPL", "rcosc_comparator_p"),
]
_TOP_NFETS = ["XMDISCH", "XMG1A", "XMG1B", "XMG2A", "XMG2B"]
_TOP_PFETS = ["XMG1C", "XMG1D", "XMG2C", "XMG2D"]
_TOP_TRACKS = [
    "vh", "vl", "ibias", "pb", "vc", "cmph_out", "cmpl_out",
    "mid1", "mid2", "qbar", "clk", "vdd", "vss",
] + [f"t{i}" for i in range(8)]
_TOP_PINS = ["vdd", "vss", "clk"] + [f"t{i}" for i in range(8)]


def build_rcosc_top(devices: dict, ctx: dict) -> tuple[Composer, list[str]]:
    """The full hierarchy: `rcosc_bias`, `rcosc_trim_bank` and two
    `rcosc_comparator` instances placed as sub-cells (never redrawn), plus the
    timing capacitor, the discharge switch and the NOR-NOR SR latch drawn here
    (issue #27).

    Routed on the level above the sub-cells' own: metal2 columns, metal3
    tracks (`gen_lib.Channel` with `port_via=VIA1`). That layer split is what
    makes hierarchical composition safe -- a sub-cell routes on metal1/metal2
    and exposes metal1 pin pads *above* its own top track, so nothing this
    level draws can cross anything a sub-cell drew.

    `CTIMING` is the one hand-drawn device in the design: `klt gen cap_array`
    refuses gf180mcu outright, even though `klt extract`'s curated gf180mcu
    deck recognises all three of the PDK's MiM densities -- see
    `gen_lib.Composer.add_mim_cap` and `layout/README.md`."""
    c = Composer("rcosc_top")
    row = Row(c)
    subckt_pins = ctx["__subckt_pins__"]

    # Sub-cells: map each instance's positional nodes onto its own pin names,
    # then onto the pin coordinates its builder reported. Kept as a *list* of
    # (net, xy) pairs, not a dict: a sub-cell can export two pins that land
    # on the same top-level net (post-#50 the trim bank's `p` and `vdd` pins
    # both connect to the top's `vdd`), and a dict keyed by net would let one
    # pad's coordinates silently overwrite the other's -- leaving that pad
    # unrouted and its device end floating.
    sub_pins: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    for inst, cell_name in _TOP_SUBCELLS:
        origin = row.place_cell(
            CELLS_DIR / f"{cell_name}.gds", cell_name, inst.lower()[1:]
        )["__origin__"]
        net_of = dict(zip(subckt_pins[cell_name], devices[inst].nodes, strict=True))
        sub_pins[inst] = [
            (net_of[pin], (origin[0] + px, origin[1] + py))
            for pin, (px, py) in ctx[cell_name].items()
        ]

    def sub_pin_xy(inst: str, net: str) -> tuple[float, float]:
        """First exported pad of `inst` wired to top-level `net`."""
        for n, xy in sub_pins[inst]:
            if n == net:
                return xy
        raise KeyError(f"{inst} exports no pin on net {net!r}")

    placed = {}
    for name in _TOP_NFETS + _TOP_PFETS:
        placed[name] = row.place("mos_array", _mos_params(devices[name]), name.lower()[1:])

    well_x0 = row.left_um["mg1c"] + COL_OFFSET_UM - 0.5
    p_well = row.place(
        "well_island",
        {"inner_width_um": 1.0, "inner_height_um": 1.0, "contacts_per_side": 1, "net": ""},
        "pwell_tap",
    )
    well_x1 = row.right_um["pwell_tap"] - COL_OFFSET_UM + 0.5
    c.draw_nwell(well_x0, -0.65, well_x1, row.top_um + 0.5)

    ctiming = devices["XCTIMING"]
    cap_bottom, cap_top = row.place_mim_cap(
        ctiming.param_um("c_width"), ctiming.param_um("c_length"), "ctiming"
    )
    # Bring both MiM terminals down the BEOL stack to metal1, so they enter the
    # channel router as ordinary metal1 ports like every other terminal.
    down = ((gen_lib.VIA3, gen_lib.METAL3), (gen_lib.VIA2, gen_lib.METAL2),
            (gen_lib.VIA1, gen_lib.METAL1))
    c.via_stack(cap_bottom[0], cap_bottom[1], down)
    c.via_stack(cap_top[0], cap_top[1], down)

    ch = Channel(
        c,
        column_layer=gen_lib.METAL2,
        track_layer=gen_lib.METAL3,
        track_via=gen_lib.VIA2,
        port_via=gen_lib.VIA1,
        y0_um=row.top_um + CHANNEL_CLEARANCE_UM,
        pitch_um=TRACK_PITCH_UM,
    )

    for inst, _cell in _TOP_SUBCELLS:
        for net, (x, y) in sub_pins[inst]:
            ch.add(net, x, y, x)

    for name in _TOP_NFETS + _TOP_PFETS:
        key = name.lower()[1:]
        d_net, g_net, s_net, _b_net = devices[name].nodes
        gate_x, _, _ = placed[name].port_abs("U0_G")
        for port, net, column_x in (
            ("U0_S", s_net, row.left_um[key]),
            ("U0_D", d_net, row.right_um[key]),
            ("U0_G", g_net, gate_x),
        ):
            x, y, _ = placed[name].port_abs(port)
            ch.add(net, x, y, column_x)

    tap_x, tap_y, _ = p_well.port_abs("TAP_N")
    ch.add("vdd", tap_x, tap_y, tap_x)

    for point, net in ((cap_bottom, ctiming.nodes[0]), (cap_top, ctiming.nodes[1])):
        ch.add(net, point[0], point[1], point[0])

    ch.route(_TOP_TRACKS)
    pad_y = ch.top_y_um(_TOP_TRACKS) + PAD_CLEARANCE_UM
    pin_column = {
        "vdd": sub_pin_xy("XXBIAS", "vdd")[0],
        "vss": sub_pin_xy("XXBIAS", "vss")[0],
        "clk": placed["XMDISCH"].port_abs("U0_G")[0],
    }
    for i in range(8):
        pin_column[f"t{i}"] = sub_pin_xy("XXTRIM", f"t{i}")[0]
    for net in _TOP_PINS:
        ch.pin_pad(net, pin_column[net], pad_y, gen_lib.METAL2_LABEL)

    # MUST be the last thing this function does, after every `klt gen` call:
    # an imported sub-cell is a live PCell proxy that KLayout re-evaluates --
    # wiping this marker -- on the next generation. See `place_gds`'s docstring.
    patched = c.patch_high_sheet_resistors()
    assert patched == 13, f"expected 13 resistors patched, got {patched}"
    return c, _TOP_PINS


def _write_reference_netlist_bias(devices: dict, path: Path, ctx: dict) -> None:
    lines = [
        "* LVS reference for layout/cells/rcosc_bias.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "*",
        "* Every resistor/nfet's bulk terminal is tied to 'vsubs', not 'vss',",
        "* matching klt's gf180mcu curated extraction deck: gf180mcu has no",
        "* distinct tap layer, so every NMOS body / resistor bulk terminal is",
        "* unconditionally tied to the deck's synthesized substrate_net global",
        "* ('vsubs') regardless of drawn geometry (klayout_tools/decks/",
        "* gf180mcu.py; klayout_tools/lvs.py's _body_net_warnings docstring).",
        "* The schematic (design/rcosc_bias.sch) ties these same bulk terminals",
        "* to 'vss' for correct SPICE simulation -- this is a disclosed LVS-",
        "* reference-only modeling accommodation for that documented deck",
        "* limitation, not a schematic or spec change (mirrors gf180-temp-por's",
        "* lvs_reference.py: 'the deck ties every drawn resistor's bulk to its",
        "* substrate global' -- see layout/README.md for the full rationale).",
        "* The pfet bulk terminals are NOT rewritten: this cell draws a real",
        "* n-well tap ('klt gen well_island', see build_rcosc_bias) tying the",
        "* shared PMOS well to vdd, so the layout genuinely reports those",
        "* bodies on the vdd net and the schematic's own vdd bulk connection",
        "* compares directly, no accommodation needed (same construction as",
        "* rcosc_comparator's, see the comparator's reference header).",
        "* N2 is written 'W=16u nf=1' rather than the schematic's",
        "* 'W=16u nf=8' -- the same device (gf180mcu's W is the total channel",
        "* width), respelled because klt's reference normalizer rejects nf>1;",
        "* the layout's eight drawn fingers are folded back together by",
        "* klt lvs's options.combine_devices (see layout/run_checks.sh).",
        "* Resistors are written as plain R-elements (value = sheet_rho *",
        "* r_length/r_width) rather than X subckt calls: klt's subckt-call",
        "* reference-netlist normalizer only converts MOS (l/w-bearing) X",
        "* cards, not resistor (r_length/r_width) ones (klayout_tools/",
        "* netlist_normalize.py) -- filed as klayout-tools#1550's sibling",
        "* finding, see layout/README.md.",
    ] + _bias_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _bias_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    """The re-spun bias cell's LVS reference cards (issue #44): the unchanged
    RBA/RBB/RBC ladder plus issue #39's beta-multiplier core -- RZ, N1, the
    8-finger N2, the P1/P2 pfet mirror and SEED. Terminal nets come from the
    netlist's own `nodes` (including the internal `pb` PMOS gate bus and
    `n2s` degeneration node), never retyped; `_mos_ref_card` applies the two
    disclosed reference-form rewrites (NMOS body -> `vsubs`, `nf>1` respelled
    `nf=1` at the schematic's total W -- N2's eight drawn fingers fold back
    together via `klt lvs`'s `options.combine_devices: ["nfet"]`,
    `run_checks.sh`). The PMOS bulk terminals are NOT rewritten: this cell
    draws a real n-well tap tying the PMOS well to `vdd`, so the layout
    genuinely reports those bodies on the `vdd` net."""
    lines = [
        ".SUBCKT rcosc_bias vdd vss vh vl ibias pb" + (" vsubs" if vsubs_pin else "")
    ]
    for name in ("XRBA", "XRBB", "XRBC", "XRZ"):
        d = devices[name]
        r_ohm = _res_r_ohm(d.param_um("r_length"), d.param_um("r_width"))
        lines.append(f"R${d.name[1:]} {d.nodes[0]} {d.nodes[1]} vsubs {r_ohm:.6g} ppolyf_u_1k")
    lines += [_mos_ref_card(name, devices[name]) for name in ("XN1", "XN2", "XP1", "XP2", "XSEED")]
    lines.append(".ENDS")
    return lines


def _write_reference_netlist_trim_bank(devices: dict, path: Path, ctx: dict) -> None:
    lines = [
        "* LVS reference for layout/cells/rcosc_trim_bank.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "* See rcosc_bias's reference netlist header (layout/build_cells.py)",
        "* for why resistor bulk terminals are 'vsubs' here (not the",
        "* schematic's 'vss') and resistors are plain R-elements.",
        "* Post-#43 (issue #50's re-spin) 'vdd' is a new pin and 'vss' is a",
        "* real routed net again, not a bulk-only tie: the per-bit complement",
        "* inverter's nfet sources sit on 'vss', its pfet sources (and the",
        "* eight transmission-gate pfet bodies, through the cell's one drawn",
        "* n-well tap) sit on 'vdd', so both stay in the pin list. NMOS and",
        "* resistor bulk terminals still extract to the deck's synthesized",
        "* 'vsubs'; the pfet bulk terminals are written 'vdd' as the schematic",
        "* ties them, matched by the layout's drawn, tapped well.",
    ] + _trim_bank_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _trim_mos_ref_card(name: str, d: Device) -> str:
    """One MOS subckt-call line for the trim bank's LVS reference netlist.

    Same two disclosed rewrites as `_mos_ref_card` (NMOS body -> `vsubs`;
    `nf=1` at the schematic's total width -- every post-#43 trim MOS is
    `nf=1`, so the respell is exact), plus one trim-specific normalization:
    `W`/`L` literals are re-emitted from the parsed micrometre value rather
    than passed through verbatim, because the post-#43 schematic spells the
    transmission-gate widths with xschem's double-u micrometre suffix
    (`W=24uu`), a spelling `klt`'s reference normalizer is not documented to
    accept -- `24u` is the same value in the canonical spelling."""
    d_net, g_net, s_net, b_net = d.nodes
    if not d.model.startswith("pfet"):
        b_net = "vsubs"
    return (
        f"{name} {d_net} {g_net} {s_net} {b_net} {d.model} "
        f"L={d.param_um('l'):.6g}u W={d.param_um('w'):.6g}u nf=1"
    )


def _trim_bank_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    res_order = ["XRFIX"] + [f"XR{i}" for i in range(8)]
    mos_order = (
        [f"XSW{i}" for i in range(8)]
        + [f"XPW{i}" for i in range(8)]
        + [f"XNINV{i}" for i in range(8)]
        + [f"XPINV{i}" for i in range(8)]
    )
    lines = [
        ".SUBCKT rcosc_trim_bank p m vss t0 t1 t2 t3 t4 t5 t6 t7 vdd"
        + (" vsubs" if vsubs_pin else "")
    ]
    nodes = ["p"] + [f"c{i}" for i in range(1, 9)] + ["m"]
    for i, name in enumerate(res_order):
        d = devices[name]
        r_ohm = _res_r_ohm(d.param_um("r_length"), d.param_um("r_width"))
        lines.append(f"R${name[1:]} {nodes[i]} {nodes[i + 1]} vsubs {r_ohm:.6g} ppolyf_u_1k")
    lines += [_trim_mos_ref_card(name, devices[name]) for name in mos_order]
    lines.append(".ENDS")
    return lines


def _mos_ref_card(name: str, d: Device) -> str:
    """One MOS subckt-call line for an LVS reference netlist.

    Two disclosed rewrites of the schematic's own card, both forced by the
    reference form `klt lvs` can read and neither a schematic change:

    * an NMOS body node is rewritten to `vsubs` (the deck's synthesized
      substrate global -- see `_write_reference_netlist_bias`'s header for the
      full rationale); a PMOS body node is left alone, because this layout
      draws a real, tied n-well for it.
    * `nf` is written as 1 with `W` left at the schematic's *total* width.
      `klt`'s subckt-call normalizer (`klayout_tools/netlist_normalize.py`)
      rejects `nf>1` outright rather than carrying it, since the plain-element
      MOS form it converts to has no finger parameter -- so a multi-finger
      device has to be spelled as the single wide device it is electrically
      equivalent to, and the layout's real fingers folded back together by
      `klt lvs`'s `options.combine_devices`. Safe on this PDK precisely
      because gf180mcu's `W` is already the total width (`W/nf` per finger);
      it would not be on a PDK whose `W` is per-finger.
    """
    d_net, g_net, s_net, b_net = d.nodes
    if not d.model.startswith("pfet"):
        b_net = "vsubs"
    return (
        f"{name} {d_net} {g_net} {s_net} {b_net} {d.model} "
        f"L={d.params['l']} W={d.params['w']} nf=1"
    )


def _comparator_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    return (
        [
            ".SUBCKT rcosc_comparator vdd vss ibias inp inn out"
            + (" vsubs" if vsubs_pin else "")
        ]
        + [_mos_ref_card(name, devices[name]) for name in _CMP_ORDER]
        + [".ENDS"]
    )


def _comparator_p_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    return (
        [
            ".SUBCKT rcosc_comparator_p vdd vss pb inp inn out"
            + (" vsubs" if vsubs_pin else "")
        ]
        + [_mos_ref_card(name, devices[name]) for name in _CMPP_ORDER]
        + [".ENDS"]
    )


def _write_reference_netlist_comparator_p(devices: dict, path: Path, ctx: dict) -> None:
    lines = [
        "* LVS reference for layout/cells/rcosc_comparator_p.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "* Same accommodations as rcosc_comparator's reference (see its header",
        "* and rcosc_bias's): every *NMOS* bulk terminal reads 'vsubs' here",
        "* rather than the schematic's 'vss' (the deck's synthesized substrate",
        "* global), while the five PMOS bulk terminals are NOT rewritten -- this",
        "* cell draws a real n-well tap ('klt gen well_island') tying the shared",
        "* PMOS well to vdd, so the layout genuinely reports those bodies on",
        "* the vdd net. The three multi-finger pfets (MPTAIL W=16u nf=4, and",
        "* the W=8u nf=4 pair MPINN/MPINP) are written nf=1 at the schematic's",
        "* total W -- gf180mcu's W is the total channel width -- because klt's",
        "* reference normalizer rejects nf>1; the drawn fingers are folded back",
        "* together by klt lvs's options.combine_devices: [\"pfet\"] (see",
        "* layout/run_checks.sh).",
    ] + _comparator_p_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _write_reference_netlist_comparator(devices: dict, path: Path, ctx: dict) -> None:
    lines = [
        "* LVS reference for layout/cells/rcosc_comparator.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "* See rcosc_bias's reference netlist header (layout/build_cells.py)",
        "* for why every *NMOS* bulk terminal reads 'vsubs' here rather than",
        "* the schematic's 'vss'. The three PMOS bulk terminals are NOT",
        "* rewritten: this cell draws a real n-well tap ('klt gen well_island')",
        "* tying the shared PMOS well to vdd, so the layout genuinely reports",
        "* those bodies on the vdd net and no accommodation is needed.",
        "* MTAIL is written 'W=16u nf=1' rather than the schematic's",
        "* 'W=16u nf=8' -- the same device (gf180mcu's W is the total channel",
        "* width), respelled because klt's reference normalizer rejects nf>1;",
        "* the layout's eight drawn fingers are folded back together by",
        "* klt lvs's options.combine_devices (see layout/run_checks.sh).",
    ] + _comparator_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _write_reference_netlist_top(devices: dict, path: Path, ctx: dict) -> None:
    """The whole-hierarchy LVS reference.

    Written hierarchically (each sub-block's own `.SUBCKT`, then `rcosc_top`
    instantiating them) so it reads as the schematic does, and flattened by
    `klt lvs`'s `options.flatten_reference` at compare time to meet the
    layout side, which `klt extract` always emits flat. Every accommodation
    the three sub-block references already document applies here unchanged and
    consistently across the hierarchy -- NMOS/resistor bulk on `vsubs`, PMOS
    bulk on the real drawn well, resistors and the MiM capacitor as plain
    elements."""
    by_cell = ctx["__devices_by_cell__"]
    trim_pins = " ".join(ctx["__subckt_pins__"]["rcosc_trim_bank"])
    ctiming = devices["XCTIMING"]
    c_f = _mim_c_farad(ctiming.param_um("c_width"), ctiming.param_um("c_length"))

    lines = [
        "* LVS reference for layout/cells/rcosc_top.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "* Sub-block .SUBCKTs below are byte-identical to the three per-cell",
        "* references in layout/lvs_ref/ (same generator functions), so the",
        "* hierarchy is verified against exactly what each cell was verified",
        "* against on its own. See those files' headers, and layout/README.md,",
        "* for the 'vsubs' bulk-tie accommodation and the plain-element",
        "* resistor/capacitor form.",
        "* CTIMING is a plain C element whose value is the deck's own two-term",
        "* area+perimeter law for the gf180mcu MiM density this design commits",
        f"* to ({MIM_CAP_CLASS}, c_cox={MIM_AREA_CAP_F_UM2:g} F/um^2 /",
        f"* c_capsw={MIM_PERIM_CAP_F_UM:g} F/um, klayout_tools/decks/gf180mcu.py)",
        "* evaluated at the schematic's own c_width/c_length -- not a retyped",
        "* capacitance. Selected at extraction time with",
        f"* `klt extract --deck-option mim_cap={MIM_CAP_CLASS}`.",
        "",
    ]
    lines += _bias_subckt(by_cell["rcosc_bias"], vsubs_pin=True)
    lines += _trim_bank_subckt(by_cell["rcosc_trim_bank"], vsubs_pin=True)
    lines += _comparator_subckt(by_cell["rcosc_comparator"], vsubs_pin=True)
    lines += _comparator_p_subckt(by_cell["rcosc_comparator_p"], vsubs_pin=True)

    lines.append(
        ".SUBCKT rcosc_top " + " ".join(ctx["__subckt_pins__"]["rcosc_top"])
    )
    bias_nodes = " ".join(devices["XXBIAS"].nodes)
    lines.append(f"XXBIAS {bias_nodes} vsubs rcosc_bias")
    trim_net_of = dict(
        zip(ctx["__subckt_pins__"]["rcosc_trim_bank"], devices["XXTRIM"].nodes, strict=True)
    )
    lines.append(
        "XXTRIM "
        + " ".join(trim_net_of[p] for p in trim_pins.split())
        + " vsubs rcosc_trim_bank"
    )
    lines.append(
        f"C$CTIMING {ctiming.nodes[0]} {ctiming.nodes[1]} {c_f:.6g} {MIM_CAP_CLASS}"
    )
    lines.append(
        f"XXCMPH " + " ".join(devices["XXCMPH"].nodes) + " vsubs rcosc_comparator"
    )
    lines.append(
        f"XXCMPL " + " ".join(devices["XXCMPL"].nodes) + " vsubs rcosc_comparator_p"
    )
    for name in ["XMDISCH"] + _TOP_NFETS[1:] + _TOP_PFETS:
        lines.append(_mos_ref_card(name, devices[name]))
    lines += [".ENDS", ""]
    path.write_text("\n".join(lines))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: Build order matters: `rcosc_top` instantiates the other cells as
#: sub-cells, so they have to exist on disk (and be current) before it is
#: built.
CELL_ORDER = [
    "rcosc_bias", "rcosc_trim_bank", "rcosc_comparator", "rcosc_comparator_p", "rcosc_top",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify committed GDS/reference netlists are current")
    parser.add_argument("--cell", choices=CELL_ORDER, help="build only this cell")
    args = parser.parse_args()

    if not NETLIST_PATH.exists():
        print(f"error: {NETLIST_PATH} does not exist -- run design/regen-netlist.sh first", file=sys.stderr)
        return 1

    netlist_text = NETLIST_PATH.read_text()
    devices_by_cell = {
        "rcosc_bias": parse_subckt(netlist_text, "rcosc_bias"),
        "rcosc_trim_bank": parse_subckt(netlist_text, "rcosc_trim_bank"),
        "rcosc_comparator": parse_subckt(netlist_text, "rcosc_comparator"),
        "rcosc_comparator_p": parse_subckt(netlist_text, "rcosc_comparator_p"),
        "rcosc_top": parse_subckt(netlist_text, "rcosc_top"),
    }
    builders = {
        "rcosc_bias": (build_rcosc_bias, _write_reference_netlist_bias),
        "rcosc_trim_bank": (build_rcosc_trim_bank, _write_reference_netlist_trim_bank),
        "rcosc_comparator": (build_rcosc_comparator, _write_reference_netlist_comparator),
        "rcosc_comparator_p": (build_rcosc_comparator_p, _write_reference_netlist_comparator_p),
        "rcosc_top": (build_rcosc_top, _write_reference_netlist_top),
    }

    CELLS_DIR.mkdir(exist_ok=True)
    LVS_REF_DIR.mkdir(exist_ok=True)

    # `rcosc_top` needs each sub-cell's pin coordinates to route to it, and
    # each sub-block's own devices/pin order to write its reference netlist --
    # all taken from the sub-cell's own builder and from the schematic netlist
    # rather than re-measured or hand-copied, so a floorplan or schematic
    # change cannot desynchronise the two.
    ctx: dict = {
        "__devices_by_cell__": devices_by_cell,
        "__subckt_pins__": {
            name: parse_subckt_pins(netlist_text, name)
            for name in (
                "rcosc_bias", "rcosc_trim_bank", "rcosc_comparator",
                "rcosc_comparator_p", "rcosc_top",
            )
        },
    }

    ok = True
    selected = [args.cell] if args.cell else CELL_ORDER
    # Building `rcosc_top` requires every sub-cell builder to have run first
    # (for its pin coordinates), so a `--cell rcosc_top` run still builds them.
    to_build = CELL_ORDER if "rcosc_top" in selected else selected
    for cell_name in CELL_ORDER:
        if cell_name not in to_build:
            continue
        build_fn, ref_writer = builders[cell_name]
        devices = devices_by_cell[cell_name]
        gds_path = CELLS_DIR / f"{cell_name}.gds"
        ref_path = LVS_REF_DIR / f"{cell_name}.spice"

        if args.check:
            before = _sha256(gds_path) if gds_path.exists() else None
            ref_before = ref_path.read_text() if ref_path.exists() else None

        if cell_name == "rcosc_top":
            composer, pins = build_fn(devices, ctx)
        else:
            composer, pins = build_fn(devices)
            ctx[cell_name] = getattr(composer, "pins_um", {})

        if cell_name not in selected:
            # Built only for its pin geometry; neither written nor compared.
            continue

        tmp_gds = gds_path.with_suffix(".gds.tmp")
        composer.write(str(tmp_gds))
        ref_writer(devices, ref_path.with_suffix(".spice.tmp"), ctx)

        if args.check:
            after = _sha256(tmp_gds)
            ref_after = ref_path.with_suffix(".spice.tmp").read_text()
            # --check never overwrites the committed files -- just compares
            match = before == after and ref_before == ref_after
            tmp_gds.unlink()
            ref_path.with_suffix(".spice.tmp").unlink()
            status = "OK" if match else "STALE"
            print(f"{cell_name}: {status}")
            ok = ok and match
        else:
            tmp_gds.replace(gds_path)
            ref_path.with_suffix(".spice.tmp").replace(ref_path)
            print(f"{cell_name}: wrote {gds_path} (pins: {', '.join(pins)})")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
