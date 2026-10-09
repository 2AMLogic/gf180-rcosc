#!/usr/bin/env python3
"""Offline bench / `klt sim` request generator for the clk waveform-shape
characterization (issue #91, offline subset).

This script launches NO simulator and performs NO cloud operation.  It writes
testbench netlists, three supply-specific `klt sim` requests (nine
process x temperature corners each) and a provenance file.  Executing the
requests is a later, separately approved campaign and must go through
`klt sim` with the batch backend (see sim/waveform/README.md).

Representative grid (exactly 27 points, a subset of sim/pvt's 63-point grid):
    process {tt, ss, ff} x temperature {-40, 27, 85} C x supply {3.0, 3.3, 3.6} V
Process-section definitions, TEMPS_C and VDDS_V are imported from
sim/pvt/pvt_sweep.py (not re-typed).

Trim code: per process, the code that a COMMITTED campaign calibrated at that
process's own 27 C / 3.3 V point is held at every temperature/supply point.
The calibration source must be named explicitly (--cal-run); nothing is
recalibrated here and nothing is defaulted.

Usage:
    python3 -I sim/waveform/prepare.py --cal-run sim/pvt/results/20260923T030125Z
    python3 -I sim/waveform/prepare.py --cal-run ... --probe tt:27:3.3
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "pvt"))
from pvt_sweep import (  # noqa: E402
    PROCESS_CORNERS, REF_TEMP_C, REF_VDD_V, TEMPS_C, VDDS_V,
)

PROCESSES = ("tt", "ss", "ff")
SRC = REPO / "design" / "netlist" / "pvt_tb.spice"
MODELS = {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"}

# Defaults (all configurable on the command line).  Units: seconds, volts,
# farads unless the name says otherwise.
DEFAULTS = {
    "ramp_ns": 1000.0,        # linear 0 -> VDD rail (and trim pins) ramp
    "tstop_ns": 20000.0,      # transient length
    "tstep": "200p",          # .tran print/suggested step
    "tmax": "200p",           # .tran maximum internal time step
    "window_ns": 2000.0,      # steady window = final window_ns
    "min_cycles": 20,         # complete cycles required in the window
    # Nominal output load: the calibration bench (design/netlist/pvt_tb.spice)
    # puts NO explicit capacitance on clk, so the nominal load is 0 F extra
    # (DUT-internal loading only).  A non-zero load invalidates "code held from
    # an unloaded calibration" and is recorded as such.
    "load_f": 0.0,
    "reltol": 1e-3,           # ngspice default, made explicit
    "abstol": 1e-12,          # A
    "vntol": 1e-6,            # V
}
TRIM_BITS = 8
CAL_TARGETS = {
    "ratified": ("calibration_spec_target", "posttrim_ratif"),
    "surrogate": ("calibration_surrogate_target", "posttrim_surr"),
}


class PrepareError(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grid() -> list[tuple[str, float, float]]:
    """The exactly-27-point representative grid, (process, temp_c, vdd_v)."""
    for p in PROCESSES:
        if p not in PROCESS_CORNERS:
            raise PrepareError(f"process {p!r} missing from sim/pvt/pvt_sweep.py PROCESS_CORNERS")
    pts = [(p, t, v) for p in PROCESSES for t in TEMPS_C for v in VDDS_V]
    if len(pts) != 27 or len(set(pts)) != 27:
        raise PrepareError(f"grid is not 27 unique points ({len(pts)})")
    return pts


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    return r.stdout.strip() if r.returncode == 0 else ""


def load_calibration(cal_run: Path, target: str = "ratified", require_committed: bool = True) -> dict:
    """Load and validate per-process calibrated codes from a committed
    sim/pvt campaign.  Returns {"codes": {proc: int}, "source": {...}}."""
    if target not in CAL_TARGETS:
        raise PrepareError(f"unknown calibration target {target!r}")
    key, pass_name = CAL_TARGETS[target]
    cal_run = Path(cal_run)
    man_path = cal_run / "manifest.json"
    if not man_path.is_file():
        raise PrepareError(f"calibration source has no manifest.json: {cal_run}")
    try:
        man = json.loads(man_path.read_text())
    except ValueError as e:
        raise PrepareError(f"calibration manifest is not valid JSON: {e}") from e
    cal = man.get(key)
    if not isinstance(cal, dict):
        raise PrepareError(f"{man_path} has no {key!r} (not a calibration campaign manifest)")
    codes = {}
    for p in PROCESSES:
        ent = cal.get(p)
        if not isinstance(ent, dict):
            raise PrepareError(f"calibration lacks process {p!r}")
        code = ent.get("code")
        if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 2 ** TRIM_BITS:
            raise PrepareError(f"calibration code for {p!r} invalid: {code!r}")
        if ent.get("saturated"):
            raise PrepareError(f"calibration for {p!r} is saturated; code is not a trimmed value")
        codes[p] = code
    # Coverage: the same code must appear, status ok, at all 9 T/V points.
    csv_path = cal_run / "results.csv"
    if not csv_path.is_file():
        raise PrepareError(f"calibration source has no results.csv: {cal_run}")
    seen = {p: set() for p in PROCESSES}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row["pass"] != pass_name or row["process"] not in codes:
                continue
            if row["status"] != "ok":
                raise PrepareError(f"calibration campaign row not ok: {row['process']} {row['temp_c']} {row['vdd_v']}")
            if int(row["trim_code"]) != codes[row["process"]]:
                raise PrepareError(
                    f"{pass_name} row for {row['process']} holds code {row['trim_code']}, "
                    f"manifest says {codes[row['process']]}")
            seen[row["process"]].add((float(row["temp_c"]), float(row["vdd_v"])))
    want = {(t, v) for t in TEMPS_C for v in VDDS_V}
    for p in PROCESSES:
        if seen[p] != want:
            raise PrepareError(f"calibration campaign does not cover all T/V points for {p!r}")
    rel = str(cal_run.resolve().relative_to(REPO)) if cal_run.resolve().is_relative_to(REPO) else str(cal_run)
    committed = ""
    if require_committed:
        if not _git("ls-files", "--error-unmatch", str(man_path.resolve())):
            raise PrepareError(f"calibration source is not a committed file: {man_path}")
        committed = _git("log", "-1", "--format=%H", "--", str(man_path.resolve()))
        if not committed:
            raise PrepareError(f"cannot determine committing hash of {man_path}")
    return {
        "codes": codes,
        "source": {
            "campaign_dir": rel,
            "target": target,
            "manifest_key": key,
            "campaign_runid": man.get("runid"),
            "campaign_git_sha": man.get("git_sha"),
            "campaign_git_dirty": man.get("git_dirty"),
            "manifest_sha256": sha256(man_path),
            "results_csv_sha256": sha256(csv_path),
            "committing_hash": committed or None,
            "calibration_point": {"temp_c": REF_TEMP_C, "vdd_v": REF_VDD_V},
            "per_process_f_hz": {p: cal[p].get("f_hz") for p in PROCESSES},
            "coverage": "each code verified at all 9 temperature/supply points of the campaign",
        },
    }


def dut_block() -> str:
    text = SRC.read_text().splitlines()
    start = next(i for i, l in enumerate(text) if "expanding" in l and "rcosc_top.sym" in l)
    end = next(i for i, l in enumerate(text) if l.strip() == ".end")
    block = [l for l in text[start:end] if not l.startswith(("** sym_path:", "** sch_path:"))]
    return (
        "* schematic DUT for the waveform bench: pvt_tb.spice's embedded rcosc_top hierarchy\n"
        "* (generated by prepare.py; no device or connection edited)\n"
        + "\n".join(block) + "\n")


def tag_of(vdd: float) -> str:
    return f"v{int(round(vdd * 10)):02d}"


def tb_text(vdd: float, code: int, cfg: dict, label: str) -> str:
    r = cfg["ramp_ns"]
    lines = [
        f"* rcosc_top waveform bench ({label}): VDD ramp 0->{vdd:g} V in {r:g} ns, "
        f"trim code 0x{code:02X} (generated by prepare.py)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".options reltol={cfg['reltol']:g} abstol={cfg['abstol']:g} vntol={cfg['vntol']:g}",
        '.include "rcosc_top_schematic.spice"',
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 PWL(0 0 {r:g}n {vdd:g})",
    ]
    for i in range(TRIM_BITS):
        lines.append(f"VT{i} t{i} 0 PWL(0 0 {r:g}n {vdd:g})" if (code >> i) & 1 else f"VT{i} t{i} 0 DC 0")
    if cfg["load_f"] > 0:
        lines.append(f"CLOAD clk 0 {cfg['load_f']:g}")
    lines.append(".save v(clk) v(vdd)")
    return "\n".join(lines) + "\n"


def request(name: str, vdd: float, procs, temps, cfg: dict) -> dict:
    """One `klt sim` request: len(procs) x len(temps) corners, one tran each."""
    vmid = vdd / 2
    return {
        "netlist": name,
        "engine": "ngspice",
        "netlist_source": "schematic",
        "models": dict(MODELS),
        "corners": {
            "process": [{"name": n, "sections": [PROCESS_CORNERS[n][0], PROCESS_CORNERS[n][1],
                                                 PROCESS_CORNERS[n][2], "cap_mim"]} for n in procs],
            "temperature_c": list(temps),
        },
        "analysis": {"kind": "tran",
                     "args": f"{cfg['tstep']} {cfg['tstop_ns']:g}n 0 {cfg['tmax']}"},
        "measurements": [
            {"name": "t_first_edge", "unit": "s",
             "spice": f".meas tran t_first_edge WHEN v(clk)={vmid:.4f} RISE=1"},
        ],
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": 3600, "keep_artifacts": True, "waveforms": True,
                    "save_mode": "netlist", "ngspice_init": ["set measureprec=8"]},
    }


def _cfg_from(cfg: dict | None) -> dict:
    out = dict(DEFAULTS)
    out.update(cfg or {})
    if out["window_ns"] >= out["tstop_ns"]:
        raise PrepareError("window must be shorter than tstop")
    if out["ramp_ns"] >= out["tstop_ns"] - out["window_ns"]:
        raise PrepareError("rail ramp must finish before the steady window starts")
    if out["min_cycles"] < 2:
        raise PrepareError("min_cycles must be >= 2")
    return out


def generate(out: Path, cal: dict, cfg: dict | None = None, probe: str | None = None) -> dict:
    """Write benches, requests and provenance.json into `out`; return provenance.

    klt's corner object carries only library sections and temperature -- there
    is no per-corner parameter override -- so a bench netlist can hold exactly
    one trim code.  Codes are per process, therefore the nine process x
    temperature corners of one supply are emitted as three requests (one per
    process, three temperature corners each) rather than one nine-corner
    request.  Still 27 unique dispatched corners, one transient each.
    """
    cfg = _cfg_from(cfg)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    codes = cal["codes"]
    pts = grid()
    (out / "rcosc_top_schematic.spice").write_text(dut_block())
    if probe:
        try:
            p, t, v = probe.split(":")
            point = (p, float(t), float(v))
        except ValueError as e:
            raise PrepareError(f"--probe must be proc:temp:vdd, got {probe!r}") from e
        if point not in pts:
            raise PrepareError(f"probe {probe!r} is not one of the 27 grid points")
        jobs = [("probe", point[2], point[0], [point[1]])]
    else:
        jobs = [(f"{tag_of(v)}_{p}", v, p, list(TEMPS_C)) for v in VDDS_V for p in PROCESSES]
    requests, covered = [], []
    for stem, vdd, proc, temps in jobs:
        code = codes[proc]
        (out / f"tb_{stem}.spice").write_text(tb_text(vdd, code, cfg, stem))
        req = request(f"tb_{stem}.spice", vdd, [proc], temps, cfg)
        (out / f"request_{stem}.json").write_text(json.dumps(req, indent=2) + "\n")
        requests.append({"request": f"request_{stem}.json", "netlist": f"tb_{stem}.spice",
                         "vdd_v": vdd, "process": proc, "trim_code": code,
                         "trim_hex": f"0x{code:02X}", "temperature_c": temps,
                         "sections": req["corners"]["process"][0]["sections"],
                         "corner_count": len(temps)})
        covered += [(proc, t, vdd) for t in temps]
    if not probe and (len(covered) != 27 or set(covered) != set(pts)):
        raise PrepareError("generated requests do not cover the 27-point grid exactly once")
    prov = {
        "kind": "waveform-bench-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 91,
        "grid": {"processes": list(PROCESSES), "temperature_c": TEMPS_C, "vdd_v": VDDS_V,
                 "points": len(pts) if not probe else 1,
                 "note": "subset of the 63-point sim/pvt grid; not full signoff"},
        "process_library_mapping": {p: {"fets": PROCESS_CORNERS[p][0], "res": PROCESS_CORNERS[p][1],
                                        "mimcap": PROCESS_CORNERS[p][2], "extra": "cap_mim"}
                                    for p in PROCESSES},
        "models": MODELS,
        "calibration": cal["source"] | {"codes": {p: f"0x{c:02X}" for p, c in codes.items()}},
        "settings": {
            "ramp_ns": cfg["ramp_ns"], "tstop_ns": cfg["tstop_ns"], "tstep": cfg["tstep"],
            "tmax_time_step": cfg["tmax"], "window_ns": cfg["window_ns"],
            "min_cycles": cfg["min_cycles"], "load_f": cfg["load_f"],
            "load_note": ("no explicit clk capacitance, matching the calibration bench "
                          "design/netlist/pvt_tb.spice" if cfg["load_f"] == 0 else
                          "NON-NOMINAL load: calibration codes were set unloaded"),
            "load_matches_calibration_bench": cfg["load_f"] == 0,
            "reltol": cfg["reltol"], "abstol_a": cfg["abstol"], "vntol_v": cfg["vntol"],
            "saved_signals": ["v(clk)", "v(vdd)"],
            "units": {"time": "s (ramp/tstop/window given in ns)", "voltage": "V",
                      "capacitance": "F", "current_tolerance": "A", "temperature": "C"},
        },
        "dut": {"source": "design/netlist/pvt_tb.spice",
                "source_sha256": sha256(SRC),
                "extracted_sha256": sha256(out / "rcosc_top_schematic.spice")},
        "requests": requests,
        "execution": "later campaign only, via `klt sim --backend batch`; never a local multi-corner loop",
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cal-run", required=True, type=Path,
                    help="committed sim/pvt results dir whose 27C/3.3V calibration supplies the codes")
    ap.add_argument("--cal-target", choices=sorted(CAL_TARGETS), default="ratified")
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--probe", help="proc:temp:vdd -> one-corner request_probe.json")
    ap.add_argument("--ramp-ns", type=float, default=DEFAULTS["ramp_ns"])
    ap.add_argument("--tstop-ns", type=float, default=DEFAULTS["tstop_ns"])
    ap.add_argument("--tstep", default=DEFAULTS["tstep"])
    ap.add_argument("--tmax", default=DEFAULTS["tmax"], help="maximum time step")
    ap.add_argument("--window-ns", type=float, default=DEFAULTS["window_ns"])
    ap.add_argument("--min-cycles", type=int, default=DEFAULTS["min_cycles"])
    ap.add_argument("--load-f", type=float, default=DEFAULTS["load_f"])
    ap.add_argument("--reltol", type=float, default=DEFAULTS["reltol"])
    ap.add_argument("--abstol", type=float, default=DEFAULTS["abstol"])
    ap.add_argument("--vntol", type=float, default=DEFAULTS["vntol"])
    a = ap.parse_args()
    cfg = {"ramp_ns": a.ramp_ns, "tstop_ns": a.tstop_ns, "tstep": a.tstep, "tmax": a.tmax,
           "window_ns": a.window_ns, "min_cycles": a.min_cycles, "load_f": a.load_f,
           "reltol": a.reltol, "abstol": a.abstol, "vntol": a.vntol}
    try:
        cal = load_calibration(a.cal_run, a.cal_target)
        prov = generate(a.out, cal, cfg, a.probe)
    except PrepareError as e:
        sys.exit(f"prepare.py: {e}")
    print(f"wrote {len(prov['requests'])} request(s) to {a.out}")


if __name__ == "__main__":
    main()
