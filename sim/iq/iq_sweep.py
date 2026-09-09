#!/usr/bin/env python3
"""gf180-rcosc quiescent-current (Iq) sweep driver — issue #22, extended
#24, extended to a full PVT-corner factorial by issue #35.

Measures the block's supply current two different ways, at several trim
codes, across the **full process x temperature x supply factorial** —
7 process corners x 3 temperatures x 3 supplies = 63 grid points per code
— against the as-committed schematic sizing, so DR-0003 Row 4 ("< 500 uA
running") gets the same corner evidence the frequency spec rows have had
since issue #12.

The corner grid (`PROCESS_CORNERS`, `TEMPS_C`, `VDDS_V`, `corner_include()`)
is imported verbatim from `sim/pvt/pvt_sweep.py`, not re-typed here, so the
two campaigns' corner definitions cannot drift apart (issue #35).

Two metrics, always reported together (see DR-0008):

  iq_op   The `.op` figure issue #20 introduced and DR-0007 quoted:
          `-1e6*i(vdd)` at the DC operating point. A relaxation oscillator
          has no stable DC operating point, so this solve lands on the
          unstable equilibrium, which pins the charge-complete comparator
          XCMPH at its own output inverter's trip point in full crowbar
          conduction. Reported unchanged for continuity with DR-0007, not
          because it is the quantity DR-0003 Row 4 names.

  iq_run  `-i(vdd)` averaged over 20 whole oscillation periods (rising
          edges 5..25 of `clk`, startup skipped -- the same window
          convention `sim/pvt/pvt_sweep.py` uses). This is the quantity
          DR-0003 Row 4 names: "< 500 uA (running)", anchored to ST
          DS9826's IDDA(HSI48), a datasheet supply current for an
          oscillator that is oscillating.

Issue #24 / DR-0009: the `as-committed` sizing is re-derived against
`iq_run` specifically (not `iq_op`), because `iq_run` is the quantity
DR-0003 Row 4 actually names. Both metrics are still always measured and
reported together (never one without the other), but they are NOT expected
to agree on verdict at every sizing -- DR-0008's committed sizing happened
to satisfy both, but that was a consequence of sizing against the stricter
`.op` figure, not a general property. Report prose below states each
metric's verdict without asserting agreement.

Issue #35 scope note -- `pre-22` sizing dropped from the corner grid: the
pre-#22 sizing comparison (issue #16's `RBIAS L = 25 um`) is still recorded
at the reference corner only, in `sim/iq/results/20260906T062311Z/README.md`
and DR-0008. Running it across all 63 grid points as well would double
this driver's simulation cost for a before/after comparison the corner
campaign does not need -- the `as-committed` sizing is the one DR-0003 Row 4
is evaluated against going forward, so the grid covers it only.

Append-only evidence (CLAUDE.md): every invocation writes a fresh, UTC
run id under sim/iq/corners/<runid>/ (raw ngspice logs, one per simulated
grid point) and sim/iq/results/<runid>/ (results.csv, manifest.json,
README.md), and refuses to start if that run id already has content.

Usage:
  sim/iq/run-iq-sweep.sh                                # full grid, codes 0x00 0x80 0xC0 0xFF
  sim/iq/run-iq-sweep.sh --jobs 8
  sim/iq/run-iq-sweep.sh --subset endpoints             # fast check: tt/ff/ss x 3T x 3V only
  sim/iq/run-iq-sweep.sh --codes 0x00 0x80 0xFF
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NETLIST_DIR = os.path.join(REPO_ROOT, "design", "netlist")
SIM_IQ = os.path.join(REPO_ROOT, "sim", "iq")
SIM_PVT = os.path.join(REPO_ROOT, "sim", "pvt")

# Reuse sim/pvt/pvt_sweep.py's corner machinery verbatim (issue #35) so the
# two campaigns' corner definitions cannot drift apart. No behavior change
# to pvt_sweep.py itself -- this is a read-only import.
sys.path.insert(0, SIM_PVT)
from pvt_sweep import (  # path insert above must precede this import
    PROCESS_CORNERS,
    TEMPS_C,
    VDDS_V,
    Point,
    corner_include,
    resolve_pdk,
)

NUM = r"([-+0-9.eE]+)"

# --subset endpoints: a fast tt/ff/ss x 3T x 3V check (27 points/code), not
# a substitute for the committed record, which uses the full 7-corner grid.
ENDPOINT_PROCESSES = ("tt", "ff", "ss")

REF_PROCESS = "tt"
REF_TEMP_C = 27.0
REF_VDD_V = 3.3

TARGET_UA = 500.0

# Transient measurement window. Mirrors sim/pvt/pvt_sweep.py's own two-tier
# retry: the default window comfortably covers 25 whole periods (skip 5,
# average 20) down to ~21 MHz; corners/codes slower than that (e.g. `ss` /
# -40 C / low VDD / low trim code) retry once at the wider window, which
# covers oscillation down to ~6.25 MHz.
TSTEP = "200p"
TSTOP_NS_DEFAULT = 1200
TSTOP_NS_RETRY = 4000


def control_block(vdd_v: float, tstop_ns: int) -> str:
    """The measurement block, parameterized by supply (edge threshold) and
    transient window (retry). Identical in structure to
    design/smoke_test.sch's own .control (which this driver replaces so it
    can sweep corner/code), except the previous single-supply driver's
    fixed `1.65` edge threshold becomes `vdd_v / 2` now that VDD is swept.
    """
    vmid = vdd_v / 2.0
    return f"""
