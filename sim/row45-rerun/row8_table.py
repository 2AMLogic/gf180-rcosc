#!/usr/bin/env python3
"""Tabulate the row-8 comparator-H screen (issue #458, gen_row8_screen.py campaign).

Reads the per-variant calib / iq / delay / startup batch reports of one campaign root and
writes <ROOT>/table.md:

- worst-case running Iq at the calibrated codes (27 held-code cells) and at 0xFF (27 cells)
  against the strict 500 uA row-8 limit, with per-cell deltas vs the control;
- row-4 supply response at 27 C and row-5 held-code response over the grid, both graded
  against EACH DIE'S OWN 3.3 V / 27 C held-code frequency (the DR-0043/DR-0045 convention;
  the calibration residue vs 48.000 MHz is printed separately in the calibration table so
  the absolute basis is recoverable) -- deviations at the held code only, never 0xFF cells;
- row-10 lost-clock count at the held codes;
- comparator-H delay (vc rise through vh -> cmph_out rise, first occurrences after 700 ns)
  and its change vs control;
- fs / -40 C startup at 3.3 / 3.6 V analysed with the DR-0020 bands (sim/startup_report.py
  analyse(), the settled_report.py verdict: STARTED and t_settle_1.1% <= 10 us); the parsed
  verdicts are cached to startup_analysis.json so the waveform raws need not be retained.

Iq is the DR-0009 charge integral over clk rising edges 5..25 on the DR-0044 bench.
Usage: row8_table.py ROOT   (ROOT = the campaign results dir; writes ROOT/table.md)
"""
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "sim"))
from _module_loader import load_module  # noqa: E402

sr = load_module("startup_report", REPO / "sim" / "startup" / "startup_report.py", reuse=True)

# held codes: control per DR-0043 (results/20261112T201500Z-calib-extracted-l07, same DUT
# sha as this campaign's dutref); variants per this campaign's calib scans (nearest scanned
# code to 48 MHz at 27 C / 3.3 V, step-4 scan anchored at the control code; DR-0032/DR-0045
# allow the nearest scanned code, the ss axis is non-monotonic above 0xDC - DR-0014).
HELD = {
    "control": {"tt": 0xA4, "ff": 0x4F, "ss": 0xD4},
    "t85": {"tt": 0xA4, "ff": 0x4F, "ss": 0xD4},
    "t70": {"tt": 0xA8, "ff": 0x53, "ss": 0xD8},
    "t55": {"tt": 0xA8, "ff": 0x57, "ss": 0xD8},
    "t40": {"tt": 0xAC, "ff": 0x57, "ss": 0xDC},
    "l06": {"tt": 0xA4, "ff": 0x4F, "ss": 0xD4},
    "t70l06": {"tt": 0xA8, "ff": 0x53, "ss": 0xD8},
}
LABEL = {"control": "control", "t85": "tail x0.85", "t70": "tail x0.70", "t55": "tail x0.55",
         "t40": "tail x0.40", "l06": "load L 0.6", "t70l06": "tail x0.70 + load L 0.6"}
F_REF = 48.0e6
PROCS = ("tt", "ff", "ss")
TEMPS = (-40.0, 27.0, 85.0)
VDDS = (3.0, 3.3, 3.6)
DR0044_TABLE = Path(__file__).resolve().parent / "results" / "20261113T064105Z-iq-extracted-l07" / "table.md"


def meas(c):
    return {m["name"]: m["value"] for m in c.get("measurements", [])}


def freq_hz(mm):
    """fosc when measured; else 20 periods / (f_tb - f_ta) from the same edge window."""
    if mm.get("fosc") is not None:
        return mm["fosc"]
    if mm.get("f_ta") and mm.get("f_tb"):
        return 20.0 / (mm["f_tb"] - mm["f_ta"])
    return None


