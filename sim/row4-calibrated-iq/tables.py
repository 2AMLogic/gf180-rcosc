#!/usr/bin/env python3
"""Tables for the matched-die calibrated-code running-Iq measurement (issue #337). Offline; reads committed
run dirs, writes markdown + JSON summaries. Launches nothing.

  tables.py check  CANDDIR CTLDIR                 draw-identity checks (seeds vs DR-0032 reports, engine parity,
                                                 500 dice/group, fixed code per die, control coverage)
  tables.py TAG    CANDDIR CTLDIR OUTDIR          per-process Iq distributions and matched-die deltas vs control

CANDDIR: a gen.py cand run dir (art_<proc>/report.json or report_<proc>.json).
CTLDIR:  the matching gen.py ctl run dir (art_decks_<proc>/report.json + codes.json + <proc>_die<k>/stdout.bin).
DR-0032 baseline reports for the seed-parity check: sim/mc/results/20261112T025135Z/report_main_<proc>.json.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DR0032 = REPO / "sim" / "mc" / "results" / "20261112T025135Z"
PROCS = ("tt", "ff", "ss")
LABS = ("n40_30", "n40_33", "n40_36", "27_30", "27_33", "27_36", "85_30", "85_33", "85_36")
TEMPV = {lab: (t, v) for lab, t, v in
         [(l, (-40.0 if l.startswith("n40") else float(l.split("_")[0])), int(l.split("_")[1]) / 10)
          for l in LABS]}
LIMIT_UA = 500.0
DR44_BAND = (-4.57, 0.18)  # DR-0044: L 0.7 vs L 1 control, 108 nominal cells


def _report(rundir: Path, *names: str) -> dict:
    for n in names:
        p = rundir / n
        if p.exists():
            return json.loads(p.read_text())
    raise SystemExit(f"no report under {rundir}: looked at {names}")


def cand_corners(rundir: Path, proc: str) -> list[dict]:
    return _report(rundir, f"art_{proc}/report.json", f"report_{proc}.json")["corners"]


def ctl_report(rundir: Path, proc: str) -> dict:
    return _report(rundir, f"art_decks_{proc}/report.json", f"report_decks_{proc}.json")


def ctl_samples(rundir: Path, proc: str) -> dict[int, dict]:
    """parse every control deck unit's stdout.bin -> {sample_index: {'iq_<lab>': A, ...}}"""
    rep = ctl_report(rundir, proc)
    out = {}
    for u in rep["units"]:
        if u["status"] != "pass":
            continue
        m = re.fullmatch(rf"{proc}_die(\d+)", u["id"])
        if not m:
            continue
        vals = {}
        for line in (Path(rundir) / f"art_decks_{proc}" / u["id"] / "stdout.bin").read_text().splitlines():
            mm = re.fullmatch(r"(iq|f)_(n40_30|n40_33|n40_36|27_30|27_33|27_36|85_30|85_33|85_36)\[0\] = ([-0-9.e+]+)", line.strip())
            if mm:
                vals[f"{mm.group(1)}_{mm.group(2)}"] = float(mm.group(3))
        out[int(m.group(1))] = vals
    return out


def pct(a, b):
    return (a - b) / b * 100.0 if b else float("nan")


