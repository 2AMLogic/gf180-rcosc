#!/usr/bin/env python3
"""Row-8 (ratified Iq, DR-0003 Row 4 "< 500 uA running") on the REAL regenerated schematic netlist (issue #321): the running supply current
-i(VDD) averaged over 20 whole periods (clk rising edges 5..25, the sim/iq/iq_sweep.py `iq_run` window), as a `klt sim` request set instead of
the local sim/iq driver.  Grid per request: tt/ff/ss x -40/27/85 C at one supply; one request per (code, supply).  CONTROL_L1=1 = same-netlist
control with MLOADA/MLOADB at L=1u.  Reuses gen_row5_schematic.py's DUT text.  Launches nothing.
Usage: gen_row5_iq_schematic.py OUTDIR [CODE ...]   (default codes 0x00 0x80 0xC0 0xFF)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_calib_requests as gc  # noqa: E402
import gen_row5_schematic as g5  # noqa: E402

INTEG_LINES = "* supply-current integrator (analysis only): v(qint) = integral of -i(VDD) dt / 1 nF\nBint 0 qint I=-i(VDD)\nCint qint 0 1n\nRint qint 0 1e15\n.ic v(qint)=0\n"
VDDS = (3.0, 3.3, 3.6)
PROCS = ("tt", "ff", "ss")
TEMPS = [-40.0, 27.0, 85.0]


def request(proc_list, code, vdd):
    r = gc.request("tt", code, vdd)
    r["netlist"] = f"tb_c{code:02X}_v{int(round(vdd * 10)):02d}.spice"
    r["netlist_source"] = "schematic"
    r["corners"] = {"process": [{"name": p, "sections": [*gc.PROCESS_CORNERS[p], "cap_mim"]} for p in proc_list], "temperature_c": TEMPS}
    # f_ta / f_tb give the 20-period window (clk rising edges 5..25).  klt sim emits every .meas at deck level, so neither FROM='f_ta' nor an
    # AVG with TRIG/TARG works; instead the bench integrates the supply current on a 1 nF capacitor (INTEG_LINES) and iq_run is the charge
    # gained between the same two edges over their time difference (positive = current drawn from VDD).
    m = vdd / 2
    r["measurements"] = r["measurements"][:2] + [
        {"name": "q_a", "spice": f".meas tran q_a FIND v(qint) WHEN v(clk)={m:.4f} RISE=5", "unit": "V"},
        {"name": "q_b", "spice": f".meas tran q_b FIND v(qint) WHEN v(clk)={m:.4f} RISE=25", "unit": "V"},
        {"name": "iq_run", "spice": ".meas tran iq_run PARAM='(q_b-q_a)*1n/(f_tb-f_ta)'", "unit": "A"}]
    r["analysis"] = {"kind": "tran", "args": "200p 4000n"}
    return r


if __name__ == "__main__":
    out = Path(sys.argv[1])
    codes = [int(c, 0) for c in sys.argv[2:]] or [0x00, 0x80, 0xC0, 0xFF]
    out.mkdir(parents=True, exist_ok=True)
    (out / gc.DUT).write_text(g5.dut_text(False))
    for code in codes:
        for vdd in VDDS:
            r = request(PROCS, code, vdd)
            (out / r["netlist"]).write_text(gc.bench(code, vdd) + INTEG_LINES)
            (out / f"request_c{code:02X}_v{int(round(vdd * 10)):02d}.json").write_text(json.dumps(r, indent=2) + "\n")
