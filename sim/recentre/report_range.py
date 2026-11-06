#!/usr/bin/env python3
"""Post-process the P3 27-point batch reports (issue #66, AC 3).

Reads report_{tt,ff,ss}.json from a results dir (klt sim reports of
sim/recentre/p3/request_*.json) and prints a markdown grid.  Frequency from the
rising-edge times 5 and 25 of each clock: f = 20 / (t25 - t5)
(gen_requests.py).  Grades per point: f(0x00) <= 48 MHz <= f(0xFF), and the
post-trim error of the process's 27C/3.3V calibration code against 48 MHz.
Also compares the ratified trim range 28.800-67.200 MHz and the ratified
post-trim accuracy window (+8 % / -9 %, DR-0023).  Does NOT launch ngspice.

Usage: python3 -I sim/recentre/report_range.py <results-dir>
"""
import json
import sys
from pathlib import Path

TARGET = 48.0
RANGE = (28.8, 67.2)
ACC = (-9.0, 8.0)
CODES = {"tt": 0xA9, "ff": 0x59, "ss": 0xD7}


def freq_mhz(m: dict, which: str) -> float:
    return 20.0 / (m[f"tb_{which}"] - m[f"ta_{which}"]) / 1e6


def main(d: Path) -> int:
    rows = []
    for p in ("tt", "ff", "ss"):
        rep = json.loads((d / f"report_{p}.json").read_text())
        for c in rep["corners"]:
            m = {x["name"]: x["value"] for x in c["measurements"]}
            rows.append((p, c["supply_v"]["VDD"], c["temperature_c"], c["status"],
                         freq_mhz(m, "lo"), freq_mhz(m, "hi"), freq_mhz(m, "cal")))
    print("| proc | VDD | T (C) | status | f(0x00) MHz | f(0xFF) MHz | f(cal) MHz | cal err % | range ok | ratified range ok | acc ok |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    n_range = n_rat = n_acc = 0
    errs = {p: [] for p in CODES}
    for p, v, t, st, lo, hi, cal in rows:
        err = (cal / TARGET - 1) * 100
        errs[p].append(err)
        ok = lo <= TARGET <= hi
        rat = lo <= RANGE[0] and hi >= RANGE[1]
        acc = ACC[0] <= err <= ACC[1]
        n_range += ok
        n_rat += rat
        n_acc += acc
        print(f"| {p} | {v:.1f} | {t:g} | {st} | {lo:.3f} | {hi:.3f} | {cal:.3f} | {err:+.2f} | "
              f"{'yes' if ok else 'NO'} | {'yes' if rat else 'NO'} | {'yes' if acc else 'NO'} |")
    n = len(rows)
    print()
    print(f"* points: {n}; 48 MHz inside [f(0x00), f(0xFF)]: {n_range}/{n}; "
          f"covers ratified 28.8-67.2 MHz: {n_rat}/{n}; "
          f"post-trim error inside +8/-9 %: {n_acc}/{n}")
    for p, e in errs.items():
        print(f"* {p} (code 0x{CODES[p]:02X}): worst error {min(e):+.2f} % / {max(e):+.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
