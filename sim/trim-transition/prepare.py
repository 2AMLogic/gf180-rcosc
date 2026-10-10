#!/usr/bin/env python3
"""Offline bench / `klt sim` request generator for the live trim-code
transition bench (issue #103).

Launches NO simulator and NO cloud operation.  Writes, per (supply, skew mode),
one testbench netlist, one `klt sim` request (process tt/ss/ff at 27 C = three
corners), and one schedule file listing every code change with its exact
timing; plus provenance.json.  Nine requests = 3 supplies x 3 skew modes; with
the three process corners that is the nine tt/ss/ff x 3.0/3.3/3.6 V corners,
each under three skew modes.  Execution goes through `klt sim` (batch backend);
see sim/trim-transition/README.md.

Bank weighting (verified against the schematic's rcosc_trim_bank, DUT block
extracted by sim/waveform/prepare.py): stage i is a ppolyf resistor of length
0.7482 um x 2^i shunted by a pass switch gated by t<i> (t<i>=1 shorts it), so
the bank is plain binary, t0 = LSB, t7 = MSB, higher code = lower R = higher f.
A carry n -> n+1 therefore flips (k+1) bits where k = trailing ones of n.

Usage:  python3 -I sim/trim-transition/prepare.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_SIM = Path(__file__).resolve().parent.parent
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))
from _module_loader import load_module  # noqa: E402


def _load_waveform_prepare():
    return load_module('wf_prepare', REPO / "sim" / "waveform" / "prepare.py", reuse=False)


wf = _load_waveform_prepare()
PROCESS_CORNERS = wf.PROCESS_CORNERS
VDDS_V = wf.VDDS_V
PROCESSES = wf.PROCESSES
MODELS = wf.MODELS
TRIM_BITS = 8
TEMP_C = 27.0

# (name, lo code, hi code).  The non-carry pair flips bit 0 only and brackets
# the tt calibration code 0xA3 (sim/pvt/results/20260923T030125Z); the carries
# flip 7 (3F->40), 8 (7F->80) and 7 (BF->C0) bits, see bits_changed().
POSITIONS = [
    ("noncarry_A2_A3", 0xA2, 0xA3),
    ("carry_3F_40", 0x3F, 0x40),
    ("carry_7F_80", 0x7F, 0x80),
    ("carry_BF_C0", 0xBF, 0xC0),
]
SKEWS = {"none": 0.0, "lsb_first": 1.0, "msb_first": -1.0}   # sign = order, |.| per-bit ns
SKEW_STEP_NS = 1.0

DEFAULTS = {
    "ramp_ns": 1000.0,       # VDD and ramp-following trim pins 0 -> VDD
    "t_first_ns": 3000.0,    # start of block 0 (oscillator running >= 2 us)
    "edge_ns": 1.0,          # digital edge, 0 -> VDD linear
    "setup_settle_ns": 1500.0,
    "event_gap_ns": 700.0,   # between consecutive code changes inside a block
    "phase_step_ns": 5.25,   # extra offset per phase pair (T_nom/4 at ~48 MHz)
    "phases": 4,
    "tstep": "100p",     # 200p leaves ~0.2 % solver edge-time noise on the period; 40p hit "timestep too small" at an edge
    "tmax": "100p",
    "reltol": 1e-3, "abstol": 1e-12, "vntol": 1e-6,
}


class PrepareError(Exception):
    pass


def bits_changed(a: int, b: int) -> list[int]:
    return [i for i in range(TRIM_BITS) if ((a ^ b) >> i) & 1]


def tag_of(vdd: float, skew: str) -> str:
    return f"{wf.tag_of(vdd)}_{skew}"


def build_schedule(cfg: dict) -> dict:
    """Deterministic list of code changes.  Times in ns.  Every change has
    t_start_ns (first bit's edge begins) and per-bit start times."""
    changes = []
    t = cfg["t_first_ns"]
    prev_lo = None
    init_code = POSITIONS[0][1]
    for name, lo, hi in POSITIONS:
        if prev_lo is not None:
            changes.append({"kind": "setup", "block": name, "dir": None, "phase": None,
                            "from": prev_lo, "to": lo, "t_nom_ns": t})
        t_ev = t + cfg["setup_settle_ns"]
        n_ev = 2 * cfg["phases"]
        for j in range(n_ev):
            k = j // 2
            up = j % 2 == 0
            changes.append({"kind": "event", "block": name, "dir": "up" if up else "down",
                            "phase": k, "from": lo if up else hi, "to": hi if up else lo,
                            "t_nom_ns": t_ev + j * cfg["event_gap_ns"] + k * cfg["phase_step_ns"]})
        t = t_ev + n_ev * cfg["event_gap_ns"]
        prev_lo = lo
    tstop = t
    return {"init_code": init_code, "changes": changes, "tstop_ns": tstop}


def bit_delays(skew: str, a: int, b: int) -> dict[int, float]:
    """Per-bit start delay (ns) for the bits that differ.  lsb_first: bit i
    delayed i*step; msb_first: bit i delayed (7-i)*step; none: 0."""
    sgn = SKEWS[skew]
    out = {}
    for i in bits_changed(a, b):
        if sgn == 0:
            out[i] = 0.0
        elif sgn > 0:
            out[i] = i * SKEW_STEP_NS
        else:
            out[i] = (TRIM_BITS - 1 - i) * SKEW_STEP_NS
    return out


def resolve(sched: dict, skew: str, cfg: dict) -> list[dict]:
    """Add per-bit edge times and t_start/t_end (ns) to each change."""
    out = []
    for c in sched["changes"]:
        d = bit_delays(skew, c["from"], c["to"])
        starts = {i: c["t_nom_ns"] + dl for i, dl in d.items()}
        c2 = dict(c)
        c2["bits"] = {str(i): {"start_ns": s, "level_to": (c["to"] >> i) & 1} for i, s in starts.items()}
        c2["t_start_ns"] = min(starts.values())
        c2["t_end_ns"] = max(starts.values()) + cfg["edge_ns"]
        c2["bits_changed"] = len(d)
        out.append(c2)
    for a, b in zip(out, out[1:]):
        if not b["t_start_ns"] > a["t_end_ns"] + 100:
            raise PrepareError("consecutive code changes overlap")
    return out


def _pwl(points: list[tuple[float, float]], cont: int = 6) -> list[str]:
    toks = [f"{t:.4f}n {v:g}" for t, v in points]
    lines = []
    for k in range(0, len(toks), cont):
        chunk = " ".join(toks[k:k + cont])
        lines.append(("PWL(" if k == 0 else "+ ") + chunk + (")" if k + cont >= len(toks) else ""))
    return lines


def tb_text(vdd: float, skew: str, sched: dict, changes: list[dict], cfg: dict, label: str) -> str:
    r = cfg["ramp_ns"]
    lines = [
        f"* rcosc_top live trim-transition bench ({label}): VDD ramp 0->{vdd:g} V in {r:g} ns, then "
        f"{sum(1 for c in changes if c['kind'] == 'event')} timed +/-1 code events (generated by prepare.py)",
        f"* skew mode {skew}: per-bit step {SKEW_STEP_NS:g} ns, edge {cfg['edge_ns']:g} ns",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".options reltol={cfg['reltol']:g} abstol={cfg['abstol']:g} vntol={cfg['vntol']:g}",
        '.include "rcosc_top_schematic.spice"',
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 PWL(0 0 {r:g}n {vdd:g})",
    ]
    code = sched["init_code"]
    for i in range(TRIM_BITS):
        level = (code >> i) & 1
        pts = [(0.0, 0.0), (r, vdd * level)]
        for c in changes:
            b = c["bits"].get(str(i))
            if b is None:
                continue
            new = b["level_to"]
            pts += [(b["start_ns"], vdd * (1 - new)), (b["start_ns"] + cfg["edge_ns"], vdd * new)]
        if len(pts) == 2 and level == 0:
            lines.append(f"VT{i} t{i} 0 DC 0")
            continue
        pl = _pwl(pts)
        lines.append(f"VT{i} t{i} 0 " + pl[0])
        lines += pl[1:]
    lines.append(".save v(clk) v(vdd)")
    return "\n".join(lines) + "\n"


def request(name: str, vdd: float, tstop_ns: float, cfg: dict) -> dict:
    return {
        "netlist": name,
        "engine": "ngspice",
        "netlist_source": "schematic",
        "models": dict(MODELS),
        "corners": {
            "process": [{"name": n, "sections": [PROCESS_CORNERS[n][0], PROCESS_CORNERS[n][1],
                                                 PROCESS_CORNERS[n][2], "cap_mim"]} for n in PROCESSES],
            "temperature_c": [TEMP_C],
        },
        "analysis": {"kind": "tran", "args": f"{cfg['tstep']} {tstop_ns:g}n 0 {cfg['tmax']}"},
        "measurements": [
            {"name": "t_first_edge", "unit": "s",
             "spice": f".meas tran t_first_edge WHEN v(clk)={vdd / 2:.4f} RISE=1"},
        ],
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": 7200, "keep_artifacts": True, "waveforms": True,
                    "save_mode": "netlist", "ngspice_init": ["set measureprec=8"]},
    }


