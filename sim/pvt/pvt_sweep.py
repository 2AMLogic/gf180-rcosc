#!/usr/bin/env python3
"""gf180-rcosc PVT-corner simulation campaign driver (issue #12).

Runs the full process x temperature x supply factorial against the
xschem-derived ``design/netlist/pvt_tb.spice`` netlist and records every
result as append-only evidence under ``sim/pvt/``.

What this produces, per invocation (a new UTC-stamped run id, never an
overwrite of a previous one):

  sim/pvt/corners/<runid>/<key>.log     raw ngspice stdout/stderr, one file
                                        per simulated point
  sim/pvt/results/<runid>/results.csv   one row per simulated point
  sim/pvt/results/<runid>/manifest.json tool/PDK/git provenance + sweep config
  sim/pvt/results/<runid>/summary.md    tables + comparison against the
                                        ratified spec's own claimed figures

Passes
------
``trim_curve``     f vs. trim code at the nominal reference corner, used to
                   establish the *realized* trim range and per-code step.
``calibration``    single-point trim search (binary search over the 8-bit
                   code) at each process corner's own T=27 C / VDD=3.3 V
                   point, against both the ratified 48.000 MHz target and a
                   surrogate target (see below).
``pretrim``        full factorial at a fixed mid-scale code (0x80) -- the
                   untrimmed, free-running process/temperature/supply spread.
``posttrim_spec``  full factorial holding the ONE code that the nominal
                   reference corner (tt / 27 C / 3.3 V) calibrated to against
                   the ratified 48.000 MHz target.  This is the literal
                   single-point methodology DR-0003 assumes.
``posttrim_surr``  full factorial holding, per process corner, the code that
                   corner calibrated to against the *surrogate* target
                   f(tt, 27 C, 3.3 V, 0x80).  This is the "trim every die at
                   test" model the spec's +-1.1% row actually depends on, and
                   is the only pass that can produce a meaningful post-trim
                   residual when the ratified absolute target is unreachable.

Both post-trim passes are reported.  Neither is allowed to stand in for the
other: an oscillator spec without its trim math is not a spec.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_DIR = REPO_ROOT / "design"
NETLIST = DESIGN_DIR / "netlist" / "pvt_tb.spice"
SIM_PVT = REPO_ROOT / "sim" / "pvt"
BUILD_ROOT = REPO_ROOT / "sim" / "build"

# ---------------------------------------------------------------------------
# Ratified spec figures this campaign reports against.  Sourced from the repo
# README's ratified target-spec table, DR-0002 as corrected by DR-0003, and
# left unchanged by DR-0004.  These are NEVER edited to make a result pass --
# a contradiction is reported as a contradiction (CLAUDE.md).
# ---------------------------------------------------------------------------
SPEC = {
    "f_target_hz": 48.000e6,
    "trim_bits": 8,
    "trim_range_pct": 40.0,  # +-40% -> 28.8..67.2 MHz
    "trim_f_min_hz": 28.8e6,
    "trim_f_max_hz": 67.2e6,
    "trim_step_pct": 0.314,  # per code
    "untrimmed_spread_pct": 35.0,  # +-35% first-order
    "untrimmed_spread_lo_pct": -27.7,  # exact, in frequency
    "untrimmed_spread_hi_pct": +47.6,
    "posttrim_calpoint_pct": 1.1,  # +-1.1% at T=27 C, VDD +-10%
    "posttrim_fullrange_hi_pct": +8.0,  # -40..+85 C, VDD +-10%
    "posttrim_fullrange_lo_pct": -9.0,
}

# ---------------------------------------------------------------------------
# Sweep axes
# ---------------------------------------------------------------------------

# A "process corner" here is a *triple* of gf180mcu model-library sections --
# the FET corner, the resistor corner and the MIM-capacitor corner -- because
# an RC relaxation oscillator's period has contributions from all three.  The
# five required corners (tt/ff/ss/fs/sf) move the FET sections; the two extra
# rc_* corners hold the FETs typical and move only the passives, which is the
# module split DR-0003 derives its +-35% untrimmed process-spread row from
# (poly-R +-20% + MIM-C +-15.33%), so they let that row be checked directly.
PROCESS_CORNERS = {
    "tt": ("typical", "res_typical", "mimcap_typical"),
    "ff": ("ff", "res_ff", "mimcap_ff"),
    "ss": ("ss", "res_ss", "mimcap_ss"),
    "fs": ("fs", "res_typical", "mimcap_typical"),
    "sf": ("sf", "res_typical", "mimcap_typical"),
    "rc_f": ("typical", "res_ff", "mimcap_ff"),
    "rc_s": ("typical", "res_ss", "mimcap_ss"),
}

TEMPS_C = [-40.0, 27.0, 85.0]
VDDS_V = [3.0, 3.3, 3.6]

REF_PROCESS = "tt"
REF_TEMP_C = 27.0
REF_VDD_V = 3.3
MIDSCALE_CODE = 0x80

# Transient measurement window: skip the first 5 rising edges (startup), then
# average over the next 20 whole periods.
MEAS_FIRST_EDGE = 5
MEAS_LAST_EDGE = 25
TSTEP = "200p"
# TSTOP_NS_DEFAULT was 4000 for the DR-0004 schematic (~20 MHz free-running,
# so 4000ns gave ~80 periods of margin for a 25-edge measurement). Issue #16's
# re-sized schematic free-runs several times faster (tens of MHz), so the old
# 4000ns window now simulates far more oscillation cycles than the 25-edge
# measurement needs -- unnecessarily expensive without adding accuracy.
# Lowered to keep >=25 edges comfortably reachable at the slowest expected
# corner/code while cutting simulated-cycle count (and wall-clock cost) at
# the fast end. TSTOP_NS_RETRY is scaled down to match, still a >3x margin
# over TSTOP_NS_DEFAULT for the rare slow-corner point that needs it.
TSTOP_NS_DEFAULT = 1200
TSTOP_NS_RETRY = 4000  # used once, if the default window is too short


@dataclass(frozen=True)
class Point:
    """One simulated operating point."""

    process: str
    temp_c: float
    vdd_v: float
    code: int

    @property
    def key(self) -> str:
        return (
            f"{self.process}_T{int(self.temp_c):+04d}C_V{self.vdd_v:.1f}".replace(
                ".", "p"
            )
            + f"_code0x{self.code:02X}"
        )


@dataclass
class Result:
    point: Point
    f_hz: float | None
    period_s: float | None
    status: str
    log_path: str
    tstop_ns: int
    seconds: float = 0.0
    stderr_tail: str = ""


@dataclass
class Campaign:
    runid: str
    model_dir: Path
    log_dir: Path
    build_dir: Path
    jobs: int
    cache: dict[Point, Result] = field(default_factory=dict)
    order: list[Result] = field(default_factory=list)
    pass_rows: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PDK / tool resolution -- mirrors design/regen-netlist.sh exactly so the two
# never disagree about which install a result came from.
# ---------------------------------------------------------------------------


def resolve_pdk() -> tuple[Path, str, Path]:
    pdk = os.environ.get("PDK", "gf180mcuC")
    root = os.environ.get("PDK_ROOT", "")
    if not root and shutil.which("klt"):
        try:
            out = subprocess.run(
                ["klt", "pdk", "find", "--pdk", pdk, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if out.returncode == 0:
                root = json.loads(out.stdout).get("root", "")
        except Exception:  # pragma: no cover - best-effort resolution
            root = ""
    if not root:
        sys.exit(
            "PDK_ROOT not set and could not be resolved via "
            f"'klt pdk find --pdk {pdk}'. Set PDK_ROOT and re-run."
        )
    model_dir = Path(root) / pdk / "libs.tech" / "ngspice"
    for required in ("design.ngspice", "sm141064.ngspice"):
        if not (model_dir / required).is_file():
            sys.exit(
                f"ERROR: gf180mcu ngspice model {required} not found under {model_dir}"
            )
    return Path(root), pdk, model_dir


def tool_version(cmd: list[str], line: int = 0) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        text = (out.stdout or "") + (out.stderr or "")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines[line] if len(lines) > line else "unknown"
    except Exception:  # pragma: no cover
        return "unknown"


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # pragma: no cover
        return "unknown"


def git_dirty() -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return bool(out.stdout.strip())
    except Exception:  # pragma: no cover
        return True


# ---------------------------------------------------------------------------
# Deck composition
# ---------------------------------------------------------------------------


def corner_include(model_dir: Path, point: Point) -> str:
    fets, res, mim = PROCESS_CORNERS[point.process]
    bits = " ".join(f"b{i}={(point.code >> i) & 1}" for i in range(8))
    sm = model_dir / "sm141064.ngspice"
    return (
        "* pvt_corner.spice -- GENERATED by sim/pvt/pvt_sweep.py, do not edit.\n"
        f"* process={point.process} (fets={fets} res={res} mimcap={mim})\n"
        f"* temp={point.temp_c:g}C vdd={point.vdd_v:g}V trim=0x{point.code:02X}\n"
        f".include {model_dir / 'design.ngspice'}\n"
        f".lib {sm} {fets}\n"
        f".lib {sm} {res}\n"
        f".lib {sm} {mim}\n"
        f".lib {sm} cap_mim\n"
        f".temp {point.temp_c:g}\n"
        f".param vddval={point.vdd_v:g}\n"
        f".param {bits}\n"
    )


def control_include(point: Point, tstop_ns: int) -> str:
    vmid = point.vdd_v / 2.0
    ncyc = MEAS_LAST_EDGE - MEAS_FIRST_EDGE
    return (
        "* pvt_control.spice -- GENERATED by sim/pvt/pvt_sweep.py, do not edit.\n"
        ".control\n"
        "set noaskquit\n"
        f"tran {TSTEP} {tstop_ns}n\n"
        f"meas tran ta when v(clk)={vmid:.4f} rise={MEAS_FIRST_EDGE}\n"
        f"meas tran tb when v(clk)={vmid:.4f} rise={MEAS_LAST_EDGE}\n"
        f"let period = (tb-ta)/{ncyc}\n"
        f"let fosc = {ncyc}/(tb-ta)\n"
        "print ta tb period fosc\n"
        "quit\n"
        ".endc\n"
    )


def compose_deck(
    netlist_text: str, model_dir: Path, point: Point, tstop_ns: int
) -> str:
    deck = netlist_text
    for token, body in (
        (".include pvt_corner.spice", corner_include(model_dir, point)),
        (".include pvt_control.spice", control_include(point, tstop_ns)),
    ):
        if token not in deck:
            sys.exit(
                f"ERROR: '{token}' not found in {NETLIST}. Re-run design/regen-netlist.sh "
                "after any design/pvt_tb.sch edit."
            )
        deck = deck.replace(token, body, 1)
    return deck


FOSC_RE = re.compile(r"^\s*fosc\s*=\s*([-+0-9.eE]+)\s*$", re.M)
PERIOD_RE = re.compile(r"^\s*period\s*=\s*([-+0-9.eE]+)\s*$", re.M)


def run_point(camp: Campaign, netlist_text: str, point: Point) -> Result:
    """Simulate one operating point.  Results are cached and never re-run."""
    tstop = TSTOP_NS_DEFAULT
    last: Result | None = None
    for attempt in (1, 2):
        rundir = camp.build_dir / point.key / f"t{tstop}"
        rundir.mkdir(parents=True, exist_ok=True)
        deck = compose_deck(netlist_text, camp.model_dir, point, tstop)
        (rundir / "run.spice").write_text(deck)
        started = time.time()
        proc = subprocess.run(
            ["ngspice", "-b", "run.spice"],
            cwd=rundir,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        elapsed = time.time() - started
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        m_f, m_p = FOSC_RE.search(out), PERIOD_RE.search(out)
        log_rel = f"sim/pvt/corners/{camp.runid}/{point.key}.log"
        header = (
            "====================================================================\n"
            f"gf180-rcosc PVT corner run: {point.key}\n"
            f"run id      : {camp.runid}\n"
            f"process     : {point.process} "
            f"(fets={PROCESS_CORNERS[point.process][0]} "
            f"res={PROCESS_CORNERS[point.process][1]} "
            f"mimcap={PROCESS_CORNERS[point.process][2]})\n"
            f"temperature : {point.temp_c:g} C\n"
            f"supply      : {point.vdd_v:g} V\n"
            f"trim code   : 0x{point.code:02X} ({point.code})\n"
            f"transient   : tran {TSTEP} {tstop}n, "
            f"f = {MEAS_LAST_EDGE - MEAS_FIRST_EDGE} periods / "
            f"(t[rise={MEAS_LAST_EDGE}] - t[rise={MEAS_FIRST_EDGE}])\n"
            f"wall clock  : {elapsed:.1f} s\n"
            f"exit status : {proc.returncode}\n"
            "====================================================================\n"
        )
        (camp.log_dir / f"{point.key}.log").write_text(header + out)
        if m_f and m_p:
            f_hz = float(m_f.group(1))
            per = float(m_p.group(1))
            status = "ok" if (f_hz > 0 and per > 0) else "nonpositive"
            last = Result(point, f_hz, per, status, log_rel, tstop, elapsed)
            if status == "ok":
                return last
        else:
            last = Result(
                point,
                None,
                None,
                "no-measurement",
                log_rel,
                tstop,
                elapsed,
                stderr_tail="\n".join(out.strip().splitlines()[-6:]),
            )
        if attempt == 1:
            tstop = TSTOP_NS_RETRY  # window may have been too short at a slow corner
    assert last is not None
    return last


def simulate(
    camp: Campaign, netlist_text: str, points: list[Point]
) -> dict[Point, Result]:
    todo = [p for p in dict.fromkeys(points) if p not in camp.cache]
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=camp.jobs) as pool:
            futures = {pool.submit(run_point, camp, netlist_text, p): p for p in todo}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                res = fut.result()
                camp.cache[res.point] = res
                camp.order.append(res)
                done += 1
                fmt = f"{res.f_hz / 1e6:8.4f} MHz" if res.f_hz else f"{res.status:>12}"
                print(
                    f"  [{done:3d}/{len(todo):3d}] {res.point.key:<34} {fmt}",
                    flush=True,
                )
    return {p: camp.cache[p] for p in points}


def record(
    camp: Campaign, pass_name: str, results: dict[Point, Result], note: str = ""
) -> None:
    for point, res in results.items():
        fets, res_lib, mim = PROCESS_CORNERS[point.process]
        camp.pass_rows.append(
            {
                "pass": pass_name,
                "process": point.process,
                "fets_lib": fets,
                "res_lib": res_lib,
                "mimcap_lib": mim,
                "temp_c": f"{point.temp_c:g}",
                "vdd_v": f"{point.vdd_v:g}",
                "trim_code": point.code,
                "trim_hex": f"0x{point.code:02X}",
                "f_hz": f"{res.f_hz:.6e}" if res.f_hz else "",
                "f_mhz": f"{res.f_hz / 1e6:.6f}" if res.f_hz else "",
                "period_s": f"{res.period_s:.6e}" if res.period_s else "",
                "status": res.status,
                "tstop_ns": res.tstop_ns,
                "log": res.log_path,
                "note": note,
            }
        )


# ---------------------------------------------------------------------------
# Trim calibration
# ---------------------------------------------------------------------------


def calibrate(
    camp: Campaign,
    netlist_text: str,
    process: str,
    target_hz: float,
) -> tuple[int, float, bool]:
    """Single-point trim search at (process, 27 C, 3.3 V).

    ``R(code)`` is monotonically decreasing by construction of the trim bank
    (a set bit only ever shorts out series resistance), so ``f(code)`` is
    monotonically non-decreasing and a binary search is valid.  Returns
    ``(code, f_hz, saturated)``; ``saturated`` is True when the target lies
    outside the realized ``[f(0x00), f(0xFF)]`` range and the search had to
    clamp to an endpoint.
    """

    def f_at(code: int) -> float:
        pt = Point(process, REF_TEMP_C, REF_VDD_V, code)
        res = simulate(camp, netlist_text, [pt])[pt]
        if res.f_hz is None:
            sys.exit(
                f"ERROR: calibration point {pt.key} produced no measurement ({res.status})"
            )
        return res.f_hz

    f_lo, f_hi = f_at(0x00), f_at(0xFF)
    if target_hz <= f_lo:
        return 0x00, f_lo, True
    if target_hz >= f_hi:
        return 0xFF, f_hi, True
    lo, hi = 0x00, 0xFF
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if f_at(mid) < target_hz:
            lo = mid
        else:
            hi = mid
    f_l, f_h = f_at(lo), f_at(hi)
    return (
        (lo, f_l, False)
        if abs(f_l - target_hz) <= abs(f_h - target_hz)
        else (hi, f_h, False)
    )


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------


def pct(value: float, ref: float) -> float:
    return (value - ref) / ref * 100.0


def spread(results: dict[Point, Result], ref_hz: float | None) -> dict:
    freqs = [r.f_hz for r in results.values() if r.f_hz]
    if not freqs or not ref_hz:
        return {
            "n": 0,
            "min_hz": None,
            "max_hz": None,
            "mean_hz": None,
            "ref_hz": ref_hz,
            "lo_pct": float("nan"),
            "hi_pct": float("nan"),
            "half_span_pct": float("nan"),
        }
    lo, hi = min(freqs), max(freqs)
    return {
        "n": len(freqs),
        "min_hz": lo,
        "max_hz": hi,
        "mean_hz": statistics.fmean(freqs),
        "ref_hz": ref_hz,
        "lo_pct": pct(lo, ref_hz),
        "hi_pct": pct(hi, ref_hz),
        "half_span_pct": (hi - lo) / (hi + lo) * 100.0,
    }


def mhz(x: float | None) -> str:
    return f"{x / 1e6:.4f}" if x else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=min(12, os.cpu_count() or 4))
    ap.add_argument(
        "--runid",
        default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        help="UTC run id; a new directory is always created (append-only evidence)",
    )
    ap.add_argument(
        "--keep-build",
        action="store_true",
        help="keep sim/build/<runid>/ scratch decks after the campaign",
    )
    args = ap.parse_args()

    if not NETLIST.is_file():
        sys.exit(f"ERROR: {NETLIST} missing. Run design/regen-netlist.sh first.")
    netlist_text = NETLIST.read_text()

    pdk_root, pdk, model_dir = resolve_pdk()
    log_dir = SIM_PVT / "corners" / args.runid
    res_dir = SIM_PVT / "results" / args.runid
    for d in (log_dir, res_dir):
        if d.exists() and any(d.iterdir()):
            sys.exit(
                f"ERROR: {d} already exists and is non-empty; evidence is append-only."
            )
        d.mkdir(parents=True, exist_ok=True)
    build_dir = BUILD_ROOT / args.runid
    build_dir.mkdir(parents=True, exist_ok=True)

    # Captured BEFORE any evidence file is written, so the manifest records the
    # tree the campaign actually ran against rather than the tree its own
    # output has just made dirty.
    provenance = {"git_sha": git_sha(), "git_dirty": git_dirty()}

    camp = Campaign(args.runid, model_dir, log_dir, build_dir, args.jobs)
    factorial = [(p, t, v) for p in PROCESS_CORNERS for t in TEMPS_C for v in VDDS_V]
    started = time.time()

    # -- Pass 1: realized trim curve at the nominal reference corner ---------
    print("== pass: trim_curve (nominal reference corner) ==", flush=True)
    curve_codes = sorted(set(list(range(0x00, 0x100, 0x10)) + [0xFF]))
    curve_pts = [Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, c) for c in curve_codes]
    curve = simulate(camp, netlist_text, curve_pts)
    record(camp, "trim_curve", curve, "f vs. trim code at tt / 27 C / 3.3 V")

    f_code00 = curve[Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, 0x00)].f_hz
    f_codeff = curve[Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, 0xFF)].f_hz

    # -- Pass 2: single-point calibration, ratified + surrogate targets ------
    print("== pass: calibration ==", flush=True)
    ref_mid = Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, MIDSCALE_CODE)
    f_surrogate = simulate(camp, netlist_text, [ref_mid])[ref_mid].f_hz
    assert f_surrogate is not None

    cal_spec = {}
    cal_surr = {}
    for proc in PROCESS_CORNERS:
        cal_spec[proc] = calibrate(camp, netlist_text, proc, SPEC["f_target_hz"])
        cal_surr[proc] = calibrate(camp, netlist_text, proc, f_surrogate)
        print(
            f"  {proc:<5} spec-target -> 0x{cal_spec[proc][0]:02X} "
            f"({mhz(cal_spec[proc][1])} MHz, saturated={cal_spec[proc][2]}) | "
            f"surrogate -> 0x{cal_surr[proc][0]:02X} "
            f"({mhz(cal_surr[proc][1])} MHz, saturated={cal_surr[proc][2]})",
            flush=True,
        )

    # -- Pass 3: pre-trim factorial at fixed mid-scale code ------------------
    print("== pass: pretrim (fixed code 0x80, full factorial) ==", flush=True)
    pre_pts = [Point(p, t, v, MIDSCALE_CODE) for p, t, v in factorial]
    pre = simulate(camp, netlist_text, pre_pts)
    record(camp, "pretrim", pre, "fixed mid-scale trim code 0x80")

    # -- Pass 4: post-trim, single code from the nominal reference corner ----
    spec_code = cal_spec[REF_PROCESS][0]
    print(
        f"== pass: posttrim_spec (single code 0x{spec_code:02X}, full factorial) ==",
        flush=True,
    )
    post_spec_pts = [Point(p, t, v, spec_code) for p, t, v in factorial]
    post_spec = simulate(camp, netlist_text, post_spec_pts)
    record(
        camp,
        "posttrim_spec",
        post_spec,
        f"single-point trim at tt/27C/3.3V against 48.000 MHz -> code 0x{spec_code:02X}",
    )

    # -- Pass 5: post-trim, per-process-corner code, surrogate target --------
    print("== pass: posttrim_surr (per-corner code, full factorial) ==", flush=True)
    post_surr_pts = [Point(p, t, v, cal_surr[p][0]) for p, t, v in factorial]
    post_surr = simulate(camp, netlist_text, post_surr_pts)
    record(
        camp,
        "posttrim_surr",
        post_surr,
        f"per-corner single-point trim at 27C/3.3V against surrogate {mhz(f_surrogate)} MHz",
    )

    elapsed = time.time() - started

    # -- Evidence: CSV ------------------------------------------------------
    csv_path = res_dir / "results.csv"
    fields = [
        "pass",
        "process",
        "fets_lib",
        "res_lib",
        "mimcap_lib",
        "temp_c",
        "vdd_v",
        "trim_code",
        "trim_hex",
        "f_hz",
        "f_mhz",
        "period_s",
        "status",
        "tstop_ns",
        "log",
        "note",
    ]
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(camp.pass_rows)

    failures = [r for r in camp.order if r.status != "ok"]

    # -- Evidence: manifest -------------------------------------------------
    manifest = {
        "runid": args.runid,
        "utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": provenance["git_sha"],
        "git_dirty": provenance["git_dirty"],
        "host_arch": os.uname().machine,
        "ngspice": tool_version(["ngspice", "-v"], line=1),
        "xschem": tool_version(["xschem", "--version"], line=0),
        "pdk_root": str(pdk_root),
        "pdk": pdk,
        "model_dir": str(model_dir),
        "netlist": str(NETLIST.relative_to(REPO_ROOT)),
        "process_corners": {k: list(v) for k, v in PROCESS_CORNERS.items()},
        "temps_c": TEMPS_C,
        "vdds_v": VDDS_V,
        "midscale_code": MIDSCALE_CODE,
        "measurement": {
            "tstep": TSTEP,
            "tstop_ns": TSTOP_NS_DEFAULT,
            "tstop_ns_retry": TSTOP_NS_RETRY,
            "first_edge": MEAS_FIRST_EDGE,
            "last_edge": MEAS_LAST_EDGE,
            "cycles_averaged": MEAS_LAST_EDGE - MEAS_FIRST_EDGE,
        },
        "spec_figures": SPEC,
        "surrogate_target_hz": f_surrogate,
        "calibration_spec_target": {
            k: {"code": v[0], "f_hz": v[1], "saturated": v[2]}
            for k, v in cal_spec.items()
        },
        "calibration_surrogate_target": {
            k: {"code": v[0], "f_hz": v[1], "saturated": v[2]}
            for k, v in cal_surr.items()
        },
        "unique_points_simulated": len(camp.cache),
        "rows_recorded": len(camp.pass_rows),
        "failed_points": [r.point.key for r in failures],
        "wall_clock_s": round(elapsed, 1),
        "jobs": args.jobs,
    }
    (res_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # -- Evidence: summary --------------------------------------------------
    (res_dir / "summary.md").write_text(
        build_summary(
            camp,
            manifest,
            curve,
            curve_codes,
            pre,
            post_spec,
            post_surr,
            cal_spec,
            cal_surr,
            f_surrogate,
            f_code00,
            f_codeff,
            spec_code,
        )
    )

    if not args.keep_build:
        shutil.rmtree(build_dir, ignore_errors=True)

    print(
        f"\n== campaign complete: {len(camp.cache)} unique points, "
        f"{len(camp.pass_rows)} recorded rows, {len(failures)} failures, "
        f"{elapsed / 60:.1f} min ==\n"
        f"   logs    : sim/pvt/corners/{args.runid}/\n"
        f"   results : sim/pvt/results/{args.runid}/",
        flush=True,
    )
    return 1 if failures else 0


def build_summary(
    camp,
    manifest,
    curve,
    curve_codes,
    pre,
    post_spec,
    post_surr,
    cal_spec,
    cal_surr,
    f_surrogate,
    f_code00,
    f_codeff,
    spec_code,
) -> str:
    """Render the human-readable summary the AC's reporting rows require."""
    ref = Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, MIDSCALE_CODE)
    lines: list[str] = []
    add = lines.append

    add(f"# PVT corner campaign {camp.runid}")
    add("")
    add(
        "Generated by `sim/pvt/pvt_sweep.py` (issue #12). Append-only evidence: "
        "this file, `results.csv`, `manifest.json` and every raw log under "
        f"`sim/pvt/corners/{camp.runid}/` belong to this run id and are never "
        "rewritten by a later run."
    )
    add("")
    add("| | |")
    add("|---|---|")
    add(
        f"| git sha | `{manifest['git_sha']}`{' (dirty tree)' if manifest['git_dirty'] else ''} |"
    )
    add(f"| ngspice | {manifest['ngspice']} |")
    add(f"| PDK | {manifest['pdk']} @ `{manifest['pdk_root']}` |")
    add(f"| netlist | `{manifest['netlist']}` (from `design/pvt_tb.sch`) |")
    add(
        f"| measurement | `tran {TSTEP} {TSTOP_NS_DEFAULT}n`, f averaged over "
        f"{MEAS_LAST_EDGE - MEAS_FIRST_EDGE} whole periods (rising edges "
        f"{MEAS_FIRST_EDGE}..{MEAS_LAST_EDGE}, startup skipped) |"
    )
    add(f"| unique points simulated | {manifest['unique_points_simulated']} |")
    add(f"| recorded rows | {manifest['rows_recorded']} |")
    add(f"| failed points | {len(manifest['failed_points'])} |")
    add(f"| wall clock | {manifest['wall_clock_s']} s at {manifest['jobs']} jobs |")
    add("")

    add("## Sweep matrix")
    add("")
    add(
        "Full factorial, **every** combination simulated — no corner-by-corner "
        "spot check, no silently skipped point."
    )
    add("")
    add("| Axis | Values | Count |")
    add("|---|---|---|")
    add(
        "| process (fets / res / mimcap `.lib` sections) | "
        + ", ".join(f"`{k}` ({'/'.join(v)})" for k, v in PROCESS_CORNERS.items())
        + f" | {len(PROCESS_CORNERS)} |"
    )
    add(f"| temperature | {', '.join(f'{t:g} °C' for t in TEMPS_C)} | {len(TEMPS_C)} |")
    add(f"| supply | {', '.join(f'{v:g} V' for v in VDDS_V)} | {len(VDDS_V)} |")
    add(
        f"| **points per pass** | | **{len(PROCESS_CORNERS) * len(TEMPS_C) * len(VDDS_V)}** |"
    )
    add("")

    # -- realized trim curve
    add("## Realized trim curve (tt, 27 °C, 3.3 V)")
    add("")
    add("| code | f (MHz) | Δ vs. code 0x00 |")
    add("|---|---|---|")
    for c in curve_codes:
        r = curve[Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, c)]
        d = f"{pct(r.f_hz, f_code00):+.2f}%" if (r.f_hz and f_code00) else "n/a"
        add(f"| `0x{c:02X}` | {mhz(r.f_hz)} | {d} |")
    add("")
    if not (f_code00 and f_codeff):
        add(
            "**Trim-curve endpoints did not measure; the rows below cannot be derived.**"
        )
        return "\n".join(lines) + "\n"
    realized_span = (f_codeff - f_code00) / (f_codeff + f_code00) * 100.0
    realized_step = (f_codeff - f_code00) / f_code00 * 100.0 / 255.0
    add(
        f"Realized trim range: **{mhz(f_code00)} … {mhz(f_codeff)} MHz** "
        f"(ratio {f_codeff / f_code00:.4f}, ±{realized_span:.2f}% about the "
        f"midpoint), average step **{realized_step:.4f} %/code**."
    )
    add("")
    add("| Spec row | Ratified | Simulated | Verdict |")
    add("|---|---|---|---|")
    add(
        f"| Output frequency | {SPEC['f_target_hz'] / 1e6:.3f} MHz | "
        f"max reachable {mhz(f_codeff)} MHz at code `0xFF` | "
        + ("**not met**" if f_codeff < SPEC["f_target_hz"] else "met")
        + " |"
    )
    add(
        f"| Trim range | ±{SPEC['trim_range_pct']:.0f}% "
        f"({SPEC['trim_f_min_hz'] / 1e6:.1f}–{SPEC['trim_f_max_hz'] / 1e6:.1f} MHz) | "
        f"±{realized_span:.2f}% ({mhz(f_code00)}–{mhz(f_codeff)} MHz) | "
        + ("**not met**" if realized_span < SPEC["trim_range_pct"] else "met")
        + " |"
    )
    add(
        f"| Trim step | {SPEC['trim_step_pct']:.3f} %/code | "
        f"{realized_step:.4f} %/code | "
        + ("**not met**" if realized_step < SPEC["trim_step_pct"] * 0.9 else "met")
        + " |"
    )
    add("")

    # -- calibration
    add("## Single-point trim calibration")
    add("")
    add(
        "Binary search over the 8-bit code at each process corner's own "
        "27 °C / 3.3 V point (`f(code)` is monotonically non-decreasing by "
        "construction of the trim bank, so the search is valid)."
    )
    add("")
    add(
        f"- **Ratified target**: {SPEC['f_target_hz'] / 1e6:.3f} MHz "
        "(repo README target-spec table)."
    )
    add(
        f"- **Surrogate target**: {mhz(f_surrogate)} MHz — the design's own "
        "realized frequency at `tt / 27 °C / 3.3 V / code 0x80`. Used only "
        "because the ratified target is unreachable at every corner (below); "
        "it lets the post-trim residual still be measured with the spec's own "
        'single-point methodology instead of being reported as "undefined".'
    )
    add("")
    add(
        "| process | code @ 48.000 MHz target | f (MHz) | saturated? | code @ surrogate | f (MHz) | saturated? |"
    )
    add("|---|---|---|---|---|---|---|")
    for p in PROCESS_CORNERS:
        cs, cu = cal_spec[p], cal_surr[p]
        add(
            f"| `{p}` | `0x{cs[0]:02X}` | {mhz(cs[1])} | "
            f"{'**yes**' if cs[2] else 'no'} | `0x{cu[0]:02X}` | {mhz(cu[1])} | "
            f"{'**yes**' if cu[2] else 'no'} |"
        )
    add("")

    # -- pre-trim
    ref_f = pre[ref].f_hz
    add("## Untrimmed / free-running spread")
    add("")
    add(
        "Fixed mid-scale code `0x80` across the whole factorial. Percentages "
        f"are referenced to the nominal point `tt / 27 °C / 3.3 V` = {mhz(ref_f)} MHz."
    )
    add("")
    add(_matrix(pre, MIDSCALE_CODE, ref_f))
    add("")
    proc_only = {
        Point(p, REF_TEMP_C, REF_VDD_V, MIDSCALE_CODE): pre[
            Point(p, REF_TEMP_C, REF_VDD_V, MIDSCALE_CODE)
        ]
        for p in PROCESS_CORNERS
    }
    s_proc = spread(proc_only, ref_f)
    s_all = spread(pre, ref_f)
    add("| Condition | n | min (MHz) | max (MHz) | vs. nominal |")
    add("|---|---|---|---|---|")
    add(
        f"| process only (27 °C, 3.3 V) | {s_proc['n']} | {mhz(s_proc['min_hz'])} | "
        f"{mhz(s_proc['max_hz'])} | {s_proc['lo_pct']:+.2f}% / {s_proc['hi_pct']:+.2f}% |"
    )
    add(
        f"| full P×T×V factorial | {s_all['n']} | {mhz(s_all['min_hz'])} | "
        f"{mhz(s_all['max_hz'])} | {s_all['lo_pct']:+.2f}% / {s_all['hi_pct']:+.2f}% |"
    )
    add("")
    add("| Spec row | Ratified | Simulated (process only, fixed T/V) | Verdict |")
    add("|---|---|---|---|")
    add(
        f"| Free-running untrimmed process spread | ±{SPEC['untrimmed_spread_pct']:.0f}% "
        f"({SPEC['untrimmed_spread_lo_pct']:+.1f}% / {SPEC['untrimmed_spread_hi_pct']:+.1f}% exact) | "
        f"{s_proc['lo_pct']:+.2f}% / {s_proc['hi_pct']:+.2f}% | "
        + (
            "within the ratified bound"
            if max(abs(s_proc["lo_pct"]), abs(s_proc["hi_pct"]))
            <= max(
                abs(SPEC["untrimmed_spread_lo_pct"]),
                abs(SPEC["untrimmed_spread_hi_pct"]),
            )
            else "**exceeds the ratified bound**"
        )
        + " |"
    )
    add("")

    # -- post-trim, both passes, always reported together
    for name, data, cal, target_label in (
        (
            f"Post-trim — single code `0x{spec_code:02X}` from the ratified-target calibration",
            post_spec,
            {p: (spec_code, None, None) for p in PROCESS_CORNERS},
            f"{SPEC['f_target_hz'] / 1e6:.3f} MHz (ratified)",
        ),
        (
            "Post-trim — per-corner code from the surrogate-target calibration",
            post_surr,
            cal_surr,
            f"{mhz(f_surrogate)} MHz (surrogate)",
        ),
    ):
        add(f"## {name}")
        add("")
        add(f"Calibration target: {target_label}.")
        add("")
        p_ref = Point(REF_PROCESS, REF_TEMP_C, REF_VDD_V, cal[REF_PROCESS][0])
        base = data[p_ref].f_hz
        add(_matrix_percorner(data, cal, base))
        add("")
        cal_point = {
            Point(p, REF_TEMP_C, v, cal[p][0]): data[Point(p, REF_TEMP_C, v, cal[p][0])]
            for p in PROCESS_CORNERS
            for v in VDDS_V
        }
        s_cal = spread(cal_point, base)
        s_full = spread(data, base)
        add("| Condition | n | min (MHz) | max (MHz) | vs. calibrated nominal |")
        add("|---|---|---|---|---|")
        add(
            f"| calibration point (27 °C, VDD ±10%) | {s_cal['n']} | {mhz(s_cal['min_hz'])} | "
            f"{mhz(s_cal['max_hz'])} | {s_cal['lo_pct']:+.2f}% / {s_cal['hi_pct']:+.2f}% |"
        )
        add(
            f"| full temperature range (−40…+85 °C, VDD ±10%) | {s_full['n']} | "
            f"{mhz(s_full['min_hz'])} | {mhz(s_full['max_hz'])} | "
            f"{s_full['lo_pct']:+.2f}% / {s_full['hi_pct']:+.2f}% |"
        )
        add("")
        add("| Spec row | Ratified | Simulated | Verdict |")
        add("|---|---|---|---|")
        add(
            f"| Post-trim, at calibration point | ±{SPEC['posttrim_calpoint_pct']:.1f}% | "
            f"{s_cal['lo_pct']:+.2f}% / {s_cal['hi_pct']:+.2f}% | "
            + (
                "within"
                if max(abs(s_cal["lo_pct"]), abs(s_cal["hi_pct"]))
                <= SPEC["posttrim_calpoint_pct"]
                else "**exceeds**"
            )
            + " |"
        )
        add(
            f"| Post-trim, full temperature range | "
            f"{SPEC['posttrim_fullrange_lo_pct']:+.0f}% / "
            f"{SPEC['posttrim_fullrange_hi_pct']:+.0f}% | "
            f"{s_full['lo_pct']:+.2f}% / {s_full['hi_pct']:+.2f}% | "
            + (
                "within"
                if s_full["lo_pct"] >= SPEC["posttrim_fullrange_lo_pct"]
                and s_full["hi_pct"] <= SPEC["posttrim_fullrange_hi_pct"]
                else "**exceeds**"
            )
            + " |"
        )
        add("")
        add(
            "> Both figures above are stated together, never one without the "
            "other: the calibration-point number alone is not the accuracy of "
            "this block."
        )
        add("")

    # -- temperature and supply sensitivity, isolated
    add("## Isolated sensitivities (post-trim, per-corner surrogate calibration)")
    add("")
    add("| process | code | f(−40 °C) | f(27 °C) | f(85 °C) | ΔT coefficient |")
    add("|---|---|---|---|---|---|")
    for p in PROCESS_CORNERS:
        code = cal_surr[p][0]
        fs = [post_surr[Point(p, t, REF_VDD_V, code)].f_hz for t in TEMPS_C]
        if all(fs):
            tc = (fs[2] - fs[0]) / fs[1] / (TEMPS_C[2] - TEMPS_C[0]) * 1e6
            add(
                f"| `{p}` | `0x{code:02X}` | {mhz(fs[0])} | {mhz(fs[1])} | {mhz(fs[2])} | "
                f"{tc:+.0f} ppm/K |"
            )
    add("")
    add("| process | code | f(3.0 V) | f(3.3 V) | f(3.6 V) | supply sensitivity |")
    add("|---|---|---|---|---|---|")
    for p in PROCESS_CORNERS:
        code = cal_surr[p][0]
        fs = [post_surr[Point(p, REF_TEMP_C, v, code)].f_hz for v in VDDS_V]
        if all(fs):
            sv = (fs[2] - fs[0]) / fs[1] * 100.0
            add(
                f"| `{p}` | `0x{code:02X}` | {mhz(fs[0])} | {mhz(fs[1])} | {mhz(fs[2])} | "
                f"{sv:+.2f}% over 3.0→3.6 V |"
            )
    add("")

    if manifest["failed_points"]:
        add("## Points with no measurement")
        add("")
        for k in manifest["failed_points"]:
            add(f"- `{k}`")
        add("")

    return "\n".join(lines) + "\n"


