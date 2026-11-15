#!/usr/bin/env python3
"""Per-stage running-Iq attribution requests for row 8 (issue #347, extends DR-0044's Iq bench).

Generates (launches nothing):
  - a PROBED COPY of the flat extraction DUT named by the committed stage map (`stage_map.json`):
    every vdd-side terminal of every current-bearing stage's devices (the map's `vdd_terms`,
    i.e. the terminals on the VDD parasitic network's star) is re-terminated onto `vdd_<stage>`,
    and one 0 V source per distinct original net ties it back (`V<stage>_<k> vdd_<stage> <orig> 0`,
    inside the .SUBCKT).  A 0 V source is an ideal short and every parasitic star resistor stays
    in circuit, so the operating point and transient are unchanged -- exact, unlike a 1 mOhm probe.
    No device line is otherwise edited.
  - benches: the DR-0044 integrator bench (total `iq_run`, clk rising edges 5 -> 25) plus one
    integrator per stage (`Bint_<stage> 0 qint_<stage> I=-i(V<stage>_0)-...`), so per-stage charge
    and the total come from ONE transient.  The timing MiM and the discharge device have no vdd
    terminal: no source, no integrator -- their stage current is zero by construction.
  - `klt sim` corner requests per (code, supply) set, batch backend, `capacity_wait_s: 600`.
  - `dut.txt` with the sha256 of the source DUT, the probed copy and the stage map.

The FIRST thing to run (Test Plan item 1) is the back-to-back check: the probed total `iq_run`
at tt / 27 C / 3.3 V / 0xFF and ff / 85 C / 3.6 V / 0xFF must reproduce DR-0044's committed
figures; if it moves, the split is not trustworthy.  Usage:

    python3 -I gen_stage_iq_requests.py OUTDIR [--map stage_map.json] [--sets cFF_v33,...] [--control-l1]
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "pvt"))
sys.path.insert(0, str(REPO / "sim" / "row45-rerun"))
sys.path.insert(0, str(HERE))
import stage_map as smapp  # noqa: E402
from gen_calib_requests import PROCESS_CORNERS  # noqa: E402
from gen_row5_iq_schematic import TEMPS  # noqa: E402

CONTROL_L1 = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"   # L=1U control (DR-0044's)
CURRENT_STAGES = list(smapp.CURRENT_STAGES)
# wave 1 carries the two back-to-back cells (tt/27C/3.3V and ff/85C/3.6V, both code 0xFF)
WAVE1 = ("cFF_v33", "cFF_v36")
# (tag, code, processes): the code-0xFF cells over 500 uA in DR-0044's table, the 0xA4 item-5
# failing cells (ff x -40/27/85 at 3.3 and 3.6 V), the C0/80 ff-hot cells, the tt/27C/3.3V
# reference, ss at one supply for process scaling
SETS = [
    ("cFF_v30", 0xFF, ["ff"]), ("cFF_v33", 0xFF, ["ff", "tt"]), ("cFF_v36", 0xFF, ["ff", "tt", "ss"]),
    ("cC0_v33", 0xC0, ["ff"]), ("cC0_v36", 0xC0, ["ff"]), ("c80_v36", 0x80, ["ff"]),
    ("cA4_v33", 0xA4, ["ff"]), ("cA4_v36", 0xA4, ["ff"]),
]
VDD = {"v30": 3.0, "v33": 3.3, "v36": 3.6}


def load_map(map_path):
    m = json.loads(Path(map_path).read_text())
    smapp.check_conservation(m)
    return m


def probed_dut(text, stages_devices):
    """Re-terminate every vdd-side terminal of every current-bearing stage onto an internal
    `vdd_<stage>` node, tie that node back to its original nets with 0 V sources, and integrate
    each stage's feed on a 1 nF cap INSIDE the subckt (a source inside a subckt cannot be
    referenced from a bench-level B source -- ngspice 'unknown controlling source'; and an
    external ammeter would leave the internal vdd network as a parallel feed path).  Only the
    per-stage integrator nodes are exposed, as pins `pq_<stage>`, and measured as voltages.
    The 0 V sources are ideal shorts and every parasitic star resistor stays in circuit, so the
    operating point and transient are unchanged -- exact, unlike a 1 mOhm probe."""
    rewrite, sources, pins = {}, {}, []
    for stage in CURRENT_STAGES:
        devs = stages_devices.get(stage, [])
        nets = sorted({net for d in devs for _, net in d["vdd_terms"]})
        if not nets:
            continue
        pins.append(f"pq_{stage}")
        sources[stage] = [f"V{stage}_{k} vdd_{stage} {net} 0" for k, net in enumerate(nets)]
        for d in devs:
            for idx, _ in d["vdd_terms"]:
                rewrite.setdefault(d["name"], []).append((stage, idx))
    out, coord, inserted, nterm = [], None, False, 0
    for raw in text.splitlines():
        m = smapp.DEV_COMMENT.match(raw)
        if m:
            coord = m.group(1).startswith("$")
            out.append(raw)
            continue
        if raw.startswith(".SUBCKT") and pins:
            raw = raw + " " + " ".join(pins)
        if coord and raw.strip() and not raw.startswith("*") and re.match(r"^[XMR]\S+\s", raw):
            name = raw.split()[0]
            if name in rewrite:
                toks = raw.split()
                for stage, idx in rewrite[name]:
                    toks[1 + idx] = f"vdd_{stage}"
                    nterm += 1
                raw = " ".join(toks)
            coord = None
        if not inserted and raw.startswith(".ENDS") and sources:
            out += ["* per-stage supply probes (analysis only, issue #347): each stage's vdd-side device",
                    "* terminals are re-terminated onto an internal vdd_<stage> node; 0 V sources tie that",
                    "* node back to the original nets (ideal short; every parasitic star resistor stays in",
                    "* circuit).  Each stage's feed is integrated on 1 nF over the same edge-5-to-25 window",
                    "* as the total (DR-0044 bench); only v(pq_<stage>) is exposed, as pin pq_<stage>.",
                    f"* pins: {' '.join(pins)}"]
            for stage in CURRENT_STAGES:
                devs = stages_devices.get(stage, [])
                srcs = sources.get(stage, [])
                if not srcs:
                    continue
                out += srcs
                out += [f"Bint_{stage} 0 pq_{stage} I=" + "".join(f"-i(V{stage}_{k})" for k in range(len(srcs))),
                        f"Cint_{stage} pq_{stage} 0 1n", f"Rint_{stage} pq_{stage} 0 1e15",
                        f".ic v(pq_{stage})=0"]
            inserted = True
        out.append(raw)
    want = sum(len(d["vdd_terms"]) for ds in stages_devices.values() for d in ds)
    assert inserted and nterm == want, f"probed DUT: rewrote {nterm} terminals, map wants {want}"
    return "\n".join(out) + "\n"


def bench_lines(code, vdd, stages_devices, dut="rcosc_top_probed.spice"):
    """Bench: DR-0044's integrator bench unchanged (total `iq_run` on -i(VDD)), plus the probed
    DUT's per-stage integrator pins.  The stage integrators live inside the DUT (see
    probed_dut); the bench only measures v(pq_<stage>)."""
    pins = [f"pq_{s}" for s in CURRENT_STAGES
            if any(d["vdd_terms"] for d in stages_devices.get(s, []))]
    L = [f"* #347 per-stage Iq attribution, code 0x{code:02X}, VDD={vdd:g} V (generated by gen_stage_iq_requests.py)",
         ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
         f'.include "{dut}"',
         "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 " + " ".join(pins) + " rcosc_top",
         f"VDD vdd 0 DC {vdd:g}"]
    L += [f"VT{i} t{i} 0 DC {vdd * ((code >> i) & 1):g}" for i in range(8)]
    L += ["* supply-current integrator (analysis only): v(qint) = integral of -i(VDD) dt / 1 nF",
          "Bint 0 qint I=-i(VDD)", "Cint qint 0 1n", "Rint qint 0 1e15", ".ic v(qint)=0",
          "* per-stage integrators are inside the probed DUT; pins pq_<stage> expose v(qint_<stage>)"]
    return "\n".join(L) + "\n"


def make_request(tag, code, procs, stages_devices):
    vdd = VDD[tag.split("_")[1]]
    r = {"netlist": f"tb_{tag}.spice", "engine": "ngspice", "netlist_source": "extracted",
         "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
         "corners": {"process": [{"name": p, "sections": [*PROCESS_CORNERS[p], "cap_mim"]} for p in procs],
                     "temperature_c": TEMPS},
         "batch": {"capacity_wait_s": 600},
         "options": {"timeout_s": 1800, "keep_artifacts": True, "ngspice_init": ["set measureprec=8"]}}
    m = vdd / 2

    def meas(name, expr, unit):
        return {"name": name, "spice": f".meas tran {expr}", "unit": unit}

    ms = [meas("f_ta", f"f_ta WHEN v(clk)={m:.4f} RISE=5", "s"),
          meas("f_tb", f"f_tb WHEN v(clk)={m:.4f} RISE=25", "s"),
          meas("fosc", "fosc PARAM='20/(f_tb-f_ta)'", "Hz"),
          meas("q_a", f"q_a FIND v(qint) WHEN v(clk)={m:.4f} RISE=5", "V"),
          meas("q_b", f"q_b FIND v(qint) WHEN v(clk)={m:.4f} RISE=25", "V"),
          meas("iq_run", "iq_run PARAM='(q_b-q_a)*1n/(f_tb-f_ta)'", "A")]
    for stage in CURRENT_STAGES:
        devs = stages_devices.get(stage, [])
        if not any(d["vdd_terms"] for d in devs):
            continue
        ms += [meas(f"q_{stage}_a", f"q_{stage}_a FIND v(pq_{stage}) WHEN v(clk)={m:.4f} RISE=5", "V"),
               meas(f"q_{stage}_b", f"q_{stage}_b FIND v(pq_{stage}) WHEN v(clk)={m:.4f} RISE=25", "V"),
               meas(f"iq_{stage}", f"iq_{stage} PARAM='(q_{stage}_b-q_{stage}_a)*1n/(f_tb-f_ta)'", "A")]
    r["measurements"] = ms
    r["analysis"] = {"kind": "tran", "args": "200p 4000n"}
    return r


def generate(out: Path, map_path: Path, sets=None):
    m = load_map(map_path)
    src = Path(m["flat_deck"])
    assert src.exists(), f"DUT from the stage map not found: {src}"
    stages_devices = {s: m["stages"][s] for s in CURRENT_STAGES}
    out.mkdir(parents=True, exist_ok=True)
    probed = probed_dut(src.read_text(), stages_devices)
    (out / "rcosc_top_probed.spice").write_text(probed)
    (out / "dut.txt").write_text(
        f"source_dut: {src}\nsource_dut_sha256: {hashlib.sha256(src.read_bytes()).hexdigest()}\n"
        f"probed_dut: rcosc_top_probed.spice\nprobed_dut_sha256: {hashlib.sha256(probed.encode()).hexdigest()}\n"
        f"stage_map: {map_path}\nstage_map_sha256: {hashlib.sha256(Path(map_path).read_bytes()).hexdigest()}\n"
        f"vdd_side_devices: {m['vdd_side_summary']['devices']} terminals: {m['vdd_side_summary']['terminals']}\n")
    names = []
    for tag, code, procs in (sets or SETS):
        (out / f"request_{tag}.json").write_text(json.dumps(make_request(tag, code, procs, stages_devices), indent=2) + "\n")
        (out / f"tb_{tag}.spice").write_text(bench_lines(code, VDD[tag.split("_")[1]], stages_devices))
        names.append(f"request_{tag}.json")
    return names


def generate_control(out: Path, map_path: Path):
    """Control: the L=1U extraction (sim/cmph-fix), own stage map -- the attribution must not be an
    artifact of the L 0.7 um change.  One cell (ff / 85 C / 3.6 V / 0xFF, DR-0044's max)."""
    m = load_map(map_path)
    assert Path(m["flat_deck"]).resolve() == CONTROL_L1.resolve(), "control map must name the L=1U DUT"
    return generate(out, map_path, sets=[("cFF_v36", 0xFF, ["ff"])])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("outdir")
    ap.add_argument("--map", default=str(HERE / "stage_map.json"))
    ap.add_argument("--sets", default="", help="comma list like cFF_v33,cFF_v36 (default: all)")
    ap.add_argument("--control-l1", action="store_true")
    a = ap.parse_args()
    sets = [s for s in a.sets.split(",") if s] or None
    named = [(t, c, p) for t, c, p in SETS if sets is None or t in sets]
    if a.control_l1:
        ns = generate_control(Path(a.outdir), Path(a.map))
    else:
        ns = generate(Path(a.outdir), Path(a.map), named)
    for n in ns:
        print(n)
