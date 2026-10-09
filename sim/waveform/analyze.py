#!/usr/bin/env python3
"""Analyzer for the clk waveform-shape bench (issue #91, offline subset).

Input : `klt sim --format json -o <outdir>` reports for the requests written by
        sim/waveform/prepare.py.  Each corner's `artifacts.waveform` is a
        waveform.raw.json ({"variables": [{"name": ...}], "points": [[t, ...]]})
        -- the same convention sim/startup/startup_report.py reads -- or is
        resolved under --artifacts-root.
Output: results.json / results.csv / summary.md in a NEW directory (refuses to
        overwrite).  Fixture runs (--synthetic) are labelled SYNTHETIC and are
        never measured evidence.

Definitions (all times in seconds, voltages in volts, SI units in the JSON):
  level            50 % of the NOMINAL supply (--vdd), linear interpolation.
  r[i], f[i]       rising / falling crossings inside the steady window (final
                   `window` seconds), strictly alternating or the corner FAILS.
  complete cycle   r[i] -> f[i] -> r[i+1].  A leading falling edge before the
                   first rising edge, and a trailing falling edge after the last
                   rising edge, are incomplete boundary cycles: omitted, counted.
  P[i]=r[i+1]-r[i]   period            H[i]=f[i]-r[i]  high (pulse) width
  L[i]=r[i+1]-f[i]   low width         duty[i]=H[i]/P[i]
  c2c[i]=P[i+1]-P[i] cycle-to-cycle period difference
  rise / fall time 10-90 % / 90-10 % of nominal VDD on the SAME transition
                   (the one whose 50 % crossing is r[i] / f[i]).
  period p2p       max(P)-min(P), deterministic.
  period std       POPULATION standard deviation of P (std_deterministic_s).
                   Noiseless simulation: this is deterministic spread including
                   settling and solver/sample artifacts.  It is NOT RMS
                   stochastic jitter, and is not named jitter anywhere here.
  unsettled tail   |mean(P, last h) - mean(P, first h)| / mean(P)
                   (h = floor(n/2) rounded down to even) greater than --drift-tol, or the rail outside --vdd-tol of
                   nominal in the window.
Failures are explicit (status "FAIL: <reason>", no metrics); nothing is
imputed or defaulted to a passing number.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


class AnalysisError(Exception):
    """A corner cannot be analysed; message becomes the FAIL reason."""


@dataclass(frozen=True)
class Params:
    window_s: float = 2e-6
    min_cycles: int = 20
    min_samples_per_cycle: float = 10.0
    drift_tol: float = 0.005
    vdd_tol: float = 0.02


# ---------------------------------------------------------------- waveform --

def parse_waveform(w) -> tuple[list[float], list[float], list[float]]:
    """Validate a waveform dict and return (t, v(clk), v(vdd))."""
    if not isinstance(w, dict) or "variables" not in w or "points" not in w:
        raise AnalysisError("waveform lacks variables/points")
    names = [str(x.get("name", "")).lower() for x in w["variables"]]
    for need in ("v(clk)", "v(vdd)"):
        if need not in names:
            raise AnalysisError(f"missing signal {need}")
    ic, iv = names.index("v(clk)"), names.index("v(vdd)")
    pts = w["points"]
    if not isinstance(pts, list) or len(pts) < 2:
        raise AnalysisError("waveform has fewer than 2 points")
    t, clk, vdd = [], [], []
    for k, p in enumerate(pts):
        if len(p) != len(names):
            raise AnalysisError(f"point {k} has {len(p)} values for {len(names)} variables")
        try:
            tv, cv, vv = float(p[0]), float(p[ic]), float(p[iv])
        except (TypeError, ValueError) as e:
            raise AnalysisError(f"non-numeric value at point {k}") from e
        if not (math.isfinite(tv) and math.isfinite(cv) and math.isfinite(vv)):
            raise AnalysisError(f"non-finite value at point {k}")
        t.append(tv); clk.append(cv); vdd.append(vv)
    for k in range(1, len(t)):
        if not t[k] > t[k - 1]:
            raise AnalysisError(f"time is not strictly increasing at point {k}")
    return t, clk, vdd


def load_waveform(path: Path):
    try:
        return parse_waveform(json.loads(Path(path).read_text()))
    except OSError as e:
        raise AnalysisError(f"waveform unreadable: {e}") from e
    except ValueError as e:
        raise AnalysisError(f"waveform is not valid JSON: {e}") from e


def crossings(t, v, level):
    """All interpolated level crossings as (time, 'r'|'f', segment index i),
    the crossing lying in segment (i-1, i)."""
    out = []
    for i in range(1, len(t)):
        a, b = v[i - 1], v[i]
        if a < level <= b:
            kind = "r"
        elif a >= level > b:
            kind = "f"
        else:
            continue
        out.append((t[i - 1] + (level - a) / (b - a) * (t[i] - t[i - 1]), kind, i))
    return out


def _stats(x):
    n = len(x)
    if n == 0:
        raise AnalysisError("no values to summarise")
    m = sum(x) / n
    return {"count": n, "mean": m, "min": min(x), "max": max(x),
            "peak_to_peak": max(x) - min(x),
            "std_deterministic": math.sqrt(sum((q - m) ** 2 for q in x) / n)}


def _transition_time(t, v, seg, kind, lo, hi, prev_t, next_t):
    """10-90 (kind 'r') or 90-10 ('f') time of the transition whose 50 %
    crossing lies in segment (seg-1, seg).  prev_t/next_t bound the transition
    (neighbouring opposite 50 % crossings, or None)."""
    n = len(t)
    first, second = (lo, hi) if kind == "r" else (hi, lo)
    sgn = 1 if kind == "r" else -1

    def before(x):  # still on the near side of `first` level
        return sgn * (x - first) > 0

    j = seg - 1
    while j >= 0 and before(v[j]):
        j -= 1
    if j < 0:
        raise AnalysisError("transition start (10/90 % level) not in waveform")
    t_first = t[j] + (first - v[j]) / (v[j + 1] - v[j]) * (t[j + 1] - t[j])
    k = seg
    while k < n and sgn * (v[k] - second) < 0:
        k += 1
    if k >= n:
        raise AnalysisError("transition end (90/10 % level) not in waveform")
    t_second = t[k - 1] + (second - v[k - 1]) / (v[k] - v[k - 1]) * (t[k] - t[k - 1])
    if (prev_t is not None and t_first < prev_t) or (next_t is not None and t_second > next_t):
        raise AnalysisError("clk does not swing through the 10-90 % levels on every transition")
    return t_second - t_first


def analyse(t, clk, vdd, vdd_nom, p: Params = Params()):
    """Metrics for one corner.  Raises AnalysisError on any invalid/inadequate
    data; never returns partial or defaulted numbers."""
    if not (vdd_nom > 0 and math.isfinite(vdd_nom)):
        raise AnalysisError("nominal vdd must be positive and finite")
    tstop = t[-1]
    w0 = tstop - p.window_s
    if w0 <= t[0]:
        raise AnalysisError("run is shorter than the steady window")
    in_win = [k for k in range(len(t)) if t[k] >= w0]
    mid = vdd_nom / 2
    cr = [c for c in crossings(t, clk, mid) if c[0] >= w0]
    if len(cr) < 4:
        raise AnalysisError(f"missing crossings: {len(cr)} in the steady window")
    for a, b in zip(cr, cr[1:]):
        if a[1] == b[1]:
            raise AnalysisError("invalid crossing order: two consecutive "
                                f"{'rising' if a[1] == 'r' else 'falling'} crossings")
    lead = 0
    while cr and cr[0][1] == "f":
        cr = cr[1:]
        lead += 1
    trail = 0
    while cr and cr[-1][1] == "f":
        cr = cr[:-1]
        trail += 1
    r = [c for c in cr if c[1] == "r"]
    f = [c for c in cr if c[1] == "f"]
    ncyc = len(r) - 1
    if ncyc < p.min_cycles:
        raise AnalysisError(f"insufficient cycles: {max(ncyc, 0)} complete in window, need {p.min_cycles}")
    if len(f) != ncyc:  # guaranteed by alternation; guard anyway
        raise AnalysisError("invalid crossing order: rising/falling counts inconsistent")
    P = [r[i + 1][0] - r[i][0] for i in range(ncyc)]
    H = [f[i][0] - r[i][0] for i in range(ncyc)]
    L = [r[i + 1][0] - f[i][0] for i in range(ncyc)]
    if not all(h > 0 and l > 0 and q > 0 for h, l, q in zip(H, L, P)):
        raise AnalysisError("invalid crossing order: non-positive width")
    # samples in the span of the analysed cycles
    span0, span1 = r[0][0], r[-1][0]
    nsamp = sum(1 for x in t if span0 <= x <= span1)
    sps = nsamp / ncyc
    if sps < p.min_samples_per_cycle:
        raise AnalysisError(f"insufficient samples: {sps:.1f} per cycle, need {p.min_samples_per_cycle:g}")
    # rail check
    vw = [vdd[k] for k in in_win]
    vmean = sum(vw) / len(vw)
    if max(abs(x - vdd_nom) for x in vw) > p.vdd_tol * vdd_nom:
        raise AnalysisError(f"unsettled rail: v(vdd) leaves +/-{p.vdd_tol * 100:g}% of {vdd_nom:g} V in the window")
    # tail drift
    h = (ncyc // 2) & ~1  # even, so a strict 2-cycle alternation is not read as drift
    m0, m1 = sum(P[:h]) / h, sum(P[ncyc - h:]) / h
    drift = (m1 - m0) / (sum(P) / ncyc)
    if abs(drift) > p.drift_tol:
        raise AnalysisError(f"unsettled tail: period drifts {drift * 100:+.3f}% between window halves "
                            f"(tolerance {p.drift_tol * 100:g}%)")
    # transitions, using all crossings (not only windowed) to bound them
    allc = crossings(t, clk, mid)
    times = [c[0] for c in allc]
    lo, hi = 0.1 * vdd_nom, 0.9 * vdd_nom

    def bounds(tc):
        k = times.index(tc)
        return (times[k - 1] if k > 0 else None, times[k + 1] if k + 1 < len(times) else None)

    rise, fall = [], []
    for c in r:
        pt, nt = bounds(c[0])
        rise.append(_transition_time(t, clk, c[2], "r", lo, hi, pt, nt))
    for c in f:
        pt, nt = bounds(c[0])
        fall.append(_transition_time(t, clk, c[2], "f", lo, hi, pt, nt))
    duty = [h_ / q for h_, q in zip(H, P)]
    c2c = [P[i + 1] - P[i] for i in range(ncyc - 1)]
    c2cs = _stats(c2c) if c2c else None
    if c2cs:
        c2cs["max_abs"] = max(abs(x) for x in c2c)
    return {
        "units": {"time": "s", "voltage": "V", "duty": "ratio"},
        "level_v": mid, "vdd_nominal_v": vdd_nom, "vdd_window_mean_v": vmean,
        "window_s": p.window_s, "window_start_s": w0, "tstop_s": tstop,
        "n_complete_cycles": ncyc, "samples_per_cycle": sps,
        "omitted_boundary": {"leading_falling_edges": lead, "trailing_falling_edges": trail},
        "period_s": _stats(P),
        "frequency_mean_hz": 1.0 / (sum(P) / ncyc),
        "pulse_high_s": _stats(H), "pulse_low_s": _stats(L), "duty": _stats(duty),
        "rise_time_10_90_s": _stats(rise), "fall_time_90_10_s": _stats(fall),
        "cycle_to_cycle_s": c2cs,
        "tail_drift_fraction": drift,
        "spread_kind": ("deterministic (noiseless transient): includes settling and "
                        "solver/sample artifacts; NOT stochastic RMS jitter"),
    }


# ----------------------------------------------------------------- reports --

def analyse_report(report_path: Path, vdd_nom: float, p: Params = Params(),
                   artifacts_root: Path | None = None):
    """Rows (one per corner) for a klt sim report.  A missing/failed report
    yields a single FAIL row rather than silence."""
    rp = Path(report_path)
    base = {"report": rp.name, "vdd_v": vdd_nom}
    try:
        d = json.loads(rp.read_text())
    except OSError as e:
        return [base | {"process": None, "temp_c": None, "status": f"FAIL: report unreadable: {e}"}], {}
    except ValueError as e:
        return [base | {"process": None, "temp_c": None, "status": f"FAIL: report is not valid JSON: {e}"}], {}
    meta = {"report": rp.name, "vdd_v": vdd_nom, "status": d.get("status"),
            "corner_count": d.get("corner_count"),
            "remote": (d.get("environment") or {}).get("remote"),
            "synthetic": bool(d.get("synthetic"))}
    corners = d.get("corners")
    if not isinstance(corners, list) or not corners:
        return [base | {"process": None, "temp_c": None, "status": "FAIL: report has no corners"}], meta
    rows = []
    if d.get("corner_count") not in (None, len(corners)):
        rows.append(base | {"process": None, "temp_c": None,
                            "status": f"FAIL: corner_count {d.get('corner_count')} != {len(corners)} corners listed"})
    for c in corners:
        row = base | {"process": c.get("process"), "temp_c": c.get("temperature_c")}
        if c.get("status") in (None, "error"):
            row["status"] = f"FAIL: klt corner status {c.get('status')!r}"
            rows.append(row)
            continue
        wf = (c.get("artifacts") or {}).get("waveform")
        if not wf:
            row["status"] = "FAIL: no waveform artifact"
            rows.append(row)
            continue
        wf = Path(wf)
        if artifacts_root:
            wf = Path(artifacts_root) / wf.parent.name / wf.name
        try:
            t, clk, vdd = load_waveform(wf)
            row["metrics"] = analyse(t, clk, vdd, vdd_nom, p)
            row["status"] = "OK"
        except AnalysisError as e:
            row["status"] = f"FAIL: {e}"
        rows.append(row)
    return rows, meta


FIELDS = ["process", "temp_c", "vdd_v", "status", "n_cycles", "period_mean_ns", "period_p2p_ps",
          "period_std_det_ps", "c2c_max_abs_ps", "high_mean_ns", "low_mean_ns", "duty_mean",
          "duty_min", "duty_max", "rise_mean_ps", "fall_mean_ps"]


def flat(r):
    m = r.get("metrics")
    out = {k: r.get(k) for k in ("process", "temp_c", "vdd_v", "status")}
    if m:
        c2c = m["cycle_to_cycle_s"]
        out |= {"n_cycles": m["n_complete_cycles"],
                "period_mean_ns": m["period_s"]["mean"] * 1e9,
                "period_p2p_ps": m["period_s"]["peak_to_peak"] * 1e12,
                "period_std_det_ps": m["period_s"]["std_deterministic"] * 1e12,
                "c2c_max_abs_ps": c2c["max_abs"] * 1e12 if c2c else None,
                "high_mean_ns": m["pulse_high_s"]["mean"] * 1e9,
                "low_mean_ns": m["pulse_low_s"]["mean"] * 1e9,
                "duty_mean": m["duty"]["mean"], "duty_min": m["duty"]["min"], "duty_max": m["duty"]["max"],
                "rise_mean_ps": m["rise_time_10_90_s"]["mean"] * 1e12,
                "fall_mean_ps": m["fall_time_90_10_s"]["mean"] * 1e12}
    return out


def write_run(out: Path, rows, metas, p: Params, synthetic: bool, note: str = ""):
    out = Path(out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run {out}")
    out.mkdir(parents=True)
    synthetic = synthetic or any(m.get("synthetic") for m in metas)
    banner = ("SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE" if synthetic else
              "Analysis of simulator output; evidence status is set by the originating campaign record")
    nfail = sum(1 for r in rows if r["status"] != "OK")
    doc = {"label": banner, "synthetic": synthetic, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "params": asdict(p), "note": note, "reports": metas, "n_corners": len(rows),
           "n_fail": nfail, "all_ok": nfail == 0 and bool(rows), "corners": rows}
    (out / "results.json").write_text(json.dumps(doc, indent=2) + "\n")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in flat(r).items()})
    L = [f"# Waveform analysis {out.name}", "", f"**{banner}**", "",
         "Spread columns are deterministic (noiseless transient); they are not stochastic",
         "RMS jitter and not the external SOF-arrival jitter assumption.", ""]
    if note:
        L += [f"Note: {note}", ""]
    L += [f"{len(rows)} corner row(s), {nfail} failing.", "",
          "| process | T (C) | VDD (V) | status | cycles | period (ns) | p2p (ps) | std det (ps) | max abs c2c (ps) | high (ns) | low (ns) | duty | rise (ps) | fall (ps) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def g(x, f="%.4g"):
        return "-" if x is None else f % x
    for r in rows:
        x = flat(r)
        L.append(f"| {x['process']} | {g(x['temp_c'])} | {g(x['vdd_v'])} | {x['status']} | {g(x.get('n_cycles'), '%d')} | "
                 f"{g(x.get('period_mean_ns'))} | {g(x.get('period_p2p_ps'))} | {g(x.get('period_std_det_ps'))} | "
                 f"{g(x.get('c2c_max_abs_ps'))} | {g(x.get('high_mean_ns'))} | {g(x.get('low_mean_ns'))} | "
                 f"{g(x.get('duty_mean'))} | {g(x.get('rise_mean_ps'))} | {g(x.get('fall_mean_ps'))} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="klt sim JSON reports")
    ap.add_argument("--vdd", nargs="+", type=float, required=True, help="nominal supply per report, same order")
    ap.add_argument("--artifacts-root", nargs="*", type=Path, default=None)
    ap.add_argument("--outdir", required=True, type=Path, help="NEW results directory (never overwritten)")
    ap.add_argument("--synthetic", action="store_true", help="label the run as synthetic fixture output")
    ap.add_argument("--note", default="")
    ap.add_argument("--window-ns", type=float, default=Params.window_s * 1e9)
    ap.add_argument("--min-cycles", type=int, default=Params.min_cycles)
    ap.add_argument("--min-samples-per-cycle", type=float, default=Params.min_samples_per_cycle)
    ap.add_argument("--drift-tol", type=float, default=Params.drift_tol)
    ap.add_argument("--vdd-tol", type=float, default=Params.vdd_tol)
    a = ap.parse_args()
    if len(a.vdd) != len(a.reports):
        ap.error("--vdd needs one value per report")
    if a.artifacts_root is not None and len(a.artifacts_root) != len(a.reports):
        ap.error("--artifacts-root needs one dir per report")
    p = Params(a.window_ns * 1e-9, a.min_cycles, a.min_samples_per_cycle, a.drift_tol, a.vdd_tol)
    rows, metas = [], []
    for k, rep in enumerate(a.reports):
        rr, mm = analyse_report(Path(rep), a.vdd[k], p, a.artifacts_root[k] if a.artifacts_root else None)
        rows += rr
        metas.append(mm or {"report": Path(rep).name, "vdd_v": a.vdd[k]})
    doc = write_run(a.outdir, rows, metas, p, a.synthetic, a.note)
    print(f"wrote {a.outdir}: {doc['n_corners']} corner row(s), {doc['n_fail']} failing; {doc['label']}")
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
