#!/usr/bin/env python3
"""Row-8 side check for the row-5 candidate (issue #321): average supply current (200 ns window after start-up) of the DR-0028
netlist as extracted (base) and with comparator-H mirror-load L 0.7 um (ll07), ff 3.6 V at -40/27/85 C, code 0x4F.
This is the oscillating mean current, not the ratified Iq definition (sim/iq); it is a base-vs-variant delta check only.
Usage: gen_row5_iq.py OUTDIR"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_calib_requests as gc  # noqa: E402
import gen_row5_candidate as g5  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for name, text in (("base", gc.SRC.read_text()), ("ll07", g5.dut(0.7))):
    (out / f"dut_{name}.spice").write_text(text)
    b = gc.bench(0x4F, 3.6).replace(gc.DUT, f"dut_{name}.spice")
    (out / f"tb_{name}.spice").write_text(b)
    r = gc.request("ff", 0x4F, 3.6)
    r["netlist"] = f"tb_{name}.spice"
    r["corners"]["temperature_c"] = [-40.0, 27.0, 85.0]
    r["measurements"] = [{"name": "iq", "spice": ".meas tran iq AVG i(VDD) FROM=900n TO=1200n", "unit": "A"}]
    (out / f"request_{name}.json").write_text(json.dumps(r, indent=2) + "\n")
