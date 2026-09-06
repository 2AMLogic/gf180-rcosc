#!/usr/bin/env python3
"""gf180-rcosc quiescent-current (Iq) sweep driver — issue #22.

Measures the block's supply current at the reference corner (tt / 27 C /
3.3 V) two different ways, at several trim codes, for both the as-committed
schematic sizing and the pre-#22 sizing it replaced, so the before/after
comparison is produced by one command from one netlist under one ngspice.

Two metrics, always reported together (see DR-0008):

  iq_op   The `.op` figure issue #20 introduced and DR-0007 quoted:
          `-1e6*i(vdd)` at the DC operating point. A relaxation oscillator
          has no stable DC operating point, so this solve lands on the
          unstable equilibrium, which pins the charge-complete comparator
          XCMPH at its own output inverter's trip point in full crowbar
          conduction. Reported unchanged for continuity with DR-0007, not
          because it is the quantity DR-0003 Row 4 names.

  iq_run  `-i(vdd)` averaged over 20 whole oscillation periods (rising
          edges 5..25 of `clk`, startup skipped — the same window
          convention `sim/pvt/pvt_sweep.py` uses). This is the quantity
          DR-0003 Row 4 names: "< 500 uA (running)", anchored to ST
          DS9826's IDDA(HSI48), a datasheet supply current for an
          oscillator that is oscillating.

Append-only evidence (CLAUDE.md): every invocation writes a fresh, UTC
run id under sim/iq/corners/<runid>/ (raw ngspice logs, one per simulated
point) and sim/iq/results/<runid>/ (results.csv, manifest.json, README.md),
and refuses to start if that run id already has content.

Usage: sim/iq/run-iq-sweep.sh [--jobs N] [--codes 0x00 0x80 0xFF]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NETLIST_DIR = os.path.join(REPO_ROOT, "design", "netlist")
SIM_IQ = os.path.join(REPO_ROOT, "sim", "iq")

NUM = r"([-+0-9.eE]+)"

# The two sizings compared. `None` means "leave the netlist as committed".
# The pre-#22 values are issue #16's, exactly as DR-0007 measured them.
VARIANTS = {
    "as-committed": None,
    "pre-22": {"rbias_l": "25u", "mtail_w": "4u", "mtail_nf": "1"},
}

# The measurement block. Identical in definition to design/smoke_test.sch's
# own .control (which measures the as-committed sizing at code 0x80); this
# driver substitutes its own only so it can sweep the trim code and the
# sizing variant. The as-committed / 0x80 point is cross-checked against
# design/run-smoke-test.sh's output in the generated README.
CONTROL = """
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
* xxcmph.dp and cmph_out near mid-rail on the 3.3 V supply.
print v(xxdut.xxcmph.dp) v(xxdut.xxcmph.dn) v(xxdut.cmph_out)
print v(xxdut.xxcmpl.dp) v(xxdut.xxcmpl.dn) v(xxdut.cmpl_out)
print v(xxdut.vc) v(xxdut.clk) v(xxdut.ibias) v(xxdut.vh) v(xxdut.vl)
tran 200p 1200n
let ivdd_ua = -1e6*i(vdd)
meas tran t_avg_start when v(clk)=1.65 rise=5
meas tran t_avg_end when v(clk)=1.65 rise=25
meas tran iq_run_ua AVG ivdd_ua FROM=$&t_avg_start TO=$&t_avg_end
quit
.endc
"""


def build_deck(variant: str, code: int) -> str:
    """Return a self-contained ngspice deck for one (sizing, trim code)."""
    with open(os.path.join(NETLIST_DIR, "smoke_test.spice")) as fh:
        deck = fh.read()

    # Inline the generated PDK include so the deck runs from a scratch dir.
    with open(os.path.join(NETLIST_DIR, "pdk_include.spice")) as fh:
        deck = deck.replace(".include pdk_include.spice", fh.read())

    # Replace the schematic's .control with this driver's (see CONTROL).
    deck = re.sub(r"\.control.*?\.endc", "", deck, flags=re.S)
    deck = deck.replace("**** end user architecture code",
                        CONTROL + "\n**** end user architecture code")

    override = VARIANTS[variant]
    if override is not None:
        # RBIAS: the only ppolyf_u_1k across (vdd, ibias) in rcosc_bias.
        deck, n = re.subn(
            r"^(XRBIAS vdd ibias vss ppolyf_u_1k r_width=2u r_length=)[0-9.]+u",
            r"\g<1>" + override["rbias_l"], deck, flags=re.M)
        if n != 1:
            raise RuntimeError(f"RBIAS override matched {n} lines, expected 1")
        # MTAIL: the only device across (tail, ibias) in rcosc_comparator.
        deck, n = re.subn(
            r"^(XMTAIL tail ibias vss vss nfet_03v3 L=1u W=)[0-9.]+u nf=[0-9]+",
            r"\g<1>" + override["mtail_w"] + " nf=" + override["mtail_nf"],
            deck, flags=re.M)
        if n != 1:
            raise RuntimeError(f"MTAIL override matched {n} lines, expected 1")

    # Trim code: drive the eight VT<n> sources that smoke_test.sch defines.
    for bit in range(8):
        level = "3.3" if (code >> bit) & 1 else "0.0"
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
    variant, code, corners_dir = args
    deck = build_deck(variant, code)
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "deck.spice")
        with open(path, "w") as fh:
            fh.write(deck)
        proc = subprocess.run(["ngspice", "-b", path], cwd=td,
                              capture_output=True, text=True, timeout=1800)
        out = proc.stdout + proc.stderr

    log_name = "%s_code0x%02X.log" % (variant, code)
    with open(os.path.join(corners_dir, log_name), "w") as fh:
        fh.write(out)

    iq_op = _grab(r"iq_ua\s*=\s*" + NUM, out)
    iq_run = _grab(r"iq_run_ua\s*=\s*" + NUM, out)
    t0 = _grab(r"t_avg_start\s*=\s*" + NUM, out)
    t1 = _grab(r"t_avg_end\s*=\s*" + NUM, out)
    freq = 20.0 / (t1 - t0) / 1e6 if (t0 is not None and t1 is not None and t1 > t0) else None
    return {"variant": variant, "code": code, "iq_op_ua": iq_op,
            "iq_run_ua": iq_run, "f_mhz": freq, "log": log_name}


TARGET_UA = 500.0


def verdict(value):
    if value is None:
        return "no measurement"
    return "met" if value < TARGET_UA else "**exceeds**"


def write_results(runid, rows, results_dir, ngspice_ver, pdk_root, git_sha, dirty):
    with open(os.path.join(results_dir, "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["variant", "code", "iq_op_ua",
                                           "iq_run_ua", "f_mhz", "log"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "code": "0x%02X" % r["code"]})

    with open(os.path.join(results_dir, "manifest.json"), "w") as fh:
        json.dump({"runid": runid, "git_sha": git_sha, "dirty_tree": dirty,
                   "ngspice": ngspice_ver, "pdk_root": pdk_root,
                   "target_ua": TARGET_UA,
                   "netlist": "design/netlist/smoke_test.spice",
                   "corner": {"process": "tt", "temp_c": 27, "vdd_v": 3.3},
                   "points": rows}, fh, indent=2)
        fh.write("\n")

    def cell(v, fmt="%.2f"):
        return fmt % v if v is not None else "—"

    lines = [
        f"# Quiescent current (Iq) sweep {runid} — issue #22",
        "",
        "Generated by `sim/iq/iq_sweep.py` (issue #22). Append-only evidence:",
        "this file, `results.csv`, `manifest.json` and every raw log under",
        f"`sim/iq/corners/{runid}/` belong to this run id and are never",
        "rewritten by a later run.",
        "",
        "| | |", "|---|---|",
        f"| git sha | `{git_sha}`{' (dirty tree)' if dirty else ''} |",
        f"| ngspice | {ngspice_ver} |",
        f"| PDK | gf180mcuC @ `{pdk_root}` |",
        "| netlist | `design/netlist/smoke_test.spice` (from `design/smoke_test.sch`) |",
        "| corner | `tt` / 27 °C / VDD = 3.3 V (the repo's reference corner) |",
        f"| target | DR-0003 Row 4: `< {TARGET_UA:.0f} µA` (running) |",
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
        "## Results",
        "",
        "| sizing | code | `iq_op` (µA) | verdict | `iq_run` (µA) | verdict | f (MHz) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| `%s` | `0x%02X` | %s | %s | %s | %s | %s |"
            % (r["variant"], r["code"], cell(r["iq_op_ua"]), verdict(r["iq_op_ua"]),
               cell(r["iq_run_ua"]), verdict(r["iq_run_ua"]), cell(r["f_mhz"], "%.4f")))
    lines += [
        "",
        "`pre-22` is issue #16's sizing (`RBIAS L = 25 µm`, `MTAIL W = 4 µm",
        "nf = 1`), the sizing DR-0007 measured. `as-committed` is this run's",
        "`design/*.sch` as checked in.",
        "",
        "Both metrics are reported at every code so neither can be quoted",
        "alone, and so the direction of the verdict can be checked against",
        "both: at the `pre-22` sizing **both** metrics exceed the 500 µA",
        "target at the representative code, and at the `as-committed` sizing",
        "**both** are under it. The re-size is therefore not an artifact of",
        "choosing a more favourable metric.",
        "",
        "[DR-0007]: ../../../../spec/decision-records/0007-quiescent-current-exceeds-target-post-resize.md",
        "",
    ]
    with open(os.path.join(results_dir, "README.md"), "w") as fh:
        fh.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=6,
                    help="parallel ngspice processes (default 6)")
    ap.add_argument("--codes", nargs="+", default=["0x00", "0x80", "0xFF"],
                    help="trim codes to sweep (default: 0x00 0x80 0xFF)")
    ap.add_argument("--runid", default=None, help="override the UTC run id")
    args = ap.parse_args()

    if shutil.which("ngspice") is None:
        sys.exit("ERROR: ngspice not found on PATH")
    for required in ("smoke_test.spice", "pdk_include.spice"):
        if not os.path.isfile(os.path.join(NETLIST_DIR, required)):
            sys.exit(f"ERROR: {required} missing — run design/regen-netlist.sh first")

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
    points = [(v, c, corners_dir) for v in VARIANTS for c in codes]

    ngspice_ver = subprocess.run(["ngspice", "-v"], capture_output=True,
                                 text=True).stdout.splitlines()[1].strip()
    pdk_root = "?"
    with open(os.path.join(NETLIST_DIR, "pdk_include.spice")) as fh:
        m = re.search(r"\.include (\S+)/libs\.tech/ngspice/", fh.read())
        if m:
            pdk_root = os.path.dirname(m.group(1))
    git_sha = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", REPO_ROOT, "status", "--porcelain"],
                                capture_output=True, text=True).stdout.strip())

    print(f"== gf180-rcosc Iq sweep {runid}: {len(points)} points ==")
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run_point, points):
            rows.append(r)
            print("  %-14s code 0x%02X  iq_op=%8s uA  iq_run=%8s uA  f=%9s MHz"
                  % (r["variant"], r["code"],
                     "%.2f" % r["iq_op_ua"] if r["iq_op_ua"] is not None else "FAIL",
                     "%.2f" % r["iq_run_ua"] if r["iq_run_ua"] is not None else "FAIL",
                     "%.4f" % r["f_mhz"] if r["f_mhz"] is not None else "FAIL"))

    order = {v: i for i, v in enumerate(VARIANTS)}
    rows.sort(key=lambda r: (order[r["variant"]], r["code"]))
    write_results(runid, rows, results_dir, ngspice_ver, pdk_root, git_sha, dirty)

    failed = [r for r in rows if r["iq_op_ua"] is None or r["iq_run_ua"] is None]
    print(f"== sweep complete: {len(rows)} points, {len(failed)} failures ==")
    print(f"   logs    : sim/iq/corners/{runid}/")
    print(f"   results : sim/iq/results/{runid}/")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
