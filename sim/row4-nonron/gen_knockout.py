#!/usr/bin/env python3
"""Knock-out requests (ss only, 27 C, 3.0/3.3/3.6 V, code 212) reusing sim/row45-attribution/gen_stage_requests.py unchanged.
Usage: gen_knockout.py OUTDIR VARIANT   (see variant.py)"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "row45-attribution"))
sys.path.insert(0, str(HERE))
import gen_stage_requests as g  # noqa: E402
import variant  # noqa: E402

if __name__ == "__main__":
    out, name = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    src = out / "rcosc_top_variant_src.spice"
    src.write_text(variant.build(g.SRC.read_text(), name))
    g.SRC = src
    g.CODES.clear()
    code = int(name[5:]) if name.startswith("ideal") else int(name[4:]) if name.startswith("ctrl") and name[4:] else 212
    g.CODES.update({"ss": code})
    g.TEMPS_C = [27]
    for n in g.generate(out):
        print(n)
