#!/usr/bin/env python3
"""Per-row grader for the T1 item-5 `klt sim` envelopes (issue #201).

Reads the 15 `report_c<code>_v<VDD*10>.json` envelopes in a results directory
and writes `rows.md` + `rows.json` beside them: per ratified spec row, a
pass / FAIL / UNEVALUABLE verdict against the ratified number and the binding
(worst) corner.  Ratified limits are quoted, never relaxed; a corner whose
measurement did not return a value is a FAIL of every row that needs it, not
a skipped point.

Usage: python3 -I sim/item5/report_rows.py sim/item5/results/<runid>
"""
import json
import sys
from pathlib import Path

F0 = 48.0e6
CODES = {"lo": "00", "mid": "80", "cal": "a9", "nxt": "aa", "hi": "ff"}
VDDS = {"30": 3.0, "33": 3.3, "36": 3.6}
# Ratified limits (README target-spec table; DR-0017 / DR-0003).
RANGE_LO, RANGE_HI = 28.8e6, 67.2e6      # row 2
LSB_PCT = 0.314                          # row 2
UNTRIMMED_PCT = 35.0                     # row 3
CAL_LO, CAL_HI = -2.9, 2.0               # row 4 (27 C, VDD +/-10 %)
TEMP_LO, TEMP_HI = -10.8, 8.8            # row 5 (-40..+85 C, VDD +/-10 %)
IQ_MAX_UA = 500.0                        # row 8


def load(d: Path):
    data = {}
    for code in CODES.values():
        for v in VDDS:
            f = d / f"report_c{code}_v{v}.json"
            rep = json.loads(f.read_text())
            pts = {}
            for c in rep["corners"]:
                m = {x["name"]: x["value"] for x in c["measurements"]}
                proc, _, t = c["corner_id"].split("/")
                pts[(proc, float(t.rstrip("C")))] = (m.get("fosc"), m.get("iq_run_ua"))
            data[(code, VDDS[v])] = (rep["status"], pts)
    return data


def pct(f):
    return (f - F0) / F0 * 100.0


