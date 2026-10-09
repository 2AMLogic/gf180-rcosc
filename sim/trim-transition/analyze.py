#!/usr/bin/env python3
"""Analyzer for the live trim-code transition bench (issue #103).

Input : `klt sim --format json -o <outdir>` reports for the requests written by
        sim/trim-transition/prepare.py, given as TAG=report.json (TAG = request
        stem without `request_`, e.g. v33_lsb_first); the matching
        schedule_<TAG>.json (exact change times) is read from --bench-dir.
        Waveforms are waveform.raw.json files as in sim/waveform/analyze.py.
Output: results.json / results.csv (one row per event) / summary.md (verdict
        table per corner x step) in a NEW directory (refuses to overwrite).

Definitions (seconds, volts; 50 % of NOMINAL vdd, linear interpolation):
  r[i]            rising clk crossings; P[i]=r[i+1]-r[i]; H[i], L[i] high/low
                  widths of cycle i (the falling crossing between r[i], r[i+1]).
  event           one +/-1 code step from schedule: t_start (first select edge
                  begins) .. t_end (last select edge ends).
  kstart, kend    index of the cycle containing t_start / t_end.
  window (3 cyc)  cycles kstart-1 .. max(kstart+1, kend): the cycle before, the
                  cycle containing the change, the next (extended if a skewed
                  change straddles a rising edge).
  P_old, P_new    mean of the 8 cycles kstart-9..kstart-2 / of the 8 cycles ending
                  2 cycles before the NEXT scheduled change (or end of run).
                  The run FAILS if either steady window starts before the
                  neighbouring change has ended.
  min/max period  over the window.  excursion = how far the window periods
                  leave [min(P_old,P_new), max(P_old,P_new)], in % of P_old.
  runt            any window high or low width < runt_frac x steady width
                  (H_old / L_old), OR an incomplete swing (after a rising
                  crossing clk does not reach 90 % of VDD, after a falling one
                  10 %).
  missing/extra   any window period > 1.5 x max(P_old,P_new) or
  edge            < 0.5 x min(P_old,P_new).
  settle cycles   cycles from kstart to the first cycle after which every
                  period up to the steady window is within settle_tol x P_new
                  of P_new (0 = the change cycle already is).  None = never
                  settles (also reported as a failure of the event).
  phase           (t_start - r[kstart]) / P[kstart], where in its cycle the
                  first select edge lands.
Verdict screens (bench screening thresholds, NOT ratified spec rows):
  VIOLATION  runt, missing/extra edge, or never settles;
  FLAG       excursion > exc_flag (5 %) or settle cycles > settle_flag (3);
  PASS       otherwise.
Failures are explicit; nothing is imputed.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import sys
from bisect import bisect_right
from dataclasses import dataclass, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wfa = _load("wf_analyze", "sim/waveform/analyze.py")
AnalysisError = wfa.AnalysisError
NS = 1e-9


@dataclass(frozen=True)
class Params:
    runt_frac: float = 0.5
    settle_tol: float = 0.001
    exc_flag: float = 0.05
    settle_flag: int = 3
    steady_cycles: int = 8
    swing_hi: float = 0.9
    swing_lo: float = 0.1
    vdd_tol: float = 0.02


def _edges(t, clk, vdd_nom):
    cr = wfa.crossings(t, clk, vdd_nom / 2)
    r = [c[0] for c in cr if c[1] == "r"]
    f = [c[0] for c in cr if c[1] == "f"]
    return r, f


def _fall_after(f, x):
    k = bisect_right(f, x)
    return f[k] if k < len(f) else None


def analyse_event(t, clk, r, f, ev, prev_end, next_start, vdd_nom, p: Params):
    """Metrics for one event; raises AnalysisError if it cannot be measured."""
    n = p.steady_cycles
    ts, te = ev["t_start_ns"] * NS, ev["t_end_ns"] * NS
    ks = bisect_right(r, ts) - 1
    ke = bisect_right(r, te) - 1
    if ks < n + 1:
        raise AnalysisError("event too early: not enough preceding cycles")
    lo_i, hi_i = ks - 1, max(ks + 1, ke)
    kn = bisect_right(r, next_start) - 1          # cycle containing next change / end
    if kn + 0 > len(r) - 1 or hi_i + 1 > len(r) - 2:
        raise AnalysisError("waveform ends inside the event window")
    if r[ks - n - 1] <= prev_end:
        raise AnalysisError("preceding steady window starts before the previous change ended")
    new0 = kn - n - 1                              # steady cycles new0 .. kn-2
    if new0 <= hi_i + 1 or r[new0] <= te:
        raise AnalysisError("steady window of the new code overlaps the event")
    if kn - 1 >= len(r) - 1:
        raise AnalysisError("waveform ends before the new-code steady window")
    P = lambda i: r[i + 1] - r[i]
    old = list(range(ks - n - 1, ks - 1))
    new = list(range(new0, kn - 1))
    Po = sum(P(i) for i in old) / len(old)
    Pn = sum(P(i) for i in new) / len(new)
    Hs, Ls = [], []
    for i in old:
        fa = _fall_after(f, r[i])
        if fa is None or not r[i] < fa < r[i + 1]:
            raise AnalysisError("steady cycle without a clean falling edge")
        Hs.append(fa - r[i]); Ls.append(r[i + 1] - fa)
    Ho, Lo = sum(Hs) / len(Hs), sum(Ls) / len(Ls)
    # sanity: steady windows must themselves be quiet, else a limit cycle
    steady_spread_old = max(abs(P(i) - Po) for i in old) / Po
    win = list(range(lo_i, hi_i + 1))
    periods = [P(i) for i in win]
    runt, reasons = False, []
    for i in win:
        fa = _fall_after(f, r[i])
        if fa is None or fa >= r[i + 1]:
            runt = True; reasons.append(f"cycle {i - ks:+d}: no falling crossing")
            continue
        h, l = fa - r[i], r[i + 1] - fa
        if h < p.runt_frac * Ho:
            runt = True; reasons.append(f"cycle {i - ks:+d}: high {h / NS:.2f} ns < {p.runt_frac:g} x {Ho / NS:.2f}")
        if l < p.runt_frac * Lo:
            runt = True; reasons.append(f"cycle {i - ks:+d}: low {l / NS:.2f} ns < {p.runt_frac:g} x {Lo / NS:.2f}")
        # swing within each half cycle
        for a, b, hi in ((r[i], fa, True), (fa, r[i + 1], False)):
            j0, j1 = bisect_right(t, a), bisect_right(t, b)
            seg = clk[j0:j1]
            if not seg:
                continue
            if hi and max(seg) < p.swing_hi * vdd_nom:
                runt = True; reasons.append(f"cycle {i - ks:+d}: high pulse peaks at {max(seg):.2f} V")
            if not hi and min(seg) > p.swing_lo * vdd_nom:
                runt = True; reasons.append(f"cycle {i - ks:+d}: low pulse bottoms at {min(seg):.2f} V")
    plo, phi = min(Po, Pn), max(Po, Pn)
    missing = any(q > 1.5 * phi or q < 0.5 * plo for q in periods)
    exc = max(0.0, (plo - min(periods)) / Po, (max(periods) - phi) / Po)
    tol = p.settle_tol * Pn
    settle = None
    for m in range(ks, kn - 1):
        if all(abs(P(j) - Pn) <= tol for j in range(m, kn - 1)):
            settle = m - ks
            break
    if settle is not None and settle > new0 - ks:  # only the steady window itself is in tolerance
        settle = None
    verdict = ("VIOLATION" if (runt or missing or settle is None) else
               "FLAG" if (exc > p.exc_flag or settle > p.settle_flag) else "PASS")
    return {
        "p_old_s": Po, "p_new_s": Pn, "p_step_pct": (Pn - Po) / Po * 100,
        "p_min_s": min(periods), "p_max_s": max(periods),
        "window_cycles": len(win), "excursion_pct": exc * 100,
        "runt": runt, "runt_reasons": reasons, "missing_edge": missing,
        "settle_cycles": settle, "phase_in_cycle": (ts - r[ks]) / P(ks),
        "steady_spread_old_pct": steady_spread_old * 100,
        "verdict": verdict,
    }


def analyse_corner(t, clk, vdd, sched, p: Params = Params()):
    """One row per event.  Raises AnalysisError for run-level problems."""
    vn = sched["vdd_v"]
    r, f = _edges(t, clk, vn)
    t_end = t[-1]
    # rail check after startup
    t0 = sched["changes"][0]["t_start_ns"] * NS - 500 * NS
    vw = [v for tt, v in zip(t, vdd) if tt >= t0]
    if not vw or max(abs(x - vn) for x in vw) > p.vdd_tol * vn:
        raise AnalysisError(f"rail leaves +/-{p.vdd_tol * 100:g}% of {vn:g} V after startup")
    if t_end < sched["tstop_ns"] * NS * 0.999:
        raise AnalysisError(f"run ends at {t_end / NS:.0f} ns, schedule needs {sched['tstop_ns']:g} ns")
    ch = sched["changes"]
    rows = []
    for k, ev in enumerate(ch):
        if ev["kind"] != "event":
            continue
        prev_end = (ch[k - 1]["t_end_ns"] if k else 0.0) * NS
        nxt = (ch[k + 1]["t_start_ns"] if k + 1 < len(ch) else sched["tstop_ns"]) * NS
        row = {k2: ev[k2] for k2 in ("block", "dir", "from", "to", "bits_changed")}
        row["phase_idx"] = ev["phase"]
        row["t_start_ns"] = ev["t_start_ns"]
        try:
            row |= analyse_event(t, clk, r, f, ev, prev_end, nxt, vn, p)
            row["status"] = "OK"
        except AnalysisError as e:
            row["status"] = f"FAIL: {e}"
            row["verdict"] = "FAIL"
        rows.append(row)
    return rows


def analyse_report(tag, report_path: Path, bench_dir: Path, p: Params = Params(), artifacts_root=None):
    """Returns (event rows with process/tag/skew/vdd, meta)."""
    rp = Path(report_path)
    sp = Path(bench_dir) / f"schedule_{tag}.json"
    base = {"tag": tag, "report": rp.name}

    def fail(msg, **kw):
        return [base | {"process": None, "verdict": "FAIL", "status": f"FAIL: {msg}"} | kw]
    try:
        sched = json.loads(sp.read_text())
    except (OSError, ValueError) as e:
        return fail(f"schedule unreadable: {e}"), {"report": rp.name, "tag": tag}
    base |= {"vdd_v": sched["vdd_v"], "skew": sched["skew"]}
    try:
        d = json.loads(rp.read_text())
    except OSError as e:
        return fail(f"report unreadable: {e}", **base), {"report": rp.name, "tag": tag}
    except ValueError as e:
        return fail(f"report is not valid JSON: {e}", **base), {"report": rp.name, "tag": tag}
    meta = {"report": rp.name, "tag": tag, "vdd_v": sched["vdd_v"], "skew": sched["skew"],
            "status": d.get("status"), "corner_count": d.get("corner_count"),
            "remote": (d.get("environment") or {}).get("remote"),
            "klt": (d.get("provenance") or {}).get("klt_version"),
            "synthetic": bool(d.get("synthetic"))}
    corners = d.get("corners")
    if not isinstance(corners, list) or not corners:
        return [base | {"process": None, "verdict": "FAIL", "status": "FAIL: report has no corners"}], meta
    rows = []
    if d.get("corner_count") not in (None, len(corners)):
        rows.append(base | {"process": None, "verdict": "FAIL",
                            "status": f"FAIL: corner_count {d.get('corner_count')} != {len(corners)} corners listed"})
    for c in corners:
        cb = base | {"process": c.get("process"), "temp_c": c.get("temperature_c")}
        if c.get("status") in (None, "error"):
            rows.append(cb | {"verdict": "FAIL", "status": f"FAIL: klt corner status {c.get('status')!r}"})
            continue
        wfp = (c.get("artifacts") or {}).get("waveform")
        if not wfp:
            rows.append(cb | {"verdict": "FAIL", "status": "FAIL: no waveform artifact"})
            continue
        wfp = Path(wfp)
        if artifacts_root:
            wfp = Path(artifacts_root) / wfp.parent.name / wfp.name
        try:
            t, clk, vdd = wfa.load_waveform(wfp)
            rows += [cb | x for x in analyse_corner(t, clk, vdd, sched, p)]
        except AnalysisError as e:
            rows.append(cb | {"verdict": "FAIL", "status": f"FAIL: {e}"})
    return rows, meta


# ---------------------------------------------------------------- reports --

def aggregate(rows):
    """Group events by corner x step (process, vdd, skew, block, dir)."""
    groups: dict[tuple, list] = {}
    for r in rows:
        key = (r.get("process"), r.get("vdd_v"), r.get("skew"), r.get("block"), r.get("dir"))
        groups.setdefault(key, []).append(r)
    out = []
    order = {"PASS": 0, "FLAG": 1, "VIOLATION": 2, "FAIL": 3}
    for key, g in groups.items():
        ok = [x for x in g if x.get("status") == "OK"]
        a = dict(zip(("process", "vdd_v", "skew", "block", "dir"), key))
        a["events"] = len(g)
        a["verdict"] = max((x["verdict"] for x in g), key=lambda v: order[v])
        if ok:
            a |= {"p_min_ns": min(x["p_min_s"] for x in ok) * 1e9,
                  "p_max_ns": max(x["p_max_s"] for x in ok) * 1e9,
                  "p_old_ns": sum(x["p_old_s"] for x in ok) / len(ok) * 1e9,
                  "p_new_ns": sum(x["p_new_s"] for x in ok) / len(ok) * 1e9,
                  "excursion_pct_max": max(x["excursion_pct"] for x in ok),
                  "runt": any(x["runt"] for x in ok), "missing_edge": any(x["missing_edge"] for x in ok),
                  "settle_max": (None if any(x["settle_cycles"] is None for x in ok)
                                 else max(x["settle_cycles"] for x in ok)),
                  "phase_min": min(x["phase_in_cycle"] for x in ok), "phase_max": max(x["phase_in_cycle"] for x in ok)}
        a["n_fail"] = len(g) - len(ok)
        out.append(a)
    return sorted(out, key=lambda a: tuple(str(a.get(k)) for k in ("vdd_v", "process", "skew", "block", "dir")))


CSV_FIELDS = ["tag", "process", "vdd_v", "skew", "block", "dir", "phase_idx", "from", "to", "bits_changed",
              "t_start_ns", "status", "verdict", "p_old_ns", "p_new_ns", "p_min_ns", "p_max_ns",
              "excursion_pct", "runt", "missing_edge", "settle_cycles", "phase_in_cycle"]


def flat(r):
    o = {k: r.get(k) for k in ("tag", "process", "vdd_v", "skew", "block", "dir", "from", "to",
                               "bits_changed", "t_start_ns", "status", "verdict", "excursion_pct",
                               "runt", "missing_edge", "settle_cycles")}
    o["phase_idx"] = r.get("phase_idx")
    o["phase_in_cycle"] = r.get("phase_in_cycle")
    for k in ("p_old", "p_new", "p_min", "p_max"):
        if f"{k}_s" in r:
            o[f"{k}_ns"] = r[f"{k}_s"] * 1e9
    return o


def write_run(out: Path, rows, metas, p: Params, synthetic: bool, note: str = ""):
    out = Path(out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run {out}")
    out.mkdir(parents=True)
    synthetic = synthetic or any(m.get("synthetic") for m in metas)
    banner = ("SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE" if synthetic else
              "Analysis of simulator output; evidence status is set by the originating campaign record")
    agg = aggregate(rows)
    counts = {v: sum(1 for r in rows if r.get("verdict") == v) for v in ("PASS", "FLAG", "VIOLATION", "FAIL")}
    doc = {"label": banner, "synthetic": synthetic,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "params": asdict(p), "note": note, "reports": metas, "n_events": len(rows),
           "verdict_counts": counts, "all_pass": counts["PASS"] == len(rows) and bool(rows),
           "no_violation": counts["VIOLATION"] == 0 and counts["FAIL"] == 0 and bool(rows),
           "aggregate": agg, "events": rows}
    (out / "results.json").write_text(json.dumps(doc, indent=1) + "\n")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in flat(r).items()})

    def g(x, f="%.4g"):
        return "-" if x is None else f % x
    L = [f"# Trim-transition analysis {out.name}", "", f"**{banner}**", ""]
    if note:
        L += [f"Note: {note}", ""]
    L += [f"{len(rows)} event row(s): {counts['PASS']} PASS, {counts['FLAG']} FLAG, "
          f"{counts['VIOLATION']} VIOLATION, {counts['FAIL']} FAIL.",
          "Screens (bench thresholds, not ratified spec rows): VIOLATION = runt / missing-extra edge / never settles; "
          f"FLAG = excursion > {p.exc_flag * 100:g} % or settle > {p.settle_flag} cycles.", "",
          "| process | VDD (V) | skew | step | dir | events | min P (ns) | max P (ns) | P old->new (ns) | excursion max (%) | runt | missing | settle max (cyc) | verdict |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in agg:
        L.append(f"| {a['process']} | {g(a['vdd_v'])} | {a['skew']} | {a['block']} | {a['dir']} | {a['events']} | "
                 f"{g(a.get('p_min_ns'), '%.3f')} | {g(a.get('p_max_ns'), '%.3f')} | "
                 f"{g(a.get('p_old_ns'), '%.3f')}->{g(a.get('p_new_ns'), '%.3f')} | {g(a.get('excursion_pct_max'), '%.2f')} | "
                 f"{a.get('runt', '-')} | {a.get('missing_edge', '-')} | {g(a.get('settle_max'), '%d')} | {a['verdict']}"
                 + (f" ({a['n_fail']} failed)" if a["n_fail"] else "") + " |")
    fails = [r for r in rows if r.get("status") != "OK"]
    if fails:
        L += ["", "## Failed rows", ""] + [f"- {r.get('tag')} {r.get('process')} {r.get('block')} {r.get('dir')}: {r['status']}"
                                          for r in fails[:50]]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="TAG=report.json (TAG e.g. v33_lsb_first)")
    ap.add_argument("--bench-dir", type=Path, default=HERE, help="dir with schedule_<TAG>.json")
    ap.add_argument("--artifacts-root", type=Path, default=None)
    ap.add_argument("--outdir", required=True, type=Path, help="NEW results directory (never overwritten)")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--runt-frac", type=float, default=Params.runt_frac)
    ap.add_argument("--settle-tol", type=float, default=Params.settle_tol)
    ap.add_argument("--exc-flag", type=float, default=Params.exc_flag)
    ap.add_argument("--settle-flag", type=int, default=Params.settle_flag)
    a = ap.parse_args()
    p = Params(runt_frac=a.runt_frac, settle_tol=a.settle_tol, exc_flag=a.exc_flag, settle_flag=a.settle_flag)
    rows, metas = [], []
    for spec in a.reports:
        if "=" not in spec:
            ap.error(f"{spec!r}: expected TAG=report.json")
        tag, rep = spec.split("=", 1)
        rr, mm = analyse_report(tag, Path(rep), a.bench_dir, p, a.artifacts_root)
        rows += rr
        metas.append(mm)
    doc = write_run(a.outdir, rows, metas, p, a.synthetic, a.note)
    c = doc["verdict_counts"]
    print(f"wrote {a.outdir}: {doc['n_events']} events, {c}; {doc['label']}")
    return 0 if doc["no_violation"] else 1


if __name__ == "__main__":
    sys.exit(main())