def check(canddir: Path, ctldir: Path) -> int:
    rc = 0
    engines = set()
    for proc in PROCS:
        cs = cand_corners(canddir, proc)
        base = json.loads((DR0032 / f"report_main_{proc}.json").read_text())["corners"]
        n_seed_ok = sum(1 for c, b in zip(cs, base)
                        if c["monte_carlo"]["sample_index"] == b["monte_carlo"]["sample_index"]
                        and c["monte_carlo"]["seed"] == b["monte_carlo"]["seed"]
                        and c["monte_carlo"]["process_seed"] == b["monte_carlo"]["process_seed"]
                        and c["monte_carlo"]["mismatch_seed"] == b["monte_carlo"]["mismatch_seed"])
        ids = [c["monte_carlo"]["sample_index"] for c in cs]
        codes = {int(next(m["value"] for m in c["measurements"] if m["name"] == "code_clamped")) for c in cs}
        ctlr = ctl_report(ctldir, proc)
        ctl_ids = {int(m.group(1)) for u in ctlr["units"] if (m := re.fullmatch(rf"{proc}_die(\d+)", u["id"]))}
        ctl_pass = {int(m.group(1)) for u in ctlr["units"] if u["status"] == "pass" and (m := re.fullmatch(rf"{proc}_die(\d+)", u["id"]))}
        envs = _report(canddir, f"art_{proc}/report.json", f"report_{proc}.json")["environment"]
        engines.add(envs["engine_version"])
        ok = (len(cs) == 500 and n_seed_ok == 500 and len(set(ids)) == 500
              and len(codes) >= 1 and ctl_ids == set(range(500)) and ctl_pass == set(range(500)))
        print(f"{proc}: corners={len(cs)} seed-parity-vs-DR-0032={n_seed_ok}/500 distinct-dice={len(set(ids))} "
              f"codes={sorted(codes)} control-units={len(ctl_ids)}/500 pass={len(ctl_pass)}/500 "
              f"engine={envs['engine_version']} -> {'OK' if ok else 'FAIL'}")
        rc |= 0 if ok else 1
    print(f"engine builds seen (candidate side): {sorted(engines)}; control side: "
          f"{sorted({ctl_report(ctldir, p)['environment']['engine_version'] for p in PROCS})}")
    return rc


