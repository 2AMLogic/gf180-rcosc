#!/usr/bin/env python3
"""Interior-temperature curvature analyzer (issue #125, offline subset).

Input : the provenance.json written by sim/temperature/prepare.py and the
        `klt sim --format json` reports of its three requests.  Each corner's
        frequency is measured by sim/waveform/analyze.py (`analyse_report`,
        same failure semantics: any invalid waveform is an explicit FAIL row).
Output: results.json / results.csv / summary.md in a NEW directory (refuses to
        overwrite).  Fixture runs (--synthetic, or any report marked
        "synthetic") carry SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE.

Definitions, per process, on the 12-point axis T[0..11] (degrees C), with
f27 the freshly measured 27 C frequency of the SAME process / code:
  adjacent difference   d_i   = f[i+1]-f[i]                      (Hz, raw)
                        d_ppm = 1e6*(f[i+1]-f[i])/f27            (ppm of f27)
  adjacent slope        s_i   = 1e6*(f[i+1]-f[i])/(f27*(T[i+1]-T[i]))  (ppm/C)
  endpoint slope        1e6*(f(85)-f(-40))/(f27*125)              (ppm/C)
  curvature residual    r(T)  = 1e6*(f(T)-f_lin(T))/f27  (signed ppm), f_lin
                        the piecewise-linear interpolation of the measured
                        -40/27/85 C anchors (segment -40..27 and 27..85).
  tolerance             100 ppm of f27 (diagnostic, NOT a spec).  d_ppm > +100
                        rising, < -100 falling, otherwise flat (equality flat).
                        Monotonicity from the set of non-flat signs: none ->
                        flat, {rising} -> increasing, {falling} -> decreasing,
                        both -> nonmonotone.  |r| > 100 is flagged; equality is
                        inside tolerance.
Status per process: COMPLETE (all 12 valid), INCOMPLETE (missing / failed /
non-finite / non-positive points or anchors) or INVALID (duplicate, off-grid
or provenance-mismatched rows).  Only COMPLETE yields a monotonicity class or
curvature verdict; otherwise valid rows are kept as diagnostics, intervals and
residuals are computed only where their own endpoints/anchors are valid (no
interpolation across missing data).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tp = _load("rcosc_temperature_prepare", HERE / "prepare.py")
wa = _load("rcosc_waveform_analyze", tp.WAVEFORM / "analyze.py")

TEMPS_C = list(tp.TEMPS_C)
PROCESSES = tp.PROCESSES
TOL_PPM = tp.TOL_PPM
SYNTHETIC_LABEL = tp.SYNTHETIC_LABEL
MEASURED_LABEL = ("Analysis of simulator output; evidence status is set by the originating campaign "
                  "record (numerical convergence not established by this analysis)")
STATUS_RANK = {"COMPLETE": 0, "INCOMPLETE": 1, "INVALID": 2}


class ProvenanceError(Exception):
    pass


def grid_index(t, temps=TEMPS_C):
    """Index of temperature t on the axis, or None (off-grid / not a number)."""
    try:
        x = float(t)
    except (TypeError, ValueError):
        return None
    for i, g in enumerate(temps):
        if abs(x - g) <= 1e-9:
            return i
    return None


def valid_frequency(f) -> str | None:
    """None if f is a usable frequency, else the reason it is not."""
    if isinstance(f, bool) or not isinstance(f, (int, float)):
        return "frequency missing or not a number"
    if not math.isfinite(f):
        return "non-finite frequency"
    if f <= 0:
        return "non-positive frequency"
    return None


def classify(d_ppm: float, tol: float = TOL_PPM) -> str:
    if d_ppm > tol:
        return "rising"
    if d_ppm < -tol:
        return "falling"
    return "flat"


def monotonicity(classes) -> str:
    s = {c for c in classes if c != "flat"}
    if not s:
        return "flat"
    if s == {"rising"}:
        return "monotone increasing"
    if s == {"falling"}:
        return "monotone decreasing"
    return "nonmonotone"


def analyse_curve(points, temps=TEMPS_C, tol_ppm: float = TOL_PPM, ref_c: float = tp.REF_TEMP_C,
                  anchors=tp.ANCHORS_C) -> dict:
    """Curve metrics for one process.

    points: iterable of dicts with "temp_c", "f_hz" and optional "status"
    ("OK" or "FAIL: ...") and "invalid" (a provenance/identity reason).
    Never returns a monotonicity class or curvature verdict unless the curve
    is COMPLETE."""
    temps = list(temps)
    n = len(temps)
    rows, by_idx, invalid, incomplete = [], {}, [], []
    for p in points:
        row = {"temp_c": p.get("temp_c"), "f_hz": p.get("f_hz"), "status": p.get("status", "OK")}
        i = grid_index(row["temp_c"], temps)
        if p.get("invalid"):
            row["status"] = f"INVALID: {p['invalid']}"
            invalid.append(f"{row['temp_c']} C: {p['invalid']}")
        elif i is None:
            row["status"] = "INVALID: temperature not on the 12-point axis"
            invalid.append(f"off-grid temperature {row['temp_c']!r}")
        elif row["status"] == "OK":
            why = valid_frequency(row["f_hz"])
            if why:
                row["status"] = f"FAIL: {why}"
        rows.append(row)
        if i is not None and not p.get("invalid"):
            by_idx.setdefault(i, []).append(row)
    good = {}
    for i, rs in by_idx.items():
        if len(rs) > 1:
            for r in rs:
                if not r["status"].startswith("INVALID"):
                    r["status"] = "INVALID: duplicate point"
            invalid.append(f"duplicate point at {temps[i]:g} C ({len(rs)} rows)")
        elif rs[0]["status"] == "OK":
            good[i] = float(rs[0]["f_hz"])
    for i in range(n):
        if i not in good and len(by_idx.get(i, [])) <= 1:
            rs = by_idx.get(i)
            incomplete.append(f"{temps[i]:g} C " + (rs[0]["status"] if rs else "missing"))
    iref = grid_index(ref_c, temps)
    ia = [grid_index(a, temps) for a in anchors]
    missing_anchor = [temps[i] for i in ia if i not in good]
    status = "INVALID" if invalid else ("INCOMPLETE" if incomplete else "COMPLETE")
    out = {"status": status, "invalid_reasons": invalid, "incomplete_reasons": incomplete,
           "missing_anchors_c": missing_anchor, "tolerance_ppm": tol_ppm, "rows": rows,
           "n_valid": len(good), "n_expected": n}
    f27 = good.get(iref)
    out["f27_hz"] = f27
    # normalized values and adjacent intervals (only where both ends valid)
    intervals = []
    for i in range(n - 1):
        iv = {"t0_c": temps[i], "t1_c": temps[i + 1]}
        if i in good and i + 1 in good:
            iv["diff_hz"] = good[i + 1] - good[i]
            if f27 is not None:
                iv["diff_ppm"] = 1e6 * (good[i + 1] - good[i]) / f27
                iv["slope_ppm_per_c"] = 1e6 * (good[i + 1] - good[i]) / (f27 * (temps[i + 1] - temps[i]))
                iv["class"] = classify(iv["diff_ppm"], tol_ppm)
        else:
            iv["skipped"] = "endpoint missing or invalid; not interpolated"
        intervals.append(iv)
    out["intervals"] = intervals
    for r in rows:
        i = grid_index(r["temp_c"], temps)
        if f27 is not None and r["status"] == "OK" and i in good:
            r["norm_ppm"] = 1e6 * (good[i] - f27) / f27
    lo, hi = ia[0], ia[-1]
    out["endpoint_slope_ppm_per_c"] = (
        1e6 * (good[hi] - good[lo]) / (f27 * (temps[hi] - temps[lo]))
        if f27 is not None and lo in good and hi in good else None)
    # piecewise-linear residual against the measured anchors
    resid = []
    for k in range(len(ia) - 1):
        a, b = ia[k], ia[k + 1]
        if f27 is None or a not in good or b not in good:
            continue
        for i in range(a, b + 1):
            if i not in good:
                continue
            w = (temps[i] - temps[a]) / (temps[b] - temps[a])
            flin = good[a] + w * (good[b] - good[a])
            resid.append({"temp_c": temps[i], "f_linear_hz": flin,
                          "residual_ppm": 0.0 if i in (a, b) else 1e6 * (good[i] - flin) / f27})
    seen, res_u = set(), []
    for r in resid:
        if r["temp_c"] not in seen:
            seen.add(r["temp_c"])
            res_u.append(r)
    out["residuals"] = res_u
    if res_u:
        worst = max(res_u, key=lambda r: abs(r["residual_ppm"]))
        out["max_abs_residual_ppm"] = abs(worst["residual_ppm"])
        out["max_residual_signed_ppm"] = worst["residual_ppm"]
        out["max_residual_temp_c"] = worst["temp_c"]
    else:
        out["max_abs_residual_ppm"] = out["max_residual_signed_ppm"] = out["max_residual_temp_c"] = None
    if status == "COMPLETE":
        out["monotonicity"] = monotonicity(iv["class"] for iv in intervals)
        out["curvature_verdict"] = ("EXCEEDS_TOLERANCE" if out["max_abs_residual_ppm"] > tol_ppm
                                    else "WITHIN_TOLERANCE")
    else:
        out["monotonicity"] = f"NOT EVALUATED ({status})"
        out["curvature_verdict"] = f"NOT EVALUATED ({status})"
    return out


# ------------------------------------------------------------ provenance --

def load_manifest(path: Path) -> dict:
    """Load and check a prepare.py manifest against the fixed campaign
    definition; any deviation is a provenance error, never silently used."""
    try:
        m = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise ProvenanceError(f"manifest unreadable: {e}") from e
    if m.get("kind") != tp.KIND:
        raise ProvenanceError(f"manifest kind {m.get('kind')!r} is not {tp.KIND!r}")
    g = m.get("grid") or {}
    if [float(x) for x in g.get("temperature_c", [])] != TEMPS_C or g.get("vdd_v") != tp.VDD_V \
            or g.get("load_f") != tp.LOAD_F or list(g.get("processes", [])) != list(PROCESSES):
        raise ProvenanceError("manifest grid differs from the 36-point campaign definition")
    cal = m.get("calibration") or {}
    want = {p: f"0x{c:02X}" for p, c in tp.EXPECTED_CODES.items()}
    if cal.get("codes") != want or cal.get("campaign_runid") != tp.CAL_RUNID \
            or cal.get("campaign_git_sha") != tp.CAL_GIT_SHA or cal.get("target") != tp.TARGET:
        raise ProvenanceError("manifest calibration source/codes/target differ from the held calibration")
    reqs = m.get("requests") or []
    if sorted(r.get("process") for r in reqs) != sorted(PROCESSES):
        raise ProvenanceError("manifest does not hold exactly one request per process")
    for r in reqs:
        if r.get("trim_hex") != want[r["process"]] or \
                [float(x) for x in r.get("temperature_c", [])] != TEMPS_C:
            raise ProvenanceError(f"manifest request for {r['process']} differs from the campaign definition")
        if not r.get("netlist_sha256") or not r.get("dut_sha256"):
            raise ProvenanceError(f"manifest request for {r['process']} lacks generated hashes")
    return m


def match_report(report: dict, manifest: dict) -> tuple[dict | None, str | None]:
    """Map a klt report to its manifest request by the netlist sha256 klt
    records; check the DUT include hash too.  Returns (request, error)."""
    env = report.get("environment") or {}
    sha = env.get("netlist_sha256")
    if not sha:
        return None, "report records no netlist_sha256 (provenance unverifiable)"
    req = next((r for r in manifest["requests"] if r["netlist_sha256"] == sha), None)
    if req is None:
        return None, f"netlist sha256 {sha[:12]} matches no request in the manifest"
    dut = [c for c in (env.get("netlist_closure") or [])
           if Path(str(c.get("path", ""))).name == manifest["dut"]["extracted"]]
    if len(dut) != 1:
        return req, "report closure does not record the extracted DUT include"
    if dut[0].get("sha256") != req["dut_sha256"]:
        return req, "DUT include sha256 differs from the manifest"
    return req, None


def collect(manifest: dict, report_paths, params, artifacts_roots=None):
    """Return (per-process point lists, report metadata, report-level failures)."""
    pts = {p: [] for p in PROCESSES}
    metas, report_fail = [], []
    seen_req = {}
    for k, rp in enumerate(report_paths):
        rp = Path(rp)
        root = artifacts_roots[k] if artifacts_roots else None
        try:
            d = json.loads(rp.read_text())
        except (OSError, ValueError) as e:
            report_fail.append({"report": rp.name, "status": f"FAIL: report unreadable: {e}"})
            metas.append({"report": rp.name, "status": "unreadable"})
            continue
        req, err = match_report(d if isinstance(d, dict) else {}, manifest)
        rows, meta = wa.analyse_report(rp, tp.VDD_V, params, root)
        meta = dict(meta or {"report": rp.name})
        meta["request"] = req["request"] if req else None
        meta["provenance"] = err or "ok"
        metas.append(meta)
        if req and req["process"] in seen_req and not err:
            err = f"second report for request {req['request']} (also {seen_req[req['process']]})"
        if req and not err:
            seen_req[req["process"]] = rp.name
        for r in rows:
            proc = r.get("process")
            if proc is None:  # report-level failure from the waveform analyzer
                report_fail.append({"report": rp.name, "status": r["status"]})
                continue
            point = {"temp_c": r.get("temp_c"), "report": rp.name, "status": r["status"],
                     "f_hz": (r.get("metrics") or {}).get("frequency_mean_hz")}
            if err:
                point["invalid"] = f"provenance mismatch: {err}"
            elif proc != req["process"]:
                point["invalid"] = f"provenance mismatch: corner process {proc!r} in the {req['process']} request"
            if proc not in pts:
                report_fail.append({"report": rp.name,
                                    "status": f"INVALID: process {proc!r} not in the campaign"})
                continue
            pts[proc].append(point)
    return pts, metas, report_fail


def evaluate(pts: dict, report_fail) -> dict:
    curves = {}
    for p in PROCESSES:
        c = analyse_curve(pts[p])
        for row, src in zip(c["rows"], pts[p]):
            row["report"] = src.get("report")
        curves[p] = c
    overall = max((c["status"] for c in curves.values()), key=STATUS_RANK.get)
    if report_fail and overall == "COMPLETE":
        overall = "INCOMPLETE"
    return {"status": overall, "curves": curves, "report_failures": report_fail}


# ---------------------------------------------------------------- output --

CSV_FIELDS = ["evidence_label", "process", "temp_c", "status", "f_hz", "norm_ppm", "report"]


def write_run(out: Path, result: dict, manifest: dict, metas, synthetic: bool, note: str = "",
              params=None) -> dict:
    out = Path(out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run {out}")
    synthetic = bool(synthetic or any(m.get("synthetic") for m in metas))
    label = SYNTHETIC_LABEL if synthetic else MEASURED_LABEL
    doc = {"label": label, "synthetic": synthetic, "issue": tp.ISSUE,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "note": note,
           "tolerance_ppm_of_f27": TOL_PPM, "tolerance_kind": "diagnostic, not a spec",
           "temperature_c": TEMPS_C, "status": result["status"],
           "schematic_equivalence": (manifest.get("schematic_equivalence") or {}).get("status", "UNKNOWN"),
           "manifest": {"calibration": manifest.get("calibration"),
                        "design_revision": manifest.get("design_revision"),
                        "requests": manifest.get("requests")},
           "waveform_params": params, "reports": metas,
           "report_failures": result["report_failures"], "curves": result["curves"]}
    out.mkdir(parents=True)
    (out / "results.json").write_text(json.dumps(doc, indent=2, default=str) + "\n")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for p, c in result["curves"].items():
            for r in c["rows"]:
                w.writerow({"evidence_label": label, "process": p, "temp_c": r.get("temp_c"),
                            "status": r["status"], "f_hz": r.get("f_hz"), "norm_ppm": r.get("norm_ppm"),
                            "report": r.get("report")})

    def g(x, f="%.4g"):
        return "-" if x is None else f % x
    L = [f"# Interior-temperature analysis {out.name}", "", f"**{label}**", "",
         f"Overall status: **{result['status']}**. Tolerance {TOL_PPM:g} ppm of f27 is a diagnostic, "
         "not a spec. Schematic equivalence with the calibration revision: "
         f"**{doc['schematic_equivalence']}**.", ""]
    if note:
        L += [f"Note: {note}", ""]
    for f in result["report_failures"]:
        L.append(f"- report {f['report']}: {f['status']}")
    for p, c in result["curves"].items():
        code = (manifest.get("calibration") or {}).get("codes", {}).get(p)
        L += ["", f"## {p} (held code {code})", "",
              f"status **{c['status']}**; monotonicity: {c['monotonicity']}; curvature: {c['curvature_verdict']}",
              f"f27 = {g(c['f27_hz'], '%.6g')} Hz; endpoint slope {g(c['endpoint_slope_ppm_per_c'])} ppm/C; "
              f"max |residual| {g(c['max_abs_residual_ppm'])} ppm at {g(c['max_residual_temp_c'])} C "
              f"(signed {g(c['max_residual_signed_ppm'])})"]
        for r in c["invalid_reasons"] + c["incomplete_reasons"]:
            L.append(f"- {r}")
        L += ["", "| T0 (C) | T1 (C) | diff (Hz) | diff (ppm f27) | slope (ppm/C) | class |",
              "|---|---|---|---|---|---|"]
        for iv in c["intervals"]:
            L.append(f"| {iv['t0_c']:g} | {iv['t1_c']:g} | {g(iv.get('diff_hz'))} | {g(iv.get('diff_ppm'))} | "
                     f"{g(iv.get('slope_ppm_per_c'))} | {iv.get('class', iv.get('skipped', '-'))} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def main(argv=None) -> int:
    P = wa.Params
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="klt sim JSON reports, one per request")
    ap.add_argument("--manifest", required=True, type=Path, help="provenance.json from prepare.py")
    ap.add_argument("--outdir", required=True, type=Path, help="NEW results directory (never overwritten)")
    ap.add_argument("--artifacts-root", nargs="*", type=Path, default=None)
    ap.add_argument("--synthetic", action="store_true", help="label the run as synthetic fixture output")
    ap.add_argument("--note", default="")
    ap.add_argument("--window-ns", type=float, default=P.window_s * 1e9)
    ap.add_argument("--min-cycles", type=int, default=P.min_cycles)
    ap.add_argument("--min-samples-per-cycle", type=float, default=P.min_samples_per_cycle)
    ap.add_argument("--drift-tol", type=float, default=P.drift_tol)
    ap.add_argument("--vdd-tol", type=float, default=P.vdd_tol)
    a = ap.parse_args(argv)
    if a.artifacts_root is not None and len(a.artifacts_root) != len(a.reports):
        ap.error("--artifacts-root needs one dir per report")
    if a.outdir.exists():
        print(f"analyze.py: refusing to overwrite existing run {a.outdir}", file=sys.stderr)
        return 2
    try:
        man = load_manifest(a.manifest)
    except ProvenanceError as e:
        print(f"analyze.py: {e}", file=sys.stderr)
        return 2
    params = P(a.window_ns * 1e-9, a.min_cycles, a.min_samples_per_cycle, a.drift_tol, a.vdd_tol)
    pts, metas, rfail = collect(man, a.reports, params, a.artifacts_root)
    res = evaluate(pts, rfail)
    doc = write_run(a.outdir, res, man, metas, a.synthetic, a.note,
                    {"window_s": params.window_s, "min_cycles": params.min_cycles,
                     "min_samples_per_cycle": params.min_samples_per_cycle,
                     "drift_tol": params.drift_tol, "vdd_tol": params.vdd_tol})
    print(f"wrote {a.outdir}: status {doc['status']}; {doc['label']}")
    return 0 if doc["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
