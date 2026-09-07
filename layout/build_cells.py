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

from gen_lib import Composer  # noqa: E402
from netlist_parse import parse_subckt  # noqa: E402

GAP_UM = 4.0
ROW2_GAP_UM = 3.0
SHEET_RHO_OHM_SQ = 1000.0  # ppolyf_u_1k, DR-0003 sec 5.1/6.1

# klayout-tools#1551 workaround -- see module docstring.
_R1_LENGTH_NUDGE_UM = 1.4966


def _res_r_ohm(length_um: float, width_um: float) -> float:
    return SHEET_RHO_OHM_SQ * length_um / width_um


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
    for i, sw_name in enumerate(sw_order):
        r_name = res_order[i + 1]
        r, sw = placed_r[r_name], placed_sw[sw_name]
        r_a, r_b = r.port_abs("R0_A"), r.port_abs("R0_B")
        sw_s, sw_d, sw_g = sw.port_abs("U0_S"), sw.port_abs("U0_D"), sw.port_abs("U0_G")
        c.wire_z((r_a[0], r_a[1]), (sw_s[0], sw_s[1]), 0.42, y_mid)
        c.wire_z((r_b[0], r_b[1]), (sw_d[0], sw_d[1]), 0.42, y_mid)
        gate_net = devices[sw_name].nodes[1]  # t{i}
        c.add_pin_label(sw_g[0], sw_g[1], gate_net)

    p_port = placed_r["XRFIX"].port_abs("R0_A")
    m_port = placed_r["XR7"].port_abs("R0_B")
    c.add_pin_label(p_port[0], p_port[1], "p")
    c.add_pin_label(m_port[0], m_port[1], "m")

    patched = c.patch_high_sheet_resistors()
    assert patched == 9, f"expected 9 resistors patched, got {patched}"
    return c, ["p", "m"] + [f"t{i}" for i in range(8)]


def _write_reference_netlist_bias(devices: dict, path: Path) -> None:
    rba, rbb, rbc, rbias = devices["XRBA"], devices["XRBB"], devices["XRBC"], devices["XRBIAS"]
    mbiasd = devices["XMBIASD"]
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
        ".SUBCKT rcosc_bias vdd vss vh vl ibias",
        f"R$RBA vdd vh vsubs {_res_r_ohm(rba.param_um('r_length'), rba.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBB vh vl vsubs {_res_r_ohm(rbb.param_um('r_length'), rbb.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBC vl vss vsubs {_res_r_ohm(rbc.param_um('r_length'), rbc.param_um('r_width')):.6g} ppolyf_u_1k",
        f"R$RBIAS vdd ibias vsubs {_res_r_ohm(rbias.param_um('r_length'), rbias.param_um('r_width')):.6g} ppolyf_u_1k",
        f"XMBIASD ibias ibias vss vsubs nfet_03v3 L={mbiasd.params['l']} W={mbiasd.params['w']} nf={mbiasd.param_int('nf')}",
        ".ENDS",
        "",
    ]
    path.write_text("\n".join(lines))


def _write_reference_netlist_trim_bank(devices: dict, path: Path) -> None:
    res_order = ["XRFIX"] + [f"XR{i}" for i in range(8)]
    sw_order = [f"XSW{i}" for i in range(8)]
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
        ".SUBCKT rcosc_trim_bank p m t0 t1 t2 t3 t4 t5 t6 t7",
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
    lines += [".ENDS", ""]
    path.write_text("\n".join(lines))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify committed GDS/reference netlists are current")
    parser.add_argument("--cell", choices=["rcosc_bias", "rcosc_trim_bank"], help="build only this cell")
    args = parser.parse_args()

    if not NETLIST_PATH.exists():
        print(f"error: {NETLIST_PATH} does not exist -- run design/regen-netlist.sh first", file=sys.stderr)
        return 1

    netlist_text = NETLIST_PATH.read_text()
    bias_devices = parse_subckt(netlist_text, "rcosc_bias")
    trim_devices = parse_subckt(netlist_text, "rcosc_trim_bank")

    CELLS_DIR.mkdir(exist_ok=True)
    LVS_REF_DIR.mkdir(exist_ok=True)

    builds = []
    if args.cell in (None, "rcosc_bias"):
        builds.append(("rcosc_bias", build_rcosc_bias, bias_devices, _write_reference_netlist_bias))
    if args.cell in (None, "rcosc_trim_bank"):
        builds.append(("rcosc_trim_bank", build_rcosc_trim_bank, trim_devices, _write_reference_netlist_trim_bank))

    ok = True
    for cell_name, build_fn, devices, ref_writer in builds:
        gds_path = CELLS_DIR / f"{cell_name}.gds"
        ref_path = LVS_REF_DIR / f"{cell_name}.spice"

        if args.check:
            before = _sha256(gds_path) if gds_path.exists() else None
            ref_before = ref_path.read_text() if ref_path.exists() else None

        composer, pins = build_fn(devices)
        tmp_gds = gds_path.with_suffix(".gds.tmp")
        composer.write(str(tmp_gds))
        ref_writer(devices, ref_path.with_suffix(".spice.tmp"))

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
