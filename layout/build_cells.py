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

## Floorplan (both cells)

Each cell is two rows: row 1 is the resistor chain (left to right, in
schematic node order, baseline y=0); row 2, above row 1 with a routing gap,
holds the diode-connected bias transistor (`rcosc_bias`) or the trim-bank
shunt switches (`rcosc_trim_bank`), one per resistor it shorts. Every
switch/transistor is centred in x above its own resistor so its two routing
jogs (`Composer.wire_z`) stay inside that resistor's own private x window --
no two different nets' routing ever needs to cross, since neighbouring
resistors never overlap in x (see `gen_lib.py`'s `wire_z`/`wire_l`
docstrings). `rcosc_bias`'s `RBIAS`+`MBIASD` sub-row and its `vdd`/`vss`
cross-row jogs follow the same discipline -- `build_rcosc_bias()` below
documents the left/right terminal-role swap that keeps its `vss` jog clear
of the `ibias` rail.
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

GAP_UM = 4.0
ROW2_GAP_UM = 3.0
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


def build_rcosc_bias(devices: dict) -> tuple[Composer, list[str]]:
    rba = devices["XRBA"]
    rbb = devices["XRBB"]
    rbc = devices["XRBC"]
    rbias = devices["XRBIAS"]
    mbiasd = devices["XMBIASD"]

    c = Composer("rcosc_bias")

    p_rba = c.gen_and_place(
        "res_array",
        {"length_um": rba.param_um("r_length"), "width_um": rba.param_um("r_width"), "num": 1, "dummy": 0},
        0.0, 0.0, "rba",
    )
    p_rbb = c.gen_and_place(
        "res_array",
        {"length_um": rbb.param_um("r_length"), "width_um": rbb.param_um("r_width"), "num": 1, "dummy": 0},
        p_rba.x1_um + GAP_UM, 0.0, "rbb",
    )
    p_rbc = c.gen_and_place(
        "res_array",
        {"length_um": rbc.param_um("r_length"), "width_um": rbc.param_um("r_width"), "num": 1, "dummy": 0},
        p_rbb.x1_um + GAP_UM, 0.0, "rbc",
    )

    row2_y = p_rba.bbox_um[3] + GAP_UM
    p_rbias = c.gen_and_place(
        "res_array",
        {"length_um": rbias.param_um("r_length"), "width_um": rbias.param_um("r_width"), "num": 1, "dummy": 0},
        0.0, row2_y, "rbias",
    )
    p_mbiasd = c.gen_and_place(
        "mos_array",
        {
            "w_um": mbiasd.param_um("w"), "l_um": mbiasd.param_um("l"),
            "fingers": mbiasd.param_int("nf"), "rows": 1, "cols": 1, "dummy": 0,
            "flavor": "nfet", "gate_contact": True,
        },
        p_rbias.x1_um + GAP_UM, row2_y, "mbiasd",
    )

    rba_a, rba_b = p_rba.port_abs("R0_A"), p_rba.port_abs("R0_B")
    rbb_a, rbb_b = p_rbb.port_abs("R0_A"), p_rbb.port_abs("R0_B")
    rbc_a, rbc_b = p_rbc.port_abs("R0_A"), p_rbc.port_abs("R0_B")
    rbias_a, rbias_b = p_rbias.port_abs("R0_A"), p_rbias.port_abs("R0_B")
    # U0_S (left, near RBIAS) carries the gate-tied "ibias" role; U0_D
    # (right, far from RBIAS) carries "vss" -- an nfet's S/D is symmetric,
    # so this is a free choice, and this one keeps the vss cross-row jog
    # clear of the ibias rail (see module docstring's floorplan note).
    mb_ibias_term = p_mbiasd.port_abs("U0_S")
    mb_vss_term = p_mbiasd.port_abs("U0_D")
    mb_g = p_mbiasd.port_abs("U0_G")

    c.wire_segment(rba_b[0], rba_b[1], rbb_a[0], rbb_a[1], 2.0)  # vh
    c.wire_segment(rbb_b[0], rbb_b[1], rbc_a[0], rbc_a[1], 2.0)  # vl
    c.wire_segment(rba_a[0], rba_a[1], rbias_a[0], rbias_a[1], 2.0)  # vdd (aligned x=0 on both rows)
    # ibias rail: RBIAS.B -> the gate's own x (covers MBIASD's S terminal,
    # which sits between RBIAS.B and the gate in x)
    c.wire_segment(rbias_b[0], rbias_b[1], mb_g[0], mb_ibias_term[1], 2.0)
    c.wire_segment(mb_g[0], mb_g[1], mb_g[0], mb_ibias_term[1], 0.42)
    # vss: RBC.B (row1, far right) -> MBIASD's D terminal (row2, far right
    # of its own cell) -- via RBC.B's own x column, clear of the ibias rail
    c.wire_l((rbc_b[0], rbc_b[1]), (mb_vss_term[0], mb_vss_term[1]), 0.42, via_x=rbc_b[0])

    c.add_pin_label(rba_a[0], rba_a[1], "vdd")
    c.add_pin_label(rba_b[0], rba_b[1], "vh")
    c.add_pin_label(rbb_b[0], rbb_b[1], "vl")
    c.add_pin_label(rbc_b[0], rbc_b[1], "vss")
    c.add_pin_label(rbias_b[0], rbias_b[1], "ibias")

    patched = c.patch_high_sheet_resistors()
    assert patched == 4, f"expected 4 resistors patched, got {patched}"
    # Pin coordinates, for `build_rcosc_top` to route to when it instantiates
    # this cell -- read from the same ports the labels above were placed on,
    # never re-measured off the written GDS.
    c.pins_um = {
        "vdd": (rba_a[0], rba_a[1]),
        "vh": (rba_b[0], rba_b[1]),
        "vl": (rbb_b[0], rbb_b[1]),
        "vss": (rbc_b[0], rbc_b[1]),
        "ibias": (rbias_b[0], rbias_b[1]),
    }
    return c, ["vdd", "vss", "vh", "vl", "ibias"]