def dist(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return {}
    q = lambda f: xs[min(n - 1, int(f * (n - 1)))]
    return {"n": n, "min": xs[0], "p05": q(0.05), "p50": q(0.50), "p95": q(0.95), "max": xs[-1]}


def tables(tag: str, canddir: Path, ctldir: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    summary = {"variant": tag, "limit_ua": LIMIT_UA, "dr0044_band_pct": DR44_BAND, "procs": {}}
    lines = [f"# Matched-die calibrated-code running Iq - {tag} vs L=1 um control (issue #337)",
             "",
             f"Candidate run `{canddir.name}`, control run `{ctldir.name}`. Population: DR-0032 draws "
             f"(500 per process, seed 20261008), each die calibrated at 27 C / 3.3 V on the candidate DUT and the "
             f"control measured at the SAME draw (same derived seed), code, supply and temperature. Iq in uA; "
             f"delta = (candidate - control) / control * 100. DR-0044 nominal-cell band: "
             f"{DR44_BAND[0]:+.2f}..{DR44_BAND[1]:+.2f} %. Ratified row (README / DR-0003 Row 4): < 500 uA running.",
             ""]
    for proc in PROCS:
        cs = cand_corners(canddir, proc)
        ctl = ctl_samples(ctldir, proc)
        codesjson = json.loads((ctldir / "codes.json").read_text())[proc]
        rows, deltas, cand_all, ctl_all, over, over_ctl = [], [], [], [], [], []
        missing = 0
        for c in cs:
            k = c["monte_carlo"]["sample_index"]
            d = {m["name"]: m["value"] for m in c["measurements"]}
            code = int(d["code_clamped"])
            assert any(e["sample_index"] == k and e["code"] == code for e in codesjson), (proc, k, code)
            if k not in ctl:
                missing += 1
                continue
            for lab in LABS:
                iq = d[f"iq_{lab}_a"] * 1e6
                ciq = ctl[k][f"iq_{lab}"] * 1e6
                t, v = TEMPV[lab]
                rows.append((iq, pct(iq, ciq), k, code, v, t, ciq))
                cand_all.append(iq)
                ctl_all.append(ciq)
                deltas.append(pct(iq, ciq))
                if iq >= LIMIT_UA:
                    over.append(rows[-1])
                if ciq >= LIMIT_UA:
                    over_ctl.append(rows[-1])
        worst_abs = max(rows, key=lambda r: r[0])
        worst_pct = max(rows, key=lambda r: r[1])
        best_pct = min(rows, key=lambda r: r[1])
        dd, dc = dist(deltas), dist(cand_all)
        code_counts = {}
        for c in cs:
            code = int(next(m["value"] for m in c["measurements"] if m["name"] == "code_clamped"))
            code_counts[code] = code_counts.get(code, 0) + 1
        summary["procs"][proc] = {
            "dice": len(cs), "matched_points": len(rows), "missing_control_dice": missing,
            "code_occupancy": {str(k): v for k, v in sorted(code_counts.items())},
            "codes_at_0xFF": code_counts.get(255, 0),
            "cand_iq_ua": dc, "ctl_iq_ua": dist(ctl_all), "delta_pct": dd,
            "cand_cells_ge_limit": len(over), "ctl_cells_ge_limit": len(over_ctl),
            "worst_abs": {"iq_ua": worst_abs[0], "die": worst_abs[2], "code": worst_abs[3],
                          "vdd": worst_abs[4], "temp_c": worst_abs[5], "ctl_iq_ua": worst_abs[6],
                          "delta_pct": worst_abs[1]},
            "worst_increase": {"iq_ua": worst_pct[0], "delta_pct": worst_pct[1], "die": worst_pct[2],
                               "code": worst_pct[3], "vdd": worst_pct[4], "temp_c": worst_pct[5],
                               "ctl_iq_ua": worst_pct[6]},
            "best_decrease": {"delta_pct": best_pct[1], "die": best_pct[2], "code": best_pct[3],
                              "vdd": best_pct[4], "temp_c": best_pct[5]},
            "within_dr0044_band": (dd["min"] >= DR44_BAND[0] and dd["max"] <= DR44_BAND[1]),
        }
        p = summary["procs"][proc]
        lines += [
            f"## {proc}",
            "",
            f"- dice: {p['dice']} (matched control points: {p['matched_points']}, missing control dice: {missing})",
            f"- calibrated-code occupancy: " + ", ".join(f"0x{k:02X}x{v}" for k, v in sorted(code_counts.items()))
            + f"; dice at 0xFF: {p['codes_at_0xFF']}",
            f"- candidate Iq uA: min {dc['min']:.1f} / p50 {dc['p50']:.1f} / p95 {dc['p95']:.1f} / max {dc['max']:.1f}"
            f" (control: {dist(ctl_all)['min']:.1f}..{dist(ctl_all)['max']:.1f})",
            f"- delta vs matched control %: min {dd['min']:+.2f} / p50 {dd['p50']:+.2f} / p95 {dd['p95']:+.2f} / max {dd['max']:+.2f}"
            f" -- DR-0044 band {DR44_BAND[0]:+.2f}..{DR44_BAND[1]:+.2f}: "
            f"{'inside' if p['within_dr0044_band'] else 'OUTSIDE'}",
            f"- cells >= {LIMIT_UA:.0f} uA: candidate {p['cand_cells_ge_limit']} of {len(rows)}, control {p['ctl_cells_ge_limit']}",
            f"- worst absolute: {worst_abs[0]:.1f} uA (die {worst_abs[2]}, code 0x{worst_abs[3]:02X}, "
            f"{worst_abs[4]:.1f} V, {worst_abs[5]:.0f} C; control {worst_abs[6]:.1f} uA, {worst_abs[1]:+.2f} %)",
            f"- worst increase: {worst_pct[1]:+.2f} % -> {worst_pct[0]:.1f} uA (die {worst_pct[2]}, code 0x{worst_pct[3]:02X}, "
            f"{worst_pct[4]:.1f} V, {worst_pct[5]:.0f} C; control {worst_pct[6]:.1f} uA)",
            f"- largest decrease: {best_pct[1]:+.2f} % (die {best_pct[2]}, code 0x{best_pct[3]:02X}, {best_pct[4]:.1f} V, {best_pct[5]:.0f} C)",
            "",
        ]
    (outdir / "table_vs_control.md").write_text("\n".join(lines) + "\n")
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {outdir}/table_vs_control.md and summary.json")


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "check":
        sys.exit(check(Path(sys.argv[2]), Path(sys.argv[3])))
    elif len(sys.argv) >= 5:
        tables(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        sys.exit(__doc__)
