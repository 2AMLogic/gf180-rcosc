#!/usr/bin/env python3
"""Tabulate a gen_screen.py run: per variant, fosc change (points) of ff 3.0 V at -40 / 85 C against the same variant's 3.3 V / 27 C
frequency, plus the 3.3 V / 27 C frequency itself.  Usage: screen_table.py RESULT_DIR"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
f = {}
for rep in sorted((d / "art").glob("request_*/report.json")):
    name = rep.parent.name[len("request_"):]
    for c in json.loads(rep.read_text())["corners"]:
        f[(name, c["temperature_c"])] = {m["name"]: m["value"] for m in c["measurements"]}["fosc"]
variants = sorted({k[0].rsplit("_", 1)[0] for k in f}, key=lambda v: (v != "base", v))
print("| variant | f(3.3 V, 27 C) MHz | 3.0 V / 85 C pt | 3.0 V / -40 C pt |\n|---|---|---|---|")
for v in variants:
    ref = f[(v + "_v33", 27.0)]
    print(f"| {v} | {ref / 1e6:.3f} | {100 * (f[(v + '_v30', 85.0)] / ref - 1):+.2f} | {100 * (f[(v + '_v30', -40.0)] / ref - 1):+.2f} |")
