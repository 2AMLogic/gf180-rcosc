#!/usr/bin/env python3
"""Tabulate one results dir of the variant search (issue #337): ss span (stage) and running-Iq delta vs the rebuilt-layout extraction.

  tables.py RESULTDIR   RESULTDIR holds <variant>-stage/ (ss supply x temperature, art/request_ss_v*/report.json)
                        and <variant>-iq/ (art/request_c*_v*/report.json). Writes table.md into each, prints a summary.
Baseline for Iq: sim/row45-rerun/results/20261113T064105Z-iq-extracted-l07 (same basis as DR-0045 `table_vs_l07.md`).
"""
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BASE_IQ = REPO / "sim" / "row45-rerun" / "results" / "20261113T064105Z-iq-extracted-l07"


def fosc(d):
    f = {}
    for p in sorted(Path(d).glob("art/request_ss_v*/report.json")):
        v = int(p.parent.name.split("_")[2][1:]) / 10
        for c in json.load(open(p))["corners"]:
            f[(v, c["temperature_c"])] = next(m["value"] for m in c["measurements"] if m["name"] == "fosc")
    return f


def iq(d):
    out = {}
    for p in sorted(glob.glob(str(Path(d) / "art" / "request_c*_v*" / "report.json"))):
        _, code, v = Path(p).parent.name.split("_")
        for c in json.load(open(p))["corners"]:
            m = {x["name"]: x["value"] for x in c["measurements"]}
            out[(code, v, c["process"], c["temperature_c"])] = m["iq_run"] * 1e6
    return out


base_iq = {}
for p in sorted(glob.glob(str(BASE_IQ / "art" / "request_c*_v*" / "report.json")) + glob.glob(str(BASE_IQ / "request_c*_v*" / "report.json"))):
    _, code, v = Path(p).parent.name.split("_")
    for c in json.load(open(p))["corners"]:
        m = {x["name"]: x["value"] for x in c["measurements"]}
        base_iq[(code, v, c["process"], c["temperature_c"])] = m["iq_run"] * 1e6

root = Path(sys.argv[1])
for sd in sorted(root.glob("*-stage")):
    name = sd.name[:-6]
    f = fosc(sd)
    ref = f[(3.3, 27.0)]
    out = [f"ss die, variant {name}: ref f(3.3 V, 27 C) = {ref / 1e6:.3f} MHz", "", "| T C | 3.0 V | 3.3 V | 3.6 V | span (3.6-3.0) pt |", "|---|---|---|---|---|"]
    for t in (-40.0, 27.0, 85.0):
        e = [100 * (f[(v, t)] / ref - 1) for v in (3.0, 3.3, 3.6)]
        out.append(f"| {t:g} | {e[0]:+.2f} | {e[1]:+.2f} | {e[2]:+.2f} | {e[2] - e[0]:.2f} |")
    (sd / "table.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))
    idir = root / f"{name}-iq"
    cand = iq(idir)
    rows = ["| code | VDD | die | T (C) | candidate (uA) | rebuilt-layout baseline (uA) | delta (%) |", "|---|---|---|---|---|---|---|"]
    summ = {}
    for k in sorted(cand):
        a, b = cand[k], base_iq.get(k)
        if not b:
            continue
        d = 100 * (a / b - 1)
        rows.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]:g} | {a:.1f} | {b:.1f} | {d:+.2f} |")
        s = summ.setdefault(k[0], [1e9, -1e9, 0, 0.0])
        s[0], s[1], s[2], s[3] = min(s[0], d), max(s[1], d), s[2] + (a > 500), max(s[3], a)
    (idir / "table_vs_l07.md").write_text("\n".join(rows) + "\n")
    for c, (lo, hi, n, mx) in summ.items():
        print(f"Iq {name} {c}: delta {lo:+.2f}..{hi:+.2f} %, cells>500uA {n}, max {mx:.1f} uA")
    print()
