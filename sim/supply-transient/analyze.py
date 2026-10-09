#!/usr/bin/env python3
"""Analyzer for the supply-transient / ripple bench (issue #92, offline subset).

Input : `klt sim --format json -o <outdir>` reports, one per request written by
        sim/supply-transient/prepare.py, given as TAG=report.json (TAG is the
        case tag, e.g. step_dn_r1us_tt).  Each corner's `artifacts.waveform` is a
        waveform.raw.json ({"variables": [...], "points": [[t, ...]]}) or is
        resolved under --artifacts-root.  Case stimulus (windows, levels) is read
        from case_<TAG>.json in --bench-dir (the generator's output directory).
Output: results.json / results.csv / summary.md / cycles_<TAG>.csv in a NEW
        directory (refuses to overwrite).  Fixture runs (--synthetic, or a
        report carrying `"synthetic": true`) are labelled
        "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE".

Definitions (seconds, volts, hertz; SI in the JSON):
  crossing        interpolated zero crossings of v(clk) - 0.5*v(vdd), so a moving
                  rail is not mistaken for timing.  Crossings from the start of
                  the baseline window must strictly alternate or the case FAILS.
  complete cycle  r[i] -> r[i+1] (rising to rising); a leading falling edge and a
                  trailing falling edge are incomplete and omitted.
  cycle frequency 1/(r[i+1]-r[i]), stamped at the cycle's start edge r[i].
  STEP  baseline  mean cycle frequency over cycles inside the final
                  baseline_window before the disturbance (>= min_cycles).
        endpoint  mean cycle frequency over cycles inside the final
                  endpoint_window of the record (>= min_cycles).
        peak dev  max |f_i - f_end| over cycles from the disturbance start on
                  (during and after the ramp), also as a fraction of f_end.
        settling  first complete cycle starting at/after ramp completion such that
                  it and all later cycles are within +/-band of f_end, with >=
                  min_cycles qualifying cycles and >= min_remaining of record
                  after its start; elapsed = its start edge - ramp completion.
                  `censored` (record too short / tail too short) and
                  `not_settled` (last cycle outside the band) are reported
                  explicitly, never as zero.  The band is a configurable
                  engineering metric, not the ratified trimmed-accuracy band.
  RIPPLE          after the ripple starts, discard `discard` ripple periods and
                  observe `observe` full periods.  depth =
                  (max f - min f)/mean f over cycles lying entirely in the
                  observed span; normalized sensitivity = depth / (Vpp/Vmean)
                  (dimensionless; NOT a conventional dB PSRR, no transfer-
                  function convention is defined here).
Failures are explicit (status "FAIL: <reason>", no metrics); nothing is
imputed or defaulted to a passing number.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import importlib.util
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SYN_BANNER = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wfa = _load("wf_analyze", "sim/waveform/analyze.py")
AnalysisError = wfa.AnalysisError
parse_waveform = wfa.parse_waveform
load_waveform = wfa.load_waveform


@dataclass(frozen=True)
class Params:
    band: float = 0.01                 # settling band, +/- fraction of endpoint frequency
    min_cycles: int = 20               # baseline / endpoint / qualifying / ripple-window cycles
    min_remaining_s: float = 2e-6      # record that must remain after the settled cycle starts
    min_samples_per_cycle: float = 10.0
    vdd_tol: float = 0.02              # rail level tolerance at baseline / endpoint / ripple mean
    min_cycles_per_ripple_period: float = 8.0
    ripple_amp_tol: float = 0.25       # measured ripple p-p vs configured, fractional


# ------------------------------------------------------------------ cycles --

def cycle_list(t, clk, vdd, t_from, min_spc):
    """Complete rising-to-rising cycles from t_from on, using crossings of
    v(clk) - 0.5*v(vdd).  Returns [(t_start, t_end)]."""
    d = [c - 0.5 * v for c, v in zip(clk, vdd)]
    cr = [c for c in wfa.crossings(t, d, 0.0) if c[0] >= t_from]
    if len(cr) < 3:
        raise AnalysisError(f"missing crossings: {len(cr)} after the baseline window start")
    for a, b in zip(cr, cr[1:]):
        if a[1] == b[1]:
            raise AnalysisError("invalid crossing order: two consecutive "
                                f"{'rising' if a[1] == 'r' else 'falling'} crossings")
    r = [c[0] for c in cr if c[1] == "r"]
    if len(r) < 2:
        raise AnalysisError("fewer than 2 rising crossings")
    cyc = [(r[i], r[i + 1]) for i in range(len(r) - 1)]
    for a, b in cyc:
        if not b > a:
            raise AnalysisError("invalid crossing order: non-positive period")
        n = bisect.bisect_right(t, b) - bisect.bisect_left(t, a)
        if n < min_spc:
            raise AnalysisError(f"insufficient samples: {n} in a cycle near t={a:.6g} s, need {min_spc:g} per cycle")
    return cyc


def _freqs(cyc, lo, hi):
    """(start, end, f) for cycles lying entirely inside [lo, hi]."""
    return [(a, b, 1.0 / (b - a)) for a, b in cyc if a >= lo and b <= hi]


def _mean(x):
    return sum(x) / len(x)


def _window_mean(t, y, lo, hi):
    v = [y[k] for k in range(len(t)) if lo <= t[k] <= hi]
    if not v:
        raise AnalysisError("no samples in the window")
    return _mean(v), min(v), max(v)


def _check_case(case, kind):
    if not isinstance(case, dict) or case.get("kind") != kind:
        raise AnalysisError(f"case is not a {kind} case")
    for k in ("startup_ramp_s", "baseline_window_s", "tstop_s"):
        v = case.get(k)
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise AnalysisError(f"case field {k} invalid: {v!r}")


def _baseline(t, clk, vdd, case, p, t_dist, vnom):
    bw = case["baseline_window_s"]
    b0 = t_dist - bw
    if t[0] > b0:
        raise AnalysisError("record starts after the baseline window")
    if t[-1] <= t_dist:
        raise AnalysisError("record ends before the disturbance starts")
    cyc = cycle_list(t, clk, vdd, b0, p.min_samples_per_cycle)
    base = _freqs(cyc, b0, t_dist)
    if len(base) < p.min_cycles:
        raise AnalysisError(f"insufficient baseline cycles: {len(base)} complete in the {bw * 1e6:g} us "
                            f"baseline window, need {p.min_cycles}")
    vm, _, _ = _window_mean(t, vdd, b0, t_dist)
    if abs(vm - vnom) > p.vdd_tol * vnom:
        raise AnalysisError(f"baseline rail {vm:.4g} V is not within +/-{p.vdd_tol * 100:g}% of {vnom:g} V")
    return cyc, base, vm


# -------------------------------------------------------------------- step --

def analyse_step(t, clk, vdd, case, p: Params = Params()):
    _check_case(case, "step")
    for k in ("vdd_from_v", "vdd_to_v", "ramp_s", "disturb_start_s", "ramp_end_s", "endpoint_window_s"):
        if not (isinstance(case.get(k), (int, float)) and math.isfinite(case[k])):
            raise AnalysisError(f"case field {k} invalid: {case.get(k)!r}")
    td, tr, ew = case["disturb_start_s"], case["ramp_end_s"], case["endpoint_window_s"]
    cyc, base, vm0 = _baseline(t, clk, vdd, case, p, td, case["vdd_from_v"])
    f_base = _mean([f for _, _, f in base])
    t_end = t[-1]
    designed = case["tstop_s"]
    short = t_end < designed * (1 - 1e-9)
    out = {
        "units": {"time": "s", "frequency": "Hz", "voltage": "V"},
        "vdd_from_v": case["vdd_from_v"], "vdd_to_v": case["vdd_to_v"], "ramp_s": case["ramp_s"],
        "disturb_start_s": td, "ramp_end_s": tr, "record_end_s": t_end, "designed_end_s": designed,
        "record_shorter_than_designed": short,
        "band_fraction": p.band, "band_note": "configurable engineering metric; not the ratified trimmed-accuracy band",
        "baseline_window_s": [td - case["baseline_window_s"], td], "baseline_cycles": len(base),
        "baseline_frequency_hz": f_base, "baseline_vdd_mean_v": vm0,
        "endpoint_window_s": [t_end - ew, t_end],
        "min_cycles": p.min_cycles, "min_remaining_s": p.min_remaining_s,
        "min_samples_per_cycle_required": p.min_samples_per_cycle,
    }
    series = [(a, 1.0 / (b - a)) for a, b in cyc if a >= td - case["baseline_window_s"]]
    if t_end - ew < tr:  # endpoint window would overlap the ramp: nothing to settle against
        out |= {"endpoint_frequency_hz": None, "peak_deviation": None,
                "settling": {"status": "censored", "elapsed_s": None,
                             "reason": "record ends before ramp completion plus the endpoint window"}}
        return out, series
    end = _freqs(cyc, t_end - ew, t_end)
    if len(end) < p.min_cycles:
        raise AnalysisError(f"insufficient endpoint cycles: {len(end)} complete in the final "
                            f"{ew * 1e6:g} us, need {p.min_cycles}")
    vme, _, _ = _window_mean(t, vdd, t_end - ew, t_end)
    if abs(vme - case["vdd_to_v"]) > p.vdd_tol * case["vdd_to_v"]:
        raise AnalysisError(f"endpoint rail {vme:.4g} V is not within +/-{p.vdd_tol * 100:g}% of "
                            f"{case['vdd_to_v']:g} V")
    f_end = _mean([f for _, _, f in end])
    dev = [(a, f - f_end) for a, b, f in _freqs(cyc, td, t_end)]
    if not dev:
        raise AnalysisError("no complete cycles after the disturbance starts")
    ia = max(range(len(dev)), key=lambda i: abs(dev[i][1]))
    out |= {"endpoint_frequency_hz": f_end, "endpoint_cycles": len(end), "endpoint_vdd_mean_v": vme,
            "static_shift_fraction": (f_end - f_base) / f_base,
            "peak_deviation": {"hz": abs(dev[ia][1]), "signed_hz": dev[ia][1],
                               "fraction_of_endpoint": abs(dev[ia][1]) / f_end,
                               "signed_fraction_of_endpoint": dev[ia][1] / f_end,
                               "time_after_disturb_start_s": dev[ia][0] - td,
                               "scope": "complete cycles from the disturbance start to the end of the record"}}
    post = [(a, 1.0 / (b - a)) for a, b in cyc if a >= tr]
    inband = [abs(f - f_end) <= p.band * f_end for _, f in post]
    if not post:
        out["settling"] = {"status": "censored", "elapsed_s": None, "reason": "no complete cycle after ramp completion"}
        return out, series
    k = len(post)
    while k > 0 and inband[k - 1]:
        k -= 1
    if k == len(post):
        out["settling"] = {"status": "not_settled", "elapsed_s": None,
                           "reason": f"the final cycle is outside +/-{p.band * 100:g}% of the endpoint frequency"}
    else:
        nq, remaining = len(post) - k, t_end - post[k][0]
        if nq < p.min_cycles or remaining < p.min_remaining_s:
            out["settling"] = {"status": "censored", "elapsed_s": None,
                               "reason": (f"in band only for {nq} cycle(s) / {remaining * 1e6:.4g} us at the end of the "
                                          f"record; need {p.min_cycles} cycles and {p.min_remaining_s * 1e6:g} us"),
                               "qualifying_cycles": nq, "remaining_s": remaining}
        else:
            out["settling"] = {"status": "settled", "elapsed_s": post[k][0] - tr,
                               "settled_cycle_start_s": post[k][0], "qualifying_cycles": nq,
                               "remaining_s": remaining, "reference": "elapsed from ramp completion to the "
                                                                      "start edge of the first qualifying cycle"}
    return out, series


# ------------------------------------------------------------------ ripple --

def analyse_ripple(t, clk, vdd, case, p: Params = Params()):
    _check_case(case, "ripple")
    for k in ("ripple_hz", "ripple_vpp_v", "vdd_mean_v", "ripple_start_s", "observe_start_s", "observe_end_s",
              "discard_periods", "observe_periods"):
        v = case.get(k)
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise AnalysisError(f"case field {k} invalid: {v!r}")
    f_r, vpp, vmean = case["ripple_hz"], case["ripple_vpp_v"], case["vdd_mean_v"]
    if not (f_r > 0 and vpp > 0 and vmean > 0):
        raise AnalysisError("ripple frequency, amplitude and mean must be positive")
    o0, o1 = case["observe_start_s"], case["observe_end_s"]
    if abs((o1 - o0) * f_r - case["observe_periods"]) > 1e-6 * case["observe_periods"]:
        raise AnalysisError("case observation window is not the configured number of full ripple periods")
    if t[-1] < o1 * (1 - 1e-12):
        raise AnalysisError(f"insufficient observation duration: record ends at {t[-1]:.6g} s, "
                            f"{case['observe_periods']:g} ripple periods need {o1:.6g} s")
    cyc, base, vm0 = _baseline(t, clk, vdd, case, p, case["ripple_start_s"], vmean)
    f_base = _mean([f for _, _, f in base])
    obs = _freqs(cyc, o0, o1)
    if len(obs) < p.min_cycles:
        raise AnalysisError(f"insufficient cycles: {len(obs)} complete in the observed span, need {p.min_cycles}")
    cpp = len(obs) / case["observe_periods"]
    if cpp < p.min_cycles_per_ripple_period:
        raise AnalysisError(f"inadequate resolution of the ripple: {cpp:.1f} clk cycles per ripple period, "
                            f"need {p.min_cycles_per_ripple_period:g}")
    fs = [f for _, _, f in obs]
    fm = _mean(fs)
    vm, vlo, vhi = _window_mean(t, vdd, o0, o1)
    if abs(vm - vmean) > p.vdd_tol * vmean:
        raise AnalysisError(f"ripple mean rail {vm:.4g} V is not within +/-{p.vdd_tol * 100:g}% of {vmean:g} V")
    if abs((vhi - vlo) - vpp) > p.ripple_amp_tol * vpp:
        raise AnalysisError(f"measured rail ripple {vhi - vlo:.4g} V p-p differs from configured {vpp:g} V p-p "
                            f"by more than {p.ripple_amp_tol * 100:g}%")
    depth = (max(fs) - min(fs)) / fm
    out = {
        "units": {"time": "s", "frequency": "Hz", "voltage": "V", "depth": "fraction", "sensitivity": "ratio"},
        "ripple_hz": f_r, "ripple_vpp_v": vpp, "vdd_mean_v": vmean,
        "ripple_start_s": case["ripple_start_s"], "discard_periods": case["discard_periods"],
        "observe_periods": case["observe_periods"], "observation_window_s": [o0, o1],
        "observed_cycles": len(obs), "cycles_per_ripple_period": cpp,
        "baseline_window_s": [case["ripple_start_s"] - case["baseline_window_s"], case["ripple_start_s"]],
        "baseline_cycles": len(base), "baseline_frequency_hz": f_base, "baseline_vdd_mean_v": vm0,
        "observed_frequency_mean_hz": fm, "observed_frequency_min_hz": min(fs),
        "observed_frequency_max_hz": max(fs),
        "mean_shift_fraction": (fm - f_base) / f_base,
        "modulation_depth": depth,
        "normalized_sensitivity": depth / (vpp / vmean),
        "normalized_sensitivity_definition": "modulation_depth / (Vpp/Vmean) with configured Vpp and Vmean; "
                                             "dimensionless, not a dB PSRR",
        "measured_rail": {"mean_v": vm, "peak_to_peak_v": vhi - vlo},
        "illustrative": case.get("illustrative"),
    }
    series = [(a, 1.0 / (b - a)) for a, b in cyc if a >= case["ripple_start_s"] - case["baseline_window_s"]]
    return out, series


# ----------------------------------------------------------------- reports --

BAD_STATUS = {"refused", "rejected", "submit_failed", "error"}


def analyse_report(tag, report_path: Path, bench_dir: Path, p: Params = Params(), artifacts_root=None,
                   allow_local: bool = False):
    """Returns (rows, meta, series).  Every failure is an explicit FAIL row."""
    rp = Path(report_path)
    base = {"tag": tag, "report": rp.name}
    meta = {"report": rp.name, "tag": tag}

    def fail(msg, **kw):
        return [base | kw | {"status": f"FAIL: {msg}"}], meta, None
    try:
        case = json.loads((Path(bench_dir) / f"case_{tag}.json").read_text())
    except (OSError, ValueError) as e:
        return fail(f"case file unreadable: {e}")
    base |= {"kind": case.get("kind"), "process": case.get("process"), "temp_c": case.get("temperature_c")}
    try:
        d = json.loads(rp.read_text())
    except OSError as e:
        return fail(f"report unreadable: {e}")
    except ValueError as e:
        return fail(f"report is not valid JSON: {e}")
    if not isinstance(d, dict):
        return fail("report is not a JSON object")
    remote = (d.get("environment") or {}).get("remote")
    meta |= {"status": d.get("status"), "corner_count": d.get("corner_count"), "remote": remote,
             "klt": (d.get("provenance") or {}).get("klt_version"), "synthetic": bool(d.get("synthetic"))}
    if str(d.get("status")).lower() in BAD_STATUS or d.get("refused"):
        detail = d.get("error") or d.get("message") or d.get("refused") or ""
        return fail(f"batch submission refused/failed (report status {d.get('status')!r}) {detail}".rstrip())
    corners = d.get("corners")
    if not isinstance(corners, list) or not corners:
        return fail("report has no corners")
    if len(corners) != 1 or d.get("corner_count") not in (None, 1):
        return fail(f"expected exactly 1 corner, report lists {len(corners)} (corner_count {d.get('corner_count')})")
    c = corners[0]
    if c.get("process") != case.get("process") or c.get("temperature_c") != case.get("temperature_c"):
        return fail(f"corner {c.get('process')}/{c.get('temperature_c')} does not match case "
                    f"{case.get('process')}/{case.get('temperature_c')}")
    if c.get("status") in (None, "error"):
        return fail(f"klt corner status {c.get('status')!r}" + (f": {c.get('error')}" if c.get("error") else ""))
    if not remote and not meta["synthetic"] and not allow_local:
        return fail("report was not executed on the batch fleet (environment.remote missing); "
                    "batch-only, no local grid fallback")
    wfp = (c.get("artifacts") or {}).get("waveform")
    if not wfp:
        return fail("no waveform artifact")
    wfp = Path(wfp)
    if artifacts_root:
        wfp = Path(artifacts_root) / wfp.parent.name / wfp.name
    try:
        t, clk, vdd = load_waveform(wfp)
        fn = analyse_step if case["kind"] == "step" else analyse_ripple if case["kind"] == "ripple" else None
        if fn is None:
            raise AnalysisError(f"unknown case kind {case['kind']!r}")
        m, series = fn(t, clk, vdd, case, p)
    except AnalysisError as e:
        return fail(str(e))
    return [base | {"status": "OK", "metrics": m}], meta, series


FIELDS = ["tag", "kind", "process", "temp_c", "status", "vdd_from_v", "vdd_to_v", "ramp_us", "ripple_hz",
          "baseline_mhz", "endpoint_mhz", "shift_pct", "peak_dev_pct", "settle_status", "settle_us",
          "band_pct", "depth_pct", "norm_sensitivity"]


def flat(r):
    out = {k: r.get(k) for k in ("tag", "kind", "process", "temp_c", "status")}
    m = r.get("metrics")
    if not m:
        return out
    out["baseline_mhz"] = m["baseline_frequency_hz"] / 1e6
    if r["kind"] == "step":
        s, pk = m["settling"], m["peak_deviation"]
        out |= {"vdd_from_v": m["vdd_from_v"], "vdd_to_v": m["vdd_to_v"], "ramp_us": m["ramp_s"] * 1e6,
                "band_pct": m["band_fraction"] * 100, "settle_status": s["status"],
                "settle_us": None if s["elapsed_s"] is None else s["elapsed_s"] * 1e6}
        if m["endpoint_frequency_hz"] is not None:
            out |= {"endpoint_mhz": m["endpoint_frequency_hz"] / 1e6, "shift_pct": m["static_shift_fraction"] * 100,
                    "peak_dev_pct": pk["fraction_of_endpoint"] * 100}
    else:
        out |= {"ripple_hz": m["ripple_hz"], "shift_pct": m["mean_shift_fraction"] * 100,
                "depth_pct": m["modulation_depth"] * 100, "norm_sensitivity": m["normalized_sensitivity"]}
    return out


def write_run(out: Path, rows, metas, p: Params, synthetic: bool, series=None, note: str = ""):
    out = Path(out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run {out}")
    out.mkdir(parents=True)
    synthetic = synthetic or any(m.get("synthetic") for m in metas)
    banner = (SYN_BANNER if synthetic else
              "Analysis of simulator output; evidence status is set by the originating campaign record")
    nfail = sum(1 for r in rows if r["status"] != "OK")
    doc = {"label": banner, "synthetic": synthetic, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "params": asdict(p), "note": note, "reports": metas, "n_cases": len(rows),
           "n_fail": nfail, "all_ok": nfail == 0 and bool(rows), "cases": rows}
    if synthetic:
        doc["measured_evidence"] = False   # fixtures can never be claimed as measured evidence
    (out / "results.json").write_text(json.dumps(doc, indent=2) + "\n")
    for tag, s in (series or {}).items():
        if s:
            with open(out / f"cycles_{tag}.csv", "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["cycle_start_s", "period_s", "frequency_hz"])
                for a, f in s:
                    w.writerow([f"{a:.12g}", f"{1 / f:.12g}", f"{f:.12g}"])
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in flat(r).items()})

    def g(x, f="%.4g"):
        return "-" if x is None else f % x
    L = [f"# Supply-transient analysis {out.name}", "", f"**{banner}**", "",
         f"Settling band +/-{p.band * 100:g}% of the endpoint frequency is a configurable engineering metric, not the",
         "ratified trimmed-accuracy band and not an acceptance threshold.  Ripple sensitivity is",
         "depth/(Vpp/Vmean), dimensionless; it is not a dB PSRR.", ""]
    if note:
        L += [f"Note: {note}", ""]
    L += [f"{len(rows)} case row(s), {nfail} failing.", "", "## Steps", "",
          "| case | process | T (C) | status | VDD (V) | ramp (us) | baseline (MHz) | endpoint (MHz) | shift (%) | peak dev (%) | settling | elapsed (us) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        x = flat(r)
        if r.get("kind") == "ripple":
            continue
        L.append(f"| {x['tag']} | {x['process']} | {g(x['temp_c'])} | {x['status']} | "
                 f"{g(x.get('vdd_from_v'))}->{g(x.get('vdd_to_v'))} | {g(x.get('ramp_us'))} | {g(x.get('baseline_mhz'))} | "
                 f"{g(x.get('endpoint_mhz'))} | {g(x.get('shift_pct'))} | {g(x.get('peak_dev_pct'))} | "
                 f"{x.get('settle_status') or '-'} | {g(x.get('settle_us'))} |")
    L += ["", "## Ripple", "",
          "| case | process | T (C) | status | ripple (Hz) | baseline (MHz) | mean shift (%) | depth (%) | normalized sensitivity |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        x = flat(r)
        if r.get("kind") == "step":
            continue
        L.append(f"| {x['tag']} | {x['process']} | {g(x['temp_c'])} | {x['status']} | {g(x.get('ripple_hz'))} | "
                 f"{g(x.get('baseline_mhz'))} | {g(x.get('shift_pct'))} | {g(x.get('depth_pct'))} | "
                 f"{g(x.get('norm_sensitivity'))} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def analyse_all(reports: dict, bench_dir: Path, p: Params, artifacts_root=None, allow_local=False):
    """Analyse TAG->report; every case listed in the bench provenance.json must have a report."""
    rows, metas, series = [], [], {}
    try:
        prov = json.loads((Path(bench_dir) / "provenance.json").read_text())
        expected = [e["tag"] for e in prov["requests"]]
    except (OSError, ValueError, KeyError) as e:
        rows.append({"tag": None, "status": f"FAIL: bench provenance.json unreadable: {e}"})
        expected = []
    for tag in expected:
        if tag not in reports:
            rows.append({"tag": tag, "status": "FAIL: no report supplied for this case (missing corner)"})
    for tag, rep in reports.items():
        if expected and tag not in expected:
            rows.append({"tag": tag, "status": "FAIL: report tag is not a case of the bench provenance"})
            continue
        rr, mm, ss = analyse_report(tag, Path(rep), bench_dir, p, artifacts_root, allow_local)
        rows += rr
        metas.append(mm)
        series[tag] = ss
    return rows, metas, series


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="TAG=report.json (TAG e.g. step_dn_r1us_tt)")
    ap.add_argument("--bench-dir", type=Path, required=True, help="prepare.py output dir (case_*.json, provenance.json)")
    ap.add_argument("--artifacts-root", type=Path, default=None)
    ap.add_argument("--outdir", required=True, type=Path, help="NEW results directory (never overwritten)")
    ap.add_argument("--synthetic", action="store_true", help="label the run as synthetic fixture output")
    ap.add_argument("--allow-local", action="store_true", help="accept reports without environment.remote "
                    "(single-corner debug probe only; never a campaign)")
    ap.add_argument("--note", default="")
    ap.add_argument("--band", type=float, default=Params.band)
    ap.add_argument("--min-cycles", type=int, default=Params.min_cycles)
    ap.add_argument("--min-remaining-us", type=float, default=Params.min_remaining_s * 1e6)
    ap.add_argument("--min-samples-per-cycle", type=float, default=Params.min_samples_per_cycle)
    ap.add_argument("--vdd-tol", type=float, default=Params.vdd_tol)
    a = ap.parse_args()
    reports = {}
    for item in a.reports:
        tag, sep, path = item.partition("=")
        if not sep or not tag or not path:
            ap.error(f"report argument must be TAG=report.json, got {item!r}")
        if tag in reports:
            ap.error(f"duplicate report for {tag}")
        reports[tag] = path
    p = Params(band=a.band, min_cycles=a.min_cycles, min_remaining_s=a.min_remaining_us * 1e-6,
               min_samples_per_cycle=a.min_samples_per_cycle, vdd_tol=a.vdd_tol)
    rows, metas, series = analyse_all(reports, a.bench_dir, p, a.artifacts_root, a.allow_local)
    doc = write_run(a.outdir, rows, metas, p, a.synthetic, series, a.note)
    print(f"wrote {a.outdir}: {doc['n_cases']} case row(s), {doc['n_fail']} failing; {doc['label']}")
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
