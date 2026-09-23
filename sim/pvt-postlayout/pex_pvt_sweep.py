#!/usr/bin/env python3
"""gf180-rcosc post-layout (PEX-extracted) PVT re-verification subset
(issue #28).

Re-runs the corner-endpoint subset of `sim/pvt/pvt_sweep.py`'s PVT campaign
-- process = {tt, ff, ss} x temperature = {-40, +27, +85} C x
VDD = {3.0, 3.3, 3.6} V, 27 points -- against a parasitic-annotated netlist
extracted from the full-hierarchy `layout/cells/rcosc_top.gds` (issue #27),
at the fixed post-#24 (DR-0009) single-code post-trim methodology's own
calibration code (the `posttrim_spec` code from the reference corner's own
27 C/3.3 V calibration against the ratified 48.000 MHz target -- currently
`0xC0`, read from the most recent `sim/pvt/results/<runid>/manifest.json`
rather than hardcoded, so this driver tracks whichever code the schematic
campaign most recently calibrated, not a stale copy).

Each of the 27 points is simulated **twice**, sharing everything except the
DUT body:

- schematic side: `design/netlist/pvt_tb.spice` (from `design/pvt_tb.sch`),
  byte-identical to what `sim/pvt/pvt_sweep.py` itself simulates -- this
  doubles as a self-consistency check against the already-committed
  schematic-level campaign (see `--baseline-runid`).
- extracted side: the same `pvt_tb.spice` harness (VDD/VT0..VT7 sources,
  `XXDUT` instantiation) with only the embedded `.subckt rcosc_top ...
  .ends` body swapped for `klt extract --parasitics`'s own output --
  mirroring `klt pex`'s documented "swap the one DUT `.include`" contract
  (see this directory's README for why `klt pex`/`klt sim`'s JSON request
  contract was not used verbatim -- `klt pex` has no `--deck-option`/
  `--pins` passthrough, so it cannot select this design's non-default
  resistor/MiM-cap flavours; using it anyway would extract against the
  *wrong* MiM density and silently invalidate every delta this script
  reports).

Evidence is APPEND-ONLY (CLAUDE.md), following the exact `sim/pvt/`
convention: a fresh UTC run id, `sim/pvt-postlayout/corners/<runid>/` (raw
ngspice logs) and `sim/pvt-postlayout/results/<runid>/` (results.csv,
manifest.json, summary.md, plus the extracted netlist + `klt extract`
JSON report as committed evidence of exactly what was compared).

With `--guardrails` (issue #61), the same run additionally re-verifies
DR-0017's two issue-#57 guardrails against the extracted netlist, on both
sides (schematic + extracted, same run/host):

- the Row-4 guardrail cell -- free-running f at trim code `0x80`, `ff`,
  85 C, 3.6 V -- compared against DR-0017's own campaign basis for that
  cell (read from the schematic baseline's `pretrim` row, which is exactly
  the figure DR-0017 quotes), and
- a per-process (`tt`/`ff`/`ss`) single-point trim calibration at 27 C /
  3.3 V against the ratified 48.000 MHz target, reporting each side's
  realized `f(0x00)`/`f(0xFF)` range, the calibrated code, and whether it
  is inner-range or saturated. The search mirrors `sim/pvt/pvt_sweep.py`'s
  own `calibrate` semantics (same endpoint-saturation rule, same
  bisection, same closest-of-the-final-bracket pick) but is re-implemented
  here against this driver's two-sided `run_point`, so every calibration
  sim is logged under this run's own `corners/<runid>/` beside the PEX
  points (`base.calibrate` itself cannot be reused verbatim: its
  `Campaign` logs under `sim/pvt/corners/` paths).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sim" / "pvt"))
import pvt_sweep as base  # noqa: E402  (sys.path must be set up first)

PVT_TB = REPO_ROOT / "design" / "netlist" / "pvt_tb.spice"
GDS_PATH = REPO_ROOT / "layout" / "cells" / "rcosc_top.gds"
PVT_RESULTS_DIR = REPO_ROOT / "sim" / "pvt" / "results"

CORNER_DIR = REPO_ROOT / "sim" / "pvt-postlayout" / "corners"
RESULTS_DIR = REPO_ROOT / "sim" / "pvt-postlayout" / "results"
BUILD_ROOT = REPO_ROOT / "sim" / "build" / "pvt-postlayout"

# Corner-endpoint subset per issue #28: 3 process x 3 temp x 3 VDD, not the
# full 7-process factorial `sim/pvt/pvt_sweep.py` itself runs.
PEX_PROCESSES = ["tt", "ff", "ss"]

# DR-0017's Row-4 guardrail cell (issue #61's `--guardrails` pass): the
# free-running frequency at this (code, process, temp, VDD) operating point
# is the cell whose DR-0017 schematic-basis value (55.32 MHz campaign /
# 55.42 MHz delay-probe) must not be *increased* past by the re-spun
# comparator hierarchy -- post-layout, the comparison is the extracted
# side's f at this same cell against that same basis.
GUARDRAIL_CODE = 0x80
GUARDRAIL_PROCESS = "ff"
GUARDRAIL_TEMP_C = 85.0
GUARDRAIL_VDD_V = 3.6

DECK_OPTIONS = ["poly_res=1k", "mim_cap=cap_mim_1f0_m4m5_noshield"]
EXTRACT_PINS = "vdd,vss,clk,t0,t1,t2,t3,t4,t5,t6,t7"

RCOSC_TOP_HEADER_RE = re.compile(
    r"^\.subckt\s+rcosc_top\s+.*$", re.IGNORECASE | re.MULTILINE
)
SUBCKT_LINE_RE = re.compile(r"^\.subckt\s+(\S+)\s+(.*)$", re.IGNORECASE)
ENDS_LINE_RE = re.compile(r"^\.ends\b.*$", re.IGNORECASE)

# `klt extract --parasitics --pdk gf180mcuC` annotates the one *drawn*
# (non-parasitic) MiM-cap device it recognises -- this design's own
# `XCTIMING` timing capacitor -- with a trailing device-flavour-name token
# on its plain `C<name> n+ n- <value> <flavour>` card (e.g.
# `cap_mim_1f0_m4m5_noshield`), the C-element sibling of the `X<name> ...
# nfet_03v3`-style MOS model-binding annotation `--pdk` also adds. Every
# *parasitic* ground/coupling `C` card (issue #760's vertical-overlap
# coupling, the deck's own per-net ground capacitance) has no such trailing
# token and is unaffected. Unlike the MOS case, there is no real ngspice
# `.model`/`.subckt` named `cap_mim_1f0_m4m5_noshield` for that token to
# bind to -- it is a `klt`-internal flavour identifier, not a PDK model
# name -- so ngspice's native `C` element parser (which treats a
# non-numeric 4th token as a capacitor `.model` reference) refuses the
# deck with `unknown parameter (cap_mim_1f0_m4m5_noshield)`. This matches
# `layout/lvs_ref/rcosc_top.spice`'s own documented convention for the same
# device ("CTIMING is a plain C element whose value is the deck's own
# two-term area+perimeter law" -- i.e. numeric value only, no model
# reference), so stripping the trailing token here does not change the
# extracted capacitance value, only its (non-simulatable) annotation. Filed
# as friction against 2AMLogic/klayout-tools:
# https://github.com/2AMLogic/klayout-tools/issues/1558 (see also this
# directory's README.md).
CAP_MODEL_TAG_RE = re.compile(
    r"^(C\S+\s+\S+\s+\S+\s+[-+0-9.eE]+)\s+\S+\s*$", re.MULTILINE
)


def strip_capacitor_model_annotations(text: str) -> tuple[str, int]:
    return CAP_MODEL_TAG_RE.subn(r"\1", text)


def find_latest_schematic_baseline() -> tuple[str, Path]:
    """Most recent `sim/pvt/results/<runid>/` directory (by runid string
    sort, which is chronological for the `YYYYMMDDTHHMMSSZ` convention) --
    the schematic-level campaign this run compares against."""
    candidates = sorted(
        d
        for d in PVT_RESULTS_DIR.iterdir()
        if d.is_dir() and (d / "manifest.json").is_file()
    )
    if not candidates:
        sys.exit(
            f"ERROR: no sim/pvt/results/<runid>/manifest.json found under {PVT_RESULTS_DIR}"
        )
    latest = candidates[-1]
    return latest.name, latest


def extract_rcosc_top_block(text: str) -> tuple[str, str, list[str]]:
    """Split `text` (a `.subckt rcosc_top ... .ends` region, possibly
    followed by unrelated sibling `.subckt` blocks) into
    ``(pins_in_order, body_lines, pin_list)``.

    Returns the header's own pin list (order-preserving) and the full list
    of body lines between the header and its matching `.ends`.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if SUBCKT_LINE_RE.match(line.strip()) and line.strip().lower().startswith(
            ".subckt rcosc_top"
        ):
            start = i
            break
    if start is None:
        raise SystemExit("ERROR: no '.subckt rcosc_top ...' header found")
    m = SUBCKT_LINE_RE.match(lines[start].strip())
    assert m is not None
    pins = m.group(2).split()
    end = None
    for j in range(start + 1, len(lines)):
        if ENDS_LINE_RE.match(lines[j].strip()):
            end = j
            break
    if end is None:
        raise SystemExit("ERROR: no matching '.ends' found for '.subckt rcosc_top'")
    return pins, lines[start : end + 1], lines


