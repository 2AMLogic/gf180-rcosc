#!/usr/bin/env python3
"""Offline pricing tables for the row-2 finalists (issue #460, step 4).

Reads the report_<sizing>_<corner-dir>_<stem>.json files written by run_set.py
for gen_pricing.py's three modes and prints, per sizing:

  calib  f at every scanned code at 27 C / 3.3 V per process, the
         nearest-to-48 MHz code, and the headroom to both rails (in codes and
         as a fraction of the remaining range).
  stage  the row-4 supply-span table at the per-die calibration codes: f and
         error vs the same process's 3.3 V / 27 C point, per (supply, temp);
         the ss 27 C span (max-min error over supply) is the row-4 term
         (DR-0032 basis, comparable with DR-0045 / DR-0047).
  iq     the row-8 running-Iq table (DR-0003 Row 4 "< 500 uA running", DR-0046
         basis): iq_run per (code, supply, process, temp).

Offline analysis of measured batch reports; no simulator is launched.

    python3 -I sim/row2-trimsize/pricing_table.py --reports R --mode calib|stage|iq [--out D]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGET_HZ = 48.0e6
RAILS = (0x00, 0xFF)


def read_corners(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    if str(d.get("status")).lower() in ("failed", "error", "refused") or d.get("refused"):
        raise ValueError(f"{path.name}: report status {d.get('status')!r}")
    out = []
    for c in d.get("corners") or []:
        if c.get("status") != "pass":
            raise ValueError(f"{path.name}: corner {c.get('process')}/{c.get('temperature_c')} status {c.get('status')!r}")
        ms = {m["name"]: m for m in c.get("measurements") or [] if isinstance(m, dict)}
        for k in ("fosc", "iq_run"):
            if k in ms:
                out.append({"process": c.get("process"), "temperature_c": c.get("temperature_c"),
                            "name": k, "value": ms[k].get("value")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="row-2 pricing tables (offline)")
    ap.add_argument("--reports", required=True, type=Path)
    ap.add_argument("--mode", required=True, choices=("calib", "stage", "iq"))
    ap.add_argument("--out", type=Path, default=None, help="also write the tables to OUT/pricing-<mode>.md")
    args = ap.parse_args()

    lines: list[str] = []
    files = sorted(args.reports.glob("report_*.json"))
    if not files:
        print(f"error: no report_*.json in {args.reports}", file=__import__("sys").stderr)
        return 1

    if args.mode == "calib":
        scan: dict[tuple[str, str], float] = {}   # (sizing, proc) -> {code: f}
        curves: dict[tuple[str, str], dict[int, float]] = {}
        for p in files:
            parts = p.stem.split("_")   # report_<sizing...>_<calib...>_<proc>_cXX
            sizing = parts[1]
            m = p.stem.split("_c")[-1]
            proc = p.stem.split("_")[-2]
            code = int(m, 16)
            for e in read_corners(p):
                if e["name"] == "fosc":
                    curves.setdefault((sizing, proc), {})[code] = e["value"]
        lines = ["# calib scan (27 C / 3.3 V), per sizing x process", "",
                 "| sizing | proc | scanned codes (f MHz) | nearest-48MHz code | headroom to rails |", "|---|---|---|---|---|"]
        for (sizing, proc), f in sorted(curves.items()):
            best = min(f, key=lambda c: abs(f[c] - TARGET_HZ))
            hi = ", ".join(f"0x{c:02X}:{f[c]/1e6:.3f}" for c in sorted(f))
            lines.append(f"| {sizing} | {proc} | {hi} | 0x{best:02X} ({f[best]/1e6:.3f} MHz) "
                         f"| -{best} / +{255-best} codes |")
    elif args.mode == "stage":
        pts: dict[tuple[str, str, float, float], float] = {}
        for p in files:
            stem = p.stem[len("report_"):]
            sizing, rest = stem.split("_stage_", 1)
            proc, vv = rest.split("_v")
            vdd = int(vv) / 10.0
            for e in read_corners(p):
                if e["name"] == "fosc":
                    pts[(sizing, proc, vdd, e["temperature_c"])] = e["value"]
        lines = ["# row-4 stage table at the per-die calibration codes (f MHz / error vs 3.3 V 27 C, points)", "",
                 "| sizing | proc | VDD | -40 C | 27 C | 85 C |", "|---|---|---|---|---|---|"]
        for (sizing, proc, vdd) in sorted({(a, b, c) for (a, b, c, _) in pts}):
            ref = pts.get((sizing, proc, 3.3, 27.0))
            row = []
            for t in (-40.0, 27.0, 85.0):
                f = pts.get((sizing, proc, vdd, t))
                row.append(f"{f/1e6:.3f} / {100*(f/ref-1):+.2f}%" if f and ref else "-")
            lines.append(f"| {sizing} | {proc} | {vdd:g} | " + " | ".join(row) + " |")
        lines += ["", "## ss 27 C supply span (row-4 term, DR-0032 basis)", "",
                  "| sizing | span over 3.0-3.6 V (points) |", "|---|---|"]
        for sizing in sorted({a for (a, _, _, _) in pts}):
            errs = [100 * (pts[(sizing, "ss", v, 27.0)] / pts[(sizing, "ss", 3.3, 27.0)] - 1)
                    for v in (3.0, 3.6) if (sizing, "ss", v, 27.0) in pts]
            if len(errs) == 2:
                lines.append(f"| {sizing} | {max(errs)-min(errs):.2f} |")
    else:  # iq
        cells: dict[tuple[str, int, float, str, float], float] = {}
        for p in files:
            stem = p.stem[len("report_"):]
            sizing, rest = stem.split("_iq_", 1)
            code_s, vv = rest.split("_v")
            code, vdd = int(code_s[1:], 16), int(vv) / 10.0
            for e in read_corners(p):
                cells[(sizing, code, vdd, e["process"], e["temperature_c"])] = e["value"]
        lines = ["# row-8 running Iq (uA), per sizing x code x supply (cells: tt/ff/ss x -40/27/85 C)", "",
                 "| sizing | code | VDD | worst cell | mean |", "|---|---|---|---|---|"]
        for (sizing, code, vdd) in sorted({(a, b, c) for (a, b, c, _, _) in cells}):
            vs = [v for (a, b, c, _, _), v in cells.items() if (a, b, c) == (sizing, code, vdd)]
            lines.append(f"| {sizing} | 0x{code:02X} | {vdd:g} | {max(vs)*1e6:.1f} | {sum(vs)/len(vs)*1e6:.1f} |")

    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"pricing-{args.mode}.md").write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
