#!/usr/bin/env python3
"""Row 4 `ss` span / 0xFF running-Iq variant search (issue #337, operator ruling 2026-11-18). Sim-only; launches nothing.

Same bench and DUT as sim/row4-w3r65/gen.py (extraction of the rebuilt layout, netlist text edit; layout NOT re-extracted), but the
variant name is `w<K>r<P>` with K a decimal width multiplier of the 16 bank pass devices and P the percent length of base resistor X$91
(sized by sim/row4-nonron/variant.py, which takes integer or decimal K). Usage as sim/row4-w3r65/gen.py, with NAME as the first argument:

  gen.py NAME calib OUTDIR PROC:CODE[,CODE...] ...
  gen.py NAME stage OUTDIR tt=CODE,ff=CODE,ss=CODE
  gen.py NAME iq OUTDIR [CODE ...]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim"))
from _module_loader import load_module  # noqa: E402

w3 = load_module("w3gen", REPO / "sim" / "row4-w3r65" / "gen.py", reuse=False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    w3.main([sys.argv[0]] + sys.argv[2:], name=sys.argv[1])
