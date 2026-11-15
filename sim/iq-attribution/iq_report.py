#!/usr/bin/env python3
"""Per-stage running-Iq attribution report for row 8 (issue #347).

Reads the `klt sim` batch envelopes (`request_*/report.json`) written for gen_stage_iq_requests.py
and tabulates, per corner cell: total `iq_run`, each stage's `iq_<stage>`, the sum of stages, and
the residue (total - sum) -- the residue is reported per cell, not bounded once.  The integration
window of every figure is stated (DR-0009 / DR-0044: 20 whole periods, clk rising edges 5 -> 25,
charge integrator); this campaign's figures are NOT comparable to item-5's fixed 200-1200 ns
window figures (e.g. 559.4 uA) and are labelled as such.

The timing MiM (`XCTIMING`) and the discharge device (`XMDISCH`) have no vdd terminal (the stage
map's zero-by-construction assertion proves it), so their stage current is exactly zero by
construction -- reported as zero, never as a measured near-zero.

Checks, all asserted here (the committed-assertion form of the Test Plan):
  - conservation: the committed stage map assigns every flat-extraction device exactly once;
  - back-to-back: the probed total `iq_run` at tt / 27 C / 3.3 V / 0xFF and ff / 85 C / 3.6 V /
    0xFF reproduces DR-0044's committed figures within B2B_TOL_FRAC;
  - sum: per-stage currents sum to the measured total within SUM_TOL_FRAC at every reported cell.

Usage: python3 -I iq_report.py RESULTS_DIR OUT_MD [--map ../stage_map.json] [--control]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_map  # noqa: E402
from dr0044_table import DR0044_IQ_UA  # noqa: E402

STAGES = list(stage_map.CURRENT_STAGES)
STAGE_LABELS = {"bias": "bias", "cmp_h": "comparator-H", "cmp_l": "comparator-L", "latch": "latch (+clk drive)",
                "trim": "trim bank"}
B2B_CELLS = [("0xFF", 3.3, "tt", 27.0), ("0xFF", 3.6, "ff", 85.0)]   # Test Plan item 1
B2B_TOL_FRAC = 0.01                                                  # vs DR-0044's committed total
SUM_TOL_FRAC = 0.01                                                  # sum of stages vs measured total
# DR-0044's committed control-set figures (sim/row45-rerun ...-iq-extracted-control-l1): the
# control run is compared against ITS OWN committed baseline, not the L 0.7 one
B2B_CONTROL_REF = {("0xFF", 3.6, "ff", 85.0): 779.4}
WINDOW = ("integration window: DR-0009 / DR-0044 `iq_run` basis -- 20 whole oscillation periods "
          "(clk rising edges 5 -> 25), supply charge integrated on 1 nF; not comparable to "
          "item-5's fixed 200-1200 ns window (its row-8 bench), which produced e.g. 559.4 uA "
          "at ff / 85 C / 3.6 V on a different netlist and basis")
OVER_LIMIT = 500.0


def load_envelopes(results: Path) -> dict:
    """{(code, vdd, proc, T): measurements dict} from request_*/report.json."""
    out = {}
    for rep in sorted(results.glob("request_*/report.json")):
        tag = rep.parent.name.split("_", 1)[1]           # cFF_v36
        code, vtag = tag.split("_")
        v = int(vtag[1:]) / 10
        code = "0x" + code[1:]
        for c in json.loads(rep.read_text())["corners"]:
            m = {x["name"]: x["value"] for x in c["measurements"]}
            if any(v is None for v in m.values()):
                continue                                  # a failed corner must not enter silently
            out[(code, v, c["process"], float(c["temperature_c"]))] = m
    return out


def cell_rows(m: dict) -> dict:
    stages = {s: m[f"iq_{s}"] * 1e6 for s in STAGES}
    total = m["iq_run"] * 1e6
    s = sum(stages.values())
    return {**stages, "total": total, "sum": s, "residue": total - s,
            "residue_pct": (total - s) / total * 100 if total else float("nan")}


def report(env: dict, map_path: Path, src: str, control: bool = False) -> tuple[list, dict]:
    m = json.loads(Path(map_path).read_text())
    stage_map.check_conservation(m)
    zero_stages = {s: [d["name"] for d in m["stages"][s]] for s in stage_map.ZERO_STAGES}
    assert all(not d["vdd_terms"] for s in zero_stages for d in m["stages"][s]), \
        "zero-by-construction stage has vdd-side terminals"

    ref_table = B2B_CONTROL_REF if control else DR0044_IQ_UA
    b2b_cells = [c for c in B2B_CELLS if c in ref_table] if control else B2B_CELLS
    L = [f"# Row 8 per-stage running-Iq attribution (issue #347) -- {src}", "",
         f"Source: `{src}`", "", WINDOW, "",
         "Zero by construction (no vdd terminal; the stage map asserts it): "
         + ", ".join(f"{s} ({', '.join(ds)})" for s, ds in zero_stages.items())
         + " -- these stages draw exactly 0 A of supply current; no measurement exists for them.", "",
         "## Back-to-back check (probed DUT total vs DR-0044's committed figure, same window)", "",
         "| cell | DR-0044 committed (uA) | this campaign probed total (uA) | delta | tolerance |", "|---|---|---|---|---|"]
    checks = {}
    for cell in b2b_cells:
        if cell not in env:
            checks[str(cell)] = "MISSING"
            L.append(f"| {cell} | {ref_table[cell]} | missing | | |")
            continue
        total = env[cell]["iq_run"] * 1e6
        ref = ref_table[cell]
        d = (total - ref) / ref
        ok = abs(d) <= B2B_TOL_FRAC
        checks[str(cell)] = "OK" if ok else "FAIL"
        L.append(f"| {cell[0]} / {cell[1]} V / {cell[2]} / {cell[3]:g} C | {ref:.1f} | {total:.1f} | {d * 100:+.2f} % | +/-{B2B_TOL_FRAC * 100:g} % |")

    L += ["", "## Per-cell attribution (uA)", "",
          "Window as stated above. `>500` marks the cells over the ratified limit among DR-0044's "
          "108-cell table (DR-0044's own figure quoted for reference; the campaign number is this "
          "campaign's probed total). Residue = total - sum(stages): where vdd-network parasitic "
          "displacement current and any unresolved terms land.", "",
          "| code | VDD | die | T (C) | " + " | ".join(STAGE_LABELS[s] for s in STAGES)
          + " | sum | total | residue (uA) | residue (%) | DR-0044 | |",
          "|---|" + "---|" * (len(STAGES) + 6)]
    fails = []
    for cell in sorted(env):
        r = cell_rows(env[cell])
        if abs(r["residue_pct"]) > SUM_TOL_FRAC * 100:
            fails.append((cell, r["residue_pct"]))
        dr = DR0044_IQ_UA.get(cell)
        L.append("| " + " | ".join([cell[0], f"{cell[1]:g}", cell[2], f"{cell[3]:g}"]
                                   + [f"{r[s]:.1f}" for s in STAGES]
                                   + [f"{r['sum']:.1f}", f"**{r['total']:.1f}**", f"{r['residue']:.3f}",
                                      f"{r['residue_pct']:+.3f}", f"{dr:.1f}" if dr else "-",
                                      "**>500**" if dr and dr > OVER_LIMIT else ""]) + " |")
    L += ["", f"Sum check: per-stage sum within +/-{SUM_TOL_FRAC * 100:g} % of the measured total at "
          f"{len(env) - len(fails)}/{len(env)} cells" + (f"; FAILING: {fails}" if fails else ".")]
    return L, {"b2b": checks, "sum_fails": fails, "cells": len(env)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results")
    ap.add_argument("out_md")
    ap.add_argument("--map", default=str(HERE / "stage_map.json"))
    ap.add_argument("--src", default="")
    ap.add_argument("--control", action="store_true",
                    help="compare the back-to-back cell against DR-0044's committed L=1U control figure")
    a = ap.parse_args()
    env = load_envelopes(Path(a.results))
    assert env, f"no envelopes with report.json under {a.results}"
    L, checks = report(env, Path(a.map), a.src or str(a.results), control=a.control)
    Path(a.out_md).write_text("\n".join(L) + "\n")
    print("\n".join(L))
    assert all(v == "OK" for v in checks["b2b"].values()), f"back-to-back FAILED: {checks['b2b']}"
    assert not checks["sum_fails"], f"sum check FAILED: {checks['sum_fails']}"


if __name__ == "__main__":
    main()
