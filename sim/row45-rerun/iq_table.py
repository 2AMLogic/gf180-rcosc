#!/usr/bin/env python3
"""Tabulate gen_row5_iq_schematic.py results: iq_run (uA) per (code, supply, process, T), candidate vs control.
Usage: iq_table.py CANDIDATE_DIR CONTROL_DIR  (prints markdown)"""
import glob
import json
import sys
from pathlib import Path


def load(d):
    out = {}
    for f in sorted(glob.glob(str(Path(d) / "request_*" / "report.json"))):
        name = Path(f).parent.name  # request_cFF_v33
        _, code, v = name.split("_")
        for c in json.load(open(f))["corners"]:
            m = {x["name"]: x["value"] for x in c["measurements"]}
            out[(code, v, c["process"], c["temperature_c"])] = m["iq_run"] * 1e6 if m.get("iq_run") is not None else None
    return out


cand, ctl = load(sys.argv[1]), load(sys.argv[2])
print("| code | VDD | die | T (C) | L 0.7 (uA) | control L 1.0 (uA) | delta (%) |\n|---|---|---|---|---|---|---|")
for k in sorted(cand):
    a, b = cand[k], ctl.get(k)
    if a is None or not b:
        print(f"| {k} | {a} | {b} | |")
        continue
    print(f"| 0x{k[0][1:]} | {int(k[1][1:]) / 10:.1f} | {k[2]} | {k[3]:g} | {a:.1f} | {b:.1f} | {(a - b) / b * 100:+.2f} |")
vals = [v for v in cand.values() if v is not None]
cv = [v for v in ctl.values() if v is not None]
print(f"\nmax L 0.7: {max(vals):.1f} uA (n={len(vals)}); max control: {max(cv):.1f} uA (n={len(cv)}); limit 500 uA")