def _matrix(data: dict[Point, Result], code: int, ref_hz: float | None) -> str:
    out = ["| process | T (°C) | " + " | ".join(f"{v:g} V" for v in VDDS_V) + " |"]
    out.append("|---|---|" + "---|" * len(VDDS_V))
    for p in PROCESS_CORNERS:
        for t in TEMPS_C:
            cells = []
            for v in VDDS_V:
                r = data.get(Point(p, t, v, code))
                if r and r.f_hz:
                    d = f" ({pct(r.f_hz, ref_hz):+.2f}%)" if ref_hz else ""
                    cells.append(f"{r.f_hz / 1e6:.4f}{d}")
                else:
                    cells.append("**FAIL**")
            out.append(f"| `{p}` | {t:g} | " + " | ".join(cells) + " |")
    out.append("")
    out.append("Cells are MHz (Δ vs. nominal).")
    return "\n".join(out)


def _matrix_percorner(data, cal, ref_hz) -> str:
    out = [
        "| process | code | T (°C) | " + " | ".join(f"{v:g} V" for v in VDDS_V) + " |"
    ]
    out.append("|---|---|---|" + "---|" * len(VDDS_V))
    for p in PROCESS_CORNERS:
        code = cal[p][0]
        for t in TEMPS_C:
            cells = []
            for v in VDDS_V:
                r = data.get(Point(p, t, v, code))
                if r and r.f_hz:
                    d = f" ({pct(r.f_hz, ref_hz):+.2f}%)" if ref_hz else ""
                    cells.append(f"{r.f_hz / 1e6:.4f}{d}")
                else:
                    cells.append("**FAIL**")
            out.append(
                f"| `{p}` | `0x{code:02X}` | {t:g} | " + " | ".join(cells) + " |"
            )
    out.append("")
    out.append("Cells are MHz (Δ vs. the calibrated nominal point).")
    return "\n".join(out)


if __name__ == "__main__":
    raise SystemExit(main())
