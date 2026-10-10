#!/usr/bin/env python3
"""Offline request generator for the interior-temperature campaign (issue #125).

This script launches NO simulator and performs NO cloud or network operation.
It writes three process-specific `klt sim` requests (12 temperature corners
each), their bench netlists, the extracted schematic DUT and a manifest into a
NEW directory.  Executing the requests is a later, separately approved batch
campaign (`klt sim --backend batch`, see sim/temperature/README.md).

Grid (exactly 36 unique points):
    process {tt, ss, ff} x temperature
    {-40, -27.5, -15, -2.5, 10, 22.5, 27, 35, 47.5, 60, 72.5, 85} C
    x supply 3.3 V, zero added clk capacitance.

Trim code: the per-process code calibrated against the RATIFIED 48 MHz target
at that process's own 27 C / 3.3 V point by the committed campaign
sim/pvt/results/20260923T030125Z (tt 0xA3, ss 0xCD, ff 0x59) is held at every
temperature.  Nothing is recalibrated at interior points and no surrogate code
is used.  The calibration source must be named explicitly (--cal-run).

Reused, not re-implemented: sim/waveform/prepare.py's calibration loader and
validation, DUT extraction, bench and request builders.  The historical 3-point
PVT axes (sim/pvt/pvt_sweep.py TEMPS_C) and the waveform harness's defaults and
--probe validation are untouched; this coordinator passes its own temperature
list to the request builder directly.

Usage:
    python3 -I sim/temperature/prepare.py \\
        --cal-run sim/pvt/results/20260923T030125Z --out <NEW dir>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_SIM = Path(__file__).resolve().parent.parent
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))
from _module_loader import load_module  # noqa: E402
WAVEFORM = REPO / "sim" / "waveform"


def _load(name: str, path: Path):
    """Import a sibling harness module under a unique name (both directories
    hold a `prepare.py`/`analyze.py`; plain `import prepare` would collide)."""
    return load_module(name, path, reuse=True)


wp = _load("rcosc_waveform_prepare", WAVEFORM / "prepare.py")

ISSUE = 125
PROCESSES = ("tt", "ss", "ff")
TEMPS_C = [-40.0, -27.5, -15.0, -2.5, 10.0, 22.5, 27.0, 35.0, 47.5, 60.0, 72.5, 85.0]
VDD_V = 3.3
LOAD_F = 0.0
REF_TEMP_C = 27.0
ANCHORS_C = (-40.0, 27.0, 85.0)
TOL_PPM = 100.0
TARGET = "ratified"
TARGET_HZ = 48.0e6
# The one authoritative calibration (issue #125).  20260923T030905Z is a
# delay probe (sim/pvt/delay_probe.py), not a replacement calibration.
CAL_RUNID = "20260923T030125Z"
CAL_GIT_SHA = "ed26786191202a85a71b6938563c45a1eaaa5582"
EXPECTED_CODES = {"tt": 0xA3, "ss": 0xCD, "ff": 0x59}
KIND = "interior-temperature-requests"
SYNTHETIC_LABEL = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"


class PrepareError(Exception):
    pass


def grid() -> list[tuple[str, float, float]]:
    """The exactly-36-point grid, (process, temp_c, vdd_v)."""
    if len(TEMPS_C) != 12 or len(set(TEMPS_C)) != 12 or sorted(TEMPS_C) != TEMPS_C:
        raise PrepareError("temperature axis must be 12 unique ascending values")
    for a in ANCHORS_C:
        if a not in TEMPS_C:
            raise PrepareError(f"anchor {a} C missing from the temperature axis")
    for p in PROCESSES:
        if p not in wp.PROCESS_CORNERS:
            raise PrepareError(f"process {p!r} missing from sim/pvt/pvt_sweep.py PROCESS_CORNERS")
    pts = [(p, t, VDD_V) for p in PROCESSES for t in TEMPS_C]
    if len(pts) != 36 or len(set(pts)) != 36:
        raise PrepareError(f"grid is not 36 unique points ({len(pts)})")
    return pts


def _git(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    except OSError as e:
        raise PrepareError(f"git unavailable: {e}") from e
    return r.returncode, r.stdout.strip()


def load_held_calibration(cal_run: Path, require_committed: bool = True) -> dict:
    """Load the ratified-target calibration via sim/waveform's validated loader
    (committed source, in-range unsaturated codes, held code status ok at all
    of the campaign's own T/V points, input hashes), then refuse anything that
    is not the authoritative run / codes named by issue #125."""
    try:
        cal = wp.load_calibration(Path(cal_run), TARGET, require_committed=require_committed)
    except wp.PrepareError as e:
        raise PrepareError(str(e)) from e
    src = cal["source"]
    if src.get("campaign_runid") != CAL_RUNID:
        raise PrepareError(f"calibration run id {src.get('campaign_runid')!r} is not the authoritative "
                           f"{CAL_RUNID!r}")
    if src.get("campaign_git_sha") != CAL_GIT_SHA:
        raise PrepareError(f"calibration manifest git_sha {src.get('campaign_git_sha')!r} != {CAL_GIT_SHA!r}")
    if src.get("campaign_git_dirty") is not False:
        raise PrepareError("calibration campaign does not record a clean tree (git_dirty must be false)")
    if cal["codes"] != EXPECTED_CODES:
        got = {p: f"0x{c:02X}" for p, c in cal["codes"].items()}
        raise PrepareError(f"calibrated codes {got} differ from the held codes "
                           f"{ {p: f'0x{c:02X}' for p, c in EXPECTED_CODES.items()} }")
    return cal


def design_revision() -> dict:
    """Current design revision, recorded SEPARATELY from the calibration's
    git_sha.  Schematic equivalence with the calibration revision is not
    established here.  Refuses a dirty design/ tree (the DUT hash would then
    match no revision)."""
    rc, head = _git("rev-parse", "HEAD")
    if rc != 0 or not head:
        raise PrepareError("cannot determine the current git revision")
    rc, dirty_design = _git("status", "--porcelain", "--", "design")
    if rc != 0:
        raise PrepareError("cannot determine the design/ tree state")
    if dirty_design:
        raise PrepareError("design/ has uncommitted changes; the DUT would match no revision")
    _, dirty_any = _git("status", "--porcelain")
    _, design_last = _git("log", "-1", "--format=%H", "--", "design")
    _, cal_obj = _git("cat-file", "-t", CAL_GIT_SHA)
    return {
        "head": head,
        "tree_dirty_outside_design": bool(dirty_any),
        "design_last_change_commit": design_last or None,
        "design_last_change_note": "git log -1 -- design; in a shallow clone this is the clone boundary",
        "calibration_git_sha": CAL_GIT_SHA,
        "calibration_git_sha_object_available": cal_obj == "commit",
        "same_revision_as_calibration": head == CAL_GIT_SHA,
    }


def _cfg(cfg: dict | None) -> dict:
    c = dict(cfg or {})
    if c.get("load_f", LOAD_F) != LOAD_F:
        raise PrepareError("this campaign is defined at zero added clk capacitance")
    c["load_f"] = LOAD_F
    try:
        return wp._cfg_from(c)
    except wp.PrepareError as e:
        raise PrepareError(str(e)) from e


def stem_of(proc: str) -> str:
    return f"t12_{proc}"


def generate(out: Path, cal: dict, cfg: dict | None = None) -> dict:
    """Write DUT, three benches, three requests and provenance.json into a NEW
    directory `out`; return the provenance dict.  Refuses to overwrite."""
    cfg = _cfg(cfg)
    out = Path(out)
    if out.exists():
        raise PrepareError(f"refusing to overwrite existing output {out}")
    codes = cal["codes"]
    if codes != EXPECTED_CODES:
        raise PrepareError("calibration codes differ from the held codes")
    pts = grid()
    rev = design_revision()
    out.mkdir(parents=True)
    dut = out / "rcosc_top_schematic.spice"
    dut.write_text(wp.dut_block())
    dut_sha = wp.sha256(dut)
    settings = {
        "ramp_ns": cfg["ramp_ns"], "tstop_ns": cfg["tstop_ns"], "tstep": cfg["tstep"],
        "tmax_time_step": cfg["tmax"], "window_ns": cfg["window_ns"],
        "min_cycles": cfg["min_cycles"], "load_f": cfg["load_f"],
        "reltol": cfg["reltol"], "abstol_a": cfg["abstol"], "vntol_v": cfg["vntol"],
        "saved_signals": ["v(clk)", "v(vdd)"],
        "units": {"time": "s (ramp/tstop/window given in ns)", "voltage": "V",
                  "capacitance": "F", "current_tolerance": "A", "temperature": "C"},
    }
    requests, corners, covered = [], [], []
    for proc in PROCESSES:
        stem, code = stem_of(proc), codes[proc]
        tb, rq = out / f"tb_{stem}.spice", out / f"request_{stem}.json"
        tb.write_text(wp.tb_text(VDD_V, code, cfg, stem))
        req = wp.request(tb.name, VDD_V, [proc], list(TEMPS_C), cfg)
        if req["corners"]["temperature_c"] != TEMPS_C or len(req["corners"]["process"]) != 1:
            raise PrepareError("request corner axes do not match the 12-temperature axis")
        rq.write_text(json.dumps(req, indent=2) + "\n")
        ent = {"request": rq.name, "netlist": tb.name, "process": proc, "vdd_v": VDD_V,
               "trim_code": code, "trim_hex": f"0x{code:02X}", "temperature_c": list(TEMPS_C),
               "sections": req["corners"]["process"][0]["sections"], "corner_count": len(TEMPS_C),
               "request_sha256": wp.sha256(rq), "netlist_sha256": wp.sha256(tb),
               "dut_sha256": dut_sha}
        requests.append(ent)
        for t in TEMPS_C:
            corners.append({
                "request": rq.name, "netlist": tb.name, "process": proc, "temp_c": t,
                "vdd_v": VDD_V, "load_f": LOAD_F, "trim_code": code, "trim_hex": f"0x{code:02X}",
                "calibration_runid": cal["source"]["campaign_runid"],
                "calibration_dir": cal["source"]["campaign_dir"],
                "target": TARGET, "target_hz": TARGET_HZ, "settings": settings,
                "request_sha256": ent["request_sha256"], "netlist_sha256": ent["netlist_sha256"],
                "dut_sha256": dut_sha})
            covered.append((proc, t, VDD_V))
    if len(covered) != 36 or set(covered) != set(pts):
        raise PrepareError("generated requests do not cover the 36-point grid exactly once")
    prov = {
        "kind": KIND,
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": ISSUE,
        "grid": {"processes": list(PROCESSES), "temperature_c": list(TEMPS_C), "vdd_v": VDD_V,
                 "load_f": LOAD_F, "points": len(pts),
                 "note": ("interior-temperature axis for curvature; the historical -40/27/85 C "
                          "PVT axes are unchanged and remain the basis of the discipline plant")},
        "target": {"name": TARGET, "f_hz": TARGET_HZ},
        "calibration": cal["source"] | {
            "codes": {p: f"0x{c:02X}" for p, c in codes.items()},
            "held": "per-process code held at all 12 temperatures; no interior recalibration, no surrogate",
            "not_a_calibration": "sim/pvt/results/20260923T030905Z is a delay probe, not a replacement"},
        "design_revision": rev,
        "schematic_equivalence": {
            "status": "UNVERIFIED",
            "required_before_measured_execution": (
                f"verify the DUT netlist against calibration revision {CAL_GIT_SHA}, or regenerate the "
                "calibration for the actual schematic and cite a new immutable run; the calibration "
                "git_sha is not proof of a matching schematic"),
        },
        "process_library_mapping": {p: {"fets": wp.PROCESS_CORNERS[p][0], "res": wp.PROCESS_CORNERS[p][1],
                                        "mimcap": wp.PROCESS_CORNERS[p][2], "extra": "cap_mim"}
                                    for p in PROCESSES},
        "models": dict(wp.MODELS),
        "settings": settings,
        "dut": {"source": "design/netlist/pvt_tb.spice", "source_sha256": wp.sha256(wp.SRC),
                "extracted": dut.name, "extracted_sha256": dut_sha},
        "reused": {"sim/waveform/prepare.py": wp.sha256(WAVEFORM / "prepare.py"),
                   "sim/waveform/analyze.py": wp.sha256(WAVEFORM / "analyze.py")},
        "analysis": {"reference_temp_c": REF_TEMP_C, "anchors_c": list(ANCHORS_C),
                     "tolerance_ppm_of_f27": TOL_PPM,
                     "tolerance_note": "diagnostic, not a spec; numerical convergence must be shown first"},
        "requests": requests,
        "corners": corners,
        "execution": ("later campaign only, via `klt sim --backend batch` after a successful "
                      "single-corner batch preflight; never a local multi-corner loop"),
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main(argv=None) -> int:
    d = wp.DEFAULTS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cal-run", required=True, type=Path,
                    help=f"committed calibration campaign dir (must be sim/pvt/results/{CAL_RUNID})")
    ap.add_argument("--out", required=True, type=Path, help="NEW output directory (never overwritten)")
    ap.add_argument("--ramp-ns", type=float, default=d["ramp_ns"])
    ap.add_argument("--tstop-ns", type=float, default=d["tstop_ns"])
    ap.add_argument("--tstep", default=d["tstep"])
    ap.add_argument("--tmax", default=d["tmax"], help="maximum time step")
    ap.add_argument("--window-ns", type=float, default=d["window_ns"])
    ap.add_argument("--min-cycles", type=int, default=d["min_cycles"])
    ap.add_argument("--reltol", type=float, default=d["reltol"])
    ap.add_argument("--abstol", type=float, default=d["abstol"])
    ap.add_argument("--vntol", type=float, default=d["vntol"])
    a = ap.parse_args(argv)
    cfg = {"ramp_ns": a.ramp_ns, "tstop_ns": a.tstop_ns, "tstep": a.tstep, "tmax": a.tmax,
           "window_ns": a.window_ns, "min_cycles": a.min_cycles,
           "reltol": a.reltol, "abstol": a.abstol, "vntol": a.vntol}
    try:
        cal = load_held_calibration(a.cal_run)
        prov = generate(a.out, cal, cfg)
    except PrepareError as e:
        print(f"prepare.py: {e}", file=sys.stderr)
        return 2
    print(f"wrote {len(prov['requests'])} requests / {prov['grid']['points']} points to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
