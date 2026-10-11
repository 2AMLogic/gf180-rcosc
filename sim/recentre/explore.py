#!/usr/bin/env python3
"""Single-corner probes of re-sized timing components (issue #66, AC 2/3 prep).

Each candidate is the committed extracted netlist (parasitic R/C held at the
extraction's lumped values) with only (a) the MiM timing capacitor value and
(b) a uniform scale of the nine trim-ladder poly-resistor lengths changed
(see pexlib.sizing).  Every probe is ONE ngspice transient at ONE corner and
ONE trim code, run serially.  No grid: the 27-point confirmation is a
`klt sim` request (gen_requests.py).

Modes
  curve    : f and Iq at a list of trim codes for each candidate
  points   : f and Iq at explicit proc:temp:vdd:code points (--points)
  calibrate: bisection of the trim code to the 48.000 MHz target, then the
             f at code-1 / code / code+1 (local LSB), per candidate
Candidate spec: NAME:R_SCALE:C_FF (plain C, fF; 217.2 = committed MiM) or
               NAME:R_SCALE:WxL (MiM cap_mim_1f0fF subckt, um; 20x10 = committed)
Options: --corner proc:temp:vdd (default tt:27:3.3), --tie (hard-tie vsubs,
substrate model B; default is model A, as extracted), --codes 0,64,...
"""
import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pexlib as L  # noqa: E402

TARGET = 48.0e6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["curve", "calibrate", "points"])
    ap.add_argument("cands", nargs="+")
    ap.add_argument("--corner", default="tt:27:3.3")
    ap.add_argument("--tie", action="store_true")
    ap.add_argument("--codes", default="0,64,128,192,255")
    ap.add_argument("--note", default="")
    ap.add_argument("--points", default="", help="mode 'points': proc:temp:vdd:code,... (code 0x.. ok)")
    ap.add_argument("--vc-c-scale", type=float, default=1.0,
                    help="scale the extracted vc net-to-substrate C (assumes it is bottom-plate dominated)")
    a = ap.parse_args()
    proc, t, v = a.corner.split(":")
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # results/<runid>/ (the repo-wide sim/<bench>/results/<ts> layout the
    # citation verifier resolves); the mode is recorded in results.csv and
    # command.txt.  Raw logs stay in corners/explore-<runid>-<mode>/.
    out = HERE / "results" / runid
    logs = HERE / "corners" / f"explore-{runid}-{a.mode}"
    out.mkdir(parents=True)
    base_cards = L.load_cards()
    rows = []

    def probe(name, text, code, tag, pt=None):
        pt = pt or L.base.Point(proc, float(t), float(v), code)
        # the corner is part of the log name: several points of one run share
        # a trim code, and a code-only name made their logs overwrite each
        # other (PR #158 review).  pexlib.run also refuses to overwrite.
        ctag = f"{pt.process}_{pt.temp_c:g}C_{pt.vdd_v:g}V".replace("-", "m")
        r = L.run(text, pt, logs, f"{name}_{tag}_{ctag}_0x{code:02X}")
        rows.append({"candidate": name, "mode": a.mode, "corner": f"{pt.process}:{pt.temp_c:g}:{pt.vdd_v:g}",
                     "substrate": "hard-tied" if a.tie else "as-extracted",
                     "vc_c_scale": a.vc_c_scale,
                     "code": code, "f_hz": r["f_hz"], "iq_a": r["iq_a"],
                     "log": f"sim/recentre/corners/{logs.name}/{r['log']}"})
        print(name, f"0x{code:02X}", r["f_hz"], r["iq_a"], flush=True)
        return r["f_hz"]

    for spec in a.cands:
        name, rs, cf = spec.split(":")
        if "x" in cf:
            w_, l_ = (float(x) for x in cf.split("x"))
            cards = L.sizing(base_cards, mim_wl=(w_, l_), r_scale=float(rs), vc_c_scale=a.vc_c_scale)
        else:
            cards = L.sizing(base_cards, c_timing_f=float(cf) * 1e-15, r_scale=float(rs), vc_c_scale=a.vc_c_scale)
        if a.tie:
            cards = L.variant(cards, set(), tie_substrate=True)
        text = L.harness(cards)
        if a.mode == "points":
            for spec_pt in a.points.split(","):
                pp, pt_, pv, pc = spec_pt.split(":")
                code = int(pc, 0)
                probe(name, text, code, "pt", L.base.Point(pp, float(pt_), float(pv), code))
        elif a.mode == "curve":
            for c in [int(x, 0) for x in a.codes.split(",")]:
                probe(name, text, c, "curve")
        else:
            lo, hi = 0, 255
            flo, fhi = probe(name, text, lo, "cal"), probe(name, text, hi, "cal")
            if not (flo <= TARGET <= fhi):
                print(name, "target outside range", flo, fhi)
                continue
            while hi - lo > 1:
                mid = (lo + hi) // 2
                fm = probe(name, text, mid, "cal")
                if fm < TARGET:
                    lo = mid
                else:
                    hi = mid
            flo_ = probe(name, text, lo, "cal") if False else None
            # closest of the final bracket (cache-free: values already logged)
            best = min((lo, hi), key=lambda c: abs(next(
                r["f_hz"] for r in rows if r["candidate"] == name and r["code"] == c) - TARGET))
            for c in (best - 1, best, best + 1):
                if 0 <= c <= 255 and not any(r["candidate"] == name and r["code"] == c for r in rows):
                    probe(name, text, c, "cal")
            print(name, "calibrated code", f"0x{best:02X}")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out / "command.txt").write_text(" ".join(sys.argv) + "\n" + a.note + "\n")


if __name__ == "__main__":
    main()
