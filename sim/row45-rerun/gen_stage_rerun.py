#!/usr/bin/env python3
"""Stage-attribution re-run on the #317 variant DUT: reuses sim/row45-attribution/gen_stage_requests.py unchanged, with the
source netlist replaced by variant.build(...) and the per-die codes re-derived (calib scans in results/*-calib).
Usage: gen_stage_rerun.py OUTDIR   (then run the same klt sim --batch-set as the attribution README)"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "row45-attribution"))
sys.path.insert(0, str(HERE))
import gen_stage_requests as g  # noqa: E402
import variant  # noqa: E402

CODES = {"tt": 171, "ff": 80, "ss": 218}

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    src = out / "rcosc_top_variant_src.spice"
    src.write_text(variant.build(g.SRC.read_text()))
    g.SRC = src
    g.CODES.clear()
    g.CODES.update(CODES)
    for n in g.generate(out):
        print(n)
