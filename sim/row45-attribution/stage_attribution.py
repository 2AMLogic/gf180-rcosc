#!/usr/bin/env python3
"""Stage-level attribution of the row 4 (ss) and row 5 (ff) failures on the DR-0028 netlist (issue #314, DR-0033).

Reads the `klt sim` envelopes written for gen_stage_requests.py and splits the period change against the
per-die calibration point (3.3 V, 27 C, same trim code) into the six oscillator stages.  The split is exact:

    eps = f/f_ref - 1 = T_ref/T - 1 = -(T - T_ref)/T = -sum_s (d_s - d_s_ref)/T

so each stage contributes -(delta d_s)/T percentage points and the contributions sum to eps by construction;
the stated residual is only (a) the six measured event gaps against the measured period and (b) eps against the
independent 20-period `fosc` measurement.  The charge stage is split further with t_chg = tau * L,
L = ln((VDD - v0)/(VDD - vh)) (v0 = vc at clk fall, vh = high threshold): the threshold-ratio term tau0*dL
(bias ratio and discharge depth), the RC term dtau*L0 (trim-bank R incl. switch Ron, and C) and their cross term.

Usage: python3 -I stage_attribution.py RESULTS_DIR OUT.md
"""
import json
import math
import sys
from pathlib import Path

PROCS = ["tt", "ff", "ss"]
TEMPS = [-40.0, 27.0, 85.0]
VS = [3.0, 3.3, 3.6]
EVENTS = ["ev_a", "ev_b", "ev_c", "ev_d", "ev_e", "ev_f"]
STAGES = [("cmp_h", "comparator H (vc>vh -> cmph_out)"), ("lat_h", "latch set (cmph_out -> clk rise)"),
          ("dis", "discharge (clk rise -> vc<vl)"), ("cmp_l", "comparator L (vc<vl -> cmpl_out)"),
          ("lat_l", "latch reset (cmpl_out -> clk fall)"), ("chg_ratio", "charge: threshold-ratio term"),
          ("chg_rc", "charge: RC term (trim bank R, Ron, C)"), ("chg_x", "charge: cross term")]
KEYS = [k for k, _ in STAGES]


def pt(m: dict, v: float) -> dict:
    """Stage delays (s) of one measured point; m is {measurement name: value}."""
    T = (m["ev_a3"] - m["ev_a"]) / 2
    gaps = [(m[EVENTS[(i + 1) % 6]] - m[EVENTS[i]]) % T for i in range(6)]
    if gaps[2] > T / 2:          # fast discharge: vc can pass vl before clk reaches mid-rail (signed gap, never ~T)
        gaps[2] -= T
        gaps[1] = (gaps[1] + 0) % T
        gaps[5] = (m[EVENTS[0]] - m[EVENTS[5]]) % T
    L = math.log((v - m["v0"]) / (v - m["vh"]))
    return {"T": T, "fosc_T": 1 / m["fosc"], "cmp_h": gaps[0], "lat_h": gaps[1], "dis": gaps[2], "cmp_l": gaps[3],
            "lat_l": gaps[4], "chg": gaps[5], "L": L, "tau": gaps[5] / L, "gap_sum": sum(gaps),
            "vh": m["vh"], "vl": m["vl"], "vib": m["vib"], "vpb": m["vpb"], "v": v}


def step(a: dict, b: dict) -> dict:
    """Contribution (percentage points of frequency) of each stage to the move from point a to point b."""
    out = {k: -(b[k] - a[k]) / b["T"] * 100 for k in ("cmp_h", "lat_h", "dis", "cmp_l", "lat_l")}
    dL, dtau = b["L"] - a["L"], b["tau"] - a["tau"]
    out["chg_ratio"] = -a["tau"] * dL / b["T"] * 100
    out["chg_rc"] = -dtau * a["L"] / b["T"] * 100
    out["chg_x"] = -dtau * dL / b["T"] * 100
    out["total"] = sum(out[k] for k in KEYS)
    out["eps"] = (a["T"] / b["T"] - 1) * 100          # from the measured periods
    out["eps_fosc"] = (a["fosc_T"] / b["fosc_T"] - 1) * 100
    return out


def load(res: Path) -> dict:
    d = {}
    for rep in sorted(res.glob("art/request_*/report.json")):
        proc, vtag = rep.parent.name.split("_")[1:3]
        v = int(vtag[1:]) / 10
        for c in json.loads(rep.read_text())["corners"]:
            t = float(c["corner_id"].split("/")[2].replace("n", "-").rstrip("C"))
            m = {x["name"]: x["value"] for x in c["measurements"]}
            d[(proc, t, v)] = pt(m, v)
    return d


