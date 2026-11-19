#!/usr/bin/env python3
"""Row 4 `ss` span / 0xFF running-Iq variant search (issue #337, operator ruling 2026-11-18). Sim-only; launches nothing.

Same bench and DUT as sim/row4-w3r65/gen.py (extraction of the rebuilt layout, netlist text edit; layout NOT re-extracted), but the
variant name is `w<K>r<P>` with K a decimal width multiplier of the 16 bank pass devices and P the percent length of base resistor X$91
(row4-nonron/variant.py only takes integer K). Usage as sim/row4-w3r65/gen.py, with NAME as the first argument:

  gen.py NAME calib OUTDIR PROC:CODE[,CODE...] ...
  gen.py NAME stage OUTDIR tt=CODE,ff=CODE,ss=CODE
  gen.py NAME iq OUTDIR [CODE ...]
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
spec = importlib.util.spec_from_file_location("w3gen", REPO / "sim" / "row4-w3r65" / "gen.py")
w3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w3)

_orig_build = w3.variant.build


def build(text, name):
    m = re.fullmatch(r"w(\d+(?:\.\d+)?)r(\d+)", name)
    if not m:
        return _orig_build(text, name)
    import importlib.util as iu
    s = iu.spec_from_file_location("v317", REPO / "sim" / "row45-rerun" / "variant.py")
    v = iu.module_from_spec(s)
    s.loader.exec_module(v)
    text = v.double_bank_switches(text, float(m.group(1)))
    assert text.count("r_length=12.03860U") == 1
    return text.replace("r_length=12.03860U", f"r_length={12.0386 * int(m.group(2)) / 100:.5f}U")


if __name__ == "__main__":
    name = sys.argv.pop(1)
    w3.variant.build = build
    w3.NAME = name
    sys.argv[0] = "gen.py"
    exec(compile((REPO / "sim" / "row4-w3r65" / "gen.py").read_text().split('if __name__ == "__main__":')[1].replace("\n    ", "\n").lstrip(), "gen_main", "exec"), w3.__dict__)
