#!/usr/bin/env python3
"""Tabulate the knock-out runs (issue #320): ss, 27 C, tau = t_chg/L and the stage split of the 3.0 -> 3.6 V span.
Usage: python3 -I knockout_table.py RESULTS_DIR_PREFIX OUT.md   (prefix e.g. sim/row4-nonron/results/20261112T100000Z)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "row45-attribution"))
import stage_attribution as sa  # noqa: E402

NAMES = {"ctrl": "unmodified DUT", "nojb": "bank switch junctions removed", "nojd": "discharge device junction removed",
         "nojall": "both removed", "capx": "+200 fF linear on vc"}

pre = sys.argv[1]
rows = ["# Knock-out isolation of the ss charge RC term (generated)", "",
        "ss, 27 C, code 212. tau = t_chg / ln((VDD-v0)/(VDD-vh)); span = eps(3.6 V) - eps(3.0 V) in pt vs the same netlist at 3.3 V.", "",
        "| variant | tau 3.0 V (ps) | tau 3.3 V | tau 3.6 V | tau(3.0)/tau(3.6) | RC-term span | total span | f(3.3 V) MHz |", "|---|---|---|---|---|---|---|---|"]
for k, desc in NAMES.items():
    d = sa.load(Path(f"{pre}-{k}"))
    p = {v: d[("ss", 27.0, v)] for v in (3.0, 3.3, 3.6)}
    lo, hi = sa.step(p[3.3], p[3.0]), sa.step(p[3.3], p[3.6])
    rc = hi["chg_rc"] - lo["chg_rc"]
    tot = hi["eps"] - lo["eps"]
    rows.append(f"| {k}: {desc} | {p[3.0]['tau']*1e12:.1f} | {p[3.3]['tau']*1e12:.1f} | {p[3.6]['tau']*1e12:.1f} | "
                f"{p[3.0]['tau']/p[3.6]['tau']:.4f} | {rc:+.2f} | {tot:+.2f} | {1e-6/p[3.3]['T']:.2f} |")
Path(sys.argv[2]).write_text("\n".join(rows) + "\n")
print("\n".join(rows))
