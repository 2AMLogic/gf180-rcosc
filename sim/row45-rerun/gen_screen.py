#!/usr/bin/env python3
"""Row-5 screening requests (issue #321): comparator-H output-inverter variants on the ff median die (code 0x4E = 78).
Per variant two requests: <v>_v33 (27 C, 3.3 V reference) and <v>_v30 (-40 / 85 C, 3.0 V).  The metric is the frequency change
against the same die's 3.3 V / 27 C frequency (the DR-0033 basis).  Usage: gen_screen.py OUTDIR [SET=a]   (launches nothing)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "pvt"))
sys.path.insert(0, str(HERE))
from pvt_sweep import PROCESS_CORNERS  # noqa: E402
import variant  # noqa: E402

SRC = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"
PROC, CODE = "ff", 78
# name -> (wn, wp, ln, lp) of the comparator-H output inverter; "base" is the DR-0028 netlist (1, 4, 0.5, 0.5)
SETS = {"a": {"base": (1, 4, .5, .5), "p3": (1, 3, .5, .5), "p25": (1, 2.5, .5, .5), "p2": (1, 2, .5, .5),
              "n07": (0.7, 4, .5, .5), "pl07": (1, 4, .5, .7), "p3n07": (0.7, 3, .5, .5)},
        "b": {"base": (1, 4, .5, .5), "p6": (1, 6, .5, .5), "p8": (1, 8, .5, .5), "n15": (1.5, 4, .5, .5),
              "n2": (2, 4, .5, .5), "p8n15": (1.5, 8, .5, .5), "nl07": (1, 4, .7, .5), "nl1": (1, 4, 1, .5)}}
# first-stage sets (round 2): name -> (pair W um, mirror-load L um, tail W factor); None = as extracted (4, 1, 1)
FIRST = {"c": {"base": (None, None, None), "pw3": (3, None, None), "pw6": (6, None, None), "pw8": (8, None, None),
               "ll07": (None, 0.7, None), "ll15": (None, 1.5, None), "tk15": (None, None, 1.5), "tk07": (None, None, 0.7)},
         "d": {"base": (None, None, None), "ll05": (None, 0.5, None), "ll06": (None, 0.6, None), "ll08": (None, 0.8, None),
               "ll09": (None, 0.9, None), "ll11": (None, 1.1, None), "tk085": (None, None, 0.85), "tk055": (None, None, 0.55)}}


def bench(name: str, vdd: float) -> str:
    L = [f"* #321 row-5 screen {name} ff code 0x{CODE:02X} VDD={vdd:g}",
         ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
         f'.include "dut_{name}.spice"', "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top", f"VDD vdd 0 DC {vdd:g}"]
    L += [f"VT{i} t{i} 0 DC {vdd * ((CODE >> i) & 1):g}" for i in range(8)]
    return "\n".join(L) + "\n"


def request(name: str, vdd: float, temps) -> dict:
    m = vdd / 2
    ms = [{"name": "f_ta", "spice": f".meas tran f_ta WHEN v(clk)={m:.4f} RISE=5", "unit": "s"},
          {"name": "f_tb", "spice": f".meas tran f_tb WHEN v(clk)={m:.4f} RISE=25", "unit": "s"},
          {"name": "fosc", "spice": ".meas tran fosc PARAM='20/(f_tb-f_ta)'", "unit": "Hz"}]
    return {"netlist": f"tb_{name}_v{int(round(vdd * 10)):02d}.spice", "engine": "ngspice", "netlist_source": "extracted",
            "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
            "corners": {"process": [{"name": PROC, "sections": [*PROCESS_CORNERS[PROC], "cap_mim"]}], "temperature_c": temps},
            "analysis": {"kind": "tran", "args": "200p 1200n"}, "measurements": ms,
            "batch": {"capacity_wait_s": 600},
            "options": {"timeout_s": 1800, "keep_artifacts": True, "ngspice_init": ["set measureprec=8"]}}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    which = sys.argv[2] if len(sys.argv) > 2 else "a"
    duts = ({n: variant.first_stage(SRC.read_text(), *a) for n, a in FIRST[which].items()} if which in FIRST else
            {n: variant.comparator_h_buffer(SRC.read_text(), *a) for n, a in SETS[which].items()})
    for name, text in duts.items():
        (out / f"dut_{name}.spice").write_text(text)
        for vdd, temps in ((3.3, [27.0]), (3.0, [-40.0, 85.0])):
            t = f"{name}_v{int(round(vdd * 10)):02d}"
            (out / f"tb_{t}.spice").write_text(bench(name, vdd))
            (out / f"request_{t}.json").write_text(json.dumps(request(name, vdd, temps), indent=2) + "\n")
