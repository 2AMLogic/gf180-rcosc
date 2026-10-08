#!/usr/bin/env python3
"""Post-process `klt sim` startup-time reports into append-only evidence.

Input : one or more `klt sim --format json -o <outdir>` reports produced from
        sim/startup/request_v{30,33,36}.json (each corner's artifacts.waveform
        is read from the report's `artifacts` paths, or from --artifacts-root
        if the waveform was collected to a different directory).
Output: sim/startup/results/<runid>/{results.csv,manifest.json,summary.md,
        edges.json.gz}.  Refuses to overwrite an existing run id (CLAUDE.md:
        sim/ results are append-only).

Definitions (see sim/startup/README.md and DR-0020):
  t=0            start of the 0 -> VDD supply ramp (RAMP_NS long).
  period sample  WIN-cycle mean period (e[k+WIN]-e[k])/WIN: the simulator's
                 adaptive stepping puts ~0.2 ns of numerical noise on single
                 edge times (~0.7% of a 28 ns cycle), so single cycles are
                 not graded; sample k is stamped at edge k.
  edges          rising crossings of VDD/2 on clk (linear interpolation).
  settled period F  mean period over the last TAIL_NS of the run; the tail
                 itself must be steady (max period deviation <= TAIL_TOL).
  settle time(B) the start of the first cycle after which EVERY later cycle's
                 period is within +/-B of F.  Reported for several bands B.
  NON-START      fewer than MIN_EDGES clk edges in the whole run, or fewer
                 than MIN_TAIL_EDGES in the tail: reported as a failure,
                 never as a missing number.
  NOT-SETTLED    the tail is not steady, or the last cycle is outside band B.
"""
import argparse
import csv
import datetime
import gzip
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAMP_NS = 1000
TAIL_NS = 2000
TAIL_TOL = 0.005
WIN = 8  # cycles averaged per period sample (edge-time numerical noise ~0.2 ns/cycle)
MIN_EDGES = 20
MIN_TAIL_EDGES = 20
SPEC_US = 10.0
# Bands: see DR-0020.  PRIMARY is the strictest ratified figure.
BANDS = [("1.1%", 0.011), ("2.9%", 0.029), ("10.8%", 0.108)]
PRIMARY = "1.1%"


def rising_edges(t, v, vmid):
    out = []
    for i in range(1, len(t)):
        if v[i - 1] < vmid <= v[i]:
            f = (vmid - v[i - 1]) / (v[i] - v[i - 1])
            out.append(t[i - 1] + f * (t[i] - t[i - 1]))
    return out


