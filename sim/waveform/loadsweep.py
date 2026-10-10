#!/usr/bin/env python3
"""Offline clk output-load sensitivity coordinator (issue #122).

Two subcommands, neither of which runs a simulator or touches the network:

  prepare  write 45 one-corner `klt sim` requests (extra clk capacitance
           {0,1,2,5,10} pF x process {tt,ss,ff} x supply {3.0,3.3,3.6} V, all at
           27 C) plus a sweep manifest, by calling prepare.generate(probe=...)
           once per point in its own directory.  Each process keeps the code
           calibrated UNLOADED at its own 27 C / 3.3 V point; nothing is
           recalibrated under load.  Existing output directories are refused.
  analyze  read one klt sim report per manifest point, reuse analyze.analyse_report
           for every waveform measurement/failure, and compare each point with
           the 0 F point of the same process and supply.

Definitions (frequency = 1 / mean period; units SI in JSON, percent / ps in CSV):
  rel_freq_shift_pct   100 * (f_load / f_0F - 1)
  slope_pct_per_pF     100 * (f_b/f_0F - f_a/f_0F) / ((C_b - C_a) / 1 pF)
                       between ADJACENT sampled loads; no linearity assumed
  abs_error_pct        100 * (f / 48 MHz - 1), context only
  budget               DR-0017 at-calibration budget -2.9 % / +2.0 %.  It is
                       contextual away from nominal 27 C / 3.3 V and ratifies no
                       load specification.  Only SAMPLED loads are reported; a
                       maximum load is never extrapolated.
A failed or missing waveform row yields no numbers and never a pass.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import prepare  # noqa: E402

LOADS_F = (0.0, 1e-12, 2e-12, 5e-12, 10e-12)
PROCESSES = prepare.PROCESSES
VDDS_V = (3.0, 3.3, 3.6)
TEMP_C = 27.0
TARGET_HZ = 48e6
BUDGET_PCT = (-2.9, 2.0)  # DR-0017 at-calibration budget
SYNTH = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"
MANIFEST = "sweep_manifest.json"


class SweepError(Exception):
    pass


def check_load(c) -> float:
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not math.isfinite(c):
        raise SweepError(f"invalid load {c!r}")
    for ld in LOADS_F:
        if math.isclose(c, ld, rel_tol=1e-9, abs_tol=1e-18):
            return ld
    raise SweepError(f"load {c!r} F is not on the ladder {LOADS_F}")


def point_id(proc: str, vdd: float, load_f: float) -> str:
    return f"{proc}_{prepare.tag_of(vdd)}_c{int(round(load_f * 1e15)):05d}f"


def grid() -> list[tuple[str, float, float]]:
    pts = [(p, v, c) for p in PROCESSES for v in VDDS_V for c in LOADS_F]
    if len(pts) != 45 or len({point_id(*q) for q in pts}) != 45:
        raise SweepError("grid is not 45 uniquely identified points")
    return pts


def prepare_sweep(out: Path, cal: dict, cfg: dict | None = None) -> dict:
    out = Path(out)
    if out.exists():
        raise SweepError(f"refusing to overwrite existing output {out}")
    cfg = dict(cfg or {})
    if cfg.get("load_f", 0.0) != 0.0:
        raise SweepError("load is set per point by the sweep; do not pass load_f")
    out.mkdir(parents=True)
    pts = []
    for proc, vdd, load in grid():
        pid = point_id(proc, vdd, load)
        d = out / "points" / pid
        prov = prepare.generate(d, cal, cfg | {"load_f": load}, probe=f"{proc}:{TEMP_C:g}:{vdd:g}")
        (req,) = prov["requests"]
        pts.append({
            "id": pid, "process": proc, "temperature_c": TEMP_C, "vdd_v": vdd,
            "load_f": load, "load_pf": load * 1e12,
            "load_matches_calibration_bench": load == 0.0,
            "load_kind": ("0 F: matches the unloaded calibration bench" if load == 0.0 else
                          "NON-ZERO extra clk load; code held from the unloaded calibration"),
            "trim_code": req["trim_code"], "trim_hex": req["trim_hex"],
            "request": f"points/{pid}/{req['request']}", "netlist": f"points/{pid}/{req['netlist']}",
            "provenance": f"points/{pid}/provenance.json",
            "report": f"report_{pid}.json",
        })
    man = {
        "kind": "load-sweep-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 122,
        "loads_f": list(LOADS_F), "processes": list(PROCESSES), "vdd_v": list(VDDS_V),
        "temperature_c": TEMP_C, "n_points": len(pts),
        "held_codes": {p: f"0x{c:02X}" for p, c in cal["codes"].items()},
        "hold_rule": "per process, code calibrated unloaded at its own 27 C / 3.3 V point; not recalibrated under load",
        "calibration": cal["source"],
        "settings": prov["settings"] | {"load_f": "per point"},
        "budget_pct": list(BUDGET_PCT), "target_hz": TARGET_HZ,
        "execution": "later campaign only, via `klt sim --backend batch`; never a local multi-corner loop",
        "points": pts,
    }
    (out / MANIFEST).write_text(json.dumps(man, indent=2) + "\n")
    return man


# ------------------------------------------------------------- comparison --

def validate_manifest(man: dict) -> list[dict]:
    pts = man.get("points") if isinstance(man, dict) else None
    if not isinstance(pts, list) or not pts:
        raise SweepError("manifest has no points")
    seen, keys = set(), set()
    for p in pts:
        for k in ("id", "process", "temperature_c", "vdd_v", "load_f", "report"):
            if k not in p:
                raise SweepError(f"manifest point lacks {k!r}: {p.get('id')}")
        check_load(p["load_f"])
        if p["id"] in seen:
            raise SweepError(f"duplicate point id {p['id']}")
        key = (p["process"], p["vdd_v"], check_load(p["load_f"]))
        if key in keys:
            raise SweepError(f"duplicate mapping for {key}")
        seen.add(p["id"]); keys.add(key)
    if keys != set(grid()):
        raise SweepError(f"manifest does not cover the 45-point grid exactly "
                         f"(missing {sorted(set(grid()) - keys)[:3]}, extra {sorted(keys - set(grid()))[:3]})")
    return pts


def _mean(m, k):
    return m[k]["mean"]


def compare(points: list[dict], rows: dict[str, dict]) -> dict:
    """points: validated manifest points.  rows: id -> analyze row (with
    status/metrics).  Returns {"points": [...], "groups": [...]}.  Raises
    SweepError for a missing row mapping or missing baseline."""
    missing = [p["id"] for p in points if p["id"] not in rows]
    if missing:
        raise SweepError(f"no analysis row for point(s): {missing[:5]}")
    out, groups = [], []
    for proc in PROCESSES:
        for vdd in VDDS_V:
            g = sorted((p for p in points if p["process"] == proc and p["vdd_v"] == vdd),
                       key=lambda p: p["load_f"])
            if not g or g[0]["load_f"] != 0.0:
                raise SweepError(f"missing 0 F baseline for {proc} {vdd} V")
            ent = []
            for p in g:
                r = rows[p["id"]]
                e = {"id": p["id"], "process": proc, "vdd_v": vdd, "load_f": p["load_f"],
                     "load_pf": p["load_f"] * 1e12, "trim_code": p.get("trim_code"),
                     "status": r["status"]}
                if r["status"] == "OK":
                    m = r["metrics"]
                    e |= {"frequency_hz": m["frequency_mean_hz"], "duty": _mean(m, "duty"),
                          "rise_s": _mean(m, "rise_time_10_90_s"), "fall_s": _mean(m, "fall_time_90_10_s")}
                    e["abs_error_pct"] = 100 * (e["frequency_hz"] / TARGET_HZ - 1)
                    e["outside_budget"] = not (BUDGET_PCT[0] <= e["abs_error_pct"] <= BUDGET_PCT[1])
                ent.append(e)
            base = ent[0]
            for e in ent:
                if e["status"] != "OK":
                    e["comparison"] = "FAIL: waveform row failed; no comparison"
                elif base["status"] != "OK":
                    e["comparison"] = "FAIL: zero-load baseline failed; no comparison"
                else:
                    e["comparison"] = "OK"
                    e["rel_freq_shift_pct"] = 100 * (e["frequency_hz"] / base["frequency_hz"] - 1)
                    e["duty_delta"] = e["duty"] - base["duty"]
                    for k in ("rise", "fall"):
                        e[f"{k}_delta_s"] = e[f"{k}_s"] - base[f"{k}_s"]
                        e[f"{k}_rel_change_pct"] = 100 * (e[f"{k}_s"] / base[f"{k}_s"] - 1)
            slopes = []
            for a, b in zip(ent, ent[1:]):
                s = {"from_pf": a["load_pf"], "to_pf": b["load_pf"]}
                if a["comparison"] == "OK" and b["comparison"] == "OK":
                    s["slope_pct_per_pF"] = (b["rel_freq_shift_pct"] - a["rel_freq_shift_pct"]) / (b["load_pf"] - a["load_pf"])
                else:
                    s["slope_pct_per_pF"] = None
                    s["reason"] = "FAIL: endpoint waveform row failed or baseline unavailable"
                slopes.append(s)
            # first sampled load outside the budget
            first = None
            if base["status"] == "OK" and base["outside_budget"]:
                verdict = "zero-load baseline already outside budget"
                first = 0.0
            else:
                verdict = None
                for e in ent:
                    if e["status"] != "OK":
                        verdict = f"indeterminate: waveform row failed at {e['load_pf']:g} pF before any outside-budget load"
                        break
                    if e["outside_budget"]:
                        verdict = f"first sampled load outside budget: {e['load_pf']:g} pF"
                        first = e["load_pf"]
                        break
                if verdict is None:
                    verdict = "not reached through 10 pF"
            groups.append({"process": proc, "vdd_v": vdd, "slopes": slopes,
                           "budget_status": verdict, "first_outside_budget_pf": first})
            out += ent
    return {"points": out, "groups": groups}


def analyse_points(man_dir: Path, points: list[dict], reports_dir: Path, p: analyze.Params,
                   artifacts_root: Path | None = None):
    rows, metas = {}, []
    for pt in points:
        rr, meta = analyze.analyse_report(Path(reports_dir) / pt["report"], pt["vdd_v"], p, artifacts_root)
        metas.append(meta or {"report": pt["report"], "vdd_v": pt["vdd_v"]})
        bad = [r for r in rr if r["status"] != "OK"]
        if bad:
            row = {"status": bad[0]["status"]}
        elif len(rr) != 1:
            row = {"status": f"FAIL: report holds {len(rr)} corners, expected exactly 1"}
        elif rr[0].get("process") != pt["process"] or rr[0].get("temp_c") != pt["temperature_c"]:
            row = {"status": f"FAIL: report corner {rr[0].get('process')}/{rr[0].get('temp_c')} "
                             f"does not match manifest {pt['process']}/{pt['temperature_c']}"}
        else:
            row = rr[0]
        rows[pt["id"]] = row
    return rows, metas


CSV_FIELDS = ["label", "id", "process", "vdd_v", "load_pf", "trim_code", "status", "comparison", "frequency_mhz",
              "abs_error_pct", "outside_budget", "rel_freq_shift_pct", "duty", "duty_delta",
              "rise_ps", "rise_rel_change_pct", "fall_ps", "fall_rel_change_pct"]


def write_results(out: Path, man: dict, res: dict, metas: list, synthetic: bool, p: analyze.Params) -> dict:
    out = Path(out)
    if out.exists():
        raise SweepError(f"refusing to overwrite existing run {out}")
    synthetic = synthetic or any(m.get("synthetic") for m in metas)
    banner = SYNTH if synthetic else ("Load-sensitivity analysis of simulator output; evidence status is set "
                                      "by the originating campaign record")
    nfail = sum(1 for e in res["points"] if e["comparison"] != "OK")
    doc = {"label": banner, "synthetic": synthetic,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "budget_note": "DR-0017 at-calibration -2.9%/+2.0 %; contextual away from nominal 27 C / 3.3 V; ratifies no load spec",
           "params": {"window_s": p.window_s, "min_cycles": p.min_cycles},
           "calibration": man.get("calibration"), "held_codes": man.get("held_codes"),
           "reports": metas, "n_points": len(res["points"]), "n_fail": nfail,
           "all_ok": nfail == 0 and len(res["points"]) == 45, **res}
    out.mkdir(parents=True)
    (out / "results.json").write_text(json.dumps(doc, indent=2) + "\n")

    def flatrow(e):
        d = {"label": banner, **{k: e.get(k) for k in ("id", "process", "vdd_v", "load_pf", "trim_code",
                                                      "status", "comparison", "abs_error_pct", "outside_budget",
                                                      "rel_freq_shift_pct", "duty", "duty_delta",
                                                      "rise_rel_change_pct", "fall_rel_change_pct")}}
        for k in ("frequency_hz", "rise_s", "fall_s"):
            if e.get(k) is not None:
                d[{"frequency_hz": "frequency_mhz", "rise_s": "rise_ps", "fall_s": "fall_ps"}[k]] = \
                    e[k] / (1e6 if k == "frequency_hz" else 1e-12)
        return d
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for e in res["points"]:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in flatrow(e).items()})
    g = lambda x, f="%.4g": "-" if x is None else f % x  # noqa: E731
    L = [f"# Load sensitivity {out.name}", "", f"**{banner}**", "",
         "Budget columns are DR-0017 at-calibration context only; no load specification is ratified.",
         "", f"{len(res['points'])} points, {nfail} failing.", "",
         "| process | VDD (V) | load (pF) | status | f (MHz) | shift vs 0 F (%) | abs err vs 48 MHz (%) | duty | rise (ps) | fall (ps) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for e in res["points"]:
        f = flatrow(e)
        L.append(f"| {e['process']} | {e['vdd_v']:g} | {e['load_pf']:g} | {e['comparison']} | {g(f.get('frequency_mhz'))} | "
                 f"{g(e.get('rel_freq_shift_pct'))} | {g(e.get('abs_error_pct'))} | {g(e.get('duty'))} | "
                 f"{g(f.get('rise_ps'))} | {g(f.get('fall_ps'))} |")
    L += ["", "## Interval slopes (percent per pF) and sampled budget status", ""]
    for gr in res["groups"]:
        sl = ", ".join(f"{s['from_pf']:g}-{s['to_pf']:g} pF: {g(s['slope_pct_per_pF'])}" for s in gr["slopes"])
        L.append(f"- {gr['process']} {gr['vdd_v']:g} V: {sl}; budget: {gr['budget_status']}")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--cal-run", required=True, type=Path)
    a.add_argument("--cal-target", choices=sorted(prepare.CAL_TARGETS), default="ratified")
    a.add_argument("--out", required=True, type=Path, help="NEW directory (never overwritten)")
    b = sub.add_parser("analyze")
    b.add_argument("--manifest", required=True, type=Path)
    b.add_argument("--reports-dir", required=True, type=Path, help="holds the report_<id>.json files named by the manifest")
    b.add_argument("--artifacts-root", type=Path, default=None)
    b.add_argument("--outdir", required=True, type=Path)
    b.add_argument("--synthetic", action="store_true")
    a_ = ap.parse_args()
    try:
        if a_.cmd == "prepare":
            man = prepare_sweep(a_.out, prepare.load_calibration(a_.cal_run, a_.cal_target))
            print(f"wrote {man['n_points']} requests to {a_.out}")
            return 0
        man = json.loads(a_.manifest.read_text())
        pts = validate_manifest(man)
        p = analyze.Params(window_s=man["settings"]["window_ns"] * 1e-9, min_cycles=man["settings"]["min_cycles"])
        rows, metas = analyse_points(a_.manifest.parent, pts, a_.reports_dir, p, a_.artifacts_root)
        doc = write_results(a_.outdir, man, compare(pts, rows), metas, a_.synthetic, p)
    except (SweepError, prepare.PrepareError, OSError, ValueError) as e:
        sys.exit(f"loadsweep.py: {e}")
    print(f"wrote {a_.outdir}: {doc['n_points']} points, {doc['n_fail']} failing; {doc['label']}")
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
