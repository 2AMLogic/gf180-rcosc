#!/usr/bin/env python3
"""DR-0037 `w3r65` bank candidate on the EXTRACTION of the rebuilt layout (issue #337; the DR-0043 basis).

The candidate (16 bank pass devices at 3x W, base resistor X$91 at 65 % length) is applied as netlist text to
sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice via sim/row4-nonron/variant.py (layout NOT re-extracted).
Frequency-only benches, same as sim/row45-rerun/gen_row5_extracted.py. Launches nothing.

  gen.py calib OUTDIR PROC:CODE[,CODE...] [PROC:CODE,...]   per-die calibration scan (27 C / 3.3 V)
  gen.py stage OUTDIR tt=CODE,ff=CODE,ss=CODE               9 requests (3 dies x 3 supplies, each over -40 / 27 / 85 C)
  gen.py iq OUTDIR [CODE ...]                               running Iq (row 8), default codes 0x00 0x80 0xC0 0xFF; same integrator bench as gen_row5_iq_extracted.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "row45-attribution"))
sys.path.insert(0, str(REPO / "sim" / "row45-rerun"))
import gen_calib_requests as gc  # noqa: E402
import gen_stage_requests as gs  # noqa: E402
import importlib.util  # noqa: E402

# gen_calib_requests already imported sim/row45-rerun/variant.py as "variant"; load the row4-nonron one under its own name
_spec = importlib.util.spec_from_file_location("variant_row4", REPO / "sim" / "row4-nonron" / "variant.py")
variant = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(variant)

BASE = REPO / "sim" / "row45-rerun" / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice"
NAME = "w3r65"

if __name__ == "__main__":
    if len(sys.argv) < 3 or (len(sys.argv) < 4 and sys.argv[1] != "iq"):
        sys.exit(__doc__)
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    text = variant.build(BASE.read_text(), NAME)
    (out / "rcosc_top_variant_src.spice").write_text(text)
    src = out / "rcosc_top_variant_src.spice"
    if mode == "calib":
        gc.dut_text = lambda: text
        (out / gc.DUT).write_text(text)
        for spec in sys.argv[3:]:
            proc, codes = spec.split(":")
            for c in codes.split(","):
                c = int(c, 0)
                (out / f"tb_{proc}_c{c:02X}.spice").write_text(gc.bench(c))
                (out / f"request_{proc}_c{c:02X}.json").write_text(json.dumps(gc.request(proc, c), indent=2) + "\n")
    elif mode == "stage":
        gs.PROBES[:] = []
        gs.SRC = src
        gs.probed_dut = lambda t: t
        orig = gs.request
        gs.request = lambda proc, vdd: {**orig(proc, vdd), "measurements": [m for m in orig(proc, vdd)["measurements"] if m["name"].startswith("f")]}
        gs.CODES.clear()
        gs.CODES.update({k: int(v) for k, v in (p.split("=") for p in sys.argv[3].split(","))})
        for n in gs.generate(out):
            print(n)
    elif mode == "iq":
        import gen_row5_iq_schematic as gi
        codes = [int(c, 0) for c in sys.argv[3:]] or [0x00, 0x80, 0xC0, 0xFF]
        (out / gc.DUT).write_text(text)
        for code in codes:
            for vdd in gi.VDDS:
                r = gi.request(gi.PROCS, code, vdd)
                r["netlist_source"] = "extracted"
                (out / r["netlist"]).write_text(gc.bench(code, vdd) + gi.INTEG_LINES)
                (out / f"request_c{code:02X}_v{int(round(vdd * 10)):02d}.json").write_text(json.dumps(r, indent=2) + "\n")
    else:
        sys.exit(__doc__)