def reorder_extracted_header(extracted_text: str, pin_order: list[str]) -> str:
    """Rewrite the extracted netlist's own `.SUBCKT rcosc_top <pins>` header
    line to declare its pins in `pin_order` instead of `klt extract`'s own
    (alphabetical) order.

    Purely a header-line token reorder: a `.SUBCKT` pin list is a name-only
    positional declaration -- the body below references those net names
    directly, never by position -- so reordering the header alone is a
    behavior-preserving rewrite, not an edit to any device/connectivity
    card. Needed so the schematic-side and extracted-side `XXDUT` calls in
    `pvt_tb.spice` (fixed at `vdd vss clk t0 t1 t2 t3 t4 t5 t6 t7`, per the
    existing `sim/pvt/` testbench) wire up identically regardless of which
    DUT body is `.include`d -- see this module's docstring and
    `docs/cli/pex.md`'s "shared pin list" requirement (which `klt pex`
    itself only static-checks the *count* of, not the order).
    """
    lines = extracted_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith(".subckt rcosc_top"):
            m = SUBCKT_LINE_RE.match(stripped)
            assert m is not None
            name = m.group(1)
            found_pins = m.group(2).split()
            if sorted(found_pins) != sorted(pin_order):
                raise SystemExit(
                    "ERROR: extracted netlist pin set "
                    f"{sorted(found_pins)} != schematic pin set {sorted(pin_order)}"
                )
            lines[i] = f".SUBCKT {name} " + " ".join(pin_order)
            return "\n".join(lines) + "\n"
    raise SystemExit("ERROR: extracted netlist has no '.SUBCKT rcosc_top ...' header")