.control
op
let iq_ua = -1e6*i(vdd)
print iq_ua
* Why iq_ua is not the running current: this DC equilibrium is the unstable
* one (a relaxation oscillator has no stable operating point), and it pins
* the charge-complete comparator XCMPH at its own output inverter's trip
* point -- so that buffer, and the SR-latch NOR gate its mid-rail output
* drives, are both in full crowbar conduction. Printed so that claim is
* checkable from this log rather than merely asserted: expect
* xxcmph.dp and cmph_out near mid-rail on the swept supply.
print v(xxdut.xxcmph.dp) v(xxdut.xxcmph.dn) v(xxdut.cmph_out)
print v(xxdut.xxcmpl.dp) v(xxdut.xxcmpl.dn) v(xxdut.cmpl_out)
print v(xxdut.vc) v(xxdut.clk) v(xxdut.ibias) v(xxdut.vh) v(xxdut.vl)
tran {TSTEP} {tstop_ns}n
let ivdd_ua = -1e6*i(vdd)
meas tran t_avg_start when v(clk)={vmid:.4f} rise=5
meas tran t_avg_end when v(clk)={vmid:.4f} rise=25
meas tran iq_run_ua AVG ivdd_ua FROM=$&t_avg_start TO=$&t_avg_end
quit
.endc
"""


def build_deck(point: Point, model_dir, tstop_ns: int) -> str:
    """Return a self-contained ngspice deck for one (corner, trim code)
    grid point, at the as-committed schematic sizing (see module docstring
    for why `pre-22` is not part of the corner grid)."""
    with open(os.path.join(NETLIST_DIR, "smoke_test.spice")) as fh:
        deck = fh.read()

    # Corner .lib recipe + .temp, generated by the SAME function
    # sim/pvt/pvt_sweep.py uses for its own frequency campaign (issue #35).
    # The '.param vddval=...'/'b0..b7' lines corner_include() also emits are
    # unused by this netlist (smoke_test.sch drives VDD and VT<n> as
    # discrete sources, not params) and are harmless no-ops here.
    deck, n = re.subn(r"^\.include pdk_include\.spice$",
                      lambda _m: corner_include(model_dir, point).rstrip("\n"),
                      deck, flags=re.M)
    if n != 1:
        raise RuntimeError(f"'.include pdk_include.spice' matched {n} lines, expected 1")

    # Supply voltage: the netlist's single VDD source.
    deck, n = re.subn(r"^(VDD vdd 0 dc )[0-9.]+$",
                      r"\g<1>%.4g" % point.vdd_v, deck, flags=re.M)
    if n != 1:
        raise RuntimeError(f"VDD override matched {n} lines, expected 1")

    # Replace the schematic's .control with this driver's own (see
    # control_block()).
    deck = re.sub(r"\.control.*?\.endc", "", deck, flags=re.S)
    deck = deck.replace("**** end user architecture code",
                        control_block(point.vdd_v, tstop_ns) +
                        "\n**** end user architecture code")

    # Trim code: drive the eight VT<n> sources that smoke_test.sch defines.
    for bit in range(8):
        level = "%.4g" % point.vdd_v if (point.code >> bit) & 1 else "0.0"
        deck, n = re.subn(r"^VT%d t%d 0 dc [0-9.]+$" % (bit, bit),
                          "VT%d t%d 0 dc %s" % (bit, bit, level),
                          deck, flags=re.M)
        if n != 1:
            raise RuntimeError(f"VT{bit} override matched {n} lines, expected 1")
    return deck


def _grab(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.M)
    return float(m.group(1)) if m else None


def run_point(args):
    point, corners_dir, model_dir = args
    last = None
    for attempt, tstop in enumerate((TSTOP_NS_DEFAULT, TSTOP_NS_RETRY), start=1):
        deck = build_deck(point, model_dir, tstop)
        started = time.time()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "deck.spice")
            with open(path, "w") as fh:
                fh.write(deck)
            proc = subprocess.run(["ngspice", "-b", path], cwd=td,
                                  capture_output=True, text=True, timeout=1800)
            out = proc.stdout + proc.stderr
        elapsed = time.time() - started

        log_name = f"{point.key}.log"
        fets, res, mim = PROCESS_CORNERS[point.process]
        header = (
            "====================================================================\n"
            f"gf180-rcosc Iq sweep grid point: {point.key}\n"
            f"process     : {point.process} (fets={fets} res={res} mimcap={mim})\n"
            f"temperature : {point.temp_c:g} C\n"
            f"supply      : {point.vdd_v:g} V\n"
            f"trim code   : 0x{point.code:02X} ({point.code})\n"
            f"attempt     : {attempt} (tran {TSTEP} {tstop}n)\n"
            f"wall clock  : {elapsed:.1f} s\n"
            f"exit status : {proc.returncode}\n"
            "====================================================================\n"
        )
        with open(os.path.join(corners_dir, log_name), "w") as fh:
            fh.write(header + out)

        iq_op = _grab(r"iq_ua\s*=\s*" + NUM, out)
        iq_run = _grab(r"iq_run_ua\s*=\s*" + NUM, out)
        t0 = _grab(r"t_avg_start\s*=\s*" + NUM, out)
        t1 = _grab(r"t_avg_end\s*=\s*" + NUM, out)
        freq = 20.0 / (t1 - t0) / 1e6 if (t0 is not None and t1 is not None and t1 > t0) else None
        result = {"process": point.process, "temp_c": point.temp_c,
                  "vdd_v": point.vdd_v, "code": point.code,
                  "iq_op_ua": iq_op, "iq_run_ua": iq_run, "f_mhz": freq,
                  "log": log_name, "tstop_ns": tstop}
        if iq_op is not None and iq_run is not None:
            return result
        last = result
        # else: this corner/code is slower than the default window covers
        # -- retry once at the wider TSTOP_NS_RETRY window.
    return last


def verdict(value):
    if value is None:
        return "no measurement"
    return "met" if value < TARGET_UA else "**exceeds**"


def _grid_cell(row) -> str:
    if row is None or row["iq_run_ua"] is None or row["iq_op_ua"] is None:
        return "**FAIL**"
    run_s = "%.2f" % row["iq_run_ua"]
    if row["iq_run_ua"] >= TARGET_UA:
        run_s = f"**{run_s}**"
    return f"{run_s} ({row['iq_op_ua']:.2f})"


def _matrix_for_code(by_point, code) -> str:
    out = ["| process | T (°C) | " + " | ".join(f"{v:g} V" for v in VDDS_V) + " |"]
    out.append("|---|---|" + "---|" * len(VDDS_V))
    for p in PROCESS_CORNERS:
        for t in TEMPS_C:
            cells = []
            for v in VDDS_V:
                cells.append(_grid_cell(by_point.get((p, t, v, code))))
            out.append(f"| `{p}` | {t:g} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_results(runid, rows, results_dir, ngspice_ver, pdk_root, git_sha,
                  dirty, processes, codes, subset, wall_clock_s, jobs):
    fields = ["variant", "process", "temp_c", "vdd_v", "code",
             "iq_op_ua", "iq_run_ua", "f_mhz", "log"]
    with open(os.path.join(results_dir, "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({"variant": "as-committed", "process": r["process"],
                       "temp_c": r["temp_c"], "vdd_v": r["vdd_v"],
                       "code": "0x%02X" % r["code"],
                       "iq_op_ua": r["iq_op_ua"], "iq_run_ua": r["iq_run_ua"],
                       "f_mhz": r["f_mhz"], "log": r["log"]})

    with open(os.path.join(results_dir, "manifest.json"), "w") as fh:
        json.dump({
            "runid": runid, "git_sha": git_sha, "dirty_tree": dirty,
            "ngspice": ngspice_ver, "pdk_root": pdk_root,
            "target_ua": TARGET_UA,
            "netlist": "design/netlist/smoke_test.spice",
            "variant": "as-committed",
            "corner": {
                "process_corners": {k: list(v) for k, v in PROCESS_CORNERS.items()},
                "temps_c": TEMPS_C,
                "vdds_v": VDDS_V,
                "subset": subset,
                "processes_run": list(processes),
            },
            "codes": ["0x%02X" % c for c in codes],
            "grid_points_per_code": len(processes) * len(TEMPS_C) * len(VDDS_V),
            "wall_clock_s": round(wall_clock_s, 1),
            "jobs": jobs,
            "points": rows,
        }, fh, indent=2)
        fh.write("\n")

    def cell(v, fmt="%.2f"):
        return fmt % v if v is not None else "—"

    # Index rows for lookup and worst-case selection.
    by_point = {(r["process"], r["temp_c"], r["vdd_v"], r["code"]): r for r in rows}

    worst_by_code = {}
    for code in codes:
        candidates = [r for r in rows if r["code"] == code and r["iq_run_ua"] is not None]
        if candidates:
            worst_by_code[code] = max(candidates, key=lambda r: r["iq_run_ua"])

    ref_by_code = {
        code: by_point.get((REF_PROCESS, REF_TEMP_C, REF_VDD_V, code))
        for code in codes
    }

    failed = [r for r in rows if r["iq_op_ua"] is None or r["iq_run_ua"] is None]

    lines = [
        f"# Quiescent current (Iq) PVT-corner sweep {runid} — issue #35",
        "",
        "Generated by `sim/iq/iq_sweep.py` (issue #22, extended #24, extended",
        "to a full PVT-corner factorial by issue #35). Append-only evidence:",
        "this file, `results.csv`, `manifest.json` and every raw log under",
        f"`sim/iq/corners/{runid}/` belong to this run id and are never",
        "rewritten by a later run.",
        "",
        "| | |", "|---|---|",
        f"| git sha | `{git_sha}`{' (dirty tree)' if dirty else ''} |",
        f"| ngspice | {ngspice_ver} |",
        f"| PDK | gf180mcuC @ `{pdk_root}` |",
        "| netlist | `design/netlist/smoke_test.spice` (from `design/smoke_test.sch`) |",
        "| sizing | `as-committed` only (see module docstring for why `pre-22`"
        " is not part of the grid) |",
        f"| subset | `{subset}` ({len(processes)} process corner(s) x"
        f" {len(TEMPS_C)} T x {len(VDDS_V)} V = "
        f"{len(processes) * len(TEMPS_C) * len(VDDS_V)} points/code) |",
        f"| codes | {', '.join('0x%02X' % c for c in codes)} |",
        f"| total grid points | {len(rows)} (0 failed) |" if not failed else
        f"| total grid points | {len(rows)} ({len(failed)} **FAILED**) |",
        f"| wall clock | {wall_clock_s:.1f} s at {jobs} jobs |",
        f"| target | DR-0003 Row 4: `< {TARGET_UA:.0f} µA` (running) |",
        "| Row 4 verdict basis | `iq_run` (DR-0009) -- `iq_op` reported for"
        " continuity only, per DR-0008/DR-0009 |",
        "",
        "## Two metrics, reported together",
        "",
        "- **`iq_op`** — `-1e6*i(vdd)` at the `.op` point: the measurement",
        "  issue #20 introduced and [DR-0007] quoted. A relaxation oscillator",
        "  has no stable DC operating point, so this solve converges on the",
        "  unstable equilibrium, which pins the charge-complete comparator",
        "  `XCMPH` at its own output inverter's trip point — holding that",
        "  buffer, and the SR-latch NOR gate its mid-rail output drives, in",
        "  full crowbar conduction, a state the running circuit passes through",
        "  but never rests in. The `.op` node voltages printed into every raw",
        "  log under `../../corners/` show this directly. Reported unchanged",
        "  for continuity with DR-0007.",
        "- **`iq_run`** — `-i(vdd)` averaged over 20 whole oscillation periods",
        "  (rising edges 5..25 of `clk`, startup skipped). This is the quantity",
        "  DR-0003 Row 4 names: `< 500 µA` **(running)**, anchored to ST",
        "  DS9826's `IDDA(HSI48)` — a datasheet supply current for an",
        "  oscillator that is oscillating.",
        "",
        "**Issue #35 addition**: both metrics are now measured at every grid",
        "point of the full process x temperature x supply factorial, not just",
        "the single reference corner (`tt`/27 °C/3.3 V) prior runs used. Row 4's",
        "verdict per code below is stated at the **worst-case corner** (the",
        "grid point with the highest `iq_run` at that code), with the",
        "reference-corner value given alongside it for continuity with",
        "DR-0009's own reference-corner figures.",
        "",
        "## Sweep matrix",
        "",
        "| Axis | Values | Count |",
        "|---|---|---|",
        "| process (fets / res / mimcap `.lib` sections) | "
        + ", ".join(f"`{p}`" for p in processes) + f" | {len(processes)} |",
        f"| temperature | {', '.join(f'{t:g} °C' for t in TEMPS_C)} | {len(TEMPS_C)} |",
        f"| supply | {', '.join(f'{v:g} V' for v in VDDS_V)} | {len(VDDS_V)} |",
        f"| trim code | {', '.join('0x%02X' % c for c in codes)} | {len(codes)} |",
        f"| **grid points, this run** | | **{len(rows)}** |",
        "",
        "Corner definitions (`PROCESS_CORNERS`/`TEMPS_C`/`VDDS_V`/",
        "`corner_include()`) are imported from `sim/pvt/pvt_sweep.py`",
        "verbatim, not re-typed, so the frequency and Iq campaigns cannot",
        "disagree about what a corner is (issue #35).",
        "",
        "## Full grid results (every point)",
        "",
        "One matrix per trim code. Each cell is `iq_run (iq_op)` in µA;",
        "`iq_run` is **bold** where it is at or above the 500 µA target",
        "(Row 4's verdict basis, DR-0009). `iq_op` is reported alongside for",
        "continuity only — see \"Two metrics\" above.",
        "",
    ]
    for code in codes:
        lines.append(f"### code `0x{code:02X}`")
        lines.append("")
        lines.append(_matrix_for_code(by_point, code))
        lines.append("")

    lines += [
        "## Per-code worst case (Row 4 verdict basis)",
        "",
        "| code | worst-case corner | `iq_run` (µA) | verdict | reference corner"
        " (`tt`/27 °C/3.3 V) `iq_run` (µA) | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for code in codes:
        w = worst_by_code.get(code)
        r = ref_by_code.get(code)
        if w is None:
            lines.append(f"| `0x{code:02X}` | **no measurement** | — | — | — | — |")
            continue
        worst_label = f"`{w['process']}` / {w['temp_c']:g} °C / {w['vdd_v']:g} V"
        r_run = cell(r["iq_run_ua"]) if r else "—"
        r_verdict = verdict(r["iq_run_ua"]) if r else "no measurement"
        lines.append(
            f"| `0x{code:02X}` | {worst_label} | {cell(w['iq_run_ua'])} | "
            f"{verdict(w['iq_run_ua'])} | {r_run} | {r_verdict} |"
        )
    lines += [
        "",
        "**DR-0003 Row 4 verdict, per code, at the worst-case corner over the",
        f"{subset} grid** — see table above. A code's verdict is `met`",
        "only if `iq_run` stays under 500 µA at every one of that code's",
        f"{len(processes) * len(TEMPS_C) * len(VDDS_V)} grid points; the worst-case",
        "row is exactly the maximum over that grid, so \"met\" in the table",
        "above means met everywhere for that code.",
        "",
        "[DR-0007]: ../../../../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md",
        "",
    ]
    if failed:
        lines.append("## Points with no measurement")
        lines.append("")
        for r in failed:
            lines.append(
                f"- `{r['process']}` / {r['temp_c']:g} °C / {r['vdd_v']:g} V /"
                f" `0x{r['code']:02X}` — see `{r['log']}`"
            )
        lines.append("")

    with open(os.path.join(results_dir, "README.md"), "w") as fh:
        fh.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=6,
                    help="parallel ngspice processes (default 6)")
    ap.add_argument("--codes", nargs="+", default=["0x00", "0x80", "0xC0", "0xFF"],
                    help="trim codes to sweep (default: 0x00 0x80 0xC0 0xFF)")
    ap.add_argument("--subset", choices=["full", "endpoints"], default="full",
                    help="'full': all 7 process corners (the committed record). "
                         "'endpoints': tt/ff/ss only, a fast check -- not a "
                         "substitute for the full-grid committed record.")
    ap.add_argument("--runid", default=None, help="override the UTC run id")
    args = ap.parse_args()

    for required in ("smoke_test.spice",):
        if not os.path.isfile(os.path.join(NETLIST_DIR, required)):
            sys.exit(f"ERROR: {required} missing — run design/regen-netlist.sh first")

    pdk_root, pdk, model_dir = resolve_pdk()

    runid = args.runid or datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    corners_dir = os.path.join(SIM_IQ, "corners", runid)
    results_dir = os.path.join(SIM_IQ, "results", runid)
    for d in (corners_dir, results_dir):
        if os.path.isdir(d) and os.listdir(d):
            sys.exit(f"ERROR: run id {runid} already has content at {d} — "
                     "evidence is append-only, pick a new run id")
        os.makedirs(d, exist_ok=True)

    codes = [int(c, 0) for c in args.codes]
    processes = list(PROCESS_CORNERS) if args.subset == "full" else list(ENDPOINT_PROCESSES)
    points = [Point(p, t, v, c) for p in processes for t in TEMPS_C
             for v in VDDS_V for c in codes]

    ngspice_ver = subprocess.run(["ngspice", "-v"], capture_output=True,
                                 text=True).stdout.splitlines()[1].strip()
    git_sha = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", REPO_ROOT, "status", "--porcelain"],
                                capture_output=True, text=True).stdout.strip())

    print(f"== gf180-rcosc Iq PVT sweep {runid}: {len(points)} points"
         f" ({args.subset} subset, {len(codes)} codes) ==")
    started = time.time()
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        run_args = [(p, corners_dir, model_dir) for p in points]
        done = 0
        for r in ex.map(run_point, run_args):
            rows.append(r)
            done += 1
            print("  [%4d/%4d] %-6s T%+04dC V%.1f code 0x%02X  iq_op=%8s uA  "
                 "iq_run=%8s uA  f=%9s MHz"
                 % (done, len(points), r["process"], int(r["temp_c"]), r["vdd_v"],
                    r["code"],
                    "%.2f" % r["iq_op_ua"] if r["iq_op_ua"] is not None else "FAIL",
                    "%.2f" % r["iq_run_ua"] if r["iq_run_ua"] is not None else "FAIL",
                    "%.4f" % r["f_mhz"] if r["f_mhz"] is not None else "FAIL"),
                 flush=True)
    wall_clock_s = time.time() - started

    order = {p: i for i, p in enumerate(processes)}
    rows.sort(key=lambda r: (r["code"], order[r["process"]], r["temp_c"], r["vdd_v"]))
    write_results(runid, rows, results_dir, ngspice_ver, str(pdk_root), git_sha,
                 dirty, processes, codes, args.subset, wall_clock_s, args.jobs)

    failed = [r for r in rows if r["iq_op_ua"] is None or r["iq_run_ua"] is None]
    print(f"== sweep complete: {len(rows)} points, {len(failed)} failures,"
         f" {wall_clock_s / 60:.1f} min at {args.jobs} jobs ==")
    print(f"   logs    : sim/iq/corners/{runid}/")
    print(f"   results : sim/iq/results/{runid}/")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
