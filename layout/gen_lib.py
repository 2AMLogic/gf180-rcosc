"""Composition helpers for building gf180-rcosc layout cells out of `klt gen`
primitives (issue #13).

This module is deliberately small and general: it wraps
`klayout_tools.gen.generate()` (the same in-process entry point `klt gen`'s
CLI calls) to produce one GDS per device/device-array, imports each into a
single composing `klayout.db.Layout`, places it at a caller-chosen offset,
and provides simple Manhattan-wire and pin-label helpers so a build script
can wire the placed devices together into a real subcircuit.

Why generated primitives instead of hand-drawn geometry: `klt gen`'s
`mos_array`/`res_array` generators already produce DRC-clean, PDK-rule-aware
unit devices (contacts, enclosures, spacing) for gf180mcu -- hand-drawing
the same geometry from scratch would just re-derive the same rules with more
risk of a DRC miss. See `layout/README.md` for the full rationale and the
`klt gen res_array` gf180mcu high-sheet-rho flavor gap this module works
around (`_patch_high_sheet_resistor_marker` below).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

import klayout.db as kdb
import klayout_tools.gen as ktgen

DBU_UM = 0.001

# gf180mcu layer roles used directly by this module (mirrors
# klayout_tools.gen._PDK_ROLE_LAYERS["gf180mcu"] / decks/gf180mcu.py).
METAL1 = (34, 0)
METAL1_LABEL = (34, 10)
RES_MK = (110, 5)
RESISTOR_HI = (62, 0)  # high-sheet-rho marker; see _patch_high_sheet_resistor_marker


def _um_to_dbu(value_um: float) -> int:
    return int(round(value_um / DBU_UM))


@dataclass
class Port:
    x_um: float
    y_um: float
    width_um: float
    direction_deg: float


@dataclass
class Placed:
    """A `klt gen` cell instantiated into a composing layout at (x0, y0)."""

    name: str
    x0_um: float
    y0_um: float
    bbox_um: tuple[float, float, float, float]
    ports: dict[str, Port] = field(default_factory=dict)

    def port_abs(self, port_name: str) -> tuple[float, float, float]:
        """(x_um, y_um, width_um) of `port_name` in the composing layout's
        coordinate frame."""
        p = self.ports[port_name]
        return (self.x0_um + p.x_um, self.y0_um + p.y_um, p.width_um)

    @property
    def x1_um(self) -> float:
        return self.x0_um + self.bbox_um[2]

    @property
    def y1_um(self) -> float:
        return self.y0_um + self.bbox_um[3]


class Composer:
    """Builds one composing `klayout.db.Layout` out of `klt gen` cells."""

    def __init__(self, top_cell_name: str, pdk_variant: str = "gf180mcuC"):
        self.pdk_variant = pdk_variant
        self.layout = kdb.Layout()
        self.layout.dbu = DBU_UM
        self.top = self.layout.create_cell(top_cell_name)
        self.li_metal1 = self.layout.layer(*METAL1)
        self.li_label = self.layout.layer(*METAL1_LABEL)
        self.li_res_mk = self.layout.layer(*RES_MK)
        self.li_resistor_hi = self.layout.layer(*RESISTOR_HI)
        self._tmpdir = tempfile.mkdtemp(prefix="rcosc_gen_")
        self._unique = 0

    # -- device generation + placement ------------------------------------

    def gen_and_place(
        self, generator: str, params: dict, x0_um: float, y0_um: float, label: str
    ) -> Placed:
        """Run `klt gen <generator>` with `params`, import the result, and
        place it at (x0_um, y0_um) in this composer's top cell (no
        rotation -- every cell this build script places is used
        right-side-up)."""
        self._unique += 1
        cell_name = f"{label}_{self._unique}"
        out_path = os.path.join(self._tmpdir, f"{cell_name}.gds")
        resp = ktgen.generate(
            {
                "generator": generator,
                "params": params,
                "pdk": {"variant": self.pdk_variant},
                "options": {"cell_name": cell_name, "output": out_path},
            }
        )
        self.layout.read(out_path)
        placed_cell = self.layout.cell(cell_name)
        assert placed_cell is not None, f"{cell_name} did not import"
        inst = kdb.CellInstArray(
            placed_cell.cell_index(),
            kdb.Trans(_um_to_dbu(x0_um), _um_to_dbu(y0_um)),
        )
        self.top.insert(inst)

        bbox = placed_cell.bbox()
        bbox_um = (
            bbox.left * DBU_UM,
            bbox.bottom * DBU_UM,
            bbox.right * DBU_UM,
            bbox.top * DBU_UM,
        )
        ports = {
            p["name"]: Port(p["x_um"], p["y_um"], p["width_um"], p["direction_deg"])
            for p in resp["ports"]
        }
        return Placed(cell_name, x0_um, y0_um, bbox_um, ports)

    def peek_bbox(self, generator: str, params: dict) -> tuple[float, float, float, float]:
        """Run `klt gen <generator>` with `params` and return its bbox
        (x0,y0,x1,y1) in um, WITHOUT importing/placing it into this
        composer's layout -- for a caller that needs a generated cell's
        footprint to compute a placement offset (e.g. centering a switch
        above the resistor it shunts) before committing to the real
        `gen_and_place()` call. Writes to a scratch path in this composer's
        own tmpdir; never touches `self.layout` or `self.top`."""
        self._unique += 1
        cell_name = f"peek_{self._unique}"
        out_path = os.path.join(self._tmpdir, f"{cell_name}.gds")
        resp = ktgen.generate(
            {
                "generator": generator,
                "params": params,
                "pdk": {"variant": self.pdk_variant},
                "options": {"cell_name": cell_name, "output": out_path},
            }
        )
        b = resp["bbox_um"]
        return (b["x0"], b["y0"], b["x1"], b["y1"])

    # -- wiring -------------------------------------------------------------

    def wire_segment(
        self, x0_um: float, y0_um: float, x1_um: float, y1_um: float, width_um: float
    ) -> None:
        """Draw one axis-aligned metal1 rectangle covering (x0,y0)-(x1,y1),
        `width_um` wide in the perpendicular direction. Either exactly
        horizontal or exactly vertical."""
        half = width_um / 2.0
        if abs(y0_um - y1_um) < 1e-9:  # horizontal
            lo_x, hi_x = sorted((x0_um, x1_um))
            box = kdb.Box(
                _um_to_dbu(lo_x),
                _um_to_dbu(y0_um - half),
                _um_to_dbu(hi_x),
                _um_to_dbu(y0_um + half),
            )
        elif abs(x0_um - x1_um) < 1e-9:  # vertical
            lo_y, hi_y = sorted((y0_um, y1_um))
            box = kdb.Box(
                _um_to_dbu(x0_um - half),
                _um_to_dbu(lo_y),
                _um_to_dbu(x0_um + half),
                _um_to_dbu(hi_y),
            )
        else:
            raise ValueError(
                f"wire_segment: not axis-aligned ({x0_um},{y0_um})-({x1_um},{y1_um})"
            )
        self.top.shapes(self.li_metal1).insert(box)

    def wire_l(
        self,
        p_from: tuple[float, float],
        p_to: tuple[float, float],
        width_um: float,
        via_x: float | None = None,
    ) -> None:
        """Connect two points with a two-segment Manhattan (L-shaped) wire,
        jogging at `via_x` (defaults to `p_from`'s own x -- a vertical-then-
        horizontal dogleg) if the points do not already share an axis."""
        x0, y0 = p_from
        x1, y1 = p_to
        if abs(x0 - x1) < 1e-9 or abs(y0 - y1) < 1e-9:
            self.wire_segment(x0, y0, x1, y1, width_um)
            return
        jog_x = via_x if via_x is not None else x0
        self.wire_segment(x0, y0, jog_x, y0, width_um)
        self.wire_segment(jog_x, y0, jog_x, y1, width_um)
        self.wire_segment(jog_x, y1, x1, y1, width_um)

    def wire_z(
        self,
        p_from: tuple[float, float],
        p_to: tuple[float, float],
        width_um: float,
        y_mid: float,
    ) -> None:
        """Connect two points with a three-segment Manhattan (Z-shaped)
        wire: vertical from `p_from` to `y_mid`, horizontal at `y_mid`, then
        vertical up to `p_to` -- for jogging through an empty channel
        between two rows without the two-segment `wire_l` dogleg's risk of
        clipping a row's own device geometry near the jog."""
        x0, y0 = p_from
        x1, y1 = p_to
        self.wire_segment(x0, y0, x0, y_mid, width_um)
        self.wire_segment(x0, y_mid, x1, y_mid, width_um)
        self.wire_segment(x1, y_mid, x1, y1, width_um)

    def add_pin_label(self, x_um: float, y_um: float, text: str) -> None:
        self.top.shapes(self.li_label).insert(
            kdb.Text(text, kdb.Trans(_um_to_dbu(x_um), _um_to_dbu(y_um)))
        )

    # -- gf180mcu high-sheet-rho resistor patch ------------------------------

    def patch_high_sheet_resistors(self) -> int:
        """Draw the gf180mcu `Resistor` (62/0) high-sheet-rho marker over
        every `RES_MK` (110/5) box in every imported cell, so `klt extract`
        recognises each `res_array`-drawn resistor as `ppolyf_u_1k`
        (1000 ohm/sq, this design's device -- DR-0003 sec 5.1/6.1) instead of
        the generator's only available flavor, the base `ppolyf_u`
        (~350 ohm/sq, klayout_tools.decks.gf180mcu.EXTRACTION_DECK's
        un-flavored entry). `klt gen res_array` has no gf180mcu flavor
        param that draws this marker (filed as klayout-tools#1550) -- this
        is the one-line workaround this build script applies to every
        generated resistor cell before writing the final GDS. Returns the
        number of markers patched (a build with 0 patched resistors is a
        build-script bug, not a clean run -- callers should assert this is
        nonzero)."""
        patched = 0
        for cell in self.layout.each_cell():
            boxes = [s.bbox() for s in cell.shapes(self.li_res_mk).each()]
            for box in boxes:
                cell.shapes(self.li_resistor_hi).insert(box)
                patched += 1
        return patched

    # -- output ---------------------------------------------------------------

    def write(self, path: str) -> None:
        opts = kdb.SaveLayoutOptions()
        opts.gds2_write_timestamps = False
        self.layout.write(path, opts)
