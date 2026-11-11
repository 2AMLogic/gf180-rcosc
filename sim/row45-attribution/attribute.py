#!/usr/bin/env python3
"""Row 4 / row 5 cause attribution from existing DR-0029 corner data (issue #236). No simulation.

Splits the fixed-code (0xA4) error at every grid point into
  process offset  = f(proc, 27 C, 3.3 V) vs 48 MHz   (what a fixed code cannot remove)
  supply term     = f(proc, 27 C, V) vs f(proc, 27 C, 3.3 V)
  temperature term= f(proc, T, 3.3 V) vs f(proc, 27 C, 3.3 V)
and grades two idealised levers against the UNCHANGED ratified windows:
  L1  supply term removed exactly (perfect supply regulation / tracking bias), row 4
  L2  temperature term removed exactly (perfect TC compensation), row 5 (supply term kept)
Both are upper bounds on any candidate of those lever classes: a real circuit removes less.

Usage: python3 -I sim/row45-attribution/attribute.py sim/item5/results/<runid> OUT.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "item5"))
import report_rows as r  # noqa: E402

PROCS = ["tt", "ff", "ss", "fs", "sf", "rc_f", "rc_s"]
TEMPS = [-40.0, 27.0, 85.0]
VS = [3.0, 3.3, 3.6]


def main(res: Path, out: Path) -> None:
    d = r.load(res)
    g = lambda v, p, t: d[(r.CAL, v)][1][(p, t)][0]
    L = ["# Row 4 / row 5 cause attribution (generated; source %s, code 0x%s)" % (res.as_posix(), r.CAL.upper()), "",
         "| process | f(27C,3.3V) MHz | process offset vs 48 MHz | supply term (3.0 / 3.6 V) | temp term (-40 / 85 C) |",
         "|---|---|---|---|---|"]
    for p in PROCS:
        f0 = g(3.3, p, 27.0)
        s = [(g(v, p, 27.0) - f0) / f0 * 100 for v in (3.0, 3.6)]
        t = [(g(3.3, p, c) - f0) / f0 * 100 for c in (-40.0, 85.0)]
        L.append(f"| {p} | {f0/1e6:.2f} | {r.pct(f0):+.1f} % | {s[0]:+.2f} / {s[1]:+.2f} % | {t[0]:+.2f} / {t[1]:+.2f} % |")

    def count(window_t, lo, hi, err):
        pts = [(p, t, v) for p in PROCS for t in window_t for v in VS]
        ok = [k for k in pts if lo <= err(*k) <= hi]
        return len(ok), len(pts), max(abs(err(*k)) for k in pts)

    base = lambda p, t, v: r.pct(g(v, p, t))
    nosup = lambda p, t, v: r.pct(g(3.3, p, t))            # supply term removed
    notmp = lambda p, t, v: r.pct(g(v, p, 27.0))           # temperature term removed
    # Basis used by DR-0017 (ratified derivation): each die calibrated at 27 C / 3.3 V, error vs its own calibration
    own = lambda p, t, v: (g(v, p, t) / g(3.3, p, 27.0) - 1) * 100

    L += ["", "| basis | row 4 in-window (27 C) | worst | row 5 in-window (-40..85 C) | worst |", "|---|---|---|---|---|"]
    rows = [("fixed code 0xA4, as graded (DR-0029)", base, base),
            ("L1: supply term removed exactly (row 4); L2: temperature term removed exactly (row 5)", nosup, notmp),
            ("process offset removed too (each die at its own 27 C / 3.3 V frequency; DR-0017 basis, NOT the fixed-code ruling)", own, own)]
    for name, e4, e5 in rows:
        a = count([27.0], r.CAL_LO, r.CAL_HI, e4)
        b = count(TEMPS, r.TEMP_LO, r.TEMP_HI, e5)
        L.append(f"| {name} | {a[0]}/{a[1]} | {a[2]:.2f} % | {b[0]}/{b[1]} | {b[2]:.2f} % |")
    L += ["", "Row 5 under L2 keeps the supply term, so its idealised window check is `f(proc, 27 C, V)`.", ""]
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
