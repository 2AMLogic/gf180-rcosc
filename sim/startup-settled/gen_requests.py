#!/usr/bin/env python3
"""Startup-time requests on the SETTLED netlist (issue #227, item-5 row 9).

Same stimulus as sim/startup/gen_requests.py (VDD and the set trim bits ramp 0 -> VDD in
1 us, 20 us transient, 200 ps step, clk waveform retained) but the DUT is the settled P3
netlist (DR-0023: extracted, ladder x0.70, PDK MiM; byte-copy of
sim/recentre/p3/rcosc_top_p3.spice) at its calibration code 0xA9, instead of the
pre-re-centre schematic at 0xA3.  Corner grid: 7 process x 3 T per request, one request
per supply (a PWL supply cannot take a supply_v alter) = 63 points -> batch fleet.
sim/startup/ (issue #82) is not modified.

Usage: python3 gen_requests.py [--out DIR]   # default: this directory; deterministic
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "pvt"))
from pvt_sweep import PROCESS_CORNERS, TEMPS_C, VDDS_V  # noqa: E402

CODE = 0xA9
RAMP_NS = 1000
TSTOP_NS = 20000
SRC = REPO / "sim" / "recentre" / "p3" / "rcosc_top_p3.spice"
DUT = "rcosc_top_p3.spice"


def tag(vdd):
    return f"v{int(round(vdd * 10)):02d}"


def testbench(vdd):
    r = RAMP_NS
    lines = [
        f"* rcosc_top settled-netlist startup bench, VDD ramp 0->{vdd:g} V in {r} ns, trim 0x{CODE:02X} (gen_requests.py)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f'.include "{DUT}"',
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 PWL(0 0 {r}n {vdd:g})",
    ]
    for i in range(8):
        lines.append(f"VT{i} t{i} 0 PWL(0 0 {r}n {vdd:g})" if (CODE >> i) & 1 else f"VT{i} t{i} 0 DC 0")
    lines.append(".save v(clk) v(vdd)")
    return "\n".join(lines) + "\n"


def request(vdd):
    vmid = vdd / 2
    return {
        "netlist": f"tb_{tag(vdd)}.spice",
        "engine": "ngspice",
        "netlist_source": "extracted",
        "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
        "corners": {"process": [{"name": n, "sections": [*PROCESS_CORNERS[n], "cap_mim"]}
                                for n in PROCESS_CORNERS],
                    "temperature_c": TEMPS_C},
        "analysis": {"kind": "tran", "args": f"200p {TSTOP_NS}n"},
        "measurements": [
            {"name": "t_first_edge", "unit": "s",
             "spice": f".meas tran t_first_edge WHEN v(clk)={vmid:.4f} RISE=1"},
            {"name": "t_edge_50", "unit": "s",
             "spice": f".meas tran t_edge_50 WHEN v(clk)={vmid:.4f} RISE=50"},
        ],
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": 1800, "keep_artifacts": True, "waveforms": True,
                    "save_mode": "netlist", "ngspice_init": ["set measureprec=8"]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE)
    out = ap.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    (out / DUT).write_text(SRC.read_text())
    for v in VDDS_V:
        (out / f"tb_{tag(v)}.spice").write_text(testbench(v))
        (out / f"request_{tag(v)}.json").write_text(json.dumps(request(v), indent=2) + "\n")


if __name__ == "__main__":
    main()