def table(title, cols, rows_by_col) -> list:
    L = [f"### {title}", "", "| stage | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k, name in STAGES + [("total", "**sum of stages**"), ("eps", "measured eps (periods)"),
                              ("eps_fosc", "measured eps (20-period fosc)")]:
        L.append(f"| {name} | " + " | ".join(("n/a" if r[k] != r[k] else f"{r[k]:+.2f}") for r in rows_by_col) + " |")
    return L + [""]


def report(d: dict, src: str) -> list:
    ref = lambda p: d[(p, 27.0, 3.3)]
    L = [f"# Stage-level attribution of rows 4 / 5 (generated; source {src})", "",
         "Frequency error is against the same die's 3.3 V / 27 C frequency at its calibration code "
         "(tt 165, ff 78, ss 212); contributions are percentage points and sum to the measured error.", "",
         "## Reference points (3.3 V / 27 C)", "",
         "| process | code | f MHz | T ns | cmp_h | lat_h | dis | cmp_l | lat_l | chg | vh/VDD | vl/VDD |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    codes = {"tt": 165, "ff": 78, "ss": 212}
    for p in PROCS:
        r = ref(p)
        L.append(f"| {p} | {codes[p]} | {1e-6 / r['T']:.2f} | {r['T'] * 1e9:.3f} | " + " | ".join(
            f"{r[k] * 1e9:.3f}" for k in ("cmp_h", "lat_h", "dis", "cmp_l", "lat_l", "chg"))
            + f" | {r['vh'] / 3.3:.4f} | {r['vl'] / 3.3:.4f} |")
    L.append("")
    worst_gap = max(abs(x["gap_sum"] - x["T"]) / x["T"] for x in d.values()) * 100
    worst_f = max(abs(x["fosc_T"] - x["T"]) / x["T"] for x in d.values()) * 100
    L += [f"Residuals over all {len(d)} points: event gaps vs period {worst_gap:.4f} % of T; "
          f"3-edge period vs 20-period fosc {worst_f:.3f} % of T.", ""]
    L += ["## Row 4 - supply term at 27 C (3.0 / 3.6 V against 3.3 V)", ""]
    for p in PROCS:
        a = ref(p)
        lo, hi = step(a, d[(p, 27.0, 3.0)]), step(a, d[(p, 27.0, 3.6)])
        span = {k: hi[k] - lo[k] for k in KEYS + ["total", "eps", "eps_fosc"]}
        L += table(f"{p}, 27 C (span = eps(3.6 V) - eps(3.0 V); ratified window 4.9 pt)",
                   ["3.0 V", "3.6 V", "span"], [lo, hi, span])
    L += ["## Row 5 - skew cells (move from 3.3 V / 27 C: temperature step at 3.3 V, then supply step at that T)", ""]
    for p, t, v in [("ff", 85.0, 3.0), ("ff", 85.0, 3.3), ("ff", -40.0, 3.0), ("ff", -40.0, 3.6),
                    ("tt", 85.0, 3.0), ("tt", -40.0, 3.0), ("ss", 85.0, 3.0), ("ss", -40.0, 3.0)]:
        a, mid, b = ref(p), d[(p, t, 3.3)], d[(p, t, v)]
        s1, s2, tot = step(a, mid), step(mid, b), step(a, b)
        s2["eps"] = s2["eps_fosc"] = float("nan")
        L += table(f"{p}, {t:g} C, {v:g} V", [f"T step ({t:g} C @3.3 V)", f"V step (3.3->{v:g} V)", "total"],
                   [s1, s2, tot])
    L += ["## Bias gate voltages (3.3 V ref points, V)", "", "| point | ibias gate | pb | vh | vl |", "|---|---|---|---|---|"]
    for p in PROCS:
        for t in TEMPS:
            for v in VS:
                x = d[(p, t, v)]
                L.append(f"| {p} {t:g} C {v:g} V | {x['vib']:.4f} | {x['vpb']:.4f} | {x['vh']:.4f} | {x['vl']:.4f} |")
    return L + [""]


def main(res: Path, out: Path) -> None:
    text = "\n".join(report(load(res), res.as_posix())) + "\n"
    out.write_text(text)
    print(text)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
