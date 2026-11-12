#!/usr/bin/env python3
"""Ron_eff = R_real - R_ideal from a gen_ron_requests.py run.  Usage: ron_table.py RUNDIR OUT.md"""
import json
import sys
from pathlib import Path

DV = 0.05
CODES = [0x00, 0x55, 0x80, 0xAA, 0xD4, 0xFF]
LEVELS = ["vl", "mid", "vh"]
V = [("v30", 3.0), ("v33", 3.3), ("v36", 3.6)]


def load(run: Path, variant: str, v: str) -> dict:
    rep = json.loads((run / "art" / f"request_{variant}_{v}" / "report.json").read_text())
    out = {}
    for c in rep["corners"]:
        for m in c["measurements"]:
            out[(c["temperature_c"], m["name"])] = DV / abs(m["value"])
    return out


def main(run: Path, outp: Path) -> None:
    R = {(var, v): load(run, var, v) for var in ("real", "ideal") for v, _ in V}
    lines = ["# Bank switch effective Ron vs VDD at ss (generated; source " + run.name + ")", "",
             "Ron_eff = R_real - R_ideal (ohm), bank p-m resistance at a DC node level, 50 mV across the bank.",
             "R_ideal (each bit's TG replaced by 1 mOhm if the bit is set, 1 GOhm if clear) is the ladder poly R alone at that code and corner.", ""]
    for T in (-40.0, 27.0, 85.0):
        lines += [f"## ss, {T:g} C", "", "| code | node | R_ideal 3.0 V | Ron_eff 3.0 V | Ron_eff 3.3 V | Ron_eff 3.6 V | Ron(3.0)/Ron(3.6) | R_ideal 3.6 V |", "|---|---|---|---|---|---|---|---|"]
        for ci, code in enumerate(CODES):
            for lv in LEVELS:
                n = f"i_c{ci}{lv}"
                ron = [R[("real", v)][(T, n)] - R[("ideal", v)][(T, n)] for v, _ in V]
                ri30 = R[("ideal", "v30")][(T, n)]
                ri36 = R[("ideal", "v36")][(T, n)]
                lines.append(f"| 0x{code:02X} | {lv} | {ri30:.0f} | {ron[0]:.0f} | {ron[1]:.0f} | {ron[2]:.0f} | {ron[0]/ron[2]:.3f} | {ri36:.0f} |")
        lines.append("")
    outp.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
