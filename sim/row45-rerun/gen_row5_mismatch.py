#!/usr/bin/env python3
"""Row-5 margin check for the L 0.7 um candidate (issue #321): deterministic mirror-load length mismatch.  MLOADA (X$65, diode) and
MLOADB (X$66) get independent lengths around 0.7 um (+/-0.1 um, and a common-mode +0.1 um with the opposite device at nominal);
ff median die at calibration code 0x4F, 3.3 V / 27 C reference + 3.0 V at -40 / 85 C, metric as gen_screen.py / screen_table.py.
Usage: gen_row5_mismatch.py OUTDIR   (launches nothing)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_screen as gs  # noqa: E402
import variant  # noqa: E402

VARIANTS = {"a07b07": (0.7, 0.7), "a08b07": (0.8, 0.7), "a06b07": (0.6, 0.7), "a07b08": (0.7, 0.8), "a07b06": (0.7, 0.6),
            "a08b08": (0.8, 0.8)}
gs.CODE = 0x4F
if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, (la, lb) in VARIANTS.items():
        t = variant.resize(gs.SRC.read_text(), (variant.LOAD[0],), l=la)
        t = variant.resize(t, (variant.LOAD[1],), l=lb)
        (out / f"dut_{name}.spice").write_text(t)
        for vdd, temps in ((3.3, [27.0]), (3.0, [-40.0, 85.0])):
            tag = f"{name}_v{int(round(vdd * 10)):02d}"
            (out / f"tb_{tag}.spice").write_text(gs.bench(name, vdd))
            (out / f"request_{tag}.json").write_text(json.dumps(gs.request(name, vdd, temps), indent=2) + "\n")
