#!/usr/bin/env python3
"""Fixed-code (212) width sweep of the bank pass devices, ss 27 C (issue #320). Usage: width_table.py CTRL_DIR PREFIX OUT.md K..."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "row45-attribution"))
import stage_attribution as sa  # noqa: E402

ctrl, pre, out, ks = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
R = ["# Bank pass-device width at fixed code 212 (generated)", "",
     "ss, 27 C, code NOT re-derived. Span = eps(3.6 V) - eps(3.0 V) (pt) vs the same netlist at 3.3 V.", "",
     "| W scale | tau 3.0 V (ps) | tau 3.6 V | tau(3.0)/tau(3.6) | RC-term span | total span | f(3.3 V) MHz |", "|---|---|---|---|---|---|---|"]
for k, path in [("1", ctrl)] + [(k, f"{pre}-w{k}") for k in ks]:
    d = sa.load(Path(path))
    p = {v: d[("ss", 27.0, v)] for v in (3.0, 3.3, 3.6)}
    lo, hi = sa.step(p[3.3], p[3.0]), sa.step(p[3.3], p[3.6])
    R.append(f"| {k}x | {p[3.0]['tau']*1e12:.0f} | {p[3.6]['tau']*1e12:.0f} | {p[3.0]['tau']/p[3.6]['tau']:.4f} | {hi['chg_rc']-lo['chg_rc']:+.2f} | {hi['eps']-lo['eps']:+.2f} | {1e-6/p[3.3]['T']:.2f} |")
Path(out).write_text("\n".join(R) + "\n")
print("\n".join(R))
