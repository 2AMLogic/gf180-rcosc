#!/usr/bin/env python3
"""Single-corner (tt / 27 C / 3.3 V) calibration-code probes on the revised netlist (issue #229).

The comparator-H fix moves the nominal frequency, so the DR-0023 calibration code 0xA9 no longer
lands on 48 MHz.  One operating point per code => `klt sim --backend local` is the right backend.
Usage: python3 -I gen_calib.py [--out DIR]    # default: sim/cmph-fix/calib
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "startup-fs-m40c"))
import gen_probes as g  # noqa: E402

CODES = [0xA3, 0xA4, 0xA5, 0xA6, 0xA7]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=HERE / "calib")
    out = ap.parse_args().out; out.mkdir(parents=True, exist_ok=True)
    (out / "rcosc_top_p3_cmphfix.spice").write_text((HERE / "rcosc_top_p3_cmphfix.spice").read_text())
    for code in CODES:
        g.CODE = code
        p = dict(process="tt", temp=27.0, vdd=3.3, tstop="1200n", ramp=None)
        name = f"tt_27_v33_c{code:02x}"
        tb = g.testbench(name, p).replace(f'.include "{g.DUT}"', '.include "rcosc_top_p3_cmphfix.spice"')
        (out / f"tb_{name}.spice").write_text(tb)
        (out / f"request_{name}.json").write_text(json.dumps(g.request(name, p), indent=2) + "\n")


if __name__ == "__main__":
    main()