def calib_cells(vdir):
    """(proc, code) -> fosc Hz from the calibration scan reports."""
    out = {}
    for f in sorted(glob.glob(str(vdir / "request_*_c*" / "report.json"))):
        m = re.match(r"request_(tt|ff|ss)_c([0-9A-F]+)$", Path(f).parent.name)
        if not m:
            continue
        for c in json.load(open(f))["corners"]:
            f_ = freq_hz(meas(c))
            if f_:
                out[(m.group(1), int(m.group(2), 16))] = f_
    return out


def iq_cells(vdir):
    """-> (held, cff): (proc, temp, vdd) -> (code, fosc or None, iq_uA or None, klt_status).
    The held-code requests and the all-process 0xFF requests measure the same 27
    (proc, T, VDD) keys at two different codes; they are kept as two separate maps,
    never merged, so a partially collected set can neither alias an 0xFF cell into a
    held-code row nor hide a collected 0xFF cell behind a held-code one."""
    held, cff = {}, {}
    for f in sorted(glob.glob(str(vdir / "request_iq_*" / "report.json"))):
        stem = Path(f).parent.name  # request_iq_tt_cA8_v30 / request_iq_cFF_v30
        m = re.match(r"request_iq_(?:(tt|ff|ss)_)?(c[0-9A-F]+)_v(\d+)$", stem)
        code, vdd = int(m.group(2)[1:], 16), int(m.group(3)) / 10
        for c in json.load(open(f))["corners"]:
            mm = meas(c)
            f_ = freq_hz(mm)
            iq = mm.get("iq_run")
            e = (code, f_, iq * 1e6 if iq is not None else None, c["status"])
            (cff if code == 0xFF else held)[(c["process"], c["temperature_c"], vdd)] = e
    return held, cff


def worst(cells):
    """worst iq over one 27-cell map -> (uA, cell, n_over_500, n_missing, n_grid).

    A cell with no measurement or a non-pass klt status counts as missing: it is a
    failure to demonstrate the limit, not a pass (issue #458 test plan)."""
    n = len(PROCS) * len(TEMPS) * len(VDDS)  # 27
    got = {k: v[2] for k, v in cells.items() if v[2] is not None and v[3] == "pass"}
    miss = n - len(got)
    if not got:
        return (float("nan"), None, 0, miss, n)
    k = max(got, key=got.get)
    return (got[k], k, sum(1 for x in got.values() if x >= 500.0), miss, n)


def dev_pct(f, ref):
    return (f / ref - 1) * 100 if (f is not None and ref) else None


def delay_cells(vdir):
    """(vdd, temp) -> (t_cmp_h ns, fosc MHz) at the ff corner, held ff code."""
    out = {}
    for f in sorted(glob.glob(str(vdir / "request_dly_*" / "report.json"))):
        vdd = int(re.search(r"_v(\d+)$", Path(f).parent.name).group(1)) / 10
        for c in json.load(open(f))["corners"]:
            mm = meas(c)
            if mm.get("ev_cmph") and mm.get("ev_vh"):
                t = (mm["ev_cmph"] - mm["ev_vh"]) % (1.0 / mm["fosc"]) if mm.get("fosc") \
                    else mm["ev_cmph"] - mm["ev_vh"]
                out[(vdd, c["temperature_c"])] = (t * 1e9,
                                                  mm.get("fosc", 0) / 1e6 if mm.get("fosc") else None)
    return out


