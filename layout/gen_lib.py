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

Issue #27 adds three things `rcosc_comparator`/`rcosc_top` need and the two
single-row, metal1-only cells of #13 did not:

* a **two-layer channel router** (:class:`Channel`) -- one horizontal track
  per net in a channel above a row of blocks, reached by one vertical column
  per terminal on the layer below. Two layers is what makes an arbitrary
  (non-planar) netlist routable at all: #13's cells happened to be planar in
  metal1 alone, a five-transistor differential pair is not.
* an **n-well group** helper (:meth:`Composer.draw_nwell` /
  `klt gen well_island`) so a group of PMOS devices shares one well tied to a
  real supply rail, instead of extracting with a floating body.
* a hand-drawn **MiM capacitor** (:meth:`Composer.add_mim_cap`) -- `klt gen
  cap_array` has no gf180mcu plate layers (see `layout/README.md`), so this
  is the one device in this design drawn from base layers rather than
  generated.
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
NWELL = (21, 0)

# BEOL stack (EXTRACTION_DECK.metals / .vias / .metal_labels, decks/gf180mcu.py).
VIA1 = (35, 0)
METAL2 = (36, 0)
METAL2_LABEL = (36, 10)
VIA2 = (38, 0)
METAL3 = (42, 0)
METAL3_LABEL = (42, 10)
VIA3 = (40, 0)
METAL4 = (46, 0)
VIA4 = (41, 0)
METAL5 = (81, 0)

# MiM capacitor recognition layers (EXTRACTION_DECK.capacitors, decks/gf180mcu.py):
# a FuseTop top plate covered by both CAP_MK and MIM_L_MK, over a Metal4 bottom
# plate, with Via4 taking the top plate up to Metal5.
FUSETOP = (75, 0)
CAP_MK = (117, 5)
MIM_L_MK = (117, 10)

