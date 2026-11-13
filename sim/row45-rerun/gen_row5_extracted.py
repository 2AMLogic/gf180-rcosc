#!/usr/bin/env python3
"""Row-5 re-confirmation on the extraction of the REBUILT layout (issue #321, DR-0042 follow-up): comparator-H mirror-load L 0.7 um in
layout/cells/rcosc_top.gds, extracted with gen_dut.py's recipe (P3 transformation) into results/20261112T200335Z-extract-l07/.
The new extraction renumbers its nets, so the old probe nets (gen_stage_requests.PROBES) do not apply: this generator keeps only the
frequency measurements (f_ta / f_tb / fosc), which is all AC 2/3 need (error vs the same die's 3.3 V / 27 C frequency).
Reuses gen_calib_requests.py / sim/row45-attribution/gen_stage_requests.py otherwise unchanged.  Launches nothing.

  gen_row5_extracted.py calib OUTDIR PROC:CODE[,CODE...] [PROC:CODE,...]   per-die calibration scan (27 C / 3.3 V)
  gen_row5_extracted.py stage OUTDIR tt=CODE,ff=CODE,ss=CODE               the 9-request stage re-run at those codes (frequency only)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "row45-attribution"))
sys.path.insert(0, str(HERE))
import gen_calib_requests as gc  # noqa: E402
import gen_stage_requests as gs  # noqa: E402

import os  # noqa: E402
CONTROL_L1 = os.environ.get("CONTROL_L1") == "1"  # control: extraction of the OLD layout (L=1u loads), sim/cmph-fix/
SRC = (HERE.parent / "cmph-fix" / "rcosc_top_p3_cmphfix.spice") if CONTROL_L1 else (HERE / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice")

if __name__ == "__main__":
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if mode == "calib":
        gc.dut_text = lambda: SRC.read_text()
        (out / gc.DUT).write_text(SRC.read_text())
        for spec in sys.argv[3:]:
            proc, codes = spec.split(":")
            for c in codes.split(","):
                c = int(c, 0)
                (out / f"tb_{proc}_c{c:02X}.spice").write_text(gc.bench(c))
                (out / f"request_{proc}_c{c:02X}.json").write_text(json.dumps(gc.request(proc, c), indent=2) + "\n")
    elif mode == "stage":
        gs.PROBES[:] = []
        gs.SRC = SRC
        gs.probed_dut = lambda text: text  # no probe taps: net numbering differs from the DR-0028 extraction
        orig = gs.request
        gs.request = lambda proc, vdd: {**orig(proc, vdd), "measurements": [m for m in orig(proc, vdd)["measurements"] if m["name"].startswith("f")]}
        gs.CODES.clear()
        gs.CODES.update({k: int(v) for k, v in (p.split("=") for p in sys.argv[3].split(","))})
        for n in gs.generate(out):
            print(n)
    else:
        sys.exit(__doc__)
