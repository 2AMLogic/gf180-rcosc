#!/usr/bin/env python3
"""Build the settled P3 netlist for the comparator-H output-stage fix (issue #229, DR-0028).

Same recipe as sim/recentre/gen_requests.py `write_dut` (P3 = ladder x0.70 + PDK cap_mim_1f0fF
20u x 10u on the parasitic-annotated extraction), but the extraction is of the *revised*
layout/cells/rcosc_top.gds (MBUFN W 2u -> 1u).  Needs the pinned layout toolchain
(klayout-tools 0.4.0 / klayout 0.30.12, see layout/run_checks.sh) on PATH for `klt extract`.

Usage: python3 -I gen_dut.py [--out DIR]    # writes pex/rcosc_top.pex.{spice,extract.json} and rcosc_top_p3_cmphfix.spice
"""
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "recentre"))
sys.path.insert(0, str(REPO / "sim" / "pvt-postlayout"))
import pexlib as L  # noqa: E402

PINS = "vdd,vss,clk,t0,t1,t2,t3,t4,t5,t6,t7"
DECK = ["poly_res=1k", "mim_cap=cap_mim_1f0_m4m5_noshield"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE)
    out = ap.parse_args().out
    pexdir = out / "pex"
    pexdir.mkdir(parents=True, exist_ok=True)
    pex = pexdir / "rcosc_top.pex.spice"
    cmd = ["klt", "extract", str(REPO / "layout/cells/rcosc_top.gds"), "--deck", "gf180mcu", "--top", "rcosc_top",
           "--pdk", "gf180mcuC", *[a for o in DECK for a in ("--deck-option", o)], "--pins", PINS,
           "--parasitics", "-o", str(pex), "--format", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode:
        sys.exit(r.stderr)
    (pexdir / "rcosc_top.pex.extract.json").write_text(r.stdout)
    cards = L.sizing(L.load_cards(pex), mim_wl=(20.0, 10.0), r_scale=0.70)
    text, _ = L.pex.strip_capacitor_model_annotations("\n".join(cards) + "\n")
    text = L.pex.reorder_extracted_header(text, ["vdd", "vss", "clk"] + [f"t{i}" for i in range(8)])
    (out / "rcosc_top_p3_cmphfix.spice").write_text(
        "* rcosc_top, settled P3 sizing (DR-0023) on the comparator-H output-stage fix (DR-0028, issue #229):\n"
        "* parasitic-annotated extraction of the revised layout/cells/rcosc_top.gds (MBUFN W=1u) with the\n"
        "* nine trim-ladder poly resistor lengths x0.70 and the PDK cap_mim_1f0fF 20u x 10u timing MiM.\n"
        "* Same transformation as sim/recentre/p3/rcosc_top_p3.spice; nothing else edited.\n" + text)


if __name__ == "__main__":
    main()