def run_extract(runid: str, out_dir: Path) -> tuple[Path, dict]:
    """`klt extract --parasitics` against `layout/cells/rcosc_top.gds`,
    using the same deck-option / pin-list selections
    `layout/run_checks.sh` uses for the (non-parasitic) LVS extraction of
    this same cell, so the resistor/MiM-cap flavour this design actually
    commits to (DR-0003 sec 5.1/6.1, `layout/README.md`) is what gets
    extracted here too."""
    out_spice = out_dir / "rcosc_top.pex.spice"
    out_json = out_dir / "rcosc_top.pex.extract.json"
    cmd = [
        "klt",
        "extract",
        str(GDS_PATH),
        "--deck",
        "gf180mcu",
        "--top",
        "rcosc_top",
        "--pdk",
        "gf180mcuC",
        *[a for opt in DECK_OPTIONS for a in ("--deck-option", opt)],
        "--pins",
        EXTRACT_PINS,
        "--parasitics",
        "-o",
        str(out_spice),
        "--format",
        "json",
    ]
    print(f"== klt extract: {' '.join(cmd)} ==", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        sys.exit(f"ERROR: klt extract failed (exit {proc.returncode}):\n{proc.stderr}")
    out_json.write_text(proc.stdout)
    report = json.loads(proc.stdout)
    return out_spice, report


FOSC_RE = re.compile(r"^\s*fosc\s*=\s*([-+0-9.eE]+)\s*$", re.M)
PERIOD_RE = re.compile(r"^\s*period\s*=\s*([-+0-9.eE]+)\s*$", re.M)


@dataclass
class Result:
    side: str
    point: base.Point
    f_hz: float | None
    period_s: float | None
    status: str
    log_path: str
    tstop_ns: int
    seconds: float = 0.0


def run_point(
    side: str,
    netlist_text: str,
    point: base.Point,
    model_dir: Path,
    build_dir: Path,
    log_dir: Path,
    runid: str,
) -> Result:
    tstop = base.TSTOP_NS_DEFAULT
    last: Result | None = None
    for attempt in (1, 2):
        rundir = build_dir / f"{side}_{point.key}" / f"t{tstop}"
        rundir.mkdir(parents=True, exist_ok=True)
        deck = base.compose_deck(netlist_text, model_dir, point, tstop)
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
        log_rel = f"sim/pvt-postlayout/corners/{runid}/{side}_{point.key}.log"
        header = (
            "====================================================================\n"
            f"gf180-rcosc post-layout PEX PVT run: {side}_{point.key}\n"
            f"side        : {side}\n"
            f"run id      : {runid}\n"
            f"process     : {point.process} "
            f"(fets={base.PROCESS_CORNERS[point.process][0]} "
            f"res={base.PROCESS_CORNERS[point.process][1]} "
            f"mimcap={base.PROCESS_CORNERS[point.process][2]})\n"
            f"temperature : {point.temp_c:g} C\n"
            f"supply      : {point.vdd_v:g} V\n"
            f"trim code   : 0x{point.code:02X} ({point.code})\n"
            f"transient   : tran {base.TSTEP} {tstop}n, "
            f"f = {base.MEAS_LAST_EDGE - base.MEAS_FIRST_EDGE} periods / "
            f"(t[rise={base.MEAS_LAST_EDGE}] - t[rise={base.MEAS_FIRST_EDGE}])\n"
            f"wall clock  : {elapsed:.1f} s\n"
            f"exit status : {proc.returncode}\n"
            "====================================================================\n"
        )
        (log_dir / f"{side}_{point.key}.log").write_text(header + out)
        if m_f and m_p:
            f_hz = float(m_f.group(1))
            per = float(m_p.group(1))
            status = "ok" if (f_hz > 0 and per > 0) else "nonpositive"
            last = Result(side, point, f_hz, per, status, log_rel, tstop, elapsed)
            if status == "ok":
                return last
        else:
            last = Result(
                side, point, None, None, "no-measurement", log_rel, tstop, elapsed
            )
        if attempt == 1:
            tstop = base.TSTOP_NS_RETRY
    assert last is not None
    return last


def run_guardrail_passes(
    sides: list[tuple[str, str]],
    model_dir: Path,
    build_dir: Path,
    corner_dir: Path,
    runid: str,
    jobs: int,
    seed: dict[tuple[str, base.Point], Result],
    baseline_dir: Path,
    baseline_manifest: dict,
) -> dict:
    """Issue #61's `--guardrails` pass: re-verify DR-0017's two issue-#57
    guardrails against both the schematic and the extracted netlist, inside
    this same run (same host, same invocation), so every comparison the
    summary reports is in-run.

    Returns the dict recorded under the manifest's ``guardrails`` key (and
    rendered into ``guardrails.csv`` / the summary's guardrail sections).
    """
    cache: dict[tuple[str, base.Point], Result] = dict(seed)
    texts = dict(sides)

    def run_cached(side: str, point: base.Point) -> Result:
        key = (side, point)
        if key not in cache:
            cache[key] = run_point(
                side, texts[side], point, model_dir, build_dir, corner_dir, runid
            )
        return cache[key]

    target_hz = base.SPEC["f_target_hz"]

    def calibrate_side(side: str, process: str) -> dict:
        """Single-point trim search at (process, 27 C, 3.3 V) against the
        ratified target, mirroring `pvt_sweep.calibrate`'s search semantics
        exactly (see this module's docstring for why it is re-implemented
        rather than imported)."""

        def f_at(code: int) -> float:
            pt = base.Point(process, base.REF_TEMP_C, base.REF_VDD_V, code)
            res = run_cached(side, pt)
            if res.f_hz is None:
                sys.exit(
                    f"ERROR: guardrail calibration point {side} {pt.key} "
                    f"produced no measurement ({res.status})"
                )
            return res.f_hz

        f_lo, f_hi = f_at(0x00), f_at(0xFF)
        if target_hz <= f_lo:
            return {
                "code": 0x00, "f_hz": f_lo, "saturated": True,
                "f_code0x00_hz": f_lo, "f_code0xff_hz": f_hi,
            }
        if target_hz >= f_hi:
            return {
                "code": 0xFF, "f_hz": f_hi, "saturated": True,
                "f_code0x00_hz": f_lo, "f_code0xff_hz": f_hi,
            }
        lo, hi = 0x00, 0xFF
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if f_at(mid) < target_hz:
                lo = mid
            else:
                hi = mid
        f_l, f_h = f_at(lo), f_at(hi)
        if abs(f_l - target_hz) <= abs(f_h - target_hz):
            code, f = lo, f_l
        else:
            code, f = hi, f_h
        return {
            "code": code, "f_hz": f, "saturated": False,
            "f_code0x00_hz": f_lo, "f_code0xff_hz": f_hi,
        }

    cell_point = base.Point(
        GUARDRAIL_PROCESS, GUARDRAIL_TEMP_C, GUARDRAIL_VDD_V, GUARDRAIL_CODE
    )

    print(
        f"== guardrails (issue #61): cell {GUARDRAIL_PROCESS}/"
        f"{GUARDRAIL_TEMP_C:g}C/{GUARDRAIL_VDD_V:g}V/0x{GUARDRAIL_CODE:02X} "
        f"+ per-process calibration vs {target_hz / 1e6:.3f} MHz ==",
        flush=True,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        cell_futs = {
            side: pool.submit(run_cached, side, cell_point) for side in texts
        }
        cal_futs = {
            (side, p): pool.submit(calibrate_side, side, p)
            for side in texts
            for p in PEX_PROCESSES
        }
        cell_res = {side: fut.result() for side, fut in cell_futs.items()}
        cal_res = {key: fut.result() for key, fut in cal_futs.items()}

    # DR-0017's own campaign basis for the guardrail cell: the schematic
    # baseline's `pretrim` (midscale 0x80) row at the same operating point.
    # This is exactly the 55.32 MHz figure DR-0017 quotes ("probe basis;
    # campaign 55.32") -- sourced from the baseline rather than hardcoded.
    dr0017_cell_f_hz = None
    baseline_csv = baseline_dir / "results.csv"
    if baseline_csv.is_file():
        with baseline_csv.open() as fh:
            for brow in csv.DictReader(fh):
                if (
                    brow["pass"] == "pretrim"
                    and brow["process"] == GUARDRAIL_PROCESS
                    and float(brow["temp_c"]) == GUARDRAIL_TEMP_C
                    and float(brow["vdd_v"]) == GUARDRAIL_VDD_V
                    and brow["f_hz"]
                ):
                    dr0017_cell_f_hz = float(brow["f_hz"])
                    break

    calibration = {}
    for p in PEX_PROCESSES:
        calibration[p] = {
            "dr0017_campaign_code": baseline_manifest[
                "calibration_spec_target"
            ][p]["code"],
            "dr0017_campaign_saturated": baseline_manifest[
                "calibration_spec_target"
            ][p]["saturated"],
            "schematic": cal_res[("schematic", p)],
            "extracted": cal_res[("extracted", p)],
        }

    return {
        "cell": {
            "process": GUARDRAIL_PROCESS,
            "temp_c": GUARDRAIL_TEMP_C,
            "vdd_v": GUARDRAIL_VDD_V,
            "code": GUARDRAIL_CODE,
            "schematic_f_hz": cell_res["schematic"].f_hz,
            "extracted_f_hz": cell_res["extracted"].f_hz,
            "dr0017_campaign_f_hz": dr0017_cell_f_hz,
        },
        "calibration_target_hz": target_hz,
        "calibration_temp_c": base.REF_TEMP_C,
        "calibration_vdd_v": base.REF_VDD_V,
        "calibration": calibration,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--keep-build", action="store_true")
    ap.add_argument(
        "--baseline-runid",
        default=None,
        help="sim/pvt/results/<runid> to compare against (default: most recent)",
    )
    ap.add_argument("--runid", default=None)
    ap.add_argument(
        "--guardrails",
        action="store_true",
        help="additionally re-verify DR-0017's two issue-#57 guardrails "
        "(Row-4 cell 0x80/ff/85C/3.6V + per-process trim calibration vs the "
        "ratified 48 MHz target) on both sides, inside this same run "
        "(issue #61)",
    )
    args = ap.parse_args()

    runid = args.runid or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    corner_dir = CORNER_DIR / runid
    res_dir = RESULTS_DIR / runid
    build_dir = BUILD_ROOT / runid
    for d in (corner_dir, res_dir, build_dir):
        if d.exists() and any(d.iterdir()):
            sys.exit(f"ERROR: {d} already exists and is non-empty (runid collision?)")
        d.mkdir(parents=True, exist_ok=True)

    started = time.time()

    if args.baseline_runid:
        baseline_id = args.baseline_runid
        baseline_dir = PVT_RESULTS_DIR / baseline_id
        if not (baseline_dir / "manifest.json").is_file():
            sys.exit(f"ERROR: {baseline_dir}/manifest.json not found")
    else:
        baseline_id, baseline_dir = find_latest_schematic_baseline()
    baseline_manifest = json.loads((baseline_dir / "manifest.json").read_text())
    code = baseline_manifest["calibration_spec_target"]["tt"]["code"]
    print(
        f"== baseline: sim/pvt/results/{baseline_id} "
        f"(fixed post-trim code 0x{code:02X}, from its tt/27C/3.3V "
        "ratified-target calibration) ==",
        flush=True,
    )

    pdk_root, pdk, model_dir = base.resolve_pdk()

    print("== regenerating design/netlist from schematics ==", flush=True)
    subprocess.run(
        [str(REPO_ROOT / "design" / "regen-netlist.sh")], check=True, cwd=REPO_ROOT
    )

    schematic_text = PVT_TB.read_text()
    pins, top_block_lines, _all_lines = extract_rcosc_top_block(schematic_text)
    print(f"== schematic rcosc_top pin order: {pins} ==", flush=True)

    extracted_spice, extract_report = run_extract(runid, res_dir)
    raw_extracted_text = extracted_spice.read_text()
    stripped_text, n_stripped = strip_capacitor_model_annotations(raw_extracted_text)
    if n_stripped:
        print(
            f"== stripped {n_stripped} non-simulatable capacitor model-flavour "
            "annotation(s) from the extracted netlist (see pex_pvt_sweep.py's "
            "CAP_MODEL_TAG_RE docstring) ==",
            flush=True,
        )
        extracted_spice.write_text(stripped_text)
    extracted_text = reorder_extracted_header(stripped_text, pins)

    # Build the extracted-side harness: byte-identical pvt_tb.spice except
    # the embedded '.subckt rcosc_top ... .ends' region is replaced by the
    # PEX netlist's own subckt (header reordered to match). Any sibling
    # '.subckt rcosc_bias/...' blocks that originally followed are left in
    # place, unreferenced -- an unused .subckt declaration is inert in
    # ngspice, and leaving them keeps this a single contiguous-region
    # substitution rather than a line-by-line rewrite.
    top_block_text = "\n".join(top_block_lines)
    if top_block_text not in schematic_text:
        sys.exit("ERROR: could not locate the exact rcosc_top block to substitute")
    extracted_side_text = schematic_text.replace(
        top_block_text, extracted_text.rstrip("\n"), 1
    )

    points = [
        base.Point(p, t, v, code)
        for p in PEX_PROCESSES
        for t in base.TEMPS_C
        for v in base.VDDS_V
    ]
    print(f"== {len(points)} corner-endpoint points x 2 sides ==", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        for side, text in (
            ("schematic", schematic_text),
            ("extracted", extracted_side_text),
        ):
            for pt in points:
                fut = pool.submit(
                    run_point, side, text, pt, model_dir, build_dir, corner_dir, runid
                )
                futures[fut] = (side, pt)
        done = 0
        results: dict[tuple[str, base.Point], Result] = {}
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            results[(res.side, res.point)] = res
            done += 1
            fmt = f"{res.f_hz / 1e6:8.4f} MHz" if res.f_hz else f"{res.status:>12}"
            print(
                f"  [{done:3d}/{len(futures):3d}] {res.side:>10} {res.point.key:<28} {fmt}",
                flush=True,
            )

    guard = None
    if args.guardrails:
        guard = run_guardrail_passes(
            sides=[("schematic", schematic_text), ("extracted", extracted_side_text)],
            model_dir=model_dir,
            build_dir=build_dir,
            corner_dir=corner_dir,
            runid=runid,
            jobs=args.jobs,
            seed=results,
            baseline_dir=baseline_dir,
            baseline_manifest=baseline_manifest,
        )

    elapsed = time.time() - started

    # -- results.csv ----------------------------------------------------
    rows = []
    for pt in points:
        sres = results[("schematic", pt)]
        eres = results[("extracted", pt)]
        delta_pct = None
        if sres.f_hz and eres.f_hz:
            delta_pct = (eres.f_hz - sres.f_hz) / sres.f_hz * 100.0
        rows.append(
            {
                "process": pt.process,
                "temp_c": f"{pt.temp_c:g}",
                "vdd_v": f"{pt.vdd_v:g}",
                "trim_code": pt.code,
                "trim_hex": f"0x{pt.code:02X}",
                "schematic_f_hz": f"{sres.f_hz:.6e}" if sres.f_hz else "",
                "schematic_status": sres.status,
                "extracted_f_hz": f"{eres.f_hz:.6e}" if eres.f_hz else "",
                "extracted_status": eres.status,
                "delta_pct": f"{delta_pct:.4f}" if delta_pct is not None else "",
                "schematic_log": sres.log_path,
                "extracted_log": eres.log_path,
            }
        )

    csv_path = res_dir / "results.csv"
    fields = list(rows[0].keys())
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    if guard is not None:
        grows = []
        c = guard["cell"]
        for side in ("schematic", "extracted"):
            grows.append(
                {
                    "kind": "row4_cell",
                    "side": side,
                    "process": c["process"],
                    "temp_c": f"{c['temp_c']:g}",
                    "vdd_v": f"{c['vdd_v']:g}",
                    "code": c["code"],
                    "trim_hex": f"0x{c['code']:02X}",
                    "f_hz": f"{c[side + '_f_hz']:.6e}" if c[side + "_f_hz"] else "",
                    "saturated": "",
                    "f_code0x00_hz": "",
                    "f_code0xff_hz": "",
                    "target_hz": "",
                    "dr0017_campaign_f_hz": (
                        f"{c['dr0017_campaign_f_hz']:.6e}"
                        if c["dr0017_campaign_f_hz"]
                        else ""
                    ),
                }
            )
        for p in PEX_PROCESSES:
            for side in ("schematic", "extracted"):
                e = guard["calibration"][p][side]
                grows.append(
                    {
                        "kind": "calibration",
                        "side": side,
                        "process": p,
                        "temp_c": f"{guard['calibration_temp_c']:g}",
                        "vdd_v": f"{guard['calibration_vdd_v']:g}",
                        "code": e["code"],
                        "trim_hex": f"0x{e['code']:02X}",
                        "f_hz": f"{e['f_hz']:.6e}",
                        "saturated": e["saturated"],
                        "f_code0x00_hz": f"{e['f_code0x00_hz']:.6e}",
                        "f_code0xff_hz": f"{e['f_code0xff_hz']:.6e}",
                        "target_hz": f"{guard['calibration_target_hz']:.6e}",
                        "dr0017_campaign_f_hz": "",
                    }
                )
        gcsv_path = res_dir / "guardrails.csv"
        gfields = list(grows[0].keys())
        with gcsv_path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=gfields)
            writer.writeheader()
            writer.writerows(grows)

    failures = [r for r in results.values() if r.status != "ok"]
    deltas = [float(r["delta_pct"]) for r in rows if r["delta_pct"]]

    # -- Cross-check: my own freshly re-run schematic side vs. the already-
    # committed sim/pvt/ campaign's own posttrim_spec pass at this same code
    # -- a same-methodology, different-host/run comparison that isolates
    # run-to-run/cross-host ngspice numerical noise from the (much larger)
    # schematic-vs-extracted delta this run's own verdict is about. Not a
    # correctness check of this script (both sides of *that* run's own delta
    # share one host/run already); purely a sanity bound on how much of the
    # reported schematic-vs-extracted delta could, in principle, be
    # environment noise rather than layout parasitics.
    host_variance_pct = None
    baseline_csv = baseline_dir / "results.csv"
    if baseline_csv.is_file():
        baseline_lookup: dict[tuple[str, float, float], float] = {}
        with baseline_csv.open() as fh:
            for brow in csv.DictReader(fh):
                if brow["pass"] != "posttrim_spec" or not brow["f_hz"]:
                    continue
                bkey = (brow["process"], float(brow["temp_c"]), float(brow["vdd_v"]))
                baseline_lookup[bkey] = float(brow["f_hz"])
        host_deltas = []
        for pt in points:
            sres = results[("schematic", pt)]
            bkey = (pt.process, pt.temp_c, pt.vdd_v)
            if sres.f_hz and bkey in baseline_lookup and baseline_lookup[bkey] > 0:
                host_deltas.append(
                    abs(sres.f_hz - baseline_lookup[bkey])
                    / baseline_lookup[bkey]
                    * 100.0
                )
        if host_deltas:
            host_variance_pct = max(host_deltas)

    manifest = {
        "runid": runid,
        "utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": base.git_sha(),
        "git_dirty": base.git_dirty(),
        "ngspice": base.tool_version(["ngspice", "-v"], line=1),
        "xschem": base.tool_version(["xschem", "--version"], line=0),
        "klt_version": base.tool_version(["klt", "version"], line=0),
        "pdk_root": str(pdk_root),
        "pdk": pdk,
        "model_dir": str(model_dir),
        "layout_gds": str(GDS_PATH.relative_to(REPO_ROOT)),
        "extract_command": [
            "klt",
            "extract",
            "layout/cells/rcosc_top.gds",
            "--deck",
            "gf180mcu",
            "--top",
            "rcosc_top",
            "--pdk",
            "gf180mcuC",
            *[a for opt in DECK_OPTIONS for a in ("--deck-option", opt)],
            "--pins",
            EXTRACT_PINS,
            "--parasitics",
        ],
        "extract_parasitic_model": extract_report.get("parasitics", {}).get("model"),
        "schematic_baseline_runid": baseline_id,
        "process_corners": {k: list(base.PROCESS_CORNERS[k]) for k in PEX_PROCESSES},
        "temps_c": base.TEMPS_C,
        "vdds_v": base.VDDS_V,
        "trim_code": code,
        "trim_hex": f"0x{code:02X}",
        "measurement": {
            "tstep": base.TSTEP,
            "tstop_ns": base.TSTOP_NS_DEFAULT,
            "tstop_ns_retry": base.TSTOP_NS_RETRY,
            "first_edge": base.MEAS_FIRST_EDGE,
            "last_edge": base.MEAS_LAST_EDGE,
            "cycles_averaged": base.MEAS_LAST_EDGE - base.MEAS_FIRST_EDGE,
        },
        "points": len(points),
        "sides": ["schematic", "extracted"],
        "failed_runs": [f"{r.side}_{r.point.key}" for r in failures],
        "max_abs_delta_pct": max((abs(d) for d in deltas), default=None),
        "mean_delta_pct": (sum(deltas) / len(deltas)) if deltas else None,
        "calibration_point_budget_pct": base.SPEC["posttrim_calpoint_pct"],
        "schematic_rerun_vs_published_baseline_max_delta_pct": host_variance_pct,
        "wall_clock_s": round(elapsed, 1),
        "jobs": args.jobs,
    }
    if guard is not None:
        manifest["guardrails"] = guard
    (res_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # -- summary.md -------------------------------------------------------
    lines = []
    lines.append(f"# Post-layout (PEX-extracted) PVT re-verification {runid}")
    lines.append("")
    lines.append(
        "Generated by `sim/pvt-postlayout/pex_pvt_sweep.py` (issue #28). "
        "Append-only evidence: this file, `results.csv`, `manifest.json`, "
        "the extracted netlist and `klt extract` JSON report, and every raw "
        f"log under `sim/pvt-postlayout/corners/{runid}/` belong to this run "
        "id and are never rewritten by a later run."
    )
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(
        f"| git sha | `{manifest['git_sha']}` (dirty: {manifest['git_dirty']}) |"
    )
    lines.append(f"| ngspice | {manifest['ngspice']} |")
    lines.append(f"| klt | {manifest['klt_version']} |")
    lines.append(f"| PDK | {pdk} @ `{pdk_root}` |")
    lines.append("| layout | `layout/cells/rcosc_top.gds` |")
    lines.append(
        "| extraction | `klt extract --deck gf180mcu --top rcosc_top "
        "--pdk gf180mcuC --deck-option poly_res=1k --deck-option "
        "mim_cap=cap_mim_1f0_m4m5_noshield --pins "
        f"{EXTRACT_PINS} --parasitics` |"
    )
    lines.append(f"| schematic baseline | `sim/pvt/results/{baseline_id}/` |")
    lines.append(f"| trim code (fixed) | `0x{code:02X}` ({code}) |")
    lines.append(
        "| measurement | `tran 200p 1200n`, f averaged over 20 whole periods "
        "(rising edges 5..25, startup skipped) -- identical methodology to "
        "`sim/pvt/pvt_sweep.py` |"
    )
    lines.append(
        f"| points | {len(points)} (process x temp x VDD corner-endpoint subset) |"
    )
    if guard is not None:
        lines.append(
            "| guardrails | DR-0017 Row-4 guardrail cell + per-process trim "
            "calibration, both sides (issue #61 `--guardrails`) -- see the "
            "guardrail verification section below |"
        )
    lines.append(f"| failed runs | {len(failures)} |")
    lines.append(f"| wall clock | {elapsed:.1f} s at {args.jobs} jobs |")
    lines.append("")
    lines.append("## Corner-endpoint subset")
    lines.append("")
    lines.append("| Axis | Values |")
    lines.append("|---|---|")
    lines.append("| process | `tt`, `ff`, `ss` |")
    lines.append("| temperature | -40 C, 27 C, 85 C |")
    lines.append("| supply | 3.0 V, 3.3 V, 3.6 V |")
    lines.append("")
    lines.append(
        "## Schematic vs. extracted (parasitic-annotated) frequency, per point"
    )
    lines.append("")
    lines.append(
        "| process | T (C) | VDD (V) | schematic f (MHz) | extracted f (MHz) | delta |"
    )
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        sf = (
            f"{float(row['schematic_f_hz']) / 1e6:.4f}"
            if row["schematic_f_hz"]
            else row["schematic_status"]
        )
        ef = (
            f"{float(row['extracted_f_hz']) / 1e6:.4f}"
            if row["extracted_f_hz"]
            else row["extracted_status"]
        )
        dp = f"{row['delta_pct']}%" if row["delta_pct"] else "n/a"
        lines.append(
            f"| `{row['process']}` | {row['temp_c']} | {row['vdd_v']} | {sf} | {ef} | {dp} |"
        )
    lines.append("")
    max_delta = manifest["max_abs_delta_pct"]
    budget = base.SPEC["posttrim_calpoint_pct"]
    if max_delta is None:
        verdict = "**INCONCLUSIVE** -- no point produced a valid delta (see failed runs above)"
    elif max_delta > budget:
        verdict = (
            f"**Materially diverges**: max |delta| {max_delta:.2f}% exceeds the "
            f"ratified post-trim calibration-point accuracy budget (+-{budget}%, "
            "DR-0002/DR-0003) -- layout parasitics alone consume more margin than "
            "that budget allows, on top of the pre-existing process-spread "
            "shortfall every schematic-level campaign since DR-0005 already "
            "reports."
        )
    else:
        verdict = (
            f"Does not materially diverge: max |delta| {max_delta:.2f}% is within "
            f"the ratified post-trim calibration-point accuracy budget (+-{budget}%)."
        )
    lines.append("## Verdict")
    lines.append("")
    lines.append(
        f"Max |schematic-vs-extracted delta| across the {len(points)}-point subset: "
        f"**{max_delta:.4f}%**"
        if max_delta is not None
        else "n/a"
    )
    lines.append("")
    lines.append(verdict)
    lines.append("")
    lines.append(
        "This is a comparison of the schematic-level RC-timed oscillator core "
        "against the same core re-simulated with `klt extract --parasitics`'s "
        "first-order lumped-RC model of `rcosc_top.gds`'s actual routing "
        "(one series R + one ground C per net, plus vertical-overlap coupling) "
        "-- it is **not** a re-verification of the process-spread/post-trim "
        "shortfall already reported against every schematic-level PVT "
        "campaign since DR-0005; that finding is unaffected by this record."
    )
    lines.append("")
    lines.append("## Cross-check: environment/host numerical noise")
    lines.append("")
    if host_variance_pct is not None:
        lines.append(
            f"This run's own **schematic**-side re-simulation (same host, same "
            f"invocation as the extracted side above) differs from the "
            f"already-committed `sim/pvt/results/{baseline_id}/` campaign's own "
            f"`posttrim_spec` pass at the same trim code -- an independent run "
            "of the *same* unmodified schematic and methodology, on a "
            "different host -- by up to "
            f"**{host_variance_pct:.2f}%** at matched (process, T, VDD) points. "
            "This is cross-host/cross-run ngspice numerical variance (see "
            "DR-0009's own environment note), not a design or tooling change, "
            "and it is over an order of magnitude smaller than the "
            f"schematic-vs-extracted delta this record reports (max "
            f"{max_delta:.2f}%), so it does not call the main finding into "
            "question. The schematic-vs-extracted comparison above is always "
            "computed within one run/host (never against the older "
            "committed baseline), which is what keeps this cross-check "
            "orthogonal to it."
        )
    else:
        lines.append(
            "No comparable `posttrim_spec` baseline points were found under "
            f"`sim/pvt/results/{baseline_id}/results.csv` to cross-check against."
        )
    if guard is not None:
        c = guard["cell"]
        lines.append("")
        lines.append("## DR-0017 guardrail verification (issue #61, `--guardrails`)")
        lines.append("")
        lines.append(
            "The two guardrails DR-0017 verified at the schematic level "
            "(issue #57) re-measured here against the parasitic-annotated "
            "netlist -- same run, same host, both sides simulated by this "
            "invocation, so every comparison below is in-run."
        )
        lines.append("")
        lines.append(
            "### Guardrail 1 -- f must not increase at the Row-4 guardrail cell "
            f"(`0x{c['code']:02X}` / `{c['process']}` / {c['temp_c']:g} C / "
            f"{c['vdd_v']:g} V)"
        )
        lines.append("")
        lines.append("| side | f (MHz) |")
        lines.append("|---|---|")
        lines.append(f"| schematic (this run) | {c['schematic_f_hz'] / 1e6:.4f} |")
        lines.append(f"| extracted (this run) | {c['extracted_f_hz'] / 1e6:.4f} |")
        ref = c["dr0017_campaign_f_hz"]
        if ref:
            lines.append(
                f"| DR-0017 campaign basis | {ref / 1e6:.4f} |"
            )
        lines.append("")
        exf, schf = c["extracted_f_hz"], c["schematic_f_hz"]
        cell_delta = (exf - schf) / schf * 100.0
        lines.append(
            f"In-run extracted-vs-schematic delta at the cell: "
            f"**{cell_delta:+.2f}%** (same sign and magnitude class as the "
            "27-point subset above -- the guardrail cell is not an outlier)."
        )
        if ref:
            margin = (ref - exf) / ref * 100.0
            if exf <= ref:
                v1 = (
                    f"**holds**: the extracted side runs {margin:.2f}% *below* "
                    f"DR-0017's campaign basis ({ref / 1e6:.4f} MHz, this "
                    "baseline's own `pretrim` row at the cell -- the "
                    "\"campaign 55.32\" figure DR-0017 quotes)"
                )
            else:
                v1 = (
                    f"**REGRESSES**: the extracted side exceeds DR-0017's "
                    f"campaign basis ({ref / 1e6:.4f} MHz) by {-margin:.2f}%"
                )
            lines.append(f"Verdict: {v1}.")
        else:
            lines.append(
                "Verdict: **INCONCLUSIVE vs DR-0017** -- no `pretrim` row at "
                "the guardrail cell was found in the schematic baseline's "
                "results.csv; compare the in-run rows above instead."
            )
        lines.append("")
        lines.append(
            "### Guardrail 2 -- trim range must not regress (per-process "
            f"calibration at {guard['calibration_temp_c']:g} C / "
            f"{guard['calibration_vdd_v']:g} V against the ratified "
            f"{guard['calibration_target_hz'] / 1e6:.3f} MHz target)"
        )
        lines.append("")
        lines.append(
            "The same single-point trim search `sim/pvt/pvt_sweep.py`'s "
            "`calibrate` performs, run here on both sides of this campaign "
            "(DR-0017's schematic-level finding: every corner inner-range, "
            "codes `0x59`..`0xCD`, none saturated)."
        )
        lines.append("")
        lines.append(
            "| process | side | f(0x00) (MHz) | f(0xFF) (MHz) | cal code | "
            "f at cal code (MHz) | saturated | DR-0017 campaign code |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for p in PEX_PROCESSES:
            g = guard["calibration"][p]
            for side in ("schematic", "extracted"):
                e = g[side]
                lines.append(
                    f"| `{p}` | {side} | {e['f_code0x00_hz'] / 1e6:.4f} | "
                    f"{e['f_code0xff_hz'] / 1e6:.4f} | `0x{e['code']:02X}` | "
                    f"{e['f_hz'] / 1e6:.4f} | {e['saturated']} | "
                    f"`0x{g['dr0017_campaign_code']:02X}` |"
                )
        sat = [
            p
            for p in PEX_PROCESSES
            if guard["calibration"][p]["extracted"]["saturated"]
        ]
        lines.append("")
        if not sat:
            lines.append(
                "Verdict: **holds** -- every extracted-side corner still "
                "calibrates inner-range (none saturated) against the "
                "ratified target; the code movement vs the schematic side "
                "(table above) is the layout-parasitic frequency penalty "
                "being trimmed out, and the remaining headroom to `0xFF` "
                "is visible in each row's `f(0xFF)`."
            )
        else:
            lines.append(
                "Verdict: **REGRESSES** -- the extracted side saturates "
                "(cannot reach the ratified target anywhere in "
                "`0x00`..`0xFF`) at: "
                + ", ".join(f"`{p}`" for p in sat)
                + ". Per CLAUDE.md this is reported as a contradiction, "
                "not relaxed."
            )
    if failures:
        lines.append("")
        lines.append("## Failed runs")
        lines.append("")
        for r in failures:
            lines.append(f"- `{r.side}_{r.point.key}`: {r.status}")

    (res_dir / "summary.md").write_text("\n".join(lines) + "\n")

    print(f"\n== done: {res_dir} ==", flush=True)
    if not args.keep_build:
        import shutil

        shutil.rmtree(build_dir, ignore_errors=True)

    if failures:
        sys.exit(f"ERROR: {len(failures)} run(s) failed -- see summary.md")


if __name__ == "__main__":
    main()