def startup_cells(root, v):
    """vdd -> verdict dict; analyse() over waveform.raw.json, cached in startup_analysis.json."""
    cache_p = root / "startup_analysis.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    out = {}
    for f in sorted(glob.glob(str(root / v / "startup" / "request_v*" / "report.json"))):
        vdd = int(re.search(r"_v(\d+)$", Path(f).parent.name).group(1)) / 10
        key = f"{v}/v{vdd:g}"
        if key in cache:
            out[vdd] = cache[key]
            continue
        wfs = sorted(Path(f).parent.glob("fs_novdd_n40C/waveform.raw.json"))
        if not wfs:
            out[vdd] = {"status": "NO-WAVEFORM"}
            continue
        r, _ = sr.analyse(wfs[0], vdd)
        ok = r["status"] == "STARTED" and r.get("t_settle_1.1%_ns") is not None \
            and r["t_settle_1.1%_ns"] <= sr.SPEC_US * 1e3
        entry = {"status": r["status"], "f_settled_mhz": r.get("f_settled_mhz"),
                 "t_settle_1p1_ns": r.get("t_settle_1.1%_ns"), "pass": bool(ok)}
        cache[key] = entry
        out[vdd] = entry
    cache_p.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
    return out


def dr0044_control_0xff():
    """(proc, T, vdd) -> uA from DR-0044's committed table (the same DUT as this control)."""
    out = {}
    for line in DR0044_TABLE.read_text().splitlines():
        m = re.match(r"\| 0x([0-9A-F]+) \| ([0-9.]+) \| (tt|ff|ss) \| (-?\d+) \| ([0-9.]+) \|", line)
        if m and int(m.group(1), 16) == 0xFF:
            out[(m.group(3), float(m.group(4)), float(m.group(2)))] = float(m.group(5))
    return out


