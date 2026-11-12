#!/usr/bin/env python3
"""Row-5 candidate re-run (issue #321, third increment): comparator-H mirror-load L (MLOADA/MLOADB = X$65/X$66) on the DR-0028
netlist (bank switches NOT doubled: this is the row-5 variant, independent of the row-4 candidate).  Reuses gen_calib_requests.py and
sim/row45-attribution/gen_stage_requests.py unchanged except for the DUT text; launches nothing.

  gen_row5_candidate.py calib OUTDIR LOAD_L PROC:CODE[,CODE...] [PROC:CODE,...]   per-die calibration scan (27 C / 3.3 V)
  gen_row5_candidate.py stage OUTDIR LOAD_L tt=CODE,ff=CODE,ss=CODE               the 9-request stage re-run at those codes
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "row45-attribution"))
sys.path.insert(0, str(HERE))
import gen_calib_requests as gc  # noqa: E402
import gen_stage_requests as gs  # noqa: E402
import variant  # noqa: E402


def dut(load_l: float) -> str:
    return variant.first_stage(gc.SRC.read_text(), load_l=load_l)


if __name__ == "__main__":
    mode, out, load_l = sys.argv[1], Path(sys.argv[2]), float(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    if mode == "calib":
        gc.dut_text = lambda: dut(load_l)
        (out / gc.DUT).write_text(dut(load_l))
        for spec in sys.argv[4:]:
            proc, codes = spec.split(":")
            for c in codes.split(","):
                c = int(c, 0)
                (out / f"tb_{proc}_c{c:02X}.spice").write_text(gc.bench(c))
                (out / f"request_{proc}_c{c:02X}.json").write_text(__import__("json").dumps(gc.request(proc, c), indent=2) + "\n")
    elif mode == "stage":
        src = out / "rcosc_top_variant_src.spice"
        src.write_text(dut(load_l))
        gs.SRC = src
        gs.CODES.clear()
        gs.CODES.update({k: int(v) for k, v in (p.split("=") for p in sys.argv[4].split(","))})
        for n in gs.generate(out):
            print(n)
    else:
        sys.exit(__doc__)
