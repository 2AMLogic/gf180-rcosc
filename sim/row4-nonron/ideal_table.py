#!/usr/bin/env python3
"""Real bank vs ideal-switch bank at codes 0 / 212 / 255 (issue #320), ss 27 C. t_chg = tau*L; tau and t_chg vs VDD, and the
span of each variant's frequency error and RC term. Usage: python3 -I ideal_table.py PREFIX OUT.md (PREFIX .../20261112T110000Z)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "row45-attribution"))
import stage_attribution as sa  # noqa: E402

pre = sys.argv[1]
R = ["# Real bank vs ideal-switch bank (generated)", "",
     "ss, 27 C. tau = t_chg / ln((VDD-v0)/(VDD-vh)) (ps). Spans are eps(3.6 V) - eps(3.0 V) in pt against the same netlist and code at 3.3 V.", "",
     "| bank | code | tau 3.0 V | tau 3.3 V | tau 3.6 V | tau(3.0)/tau(3.6) | RC-term span | total span | f(3.3 V) MHz |", "|---|---|---|---|---|---|---|---|---|"]
for kind in ("ctrl", "ideal"):
    for code in (0, 212, 255):
        name = f"{kind}{code}" if not (kind == "ctrl" and code == 212) else "ctrl"
        path = Path(f"{pre}-{name}") if name != "ctrl" else Path("sim/row4-nonron/results/20261112T100000Z-ctrl")
        d = sa.load(path)
        p = {v: d[("ss", 27.0, v)] for v in (3.0, 3.3, 3.6)}
        lo, hi = sa.step(p[3.3], p[3.0]), sa.step(p[3.3], p[3.6])
        R.append(f"| {'committed (TGs)' if kind == 'ctrl' else 'ideal switches'} | {code} | " + " | ".join(f"{p[v]['tau']*1e12:.0f}" for v in (3.0, 3.3, 3.6))
                 + f" | {p[3.0]['tau']/p[3.6]['tau']:.4f} | {hi['chg_rc']-lo['chg_rc']:+.2f} | {hi['eps']-lo['eps']:+.2f} | {1e-6/p[3.3]['T']:.2f} |")
Path(sys.argv[2]).write_text("\n".join(R) + "\n")
print("\n".join(R))
