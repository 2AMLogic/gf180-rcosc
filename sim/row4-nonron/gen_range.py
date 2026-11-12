#!/usr/bin/env python3
"""Trim-range endpoint requests (tt/ff/ss, 27 C, 3.3 V only) for a variant at one code (issue #320).
Usage: gen_range.py OUTDIR VARIANT CODE   -> benches + request_<proc>_v33.json; fosc is the existing 20-period measurement."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "row45-attribution"))
sys.path.insert(0, str(HERE))
import gen_stage_requests as g  # noqa: E402
import variant  # noqa: E402

if __name__ == "__main__":
    out, name, code = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    src = out / "rcosc_top_variant_src.spice"
    src.write_text(variant.build(g.SRC.read_text(), name))
    g.SRC = src
    g.CODES.clear()
    g.CODES.update({"tt": code, "ff": code, "ss": code})
    g.TEMPS_C = [27]
    g.VDDS_V = [3.3]
    for n in g.generate(out):
        print(n)