def build_rcosc_trim_bank(devices: dict) -> tuple[Composer, list[str]]:
    res_order = ["XRFIX"] + [f"XR{i}" for i in range(8)]
    sw_order = [f"XSW{i}" for i in range(8)]

    c = Composer("rcosc_trim_bank")

    placed_r: dict[str, object] = {}
    x = 0.0
    for name in res_order:
        d = devices[name]
        length_um = d.param_um("r_length")
        if name == "XR1":
            length_um = _R1_LENGTH_NUDGE_UM
        width_um = d.param_um("r_width")
        p = c.gen_and_place(
            "res_array", {"length_um": length_um, "width_um": width_um, "num": 1, "dummy": 0},
            x, 0.0, name.lower()[1:],
        )
        placed_r[name] = p
        x = p.x1_um + GAP_UM

    row1_top = placed_r["XRFIX"].bbox_um[3]
    row2_y = row1_top + ROW2_GAP_UM

    placed_sw: dict[str, object] = {}
    for i, name in enumerate(sw_order):
        d = devices[name]
        params = {
            "w_um": d.param_um("w"), "l_um": d.param_um("l"),
            "fingers": d.param_int("nf"), "rows": 1, "cols": 1, "dummy": 0,
            "flavor": "nfet", "gate_contact": True,
        }
        r_name = res_order[i + 1]
        r = placed_r[r_name]
        # peek (not place) this switch's bbox to learn its width before
        # centring it above its resistor -- peek_bbox never touches the
        # composing layout (see gen_lib.py), unlike gen_and_place
        sw_x0_bbox, _, sw_x1_bbox, _ = c.peek_bbox("mos_array", params)
        sw_width = sw_x1_bbox - sw_x0_bbox
        center_x = (r.x0_um + r.x1_um) / 2.0
        sw_x0 = center_x - sw_width / 2.0
        p = c.gen_and_place("mos_array", params, sw_x0, row2_y, name.lower()[1:])
        placed_sw[name] = p

    for a_name, b_name in zip(res_order[:-1], res_order[1:]):
        a, b = placed_r[a_name], placed_r[b_name]
        a_b, b_a = a.port_abs("R0_B"), b.port_abs("R0_A")
        c.wire_segment(a_b[0], a_b[1], b_a[0], b_a[1], 2.0)

    y_mid = row1_top + ROW2_GAP_UM / 2.0
    pins_um: dict[str, tuple[float, float]] = {}
    for i, sw_name in enumerate(sw_order):
        r_name = res_order[i + 1]
        r, sw = placed_r[r_name], placed_sw[sw_name]
        r_a, r_b = r.port_abs("R0_A"), r.port_abs("R0_B")
        sw_s, sw_d, sw_g = sw.port_abs("U0_S"), sw.port_abs("U0_D"), sw.port_abs("U0_G")
        c.wire_z((r_a[0], r_a[1]), (sw_s[0], sw_s[1]), 0.42, y_mid)
        c.wire_z((r_b[0], r_b[1]), (sw_d[0], sw_d[1]), 0.42, y_mid)
        gate_net = devices[sw_name].nodes[1]  # t{i}
        c.add_pin_label(sw_g[0], sw_g[1], gate_net)
        pins_um[gate_net] = (sw_g[0], sw_g[1])

    p_port = placed_r["XRFIX"].port_abs("R0_A")
    m_port = placed_r["XR7"].port_abs("R0_B")
    c.add_pin_label(p_port[0], p_port[1], "p")
    c.add_pin_label(m_port[0], m_port[1], "m")
    pins_um["p"] = (p_port[0], p_port[1])
    pins_um["m"] = (m_port[0], m_port[1])

    patched = c.patch_high_sheet_resistors()
    assert patched == 9, f"expected 9 resistors patched, got {patched}"
    c.pins_um = pins_um
    return c, ["p", "m"] + [f"t{i}" for i in range(8)]


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
    ("XXCMPL", "rcosc_comparator"),
]
_TOP_NFETS = ["XMDISCH", "XMG1A", "XMG1B", "XMG2A", "XMG2B"]
_TOP_PFETS = ["XMG1C", "XMG1D", "XMG2C", "XMG2D"]
_TOP_TRACKS = [
    "vh", "vl", "ibias", "vc", "cmph_out", "cmpl_out",
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
    # then onto the pin coordinates its builder reported.
    sub_pins: dict[str, dict[str, tuple[float, float]]] = {}
    for inst, cell_name in _TOP_SUBCELLS:
        origin = row.place_cell(
            CELLS_DIR / f"{cell_name}.gds", cell_name, inst.lower()[1:]
        )["__origin__"]
        net_of = dict(zip(subckt_pins[cell_name], devices[inst].nodes, strict=True))
        sub_pins[inst] = {
            net_of[pin]: (origin[0] + px, origin[1] + py)
            for pin, (px, py) in ctx[cell_name].items()
        }

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
        for net, (x, y) in sub_pins[inst].items():
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
        "vdd": sub_pins["XXBIAS"]["vdd"][0],
        "vss": sub_pins["XXBIAS"]["vss"][0],
        "clk": placed["XMDISCH"].port_abs("U0_G")[0],
    }
    for i in range(8):
        pin_column[f"t{i}"] = sub_pins["XXTRIM"][f"t{i}"][0]
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
        "* Resistors are written as plain R-elements (value = sheet_rho *",
        "* r_length/r_width) rather than X subckt calls: klt's subckt-call",
        "* reference-netlist normalizer only converts MOS (l/w-bearing) X",
        "* cards, not resistor (r_length/r_width) ones (klayout_tools/",
        "* netlist_normalize.py) -- filed as klayout-tools#1550's sibling",
        "* finding, see layout/README.md.",
    ] + _bias_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _bias_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    rba, rbb, rbc, rbias = devices["XRBA"], devices["XRBB"], devices["XRBC"], devices["XRBIAS"]
    mbiasd = devices["XMBIASD"]
    return [
        ".SUBCKT rcosc_bias vdd vss vh vl ibias" + (" vsubs" if vsubs_pin else ""),
        f"R$RBA vdd vh vsubs {_res_r_ohm(rba.param_um('r_length'), rba.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBB vh vl vsubs {_res_r_ohm(rbb.param_um('r_length'), rbb.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBC vl vss vsubs {_res_r_ohm(rbc.param_um('r_length'), rbc.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBIAS vdd ibias vsubs {_res_r_ohm(rbias.param_um('r_length'), rbias.param_um('r_width')):.6g} ppolyf_u_1k",
        f"XMBIASD ibias ibias vss vsubs nfet_03v3 L={mbiasd.params['l']} W={mbiasd.params['w']} nf={mbiasd.param_int('nf')}",
        ".ENDS",
    ]


