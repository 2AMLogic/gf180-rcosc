#!/usr/bin/env python3
"""ss scan table: fosc (MHz) per variant per code. Usage: table.py RESULTDIR"""
import json, sys, glob, os
d = sys.argv[1]
codes = ["cC8", "cD0", "cD4", "cD8"]
print("| variant | " + " | ".join(c[1:] for c in codes) + " |\n|---|" + "---|" * len(codes))
for v in sorted(os.listdir(d)):
    if not os.path.isdir(f"{d}/{v}"): continue
    row = []
    for c in codes:
        r = json.load(open(f"{d}/{v}/art/request_ss_{c}/report.json"))
        row.append(f"{r['corners'][0]['measurements'][2]['value']/1e6:.2f}")
    print(f"| {v} | " + " | ".join(row) + " |")