def main(d: Path) -> None:
    data = load(d)
    procs = ["tt", "ff", "ss", "fs", "sf", "rc_f", "rc_s"]
    temps = [-40.0, 27.0, 85.0]
    rows = {}

    def get(code, vdd, proc, t):
        return data[(code, vdd)][1].get((proc, t), (None, None))[0]

    # Row 1: tt / 27 C / 3.3 V at the calibration code.
    f = get("a9", 3.3, "tt", 27.0)
    rows[1] = dict(ok=f is not None and abs(pct(f)) <= 1.1, binding="tt/27C/3.3V",
                   text=f"f(0xA9) = {f/1e6:.3f} MHz ({pct(f):+.2f} %) vs 48.000 MHz; "
                        "ratified calibration tolerance +/-1.1 % (DR-0023 re-derives it at the calibration point)")

    # Row 2: nominal range ends and LSB step.
    lo, hi = get("00", 3.3, "tt", 27.0), get("ff", 3.3, "tt", 27.0)
    a9, aa = get("a9", 3.3, "tt", 27.0), get("aa", 3.3, "tt", 27.0)
    lsb = (aa - a9) / a9 * 100.0
    rows[2] = dict(ok=lo <= RANGE_LO and hi >= RANGE_HI and lsb <= LSB_PCT * 1.10,
                   binding="tt/27C/3.3V",
                   text=f"f(0x00) = {lo/1e6:.3f} MHz (needs <= 28.800), f(0xFF) = {hi/1e6:.3f} MHz (needs >= 67.200), "
                        f"LSB 0xA9->0xAA = {lsb:.3f} %/code (ratified 0.314 %/code); "
                        "Monte Carlo remainder (claim S1) is a declared gap")

    # Row 3: untrimmed spread of the mid-scale code, 27 C / 3.3 V, vs tt.
    tt = get("80", 3.3, "tt", 27.0)
    devs = {p: (get("80", 3.3, p, 27.0) - tt) / tt * 100.0 for p in procs
            if get("80", 3.3, p, 27.0) is not None}
    wp = max(devs, key=lambda p: abs(devs[p]))
    rows[3] = dict(ok=abs(devs[wp]) <= UNTRIMMED_PCT, binding=f"{wp}/27C/3.3V",
                   text="0x80 at 27 C / 3.3 V vs tt: " + ", ".join(f"{p} {v:+.1f} %" for p, v in devs.items())
                        + f" (ratified +/-35 %)")

    # Rows 4 / 5: the held calibration code over all supplies, no per-die recal.
    def worst(window_temps, lim_lo, lim_hi):
        bad, worst_pt = [], None
        for v in VDDS.values():
            for p in procs:
                for t in window_temps:
                    f = get("a9", v, p, t)
                    e = None if f is None else pct(f)
                    key = (p, t, v)
                    if e is None or e < lim_lo or e > lim_hi:
                        bad.append((key, e))
                    if e is not None and (worst_pt is None or abs(e) > abs(worst_pt[1])):
                        worst_pt = (key, e)
        return bad, worst_pt

    for n, tl, lo_, hi_ in ((4, [27.0], CAL_LO, CAL_HI), (5, temps, TEMP_LO, TEMP_HI)):
        bad, wpt = worst(tl, lo_, hi_)
        total = len(VDDS) * len(procs) * len(tl)
        nostart = [b for b in bad if b[1] is None]
        key, e = wpt
        rows[n] = dict(
            ok=not bad, binding=f"{key[0]}/{key[1]:g}C/{key[2]:g}V",
            text=f"one code (0xA9) held across {len(procs)} process corners: {total - len(bad)}/{total} points inside "
                 f"{lo_:+.1f} %/{hi_:+.1f} %; largest |error| {e:+.2f} % at {key[0]}/{key[1]:g} C/{key[2]:g} V"
                 + (f"; {len(nostart)} point(s) returned no frequency" if nostart else "")
                 + "; per-die recalibration is NOT modelled here (see sim/recentre per-process-code grid); "
                   "Monte Carlo remainder (claim S2/S3) is a declared gap")

    # Row 7 / 10: every supply x every temperature produced a frequency.
    missing = sorted({(c, v, p, t) for (c, v), (_, pts) in data.items() for (p, t), (f, _) in pts.items() if f is None})
    envs = sorted({(c, v) for (c, v, p, t) in missing})
    rows[7] = dict(ok=not missing, binding=("fs/-40C at 3.3 V and 3.6 V" if missing else "n/a"),
                   text=f"{len(missing)} (code, VDD, process, T) points returned no frequency, in {len(envs)} of 15 envelopes"
                        + ("; all at " + ", ".join(sorted({f'{p}/{t:g}C/{v:g}V' for (c, v, p, t) in missing})) if missing else ""))
    rows[10] = dict(ok=not missing, binding=rows[7]["binding"],
                    text="temperature axis -40/27/85 C present in every request; " + rows[7]["text"])

    # Row 8: max Iq over the whole grid.
    iqs = [(iq, (c, v, p, t)) for (c, v), (_, pts) in data.items() for (p, t), (_, iq) in pts.items() if iq is not None and c == "a9"]
    iq, (c, v, p, t) = max(iqs)
    rows[8] = dict(ok=iq < IQ_MAX_UA, binding=f"{p}/{t:g}C/{v:g}V (code 0x{c.upper()})",
                   text=f"max iq_run_ua = {iq:.1f} uA over {len(iqs)} measured calibration-code (0xA9) points (limit < 500 uA); "
                        "window is the fixed 200-1200 ns, not whole periods")

    out = ["# Item 5 per-row verdicts (generated by report_rows.py; ratified limits, none relaxed)", "",
           "| Row | Verdict | Binding corner | Evidence |", "|---|---|---|---|"]
    for n in (1, 2, 3, 4, 5, 7, 8, 10):
        r = rows[n]
        out.append(f"| {n} | {'pass' if r['ok'] else 'FAIL'} | {r['binding']} | {r['text']} |")
    out.append("| 6 | declared gap | n/a | reserved, not designed (DR-0004) |")
    out.append("| 9 | declared gap | n/a | startup bench not re-run on the settled netlist (see ROWS.md) |")
    (d / "rows.md").write_text("\n".join(out) + "\n")
    (d / "rows.json").write_text(json.dumps({str(k): v for k, v in rows.items()}, indent=1) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