#: Minimum DRC dimensions this module's own hand-drawn geometry has to clear
#: (klayout_tools/decks/gf180mcu.py `DRC_DECK`, transcribed here only as the
#: sizes the helpers below draw at -- `klt drc` remains the authority).
VIA_SIZE_UM = 0.26  # via{1,2,3,4}.width.1
WIRE_WIDTH_UM = 0.42  # >= metal1.width.1 (0.23) and metal{2..5}.width.1 (0.28)
#: Bottom-plate (Metal4) overlap of the MiM top plate: mim.enclosing.fusetop.1
#: ("MIMTM.3", 0.6 um). Drawn with margin.
MIM_PLATE_MARGIN_UM = 1.0
#: Minimum spacing from the MiM virtual bottom plate to any other Metal4:
#: mim.space.1 ("MIMTM.1", 1.2 um). Drawn with margin.
MIM_KEEPOUT_UM = 2.0


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
        self._imported: dict[str, str] = {}  # cell name -> source GDS (place_gds)

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
        self,
        x0_um: float,
        y0_um: float,
        x1_um: float,
        y1_um: float,
        width_um: float,
        layer: tuple[int, int] = METAL1,
    ) -> None:
        """Draw one axis-aligned rectangle covering (x0,y0)-(x1,y1),
        `width_um` wide in the perpendicular direction, on `layer` (metal1 by
        default -- the only layer #13's two cells route on). Either exactly
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
        self.top.shapes(self.layout.layer(*layer)).insert(box)

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

    def add_pin_label(
        self, x_um: float, y_um: float, text: str, layer: tuple[int, int] = METAL1_LABEL
    ) -> None:
        """Name the net covering (x_um, y_um) `text`, by dropping a text on
        the pin/label purpose of the routing layer it is drawn on (metal1's
        34/10 by default; `EXTRACTION_DECK.metal_labels` carries one per metal
        level). The point MUST be covered by a shape this composer drew in its
        own top cell -- a label over a *sub-cell's* metal is not reliably
        promoted to a pin by `klt extract` (observed on the well-tap ring
        during this cell's bring-up), so callers place labels on their own
        wires, never on a generated cell's pad."""
        self.top.shapes(self.layout.layer(*layer)).insert(
            kdb.Text(text, kdb.Trans(_um_to_dbu(x_um), _um_to_dbu(y_um)))
        )

    def draw_box(
        self, layer: tuple[int, int], x0_um: float, y0_um: float, x1_um: float, y1_um: float
    ) -> None:
        """Draw one plain rectangle on `layer` -- for marker/implant/well
        layers that carry no routing semantics."""
        self.top.shapes(self.layout.layer(*layer)).insert(
            kdb.Box(_um_to_dbu(x0_um), _um_to_dbu(y0_um), _um_to_dbu(x1_um), _um_to_dbu(y1_um))
        )

    def draw_nwell(self, x0_um: float, y0_um: float, x1_um: float, y1_um: float) -> None:
        """Draw one Nwell rectangle covering a whole group of PMOS devices (and
        their `well_island` tap), merging their individually generated wells
        into a single equipotential well.

        Why a group well rather than each generator's own 0.15um-margin well:
        gf180mcu's `nwell.space.1` ("NW.2a") is 0.6um even between
        equipotential wells, so two `mos_array --flavor pfet` devices placed
        for routing convenience are a DRC violation the moment they sit closer
        than that -- and, worse, three separately-walled PMOS bodies extract as
        three unrelated floating nets. One drawn well is both DRC-legal and the
        correct device model: these PMOS bodies really are one well at one
        potential. The caller is responsible for keeping every NMOS active
        outside this rectangle -- `klt extract`'s MOS split is "active inside
        the well is PMOS, outside is NMOS", so an NMOS swallowed by this box
        silently changes device class."""
        self.draw_box(NWELL, x0_um, y0_um, x1_um, y1_um)

    def via(self, layer: tuple[int, int], x_um: float, y_um: float) -> None:
        """Drop one minimum-size via cut centred at (x_um, y_um). Every via
        level in this PDK is the same 0.26um square (`via{1,2,3,4}.width.1`);
        the conductors above and below are the caller's own wires, which are
        `WIRE_WIDTH_UM` (0.42um) wide and so clear both enclosure rules
        (0.0um below Via1, 0.01um everywhere else) by 0.08um."""
        half = VIA_SIZE_UM / 2.0
        self.draw_box(layer, x_um - half, y_um - half, x_um + half, y_um + half)

    def via_stack(
        self,
        x_um: float,
        y_um: float,
        levels: tuple[tuple[tuple[int, int], tuple[int, int]], ...],
        pad_um: float = WIRE_WIDTH_UM,
    ) -> None:
        """Drop a column of vias plus their landing pads at (x_um, y_um).

        `levels` is an ordered tuple of `(via_layer, metal_below_layer)` pairs;
        the metal *above* the first via is assumed to already be drawn by the
        caller (it is the thing being brought down)."""
        half = pad_um / 2.0
        for via_layer, metal_layer in levels:
            self.via(via_layer, x_um, y_um)
            self.draw_box(
                metal_layer, x_um - half, y_um - half, x_um + half, y_um + half
            )

    # -- MiM capacitor (hand-drawn: `klt gen cap_array` has no gf180mcu plates)

    def add_mim_cap(
        self,
        x0_um: float,
        y0_um: float,
        plate_w_um: float,
        plate_h_um: float,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Draw one MiM capacitor whose top plate is `plate_w_um` x
        `plate_h_um` with its lower-left corner at (x0_um, y0_um), and return
        `((bottom_x, bottom_y), (top_x, top_y))` -- the two Metal4 points a
        caller drops a `via_stack` on to reach each terminal.

        Recognition geometry (`EXTRACTION_DECK.capacitors`, decks/gf180mcu.py):
        a `FuseTop` top plate covered by both `CAP_MK` and `MIM_L_MK`, over a
        `Metal4` bottom plate. Drawn by hand because `klt gen cap_array`
        refuses gf180mcu outright ("PDK family 'gf180mcu' has no MiM capacitor
        plate layers configured -- supported families: sky130, sg13g2") even
        though the extraction deck models all three of the PDK's MiM densities
        -- see `layout/README.md`'s `klt` gap list.

        The *top* plate's return point is deliberately not on the plate: the
        deck routes a top plate up through `Via4` to `Metal5` only, and there
        is no via above Metal5, so the only way back down to metal1 is a
        Metal5 jumper out to a second Via4 landing on ordinary Metal4 --
        placed `MIM_KEEPOUT_UM` clear of the virtual bottom plate so
        `mim.space.1` (MIMTM.1, 1.2um) still holds."""
        x1_um = x0_um + plate_w_um
        y1_um = y0_um + plate_h_um
        mid_y = (y0_um + y1_um) / 2.0
        m = MIM_PLATE_MARGIN_UM

        self.draw_box(FUSETOP, x0_um, y0_um, x1_um, y1_um)
        # CAP_MK / MIM_L_MK must cover the top plate for it to be recognised.
        self.draw_box(CAP_MK, x0_um - 0.5, y0_um - 0.5, x1_um + 0.5, y1_um + 0.5)
        self.draw_box(MIM_L_MK, x0_um - 0.5, y0_um - 0.5, x1_um + 0.5, y1_um + 0.5)
        # Bottom plate: Metal4, overlapping the top plate by >= 0.6um
        # (mim.enclosing.fusetop.1 / MIMTM.3).
        self.draw_box(METAL4, x0_um - m, y0_um - m, x1_um + m, y1_um + m)

        # Top plate -> Via4 -> Metal5 jumper -> Via4 -> ordinary Metal4 pad.
        top_via_x = (x0_um + x1_um) / 2.0
        jumper_x = x1_um + m + MIM_KEEPOUT_UM
        half = WIRE_WIDTH_UM / 2.0
        self.via(VIA4, top_via_x, mid_y)
        # Overhang both ends by half a wire width: a Metal5 run ending exactly
        # on its via's centre leaves the cut hanging over the edge
        # (`metal5.enclosing.via4.1`, 0.01um).
        self.wire_segment(
            top_via_x - half, mid_y, jumper_x + half, mid_y, WIRE_WIDTH_UM, METAL5
        )
        self.via(VIA4, jumper_x, mid_y)
        self.draw_box(METAL4, jumper_x - half, mid_y - half, jumper_x + half, mid_y + half)

        bottom_x = x0_um - m + half
        return ((bottom_x, mid_y), (jumper_x, mid_y))

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

    # -- sub-cell instantiation (hierarchical composition) --------------------

    @staticmethod
    def peek_gds_bbox(gds_path: str, cell_name: str) -> tuple[float, float, float, float]:
        """Read an already-built cell's bbox (x0,y0,x1,y1 in um) without
        importing it into this composer's layout -- the sub-cell analogue of
        `peek_bbox`, for a caller computing a placement offset."""
        scratch = kdb.Layout()
        scratch.read(gds_path)
        cell = scratch.cell(cell_name)
        assert cell is not None, f"{cell_name} not found in {gds_path}"
        b = cell.bbox()
        dbu = scratch.dbu
        return (b.left * dbu, b.bottom * dbu, b.right * dbu, b.top * dbu)

    def place_gds(
        self, gds_path: str, cell_name: str, x0_um: float, y0_um: float
    ) -> tuple[float, float, float, float]:
        """Instantiate an already-built cell (e.g. `layout/cells/
        rcosc_bias.gds`) as a sub-cell of this composer's top cell at
        (x0_um, y0_um), *without* redrawing its geometry.

        Every pin/label text inside the imported hierarchy is dropped. A
        sub-cell's own pin labels name *its* nets ("vdd", "out", ...); at the
        level above, the same text would name a different net -- and two
        instances of the same cell (this design's `XXCMPH`/`XXCMPL`) would
        label two distinct nets identically. The enclosing cell names its own
        nets with its own labels.

        A cell placed more than once is read exactly once and re-instantiated:
        `Layout.read` merges a same-named cell's shapes *into* the existing
        one, so a second read would both duplicate every shape and re-add the
        labels this method had just stripped.

        **Imported `klt gen` cells come back as live PCell proxies.** A
        generated cell round-trips through GDS carrying its PCell context
        (`PCELL=mos_array`, `P(well_present)=true`, ... in the stream), so
        KLayout re-reads it as a proxy and *re-evaluates it from those
        parameters* -- discarding anything drawn into it after generation --
        the next time the PCell library is touched, which the very next
        `klt gen` call in the same process does. Concretely: every
        high-sheet-rho resistor marker `patch_high_sheet_resistors()` had
        drawn into an imported sub-cell disappeared the moment the composing
        script generated its next device, silently turning 1k ohm/sq resistors
        back into 350's at extraction time (DRC stays clean; only the
        extracted resistance changes, by 2.9x). The caller's defence is to
        re-apply `patch_high_sheet_resistors()` *after* the last generation in
        the cell -- which every builder in `build_cells.py` already does as
        its final step."""
        if cell_name not in self._imported:
            before = {c.name for c in self.layout.each_cell()}
            self.layout.read(gds_path)
            imported = [c for c in self.layout.each_cell() if c.name not in before]
            for label_layer in (METAL1_LABEL, METAL2_LABEL, METAL3_LABEL):
                li = self.layout.layer(*label_layer)
                for c in imported:
                    c.shapes(li).clear()
            self._imported[cell_name] = gds_path
        elif self._imported[cell_name] != gds_path:
            raise ValueError(
                f"cell {cell_name!r} already imported from "
                f"{self._imported[cell_name]!r}, not {gds_path!r}"
            )
        cell = self.layout.cell(cell_name)
        assert cell is not None, f"{cell_name} not found in {gds_path}"
        self.top.insert(
            kdb.CellInstArray(
                cell.cell_index(), kdb.Trans(_um_to_dbu(x0_um), _um_to_dbu(y0_um))
            )
        )
        b = cell.bbox()
        return (
            b.left * DBU_UM,
            b.bottom * DBU_UM,
            b.right * DBU_UM,
            b.top * DBU_UM,
        )

    # -- output ---------------------------------------------------------------

    def write(self, path: str) -> None:
        opts = kdb.SaveLayoutOptions()
        opts.gds2_write_timestamps = False
        self.layout.write(path, opts)


@dataclass
class _Terminal:
    net: str
    x_um: float  # the port's own x
    y_um: float  # the port's own y
    column_x_um: float  # x of this terminal's vertical column


class Channel:
    """A two-layer channel router for one row of blocks (issue #27).

    #13's two cells were routed in metal1 alone, which works only because
    each of them is planar: every net's terminals could be reached without
    two nets' wires having to cross. A five-transistor differential pair is
    not planar (`dn` has to reach both load gates *across* `dp`'s run to the
    output buffer), and neither is `rcosc_top`. Two layers, used with a strict
    direction discipline, make an arbitrary netlist routable without a
    general-purpose maze router:

    * one **horizontal track per net**, on `track_layer`, in a channel above
      the row -- tracks never cross each other because each net owns a
      distinct y;
    * one **vertical column per terminal**, on `column_layer`, from the
      terminal up to its net's track -- columns never cross each other
      because each owns a distinct x, and they cross *tracks* only on the
      other layer, where a crossing is not a short;
    * one via per (column, track) intersection that is actually a connection.

    Two modes, selected by `port_via`:

    * `port_via=None` -- terminals are already on `column_layer` (a
      `mos_array` pad is metal1 and columns are metal1). A short horizontal
      stub on `column_layer` walks the port out to its column, so the column
      itself never runs over the device it belongs to.
    * `port_via=VIA1` -- terminals are on the layer *below* `column_layer` (a
      sub-cell's metal1 pin pad, with metal2 columns above it). The column
      starts with a via directly on the port, and `column_x_um` must be the
      port's own x.
    """

    def __init__(
        self,
        composer: Composer,
        *,
        column_layer: tuple[int, int],
        track_layer: tuple[int, int],
        track_via: tuple[int, int],
        y0_um: float,
        pitch_um: float,
        port_via: tuple[int, int] | None = None,
        width_um: float = WIRE_WIDTH_UM,
    ):
        self.c = composer
        self.column_layer = column_layer
        self.track_layer = track_layer
        self.track_via = track_via
        self.port_via = port_via
        self.y0_um = y0_um
        self.pitch_um = pitch_um
        self.width_um = width_um
        self._terminals: list[_Terminal] = []
        self.track_y_um: dict[str, float] = {}

    def add(self, net: str, x_um: float, y_um: float, column_x_um: float) -> None:
        """Register one terminal of `net` at (x_um, y_um), rising to its
        net's track in the column at `column_x_um`.

        `column_x_um == x_um` runs the column straight up out of the port,
        which is what a sub-cell pin pad wants. A different `column_x_um`
        walks the port sideways first, on `column_layer`, into the gap beside
        its block -- what a MOS device wants, since its three terminals sit
        only ~0.46um apart (narrower than one column pitch) and its own body
        is in the way of a straight-up run."""
        self._terminals.append(_Terminal(net, x_um, y_um, column_x_um))

    def route(self, net_order: list[str]) -> dict[str, float]:
        """Assign one track per net in `net_order` (bottom-up, `pitch_um`
        apart), draw every track/column/via, and return `{net: track_y_um}`.
        Raises if a net has terminals but no track, or if two columns of
        different nets would land on the same x."""
        for i, net in enumerate(net_order):
            self.track_y_um[net] = self.y0_um + i * self.pitch_um

        for t in self._terminals:
            if t.net not in self.track_y_um:
                raise ValueError(f"net {t.net!r} has a terminal but no track")

        # Two columns of *different* nets closer than one wire width plus the
        # layer's minimum spacing are a short, not a DRC nit -- catch it here,
        # at the floorplan, rather than as an unreadable `klt lvs` net.merged
        # cascade later. (0.30um covers metal1's 0.23 and metal{2..5}'s 0.28.)
        min_sep = self.width_um + 0.30
        ordered = sorted(self._terminals, key=lambda t: t.column_x_um)
        for a, b in zip(ordered[:-1], ordered[1:]):
            if a.net != b.net and (b.column_x_um - a.column_x_um) < min_sep - 1e-9:
                raise ValueError(
                    f"columns {a.net!r}@{a.column_x_um:.3f} and "
                    f"{b.net!r}@{b.column_x_um:.3f} are closer than {min_sep}um"
                )

        half = self.width_um / 2.0
        for t in self._terminals:
            track_y = self.track_y_um[t.net]
            if self.port_via is not None:
                self.c.via(self.port_via, t.x_um, t.y_um)
                self.c.draw_box(
                    self.column_layer,
                    t.x_um - half, t.y_um - half, t.x_um + half, t.y_um + half,
                )
            if abs(t.column_x_um - t.x_um) > 1e-9:
                self.c.wire_segment(
                    t.x_um, t.y_um, t.column_x_um, t.y_um, self.width_um,
                    self.column_layer,
                )
            self.c.wire_segment(
                t.column_x_um, t.y_um, t.column_x_um, track_y + half,
                self.width_um, self.column_layer,
            )
            self.c.via(self.track_via, t.column_x_um, track_y)

        by_net: dict[str, list[float]] = {}
        for t in self._terminals:
            by_net.setdefault(t.net, []).append(t.column_x_um)
        for net, xs in by_net.items():
            self.c.wire_segment(
                min(xs) - half, self.track_y_um[net], max(xs) + half,
                self.track_y_um[net], self.width_um, self.track_layer,
            )
        return self.track_y_um

    def top_y_um(self, net_order: list[str]) -> float:
        return self.y0_um + (len(net_order) - 1) * self.pitch_um

    def pin_pad(
        self,
        net: str,
        column_x_um: float,
        pad_y_um: float,
        label_layer: tuple[int, int],
    ) -> tuple[float, float]:
        """Extend `net`'s column at `column_x_um` up past every track to
        `pad_y_um`, finish it with a pad, and label it `net` there.

        Bringing every pin out to one row of pads above the channel is what
        lets the level above route to this cell without ever having to cross
        its internal tracks -- the pad row is, by construction, clear of
        them."""
        half = self.width_um / 2.0
        self.c.wire_segment(
            column_x_um, self.track_y_um[net], column_x_um, pad_y_um,
            self.width_um, self.column_layer,
        )
        self.c.draw_box(
            self.column_layer,
            column_x_um - half, pad_y_um - half, column_x_um + half, pad_y_um + half,
        )
        self.c.add_pin_label(column_x_um, pad_y_um, net, label_layer)
        return (column_x_um, pad_y_um)
