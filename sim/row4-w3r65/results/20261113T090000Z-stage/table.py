#!/usr/bin/env python3
"""Frequency-only table for gen_row5_extracted.py stage results: eps = f / f(same die, 3.3 V, 27 C) - 1, percent (issue #321)."""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
f = {}
for p in sorted(d.glob("art/request_*_v*/report.json")):
    proc, v = p.parent.name.split("_")[1:3]
    for c in json.load(open(p))["corners"]:
        f[(proc, int(v[1:]) / 10, c["temperature_c"])] = next(m["value"] for m in c["measurements"] if m["name"] == "fosc")
out = ["| die | T C | 3.0 V | 3.3 V | 3.6 V | span (3.6-3.0) |", "|---|---|---|---|---|---|"]
for proc in ("tt", "ff", "ss"):
    ref = f[(proc, 3.3, 27.0)]
    out.append(f"| {proc} | ref f(3.3 V, 27 C) = {ref/1e6:.3f} MHz | | | | |")
    for t in (-40.0, 27.0, 85.0):
        e = [100 * (f[(proc, v, t)] / ref - 1) for v in (3.0, 3.3, 3.6)]
        out.append(f"| {proc} | {t:g} | {e[0]:+.2f} | {e[1]:+.2f} | {e[2]:+.2f} | {e[2]-e[0]:.2f} |")
print("\n".join(out))
