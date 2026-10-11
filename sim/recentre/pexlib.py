"""Shared helpers for the sim/recentre/ evidence (issue #66).

Loads the committed parasitic-annotated netlist
(sim/pvt-postlayout/results/20260923T152954Z/rcosc_top.pex.spice, the exact
netlist behind the 27-point -18.8 % .. -36.9 % finding), classifies its
parasitic cards by schematic net, builds ablated / re-sized variants of it,
and runs ONE ngspice transient for ONE (netlist, corner, trim code) at a time.

Nothing here launches more than one ngspice process at once, and nothing here
is a corner grid: the 27-point confirmation is a `klt sim` corners request
(gen_requests.py), never a loop over this module.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim" / "pvt"))
sys.path.insert(0, str(REPO / "sim" / "pvt-postlayout"))
import pvt_sweep as base  # noqa: E402
import pex_pvt_sweep as pex  # noqa: E402

PEX_SRC = REPO / "sim/pvt-postlayout/results/20260923T152954Z/rcosc_top.pex.spice"
PVT_TB = REPO / "design/netlist/pvt_tb.spice"

# hub node (as named in the extracted netlist) -> schematic net.  Derived from
# device connectivity (see README.md, "Net identification").
HUB_NAME = {
    r"\$7": "vh", r"\$8": "vl", r"\$9": "pb", r"\$37": "ibias", r"\$1": "n2s",
    r"\$10": "c1", r"\$11": "c2", r"\$14": "c3", r"\$16": "c4", r"\$18": "c5",
    r"\$20": "c6", r"\$22": "c7", r"\$24": "c8", r"\$26": "vc",
    r"\$13": "tb0", r"\$15": "tb1", r"\$17": "tb2", r"\$19": "tb3",
    r"\$21": "tb4", r"\$23": "tb5", r"\$25": "tb6", r"\$27": "tb7",
    r"\$32": "cmph_out", r"\$35": "cmpl_out", r"\$36": "qbar",
    r"\$44": "mid1", r"\$45": "mid2",
    r"\$30": "dpH", r"\$31": "dnH", r"\$29": "tailH",
    r"\$33": "dpL", r"\$34": "outbL", r"\$42": "dnL", r"\$6": "tailL",
    "clk": "clk", "vdd": "vdd", "vss": "vss",
    **{f"t{i}": f"t{i}" for i in range(8)},
}
CHAIN = {f"c{i}" for i in range(1, 9)}
TIMING = {"vc"} | CHAIN
CMP = {"cmph_out", "cmpl_out", "qbar", "mid1", "mid2", "dpH", "dnH", "tailH",
       "dpL", "outbL", "dnL", "tailL", "clk"}
BIAS = {"vh", "vl", "pb", "ibias", "n2s"}

GROUPS = [  # removal order for the telescoping (cumulative) ablation
    "vc_groundC", "vc_couplingC", "chain_C", "cmp_latch_C", "other_C",
    "timing_path_R", "other_R",
]


def hub_of(node: str) -> str:
    return re.sub(r"__t\d+$", "", node)


def net_of(node: str) -> str:
    return HUB_NAME.get(hub_of(node), "?" + hub_of(node))


def load_cards(path: Path = PEX_SRC) -> list[str]:
    """Netlist lines with '+' continuations joined (comments kept)."""
    out: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("+") and out:
            out[-1] += " " + line[1:].strip()
        else:
            out.append(line)
    return out


def classify(card: str) -> str | None:
    """Parasitic group of a card, or None if it is a device / not parasitic."""
    p = card.split()
    if not p:
        return None
    n = p[0]
    if n.startswith("Rvsubs") or n.startswith("C$86") or n.startswith("X"):
        return None
    if n.startswith("R"):  # star series resistor: terminal <-> hub (p[2])
        net = net_of(p[2])
        return "timing_path_R" if net in TIMING else "other_R"
    if n.startswith("Ccc_"):
        a, b = net_of(p[1]), net_of(p[2])
        if "vc" in (a, b):
            return "vc_couplingC"
        if a in CHAIN or b in CHAIN:
            return "chain_C"
        if a in CMP or b in CMP:
            return "cmp_latch_C"
        return "other_C"
    if n.startswith("C"):  # ground cap, C_<hub> or C<pin>
        net = net_of(p[1])
        if net == "vc":
            return "vc_groundC"
        if net in CHAIN:
            return "chain_C"
        if net in CMP:
            return "cmp_latch_C"
        return "other_C"
    return None


def variant(cards: list[str], drop: set[str], *, tie_substrate: bool = False,
            devices_only_bulk: bool = False) -> list[str]:
    """Copy of the cards with every parasitic card of the listed groups
    removed.  Parasitic capacitors are deleted; parasitic star resistors are
    replaced by 1 mohm (deleting them would disconnect the device terminals
    from their net hub).  Nothing else is edited."""
    out = []
    for c in cards:
        g = classify(c)
        if g in drop:
            if c.startswith("R"):  # star R: short it (1 mohm), keep connectivity
                q = c.split()
                c = f"{q[0]} {q[1]} {q[2]} 1m"
                out.append(c)
            continue
        if tie_substrate and c.startswith("Rvsubs_dctie"):
            c = "Rvsubs_dctie vsubs 0 1m"
        out.append(c)
    return out


def mim_law_f(w_um: float, l_um: float) -> float:
    """The deck's own two-term MiM law for cap_mim_1f0_m4m5_noshield
    (layout/lvs_ref/rcosc_top.spice header): 9.87e-16 F/um^2, 3.3e-16 F/um."""
    return 9.87e-16 * w_um * l_um + 3.3e-16 * 2.0 * (w_um + l_um)


def sizing(cards: list[str], *, c_timing_f: float | None = None,
           mim_wl: tuple[float, float] | None = None,
           r_scale: float = 1.0, vc_c_scale: float = 1.0) -> list[str]:
    """Re-size the timing components of a variant: MIM value (farads) and a
    uniform scale of every trim-ladder poly resistor length (RFIX + R0..R7,
    the nine resistors of rcosc_trim_bank, lengths 17.198u .. 95.775u or
    0.748u..).  The bias-divider resistors (100u, 32u) are NOT touched."""
    out = []
    trim_lengths = {"17.198U", "0.748U", "1.497U", "2.993U", "5.986U",
                    "11.972U", "23.944U", "47.888U", "95.775U"}
    for c in cards:
        if c.startswith("C$86") and mim_wl is not None:
            # schematic-form, process-corner-aware MiM (the PDK cap_mim_1f0fF
            # subckt, exactly as design/rcosc_top.sch instantiates it) in
            # place of the extractor's fixed-value plain C element
            p = c.split()
            c = (f"XCTIMING {p[1]} {p[2]} cap_mim_1f0fF "
                 f"c_width={mim_wl[0]:g}u c_length={mim_wl[1]:g}u m=1")
        elif c.startswith("C$86") and c_timing_f is not None:
            p = c.split()
            c = f"{p[0]} {p[1]} {p[2]} {c_timing_f:.6e}"
        elif c.startswith("C_26 ") and vc_c_scale != 1.0:
            p = c.split()
            c = f"{p[0]} {p[1]} {p[2]} {float(p[3]) * vc_c_scale:.6e}"
        elif c.startswith("X$") and "ppolyf_u_1k" in c:
            m = re.search(r"r_length=([0-9.]+U)", c)
            if m and m.group(1) in trim_lengths and r_scale != 1.0:
                val = float(m.group(1)[:-1]) * r_scale
                c = c.replace(m.group(0), f"r_length={val:.5f}U")
        out.append(c)
    return out


def harness(cards: list[str]) -> str:
    """pvt_tb.spice with the embedded rcosc_top subckt replaced by `cards`
    (same substitution pex_pvt_sweep.py performs)."""
    schem = PVT_TB.read_text()
    pins, block, _ = pex.extract_rcosc_top_block(schem)
    text, _ = pex.strip_capacitor_model_annotations("\n".join(cards) + "\n")
    text = pex.reorder_extracted_header(text, pins)
    block_text = "\n".join(block)
    assert block_text in schem
    return schem.replace(block_text, text.rstrip("\n"), 1)


def schematic_harness() -> str:
    return PVT_TB.read_text()


def control(point: "base.Point", tstop_ns: int) -> str:
    vmid = point.vdd_v / 2.0
    n = base.MEAS_LAST_EDGE - base.MEAS_FIRST_EDGE
    return (
        ".control\nset noaskquit\nset measureprec=8\n"
        f"tran {base.TSTEP} {tstop_ns}n\n"
        f"meas tran ta when v(clk)={vmid:.4f} rise={base.MEAS_FIRST_EDGE}\n"
        f"meas tran tb when v(clk)={vmid:.4f} rise={base.MEAS_LAST_EDGE}\n"
        f"let fosc = {n}/(tb-ta)\n"
        "meas tran iavg avg i(VDD) from=ta to=tb\n"
        "print ta tb fosc iavg\nquit\n.endc\n"
    )


_model_dir = None


def run(text: str, point: "base.Point", logdir: Path, tag: str,
        tstop_ns: int = base.TSTOP_NS_DEFAULT) -> dict:
    """One ngspice transient.  Returns {f_hz, iq_a, log}.  Serial only."""
    global _model_dir
    if _model_dir is None:
        _model_dir = base.resolve_pdk()[2]
    for attempt in (1, 2):
        deck = text
        for token, body in (
            (".include pvt_corner.spice", base.corner_include(_model_dir, point)),
            (".include pvt_control.spice", control(point, tstop_ns)),
        ):
            deck = deck.replace(token, body, 1)
        rd = REPO / "sim" / "build" / "recentre" / tag
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "run.spice").write_text(deck)
        t0 = time.time()
        pr = subprocess.run(["ngspice", "-b", "run.spice"], cwd=rd,
                            capture_output=True, text=True, timeout=1800)
        out = pr.stdout + "\n" + pr.stderr
        logdir.mkdir(parents=True, exist_ok=True)
        log = logdir / f"{tag}.log"
        if log.exists() and attempt == 1:
            raise FileExistsError(f"refusing to overwrite raw log {log} (log tags must be unique per run)")
        log.write_text(
            f"# {tag}: {point.process} {point.temp_c:g}C {point.vdd_v:g}V "
            f"code 0x{point.code:02X} tstop {tstop_ns}n, "
            f"wall {time.time()-t0:.1f}s\n" + out)
        mf = base.FOSC_RE.search(out)
        mi = re.search(r"^\s*iavg\s*=\s*([-+0-9.eE]+)", out, re.M)
        if mf and float(mf.group(1)) > 0:
            return {"f_hz": float(mf.group(1)),
                    "iq_a": -float(mi.group(1)) if mi else None,
                    "log": f"{tag}.log"}
        tstop_ns = base.TSTOP_NS_RETRY
    return {"f_hz": None, "iq_a": None, "log": f"{tag}.log"}
