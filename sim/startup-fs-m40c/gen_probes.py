#!/usr/bin/env python3
"""Single-corner local probes for the fs / -40 C no-oscillation finding (issue #227).

Each probe is ONE corner (one process x one temperature), so `klt sim` keeps it
local (`--backend local`); no grid is launched.  The DUT is the settled P3
netlist, copied byte-for-byte from sim/recentre/p3/rcosc_top_p3.spice.
Usage:  python3 gen_probes.py [--out DIR]     # default: sim/startup-fs-m40c/probes
Output is deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "pvt"))
from pvt_sweep import PROCESS_CORNERS  # noqa: E402

SRC = REPO / "sim" / "recentre" / "p3" / "rcosc_top_p3.spice"
DUT = "rcosc_top_p3.spice"
SCHEM_SRC = REPO / "sim" / "startup" / "rcosc_top_schematic.spice"
SCHEM = "rcosc_top_schematic.spice"
# internal nodes of the schematic DUT, averaged over the last 500 ns as a state readout
SCHEM_NODES = ["vc", "vh", "vl", "ibias", "pb", "cmph_out", "cmpl_out", "qbar"]
CODE = 0xA9

# name -> dict(process, temp, vdd, tstop, ramp_ns (None = DC step supply), extra netlist lines)
PROBES = {
    "base_fs_m40_v33": dict(process="fs", temp=-40.0, vdd=3.3, tstop="1200n", ramp=None),
    "ctl_fs_m40_v30": dict(process="fs", temp=-40.0, vdd=3.0, tstop="1200n", ramp=None),
    "ctl_tt_m40_v36": dict(process="tt", temp=-40.0, vdd=3.6, tstop="1200n", ramp=None),
    "ctl_fs_27_v33": dict(process="fs", temp=27.0, vdd=3.3, tstop="1200n", ramp=None),
    "long_fs_m40_v33": dict(process="fs", temp=-40.0, vdd=3.3, tstop="6u", ramp=None),
    # supply (and the set trim bits) ramped 0 -> VDD in 1 us, as in sim/startup; hub nodes saved
    "ramp_fs_m40_v33": dict(process="fs", temp=-40.0, vdd=3.3, tstop="3u", ramp=1000, wave=True),
    "ramp_ctl_fs_m40_v30": dict(process="fs", temp=-40.0, vdd=3.0, tstop="3u", ramp=1000, wave=True),
    # same fs / -40 C / 3.3 V on the pre-re-centre schematic DUT, which has named internal nodes
    "schem_fs_m40_v33": dict(process="fs", temp=-40.0, vdd=3.3, tstop="1200n", ramp=None,
                             dut="schem"),
}


def meas(vdd, dut="p3", iq=("200n", "1200n")):
    vmid = vdd / 2
    extra = []
    if dut == "schem":
        extra = [{"name": "n_" + n.replace(".", "_"),
                  "spice": f".meas tran n_{n.replace('.', '_')} AVG v(xxdut.{n}) FROM=700n TO=1200n",
                  "unit": "V"} for n in SCHEM_NODES]
    iqm = [] if iq is None else [
        {"name": "iq_run_ua", "spice": f".meas tran iq_run_ua AVG v(iq_ua) FROM={iq[0]} TO={iq[1]}", "unit": "uA"}]
    return extra + [
        {"name": "ta", "spice": f".meas tran ta WHEN v(clk)={vmid:.4f} RISE=5", "unit": "s"},
        {"name": "tb", "spice": f".meas tran tb WHEN v(clk)={vmid:.4f} RISE=25", "unit": "s"},
        {"name": "fosc", "spice": ".meas tran fosc PARAM='20/(tb-ta)'", "unit": "Hz"},
        {"name": "clk_max", "spice": ".meas tran clk_max MAX v(clk) FROM=200n", "unit": "V"},
        {"name": "clk_min", "spice": ".meas tran clk_min MIN v(clk) FROM=200n", "unit": "V"},
    ] + iqm


def testbench(name, p):
    vdd = p["vdd"]
    lines = [
        f"* probe {name}: {p['process']} / {p['temp']:g} C / {vdd:g} V, code 0x{CODE:02X} (gen_probes.py, issue #227)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f'.include "{ SCHEM if p.get("dut") == "schem" else DUT }"',
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 {'DC %g' % vdd if p['ramp'] is None else 'PWL(0 0 %gn %g)' % (p['ramp'], vdd)}",
        "BIQ iq_ua 0 V=-1e6*i(VDD)",
    ]
    for i in range(8):
        bit = (CODE >> i) & 1
        if p["ramp"] is None or not bit:
            lines.append(f"VT{i} t{i} 0 DC {vdd * bit:g}")
        else:
            lines.append(f"VT{i} t{i} 0 PWL(0 0 {p['ramp']:g}n {vdd:g})")
    if p.get("wave"):
        # P3 hub nodes (identified from device connectivity, see README): vc, vh, comparator-H
        # tail/dp/dn/out, latch qbar, cmpl_out, bias ibias
        hubs = {"vc": "$26", "vh": "$7", "tail": "$29", "dp": "$30", "dn": "$31",
                "cmph": "$32", "qbar": "$36", "cmpl": "$35", "ibias": "$37"}
        lines.append(".save v(clk) v(vdd) " + " ".join(f"v(xxdut.\\{h})" for h in hubs.values()))
    lines += p.get("extra", [])
    return "\n".join(lines) + "\n"


def request(name, p):
    return {
        "netlist": f"tb_{name}.spice",
        "engine": "ngspice",
        "netlist_source": "schematic" if p.get("dut") == "schem" else "extracted",
        "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
        "corners": {
            "process": [{"name": p["process"], "sections": [*PROCESS_CORNERS[p["process"]], "cap_mim"]}],
            "temperature_c": [p["temp"]],
        },
        "analysis": {"kind": "tran", "args": f"200p {p['tstop']}"},
        "measurements": meas(p["vdd"], p.get("dut", "p3"), None if p.get("wave") else ("200n", "1200n")),
        "options": {"timeout_s": 1800, "keep_artifacts": True,
                    **({"waveforms": True, "save_mode": "netlist"} if p.get("wave") else {}),
                    "ngspice_init": ["set measureprec=8"]},
    }


def generate(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    (out / DUT).write_text(SRC.read_text())
    (out / SCHEM).write_text(SCHEM_SRC.read_text())
    for name, p in PROBES.items():
        (out / f"tb_{name}.spice").write_text(testbench(name, p))
        (out / f"request_{name}.json").write_text(json.dumps(request(name, p), indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "probes")
    generate(ap.parse_args().out)