def analyse(wf_path, vdd_nom):
    w = json.load(open(wf_path))
    names = [x["name"] for x in w["variables"]]
    ic, iv = names.index("v(clk)"), names.index("v(vdd)")
    pts = w["points"]
    t = [p[0] for p in pts]
    clk = [p[ic] for p in pts]
    vdd = [p[iv] for p in pts]
    tstop = t[-1]
    e = rising_edges(t, clk, vdd_nom / 2)
    t90 = next((t[i] for i in range(len(t)) if vdd[i] >= 0.9 * vdd_nom), None)
    r = {"n_edges": len(e), "tstop_ns": tstop * 1e9, "t_vdd90_ns": t90 * 1e9 if t90 else None,
         "clk_min_v": min(clk), "clk_max_v": max(clk)}
    tail0 = tstop - TAIL_NS * 1e-9
    tail = [x for x in e if x >= tail0]
    r["n_tail_edges"] = len(tail)
    if len(e) < MIN_EDGES or len(tail) < MIN_TAIL_EDGES:
        r["status"] = "NON-START"
        return r, e
    per = [(e[i + WIN] - e[i]) / WIN for i in range(len(e) - WIN)]
    tp = [per[i] for i in range(len(per)) if e[i] >= tail0]
    F = sum(tp) / len(tp)
    dev = max(abs(p - F) / F for p in tp)
    r["f_settled_mhz"] = 1e-6 / F
    r["tail_dev_pct"] = dev * 100
    if dev > TAIL_TOL:
        r["status"] = "NOT-SETTLED (tail not steady)"
        return r, e
    r["status"] = "STARTED"
    for label, b in BANDS:
        bad = [i for i, p in enumerate(per) if abs(p - F) / F > b]
        if bad and bad[-1] == len(per) - 1:
            r[f"t_settle_{label}_ns"] = None
        elif not bad:
            r[f"t_settle_{label}_ns"] = e[0] * 1e9
        else:
            r[f"t_settle_{label}_ns"] = e[bad[-1] + 1] * 1e9
    return r, e


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=HERE).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", help="klt sim JSON reports (v30, v33, v36)")
    ap.add_argument("--vdd", nargs="+", type=float, required=True,
                    help="supply for each report, same order")
    ap.add_argument("--artifacts-root", nargs="*", default=None,
                    help="per-report dir holding <corner dir>/waveform.raw.json (overrides report paths)")
    ap.add_argument("--runid", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    out = HERE / "results" / a.runid
    if out.exists():
        sys.exit(f"refusing to overwrite existing run {out}")
    rows, edges, remotes = [], {}, []
    for k, rep in enumerate(a.reports):
        d = json.load(open(rep))
        vdd = a.vdd[k]
        env_remote = d.get("environment", {}).get("remote")
        remotes.append({"report": Path(rep).name, "vdd_v": vdd, "remote": env_remote,
                        "status": d.get("status"), "corner_count": d.get("corner_count")})
        for c in d["corners"]:
            row = {"process": c["process"], "temp_c": c["temperature_c"], "vdd_v": vdd,
                   "klt_status": c["status"], "t_first_edge_ns": None}
            for m in c.get("measurements", []):
                if m["name"] == "t_first_edge" and m["value"] is not None:
                    row["t_first_edge_ns"] = m["value"] * 1e9
            wf = (c.get("artifacts") or {}).get("waveform")
            if a.artifacts_root:
                wf = str(Path(a.artifacts_root[k]) / Path(wf).parent.name / Path(wf).name) if wf else None
            if c["status"] in ("error",) or not wf or not Path(wf).exists():
                row.update(status="NO-DATA (sim error or waveform missing)")
                row["diag"] = json.dumps(c.get("diagnostics", []))[:300]
                rows.append(row)
                continue
            r, e = analyse(wf, vdd)
            row.update(r)
            edges[f"{c['process']}_{c['temperature_c']:g}C_{vdd:g}V"] = [round(x * 1e9, 3) for x in e]
            rows.append(row)
    out.mkdir(parents=True)
    fields = ["process", "temp_c", "vdd_v", "status", "klt_status", "n_edges", "f_settled_mhz",
              "tail_dev_pct", "t_first_edge_ns"] + [f"t_settle_{l}_ns" for l, _ in BANDS] + ["t_vdd90_ns", "diag"]
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4g}" if isinstance(v, float) else v) for k, v in r.items()})
    with gzip.open(out / "edges.json.gz", "wt") as fh:
        json.dump({"unit": "ns", "edges_rising_vdd_half": edges}, fh)

    def verdict(r, lab):
        if r["status"] != "STARTED":
            return "FAIL: " + r["status"]
        t = r.get(f"t_settle_{lab}_ns")
        if t is None:
            return "FAIL: not within band at end of run"
        return ("pass" if t <= SPEC_US * 1e3 else "**FAIL**")
    n = len(rows)
    summ = {}
    for lab, _ in BANDS:
        ok = [r for r in rows if verdict(r, lab) == "pass"]
        summ[lab] = {"pass": len(ok), "total": n}
    worst = {}
    for lab, _ in BANDS:
        ts = [r.get(f"t_settle_{lab}_ns") for r in rows if r.get(f"t_settle_{lab}_ns") is not None]
        worst[lab] = max(ts) if ts else None
    json.dump({"runid": a.runid, "git_sha": git("rev-parse", "HEAD"),
               "dirty_tree": bool(git("status", "--porcelain", "--", str(HERE), str(HERE.parent.parent / "design" / "netlist"))),
               "klt": subprocess.run(["klt", "--version"], capture_output=True, text=True).stdout.strip(),
               "ramp_ns": RAMP_NS, "tail_ns": TAIL_NS, "tail_tol": TAIL_TOL, "spec_us": SPEC_US,
               "bands": dict(BANDS), "primary_band": PRIMARY, "trim_code": "0xA3",
               "sim_reports": remotes, "note": a.note,
               "band_pass_counts": summ, "worst_settle_ns": worst, "points": rows},
              open(out / "manifest.json", "w"), indent=2)
        
    L = [f"# Startup-time sweep {a.runid} (issue #78)", "",
         "Generated by `sim/startup/startup_report.py` from `klt sim` reports of",
         "`sim/startup/request_v*.json`. Append-only evidence. t = 0 is the start of a",
         f"{RAMP_NS} ns linear 0 -> VDD ramp; trim code 0xA3 held at every point.",
         f"Spec: startup time <= {SPEC_US:g} us. Primary band {PRIMARY} (strictest ratified figure, DR-0020).", "",
         *( [f"**Run note: {a.note}**", ""] if a.note else [] ),
         "## Batch/sim job provenance", ""]
    for x in remotes:
        L.append(f"- `{x['report']}` (VDD {x['vdd_v']:g} V): status `{x['status']}`, {x['corner_count']} corners, remote `{x['remote']}`")
    L += ["", "## Verdict per band (points with settle time <= 10 us)", "",
          "| band (of own settled period) | pass | worst settle time (us) |", "|---|---|---|"]
    for lab, _ in BANDS:
        wv = worst[lab]
        L.append(f"| +/-{lab} | {summ[lab]['pass']}/{n} | {'—' if wv is None else '%.3f' % (wv / 1e3)} |")
    L += ["", "## Per-corner startup time (us from ramp start; bands as columns)", "",
          "| process | T (C) | VDD (V) | status | f settled (MHz) | first edge | " +
          " | ".join(f"settle +/-{l}" for l, _ in BANDS) + " | verdict (primary) |",
          "|---|---|---|---|---|---|" + "---|" * (len(BANDS) + 1)]
    def us(v):
        return "—" if v is None else "%.3f" % (v / 1e3)
    for r in sorted(rows, key=lambda r: (r["vdd_v"], r["process"], r["temp_c"])):
        L.append(f"| `{r['process']}` | {r['temp_c']:g} | {r['vdd_v']:g} | {r['status']} | "
                 f"{r.get('f_settled_mhz', float('nan')):.2f} | {us(r.get('t_first_edge_ns'))} | " +
                 " | ".join(us(r.get(f"t_settle_{l}_ns")) for l, _ in BANDS) +
                 f" | {verdict(r, PRIMARY)} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print(f"wrote {out}")
    print(json.dumps({"band_pass_counts": summ, "worst_settle_ns": worst}))


if __name__ == "__main__":
    main()
