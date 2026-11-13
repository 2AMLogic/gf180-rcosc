#!/usr/bin/env python3
"""Row-8 (ratified Iq, DR-0003 Row 4 "< 500 uA running") on the EXTRACTION of the rebuilt layout (issue #321, DR-0043 follow-up): same
integrator-based iq_run as gen_row5_iq_schematic.py, but the DUT is results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice.
Launches nothing.  Usage: gen_row5_iq_extracted.py OUTDIR [CODE ...]   (default codes 0x00 0x80 0xC0 0xFF)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_calib_requests as gc  # noqa: E402
import gen_row5_iq_schematic as gi  # noqa: E402

import os  # noqa: E402
CONTROL_L1 = os.environ.get("CONTROL_L1") == "1"  # same-recipe extraction of the OLD layout (L=1u loads), sim/cmph-fix/
SRC = (HERE.parent / "cmph-fix" / "rcosc_top_p3_cmphfix.spice") if CONTROL_L1 else (HERE / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice")

if __name__ == "__main__":
    out = Path(sys.argv[1])
    codes = [int(c, 0) for c in sys.argv[2:]] or [0x00, 0x80, 0xC0, 0xFF]
    out.mkdir(parents=True, exist_ok=True)
    (out / gc.DUT).write_text(SRC.read_text())
    for code in codes:
        for vdd in gi.VDDS:
            r = gi.request(gi.PROCS, code, vdd)
            r["netlist_source"] = "extracted"
            (out / r["netlist"]).write_text(gc.bench(code, vdd) + gi.INTEG_LINES)
            (out / f"request_c{code:02X}_v{int(round(vdd * 10)):02d}.json").write_text(json.dumps(r, indent=2) + "\n")