def generate(out: Path, cfg: dict | None = None, probe: str | None = None) -> dict:
    """probe = 'proc:vdd:skew' -> single-corner request_probe.json (debug)."""
    c = dict(DEFAULTS)
    c.update(cfg or {})
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sched = build_schedule(c)
    tstop = sched["tstop_ns"]
    (out / "rcosc_top_schematic.spice").write_text(wf.dut_block())
    jobs = [(v, s, list(PROCESSES)) for v in VDDS_V for s in SKEWS]
    if probe:
        try:
            p, v, s = probe.split(":")
            jobs = [(float(v), s, [p])]
        except ValueError as e:
            raise PrepareError(f"--probe must be proc:vdd:skew, got {probe!r}") from e
        if jobs[0][0] not in VDDS_V or s not in SKEWS or p not in PROCESSES:
            raise PrepareError(f"bad probe {probe!r}")
    reqs = []
    for vdd, skew, procs in jobs:
        stem = "probe" if probe else tag_of(vdd, skew)
        changes = resolve(sched, skew, c)
        (out / f"tb_{stem}.spice").write_text(tb_text(vdd, skew, sched, changes, c, stem))
        req = request(f"tb_{stem}.spice", vdd, tstop, c)
        req["corners"]["process"] = [x for x in req["corners"]["process"] if x["name"] in procs]
        (out / f"request_{stem}.json").write_text(json.dumps(req, indent=2) + "\n")
        (out / f"schedule_{stem}.json").write_text(json.dumps(
            {"tag": stem, "vdd_v": vdd, "skew": skew, "skew_step_ns": SKEW_STEP_NS,
             "edge_ns": c["edge_ns"], "init_code": sched["init_code"], "tstop_ns": tstop,
             "changes": changes}, indent=1) + "\n")
        reqs.append({"request": f"request_{stem}.json", "netlist": f"tb_{stem}.spice",
                     "schedule": f"schedule_{stem}.json", "vdd_v": vdd, "skew": skew,
                     "processes": procs, "temperature_c": TEMP_C})
    prov = {
        "kind": "trim-transition-bench-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 103,
        "positions": [{"name": n, "lo": f"0x{lo:02X}", "hi": f"0x{hi:02X}",
                      "bits_flipped": len(bits_changed(lo, hi))} for n, lo, hi in POSITIONS],
        "skew_modes": {k: ("no skew" if v == 0 else f"bit i delayed {'i' if v > 0 else '(7-i)'} x {SKEW_STEP_NS:g} ns")
                       for k, v in SKEWS.items()},
        "bank_weighting": "binary, t0=LSB (R stage = 0.7482 um x 2^i), t<i>=1 shorts stage i; higher code = higher f",
        "grid": {"processes": list(PROCESSES), "temperature_c": TEMP_C, "vdd_v": VDDS_V},
        "models": MODELS,
        "settings": {k: c[k] for k in c},
        "dut": {"source": "design/netlist/pvt_tb.spice", "source_sha256": wf.sha256(wf.SRC),
                "extracted_sha256": wf.sha256(out / "rcosc_top_schematic.spice")},
        "requests": reqs,
        "execution": "via `klt sim` (batch backend); never a local multi-corner loop",
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--probe", help="proc:vdd:skew -> one-corner request_probe.json")
    ap.add_argument("--tmax", default=DEFAULTS["tmax"])
    ap.add_argument("--tstep", default=DEFAULTS["tstep"])
    a = ap.parse_args()
    try:
        prov = generate(a.out, {"tmax": a.tmax, "tstep": a.tstep}, a.probe)
    except PrepareError as e:
        sys.exit(f"prepare.py: {e}")
    print(f"wrote {len(prov['requests'])} request(s) to {a.out}")


if __name__ == "__main__":
    main()