def main(root):
    root = Path(root)
    lines = ["# Row-8 comparator-H current screen (issue #458, DR-0046 lever)", "",
             f"Campaign `{root.name}`; DUTs from `gen_row8_screen.py dut` on the DR-0044 extraction"
             " (`results/20261112T200335Z-extract-l07`, sha256 `01e06dae...d16a1`); `dut_check`:"
             " every variant moves only the comparator-H tail fingers (X$39..X$46) and/or the"
             " mirror loads (X$65/X$66).",
             "Iq = DR-0009 charge integral over clk rising edges 5..25 (DR-0044 bench, batch"
             " fleet). Row-4/5 deviations are graded against **each die's own 3.3 V / 27 C"
             " held-code frequency** (DR-0043/DR-0045 convention); the calibration residue vs"
             " 48.000 MHz is in the calibration table. Row-4/5/10 use held-code cells only.",
             "",
             "## Variant DUTs (sha256 of `<variant>/iq/rcosc_top_variant.spice`; the delay set's"
             " copy differs only by the three analysis probe taps, the startup set's is the same"
             " DUT under its `rcosc_top_p3.spice` bench name)", "",
             "| variant | sha256 |", "|---|---|"]
    for v in HELD:
        p = root / v / "iq" / "rcosc_top_variant.spice"
        lines.append(f"| {LABEL[v]} | `{hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'missing'}` |")
    lines += [""]
    # ---- calibration ---------------------------------------------------------------------------
    calib = {v: calib_cells(root / v / "calib") for v in HELD}
    lines += ["## Calibration (27 C / 3.3 V; nearest scanned code to 48 MHz, step 4)", "",
              "| variant | tt code | f (MHz) | ff code | f (MHz) | ss code | f (MHz) |", "|---|---|---|---|---|---|---|"]
    fscan = {}
    for v in HELD:
        row, fscan[v] = [LABEL[v]], {}
        for p in PROCS:
            f_ = calib[v].get((p, HELD[v][p]))
            fscan[v][p] = f_
            row += [f"0x{HELD[v][p]:02X}", f"{f_/1e6:.3f}" if f_ else "DR-0043"]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "The control's codes and scan frequencies are DR-0043's committed calibration"
              " (`20261112T201500Z-calib-extracted-l07`, same DUT sha).  All row-4/5 references"
              " below are each die's own 3.3 V / 27 C held-code cell of this campaign's iq grid.",
              ""]

    # ---- iq ------------------------------------------------------------------------------------
    allheld, allcff = {}, {}
    for v in HELD:
        allheld[v], allcff[v] = iq_cells(root / v / "iq")
    fref = {v: {p: allheld[v].get((p, 27.0, 3.3), (None, None, None, None))[1] for p in PROCS} for v in HELD}
    res = [max(abs(fref[v][p] / 1e6 - 48) for p in PROCS) for v in HELD
           if all(fref[v][p] for p in PROCS) and len(allheld[v]) == 27]
    if res:
        lines += [f"Calibration residue of the references vs 48.000 MHz (max |f-48| per variant):"
                  f" {max(res):.2f} MHz worst across variants.", ""]
    lines += ["## Running Iq vs the strict 500 uA row-8 limit (worst cell named)", "",
              "| variant | worst Iq @ cal code (uA, cell) | n>=500 | miss | worst Iq @ 0xFF (uA, cell) | n>=500 | miss | d(worst cal) vs control (uA) |",
              "|---|---|---|---|---|---|---|---|"]
    ctl_worst = None
    for v in HELD:
        c, f_ = worst(allheld[v]), worst(allcff[v])
        cs = f"{c[0]:.1f} ({c[1][0]}/{c[1][1]:g}C/{c[1][2]:g}V)" if c[1] else "pending"
        fs = f"{f_[0]:.1f} ({f_[1][0]}/{f_[1][1]:g}C/{f_[1][2]:g}V)" if f_[1] else "pending"
        if v == "control":
            ctl_worst = c[0]
        d = f"{c[0]-ctl_worst:+.1f}" if (c[1] and ctl_worst and ctl_worst == ctl_worst) else ""
        lines.append(f"| {LABEL[v]} | {cs} | {c[2]} | {c[3]}/{c[4]} | {fs} | {f_[2]} | {f_[3]}/{f_[4]} | {d} |")

    # ---- rows 4 / 5 / 10 (held-code cells only) -------------------------------------------------
    lines += ["", "## Row 4 (supply response at 27 C, held code; window -2.9 / +2.0 % vs the die's 3.3 V / 27 C reference)", "",
              "| variant | tt low/high (%) | ff low/high (%) | ss low/high (%) | worst span (pt) | verdict |", "|---|---|---|---|---|---|"]
    for v, cells in allheld.items():
        per, spans = {}, []
        n_held = len(cells)
        if n_held < 27:
            lines.append(f"| {LABEL[v]} | pending ({n_held}/27 held-code cells) | | | | |")
            continue
        for p in PROCS:
            ref = fref[v][p]
            ds = [dev_pct(c[1], ref) for (pr, t, vd), c in cells.items()
                  if pr == p and t == 27.0 and c[0] == HELD[v][p] and c[1] is not None] if ref else []
            per[p] = (min(ds), max(ds)) if ds else (float("nan"), float("nan"))
            if ds:
                spans.append(per[p][1] - per[p][0])
        lo = min(x[0] for x in per.values())
        hi = max(x[1] for x in per.values())
        ok = lo >= -2.9 and hi <= 2.0
        lines.append(f"| {LABEL[v]} | " + " | ".join(f"{a:+.2f} / {b:+.2f}" for a, b in per.values())
                     + f" | {max(spans) if spans else float('nan'):.2f} | {'pass' if ok else 'FAIL'} |")

    lines += ["", "## Row 5 (held code over the 9-cell grid; window -10.8 / +8.8 % vs the die's 3.3 V / 27 C reference)", "",
              "| variant | worst cold cell (%) | worst hot cell (%) | ff/85C/3.0V (%) | verdict |", "|---|---|---|---|---|"]
    for v, cells in allheld.items():
        held_cells = cells
        if any(c[1] is None for c in held_cells.values()) or not all(fref[v][p] for p in PROCS):
            lines.append(f"| {LABEL[v]} | pending (missing cells) | | | |")
            continue
        colds, hots = [], []
        for p in PROCS:
            ref = fref[v][p]
            for k, c in held_cells.items():
                if k[0] != p:
                    continue
                d = dev_pct(c[1], ref)
                (colds if k[1] == -40.0 else hots if k[1] == 85.0 else []).append((d, k))
        cc, hc = min(colds), max(hots)
        f85 = dev_pct(held_cells.get(("ff", 85.0, 3.0), (None, None, None, None))[1], fref[v]["ff"])
        ok = cc[0] >= -10.8 and hc[0] <= 8.8
        lines.append(f"| {LABEL[v]} | {cc[0]:+.2f} ({cc[1][0]}/{cc[1][2]:g}V) | {hc[0]:+.2f} ({hc[1][0]}/{hc[1][2]:g}V) "
                     f"| {f85:+.2f} | {'pass' if ok else 'FAIL'} |")

    lines += ["", "## Row 10 (lost clock over the held-code grid)", "",
              "| variant | cells with no clock (f < 1 MHz or failed) |", "|---|---|"]
    for v, cells in allheld.items():
        lost = [k for k, c in cells.items() if (c[1] is None or c[1] < 1e6 or c[3] != "pass")]
        lines.append(f"| {LABEL[v]} | {len(lost)}" + (f" ({', '.join(f'{a}/{b:g}C/{c:g}V' for a, b, c in lost)})" if lost else "") + " |")

    # ---- delay ---------------------------------------------------------------------------------
    dly = {v: delay_cells(root / v / "delay") for v in HELD}
    lines += ["", "## Comparator-H delay at the ff held code (vc rises through vh -> cmph_out rise)", "",
              "| variant | ff code | 3.0V/85C (ns) | 3.0V/-40C (ns) | 3.6V/85C (ns) | d(3.0V/85C) vs control (ns) |",
              "|---|---|---|---|---|---|"]
    for v, d in dly.items():
        a, b, c = d.get((3.0, 85.0)), d.get((3.0, -40.0)), d.get((3.6, 85.0))
        if a and b and c and None not in (a[0], b[0], c[0]):
            da = a[0] - dly["control"][(3.0, 85.0)][0]
            lines.append(f"| {LABEL[v]} | 0x{HELD[v]['ff']:02X} | {a[0]:.2f} | {b[0]:.2f} | {c[0]:.2f} | {da:+.2f} |")
        else:
            lines.append(f"| {LABEL[v]} | 0x{HELD[v]['ff']:02X} | missing | | | |")

    # ---- startup -------------------------------------------------------------------------------
    st = {v: startup_cells(root, v) for v in HELD}
    lines += ["", "## Startup at fs / -40 C (1 us ramp, the variant's held tt code; DR-0020 primary band 1.1 %, bound 10 us)", "",
              "| variant | tt code | 3.3V status / settle (us) | 3.6V status / settle (us) | verdict |", "|---|---|---|---|---|"]
    for v, s in st.items():
        a, b = s.get(3.3), s.get(3.6)
        fmt = lambda e: f"{e['status']} / {e['t_settle_1p1_ns']/1e3:.2f}" if e and e.get("t_settle_1p1_ns") is not None else (e and e.get("status", "missing")) or "missing"
        ok = bool(a and b and a.get("pass") and b.get("pass"))
        lines.append(f"| {LABEL[v]} | 0x{HELD[v]['tt']:02X} | {fmt(a)} | {fmt(b)} | {'pass' if ok else 'FAIL'} |")

    # ---- control back-to-back --------------------------------------------------------------------
    dr0044 = dr0044_control_0xff()
    diffs = []
    for (p, t, vd), uA in dr0044.items():
        c = allcff["control"].get((p, t, vd))
        if c and c[2] is not None:
            diffs.append((c[2] - uA) / uA * 100)
    if diffs:
        lines += ["", f"Control back-to-back gate: the control DUT's 27 `0xFF` cells reproduce DR-0044's"
                  f" committed figures ({DR0044_TABLE.parent.name}) to {min(diffs):+.2f}..{max(diffs):+.2f} %"
                  f" (n={len(diffs)}).", ""]

    (root / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