def _write_reference_netlist_trim_bank(devices: dict, path: Path, ctx: dict) -> None:
    lines = [
        "* LVS reference for layout/cells/rcosc_trim_bank.gds -- generated by",
        "* layout/build_cells.py from design/netlist/rcosc_top.spice.",
        "* See rcosc_bias's reference netlist header (layout/build_cells.py)",
        "* for why resistor bulk terminals are 'vsubs' here (not the",
        "* schematic's 'vss') and resistors are plain R-elements.",
        "* 'vss' is dropped from this SUBCKT's pin list (present in the",
        "* schematic's rcosc_trim_bank p m vss t0..t7) for the same reason:",
        "* it is used *only* as every device's bulk tie there, which this",
        "* reference models as 'vsubs' instead -- so 'vss' would otherwise be",
        "* an unused, arity-mismatched pin against the layout side (which",
        "* never draws a 'vss' net at all, matching the deck's vsubs-only",
        "* substrate model).",
    ] + _trim_bank_subckt(devices) + [""]
    path.write_text("\n".join(lines))


def _trim_bank_subckt(devices: dict, vsubs_pin: bool = False) -> list[str]:
    res_order = ["XRFIX"] + [f"XR{i}" for i in range(8)]
    sw_order = [f"XSW{i}" for i in range(8)]
    lines = [
        ".SUBCKT rcosc_trim_bank p m t0 t1 t2 t3 t4 t5 t6 t7"
        + (" vsubs" if vsubs_pin else "")
    ]
    nodes = ["p"] + [f"c{i}" for i in range(1, 9)] + ["m"]
    for i, name in enumerate(res_order):
        d = devices[name]
        r_ohm = _res_r_ohm(d.param_um("r_length"), d.param_um("r_width"))
        lines.append(f"R${name[1:]} {nodes[i]} {nodes[i + 1]} vsubs {r_ohm:.6g} ppolyf_u_1k")
    for i, name in enumerate(sw_order):
        d = devices[name]
        lines.append(
            f"X{name[1:]} {nodes[i + 1]} t{i} {nodes[i + 2]} vsubs nfet_03v3 "
            f"L={d.params['l']} W={d.params['w']} nf={d.param_int('nf')}"
        )
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
    bulk on the real drawn well, `rcosc_trim_bank` without its `vss` pin,
    resistors and the MiM capacitor as plain elements."""
    by_cell = ctx["__devices_by_cell__"]
    trim_pins = " ".join(
        p for p in ctx["__subckt_pins__"]["rcosc_trim_bank"] if p != "vss"
    )
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
    for inst in ("XXCMPH", "XXCMPL"):
        lines.append(
            f"{inst} " + " ".join(devices[inst].nodes) + " vsubs rcosc_comparator"
        )
    for name in ["XMDISCH"] + _TOP_NFETS[1:] + _TOP_PFETS:
        lines.append(_mos_ref_card(name, devices[name]))
    lines += [".ENDS", ""]
    path.write_text("\n".join(lines))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: Build order matters: `rcosc_top` instantiates the other three as sub-cells,
#: so they have to exist on disk (and be current) before it is built.
CELL_ORDER = ["rcosc_bias", "rcosc_trim_bank", "rcosc_comparator", "rcosc_top"]


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
        "rcosc_top": parse_subckt(netlist_text, "rcosc_top"),
    }
    builders = {
        "rcosc_bias": (build_rcosc_bias, _write_reference_netlist_bias),
        "rcosc_trim_bank": (build_rcosc_trim_bank, _write_reference_netlist_trim_bank),
        "rcosc_comparator": (build_rcosc_comparator, _write_reference_netlist_comparator),
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
            for name in ("rcosc_bias", "rcosc_trim_bank", "rcosc_comparator", "rcosc_top")
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
