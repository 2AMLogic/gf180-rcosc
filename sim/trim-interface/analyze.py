#!/usr/bin/env python3
"""Analyzer for the trim-pin DC selection / static-current characterization
(issue #106, offline increment).

Input : `klt sim --format json -o <outdir>` reports for the requests written by
        sim/trim-interface/prepare.py, given as TAG=report.json (TAG = request
        tag, e.g. v33_t3_bg1_m50).  provenance.json from prepare.py is read from
        --bench-dir.  Each corner's `artifacts.waveform` is a waveform.raw.json
        ({"variables": [{"name": ...}], "points": [[x, ...]]}); column 0 is the
        swept target-pin voltage.
Output: results.json / results.csv / summary.md in a NEW directory (refuses to
        overwrite).  Fixture runs (--synthetic) are labelled SYNTHETIC and are
        never measured evidence.

Definitions (volts, amperes, siemens; x = swept target-pin voltage 0..VDD):
  G(x)        bank effective conductance = I_into_p / (V(p) - V(m)),
              I_into_p = -I(VP)  (VP positive terminal drives p).  This is the
              complete bank response including the parallel poly resistor, NOT
              the isolated switch conductance.
  s(x)        selection = (G - G0) / (G1 - G0); G0, G1 at x=0 and x=VDD.
              Invalid unless G1-G0 > max(g_abs_min, g_rel_min*max(|G0|,|G1|)).
  low-selected s <= sel_low; high-selected s >= sel_high.  Raw boundaries are the
              linearly interpolated sel_low crossing (upper edge of the low region
              connected to 0) and sel_high crossing (lower edge of the high region
              connected to VDD).  Each level must be crossed exactly once; s may
              not fall more than mono_tol below its running maximum.
  adjusted    low = max(0, raw_low - margin*VDD); high = min(VDD, raw_high + margin*VDD)
  inverter trip  the unique interpolated crossing of v(tb<pin>) = trip_frac*VDD,
              reported as a DIAGNOSTIC only.
  input current  I_in = -I(VTIN) in amperes, positive INTO the DUT, plus |I_in|,
              at the leak_fracs biases.
Per-supply aggregate: minimum adjusted low bound and maximum adjusted high bound
over every pin, background, bias, process and temperature, with limiting case
ids, and the maximum |I_in| with its case.  Any missing, duplicate, unexpected,
failed or invalid case makes the aggregate INCOMPLETE.  No aggregate is ever
labelled PASS: the outputs are characterized low/high bounds (screens pending
ratification), not guaranteed VIL/VIH.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


prepare = _load("ti_prepare", HERE / "prepare.py")
D = prepare.DEFAULTS
EPS = 1e-9  # level-comparison slack in s (floating point only)


class AnalysisError(Exception):
    """A case cannot be analysed; message becomes the FAIL reason."""


@dataclass(frozen=True)
class Params:
    step_frac: float = D["step_frac"]
    sel_low: float = D["sel_low"]
    sel_high: float = D["sel_high"]
    margin_frac: float = D["margin_frac"]
    mono_tol: float = D["mono_tol"]
    g_abs_min_s: float = D["g_abs_min_s"]
    g_rel_min: float = D["g_rel_min"]
    trip_frac: float = D["trip_frac"]
    leak_fracs: tuple = D["leak_fracs"]


# ---------------------------------------------------------------- waveform --

def _col(names, cands, what):
    hits = [i for i, n in enumerate(names) if n in cands]
    if len(hits) != 1:
        raise AnalysisError(f"signal {what}: expected exactly one of {sorted(cands)}, found {len(hits)}")
    return hits[0]


def parse_sweep(w, pin: int):
    """Validate a DC-sweep waveform dict; return (x, tb, i_vp, i_vtin)."""
    if not isinstance(w, dict) or "variables" not in w or "points" not in w:
        raise AnalysisError("waveform lacks variables/points")
    names = [str(v.get("name", "")).lower() for v in w["variables"]]
    cols = {
        "tb": _col(names, {f"v(xbank.tb{pin})", f"v(tb{pin})", f"v(x.xbank.tb{pin})"}, f"v(tb{pin})"),
        "ip": _col(names, {"i(vp)", "vp#branch", "i(v.vp)"}, "i(VP)"),
        "iin": _col(names, {"i(vtin)", "vtin#branch", "i(v.vtin)"}, "i(VTIN)"),
    }
    pts = w["points"]
    if not isinstance(pts, list) or len(pts) < 3:
        raise AnalysisError("waveform has fewer than 3 points")
    x, tb, ip, iin = [], [], [], []
    for k, p in enumerate(pts):
        if len(p) != len(names):
            raise AnalysisError(f"point {k} has {len(p)} values for {len(names)} variables")
        try:
            vals = [float(p[0]), float(p[cols["tb"]]), float(p[cols["ip"]]), float(p[cols["iin"]])]
        except (TypeError, ValueError) as e:
            raise AnalysisError(f"non-numeric value at point {k}") from e
        if not all(math.isfinite(v) for v in vals):
            raise AnalysisError(f"non-finite value at point {k}")
        x.append(vals[0]); tb.append(vals[1]); ip.append(vals[2]); iin.append(vals[3])
    for k in range(1, len(x)):
        if not x[k] > x[k - 1]:
            raise AnalysisError(f"sweep is not strictly increasing at point {k} (out-of-order or duplicate samples)")
    return x, tb, ip, iin


def load_sweep(path: Path, pin: int):
    try:
        return parse_sweep(json.loads(Path(path).read_text()), pin)
    except OSError as e:
        raise AnalysisError(f"waveform unreadable: {e}") from e
    except ValueError as e:
        raise AnalysisError(f"waveform is not valid JSON: {e}") from e


# ---------------------------------------------------------------- analysis --

def _interp(x0, y0, x1, y1, level):
    if y1 == y0:
        return x0
    return x0 + (level - y0) / (y1 - y0) * (x1 - x0)


def _crossings(y, level, eps=0.0):
    """Indices i such that the side of `level` changes between i-1 and i.
    side(v) = v > level + eps (a strict partition, so no double counting)."""
    side = [v > level + eps for v in y]
    return [i for i in range(1, len(y)) if side[i] != side[i - 1]]


def analyse_sweep(x, tb, ip, iin, vdd: float, mfrac: float, p: Params = Params()) -> dict:
    """Analyse one case.  Raises AnalysisError (explicit failure) for any
    invalid, unresolved, ambiguous or nonmonotone response."""
    n = prepare.sweep_points(vdd, p.step_frac)
    if len(x) != n:
        raise AnalysisError(f"expected {n} sweep points (0..VDD step {p.step_frac:g} VDD), got {len(x)}")
    tol = 1e-4 * vdd  # grid-match tolerance, absolute volts
    for k in range(n):
        if abs(x[k] - k * p.step_frac * vdd) > tol:
            raise AnalysisError(f"sweep sample {k} at {x[k]:.6g} V is not on the {k * p.step_frac * vdd:.6g} V grid "
                                "(rail endpoints must be included)")
    dv = vdd - mfrac * vdd
    if not dv > 0:
        raise AnalysisError("V(p)-V(m) must be positive")
    g = [-i / dv for i in ip]  # I_into_p = -I(VP)
    g0, g1 = g[0], g[-1]
    sep = g1 - g0
    if not sep > max(p.g_abs_min_s, p.g_rel_min * max(abs(g0), abs(g1))):
        raise AnalysisError(f"endpoint conductance unresolved: G0={g0:.4g} S, G1={g1:.4g} S")
    s = [(v - g0) / sep for v in g]
    run = s[0]
    for k, v in enumerate(s):
        run = max(run, v)
        if run - v > p.mono_tol:
            raise AnalysisError(f"nonmonotone selection at sample {k}: s={v:.4g} is {run - v:.4g} below its running maximum")
    # low-selected: s <= sel_low  -> side False; crossing = first not-low sample
    cl = _crossings(s, p.sel_low, EPS)
    ch = _crossings([-v for v in s], -p.sel_high, EPS)  # side: -s > -sel_high  <=> s < sel_high
    if len(cl) != 1:
        raise AnalysisError(f"sel_low={p.sel_low:g} level crossed {len(cl)} times (need exactly 1)")
    if len(ch) != 1:
        raise AnalysisError(f"sel_high={p.sel_high:g} level crossed {len(ch)} times (need exactly 1)")
    k = cl[0]
    raw_low = _interp(x[k - 1], s[k - 1], x[k], s[k], p.sel_low)
    k = ch[0]
    raw_high = _interp(x[k - 1], s[k - 1], x[k], s[k], p.sel_high)
    if not raw_low < raw_high:
        raise AnalysisError(f"raw low boundary {raw_low:.4g} V is not below raw high boundary {raw_high:.4g} V")
    low_adj = max(0.0, raw_low - p.margin_frac * vdd)
    high_adj = min(vdd, raw_high + p.margin_frac * vdd)
    tc = _crossings(tb, p.trip_frac * vdd)
    if len(tc) != 1:
        raise AnalysisError(f"v(tb) crossed {p.trip_frac:g} VDD {len(tc)} times (need exactly 1)")
    k = tc[0]
    trip = _interp(x[k - 1], tb[k - 1], x[k], tb[k], p.trip_frac * vdd)
    cur = {}
    for f in p.leak_fracs:
        idx = round(f / p.step_frac)
        if abs(x[idx] - f * vdd) > tol:
            raise AnalysisError(f"leakage bias {f:g} VDD is not a sweep sample")
        cur[f] = -iin[idx]  # positive into the DUT
    worst_f = max(cur, key=lambda f: abs(cur[f]))
    row = {
        "status": "OK", "valid": True,
        "g0_s": g0, "g1_s": g1,
        "raw_low_v": raw_low, "raw_high_v": raw_high,
        "raw_low_frac": raw_low / vdd, "raw_high_frac": raw_high / vdd,
        "low_bound_v": low_adj, "high_bound_v": high_adj,
        "low_bound_frac": low_adj / vdd, "high_bound_frac": high_adj / vdd,
        "inverter_trip_v": trip, "inverter_trip_frac": trip / vdd,
        "max_abs_input_current_a": abs(cur[worst_f]), "max_abs_input_current_bias_frac": worst_f,
    }
    for f in p.leak_fracs:
        key = f"{round(f * 100):03d}"
        row[f"i_in_{key}_a"] = cur[f]
        row[f"abs_i_in_{key}_a"] = abs(cur[f])
    return row


# ------------------------------------------------------------- aggregation --

def aggregate(rows: list[dict], expected: list[dict]) -> list[dict]:
    """Per-supply worst-case aggregation.  `expected` is prepare.all_cases().
    Returns one dict per supply; `complete` is False for any missing,
    duplicate, unexpected, failed or invalid case."""
    exp_ids = {c["id"] for c in expected}
    by_id: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("id") is not None:
            by_id.setdefault(r["id"], []).append(r)
    out = []
    for vdd in sorted({c["vdd_v"] for c in expected}):
        want = [c["id"] for c in expected if c["vdd_v"] == vdd]
        missing = [i for i in want if i not in by_id]
        dup = [i for i in want if len(by_id.get(i, [])) > 1]
        unexpected = sorted({r.get("id") or f"<no-id:{r.get('status')}>" for r in rows
                             if r.get("vdd_v") == vdd and (r.get("id") is None or r["id"] not in exp_ids)})
        failed = [i for i in want if i in by_id and any(r.get("status") != "OK" or not r.get("valid") for r in by_id[i])]
        unattributed = [r for r in rows if r.get("id") is None and r.get("vdd_v") == vdd]
        good = [by_id[i][0] for i in want if i in by_id and len(by_id[i]) == 1
                and by_id[i][0].get("status") == "OK" and by_id[i][0].get("valid")]
        complete = not (missing or dup or unexpected or failed or unattributed) and len(good) == len(want)
        agg = {"vdd_v": vdd, "complete": complete,
               "verdict": "CHARACTERIZED (screens pending ratification; not a guaranteed VIL/VIH)" if complete else "INCOMPLETE",
               "n_expected": len(want), "n_ok": len(good), "missing": missing, "duplicate": dup,
               "unexpected": unexpected, "failed": failed, "partial": not complete}
        if good:
            lo = min(good, key=lambda r: (r["low_bound_v"], r["id"]))
            hi = max(good, key=lambda r: (r["high_bound_v"], r["id"]))
            cu = max(good, key=lambda r: (r["max_abs_input_current_a"], r["id"]))
            agg |= {"min_low_bound_v": lo["low_bound_v"], "min_low_bound_frac": lo["low_bound_frac"],
                    "min_low_bound_case": lo["id"],
                    "max_high_bound_v": hi["high_bound_v"], "max_high_bound_frac": hi["high_bound_frac"],
                    "max_high_bound_case": hi["id"],
                    "max_abs_input_current_a": cu["max_abs_input_current_a"], "max_abs_input_current_case": cu["id"],
                    "max_abs_input_current_bias_frac": cu["max_abs_input_current_bias_frac"]}
        out.append(agg)
    return out


# ----------------------------------------------------------------- reports --

def analyse_report(tag: str, report_path: Path, meta: dict, p: Params = Params(), artifacts_root=None):
    """meta = the provenance request entry for `tag` (vdd_v, pin, background,
    m_frac).  Returns (rows, report_meta)."""
    rp = Path(report_path)
    base = {"tag": tag, "report": rp.name, "vdd_v": meta["vdd_v"], "pin": meta["pin"],
            "background": meta["background"], "m_frac": meta["m_frac"]}

    def fail(msg, **kw):
        return [base | {"id": None, "valid": False, "status": f"FAIL: {msg}"} | kw]
    rmeta = {"report": rp.name, "tag": tag}
    try:
        d = json.loads(rp.read_text())
    except OSError as e:
        return fail(f"report unreadable: {e}"), rmeta
    except ValueError as e:
        return fail(f"report is not valid JSON: {e}"), rmeta
    rmeta |= {"status": d.get("status"), "corner_count": d.get("corner_count"),
              "remote": (d.get("environment") or {}).get("remote"),
              "klt": (d.get("provenance") or {}).get("klt_version"), "synthetic": bool(d.get("synthetic"))}
    corners = d.get("corners")
    if not isinstance(corners, list) or not corners:
        return fail("report has no corners"), rmeta
    rows = []
    if d.get("status") != "pass":
        rows += fail(f"report status {d.get('status')!r} is not 'pass'")
    if d.get("corner_count") not in (None, len(corners)):
        rows += fail(f"corner_count {d.get('corner_count')} != {len(corners)} corners listed")
    for c in corners:
        proc, temp = c.get("process"), c.get("temperature_c")
        try:
            cid = prepare.case_id(proc, float(temp), meta["vdd_v"], meta["pin"], meta["background"], meta["m_frac"])
        except (TypeError, ValueError):
            rows += fail(f"corner has unusable process/temperature {proc!r}/{temp!r}")
            continue
        cb = base | {"id": cid, "process": proc, "temp_c": float(temp)}
        if c.get("status") != "pass":
            rows.append(cb | {"valid": False, "status": f"FAIL: klt corner status {c.get('status')!r}"})
            continue
        wfp = (c.get("artifacts") or {}).get("waveform")
        if not wfp:
            rows.append(cb | {"valid": False, "status": "FAIL: no waveform artifact"})
            continue
        wfp = Path(wfp)
        if artifacts_root:
            wfp = Path(artifacts_root) / wfp.parent.name / wfp.name
        try:
            x, tb, ip, iin = load_sweep(wfp, meta["pin"])
            rows.append(cb | analyse_sweep(x, tb, ip, iin, meta["vdd_v"], meta["m_frac"], p))
        except AnalysisError as e:
            rows.append(cb | {"valid": False, "status": f"FAIL: {e}"})
    return rows, rmeta


# ----------------------------------------------------------------- outputs --

def csv_fields(p: Params) -> list[str]:
    f = ["id", "tag", "process", "temp_c", "vdd_v", "pin", "background", "m_frac", "valid", "status",
         "g0_s", "g1_s", "raw_low_v", "raw_high_v", "raw_low_frac", "raw_high_frac",
         "low_bound_v", "high_bound_v", "low_bound_frac", "high_bound_frac",
         "inverter_trip_v", "inverter_trip_frac"]
    for fr in p.leak_fracs:
        k = f"{round(fr * 100):03d}"
        f += [f"i_in_{k}_a", f"abs_i_in_{k}_a"]
    return f + ["max_abs_input_current_a", "max_abs_input_current_bias_frac"]


def write_run(out: Path, rows, metas, expected, p: Params, synthetic: bool, note: str = ""):
    out = Path(out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run {out}")
    out.mkdir(parents=True)
    synthetic = synthetic or any(m.get("synthetic") for m in metas)
    banner = ("SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE" if synthetic else
              "Analysis of simulator output; evidence status is set by the originating campaign record")
    agg = aggregate(rows, expected)
    complete = bool(agg) and all(a["complete"] for a in agg)
    doc = {"label": banner, "synthetic": synthetic,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "params": asdict(p), "note": note,
           "conventions": {"input_current": "I_in = -I(VTIN), amperes, positive into the DUT; abs reported too",
                           "bank_current": "I_into_p = -I(VP)", "conductance": "S", "voltage": "V",
                           "names": "characterized low/high bounds (screens), not guaranteed VIL/VIH"},
           "reports": metas, "n_rows": len(rows), "n_expected": len(expected),
           "complete": complete, "aggregate": agg, "cases": rows}
    (out / "results.json").write_text(json.dumps(doc, indent=1) + "\n")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields(p), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})

    def g(a, k, f="%.4g"):
        return "-" if a.get(k) is None else f % a[k]
    L = [f"# Trim-interface DC analysis {out.name}", "", f"**{banner}**", ""]
    if note:
        L += [f"Note: {note}", ""]
    L += [f"{len(rows)} row(s) for {len(expected)} expected cases; overall: "
          f"{'COMPLETE' if complete else 'INCOMPLETE'}.",
          "Bounds are characterized screens (selection thresholds "
          f"{p.sel_low:g}/{p.sel_high:g}, margin {p.margin_frac:g} VDD), not guaranteed VIL/VIH; "
          "no verdict here is a PASS.", "",
          "| VDD (V) | status | ok/expected | min low bound (V, frac) | limiting case | max high bound (V, frac) | limiting case | max abs I_in (A) | case |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a in agg:
        L.append(f"| {a['vdd_v']:g} | {a['verdict'].split(' ')[0]} | {a['n_ok']}/{a['n_expected']} | "
                 f"{g(a, 'min_low_bound_v')}, {g(a, 'min_low_bound_frac', '%.3f')} | {a.get('min_low_bound_case', '-')} | "
                 f"{g(a, 'max_high_bound_v')}, {g(a, 'max_high_bound_frac', '%.3f')} | {a.get('max_high_bound_case', '-')} | "
                 f"{g(a, 'max_abs_input_current_a', '%.3e')} | {a.get('max_abs_input_current_case', '-')} |")
    for a in agg:
        if not a["complete"]:
            L += ["", f"## Incomplete: VDD {a['vdd_v']:g} V",
                  f"- missing: {len(a['missing'])}, duplicate: {len(a['duplicate'])}, "
                  f"unexpected: {len(a['unexpected'])}, failed/invalid: {len(a['failed'])}"]
    fails = [r for r in rows if r.get("status") != "OK"]
    if fails:
        L += ["", "## Failed rows", ""] + [f"- {r.get('id') or r.get('tag')}: {r['status']}" for r in fails[:50]]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="TAG=report.json (TAG e.g. v33_t3_bg1_m50)")
    ap.add_argument("--bench-dir", type=Path, default=HERE, help="dir with provenance.json from prepare.py")
    ap.add_argument("--artifacts-root", type=Path, default=None)
    ap.add_argument("--outdir", required=True, type=Path, help="NEW results directory (never overwritten)")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--sel-low", type=float, default=Params.sel_low)
    ap.add_argument("--sel-high", type=float, default=Params.sel_high)
    ap.add_argument("--margin-frac", type=float, default=Params.margin_frac)
    a = ap.parse_args()
    p = Params(sel_low=a.sel_low, sel_high=a.sel_high, margin_frac=a.margin_frac)
    try:
        prov = json.loads((a.bench_dir / "provenance.json").read_text())
    except (OSError, ValueError) as e:
        ap.error(f"provenance.json unreadable in {a.bench_dir}: {e}")
    tags = {r["tag"]: r for r in prov["requests"]}
    rows, metas = [], []
    for spec in a.reports:
        if "=" not in spec:
            ap.error(f"{spec!r}: expected TAG=report.json")
        tag, rep = spec.split("=", 1)
        if tag not in tags:
            ap.error(f"unknown request tag {tag!r}")
        rr, mm = analyse_report(tag, Path(rep), tags[tag], p, a.artifacts_root)
        rows += rr
        metas.append(mm)
    doc = write_run(a.outdir, rows, metas, prepare.all_cases(), p, a.synthetic, a.note)
    print(f"wrote {a.outdir}: {doc['n_rows']} rows, complete={doc['complete']}; {doc['label']}")
    return 0 if doc["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
