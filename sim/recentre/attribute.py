#!/usr/bin/env python3
"""Attribute the extracted-vs-schematic frequency shift (issue #66, AC 1).

Single-corner ngspice runs, executed ONE AT A TIME (no pool, no grid), on the
committed extracted netlist with parasitic groups removed:

  * leave-one-out : full extracted netlist minus one group
  * cumulative    : groups removed in GROUPS order; the last step is the
                    extracted *devices* with every parasitic R/C deleted
  * schematic     : design/netlist/pvt_tb.spice unmodified

At three corners: worst (ff/-40C/3.6V), best (ss/-40C/3.6V), centre
(tt/27C/3.3V), at the fixed trim code 0xA3 of the 27-point record.

Shares are of the schematic-to-extracted shift expressed in *period*
(1/f): the period is the additive quantity (delay adds, frequency does not).
Cumulative-removal shares sum to the total exactly by construction; the
leave-one-out sum differs from the total by the interaction term, reported
as the residual.

Usage: python3 -I sim/recentre/attribute.py            (fresh run id each time)
"""
import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pexlib as L  # noqa: E402

sys.path.insert(0, str(HERE.parent))
import evidence_stage  # noqa: E402  scratch staging + artifact store (#196)

CODE = 0xA3
CORNERS = {
    "worst": ("ff", -40.0, 3.6),
    "best": ("ss", -40.0, 3.6),
    "centre": ("tt", 27.0, 3.3),
}


def main() -> None:
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Raw output is staged in git-ignored scratch and stored through the
    # artifact store at the end (issue #196); fail closed before simulating.
    try:
        stage = evidence_stage.open_stage("recentre", runid)
    except evidence_stage.StoreError as exc:
        sys.exit(f"ERROR: evidence cannot be stored, not starting (fail closed): {exc}")
    out = stage.results / runid  # mirrors the sim/<bench>/results/<ts> layout
    logs = stage.corners / f"attribution-{runid}"
    out.mkdir(parents=True)
    logs.mkdir(parents=True)
    cards = L.load_cards()
    rows = []
    started = time.time()
    for cname, (proc, temp, vdd) in CORNERS.items():
        pt = L.base.Point(proc, temp, vdd, CODE)

        def go(label, text):
            r = L.run(text, pt, logs, f"{cname}_{label}")
            rows.append({"corner": cname, "process": proc, "temp_c": temp,
                         "vdd_v": vdd, "variant": label, "f_hz": r["f_hz"],
                         "iq_a": r["iq_a"], "log": f"sim/recentre/corners/attribution-{runid}/{r['log']}"})
            print(cname, label, r["f_hz"], flush=True)

        go("schematic", L.schematic_harness())
        go("full", L.harness(cards))
        # Model A: netlist exactly as extracted (substrate node vsubs only
        # DC-tied to ground through the extractor's 1 Tohm shunt).
        for g in L.GROUPS:
            go(f"loo_{g}", L.harness(L.variant(cards, {g})))
        dropped: set[str] = set()
        for g in L.GROUPS:
            dropped.add(g)
            go(f"cum_{g}", L.harness(L.variant(cards, set(dropped))))
        # Model B: same, but vsubs hard-tied to ground (1 mohm).  The
        # telescoping chain starts with the tie itself, so its steps sum
        # exactly to (extracted - schematic).
        go("tie_full", L.harness(L.variant(cards, set(), tie_substrate=True)))
        for g in L.GROUPS:
            go(f"tie_loo_{g}", L.harness(L.variant(cards, {g}, tie_substrate=True)))
        dropped = set()
        for g in L.GROUPS:
            dropped.add(g)
            go(f"tie_cum_{g}", L.harness(L.variant(cards, set(dropped), tie_substrate=True)))
        if cname == "centre":
            (out / "rcosc_top.devices_only.spice").write_text(
                "\n".join(L.variant(cards, set(L.GROUPS))) + "\n")
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    manifest = {
        "runid": runid, "issue": 66, "trim_code": f"0x{CODE:02X}",
        "source_netlist": str(L.PEX_SRC.relative_to(L.REPO)),
        "source_netlist_sha256": hashlib.sha256(L.PEX_SRC.read_bytes()).hexdigest(),
        "groups": L.GROUPS, "corners": CORNERS,
        "ngspice": subprocess.run(["ngspice", "-v"], capture_output=True, text=True).stdout.splitlines()[:1],
        "wall_s": round(time.time() - started, 1),
        "git_sha": L.base.git_sha(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "summary.md").write_text(
        f"# recentre attribution {runid}\n\n"
        f"Command: `{' '.join(sys.argv)}`\n\n"
        f"{len(rows)} single-corner runs at trim code 0x{CODE:02X}; `results.csv`, "
        f"`manifest.json` and the raw logs under `corners/attribution-{runid}/` are in "
        "the artifact store.\n")
    sys.exit(evidence_stage.finish_or_report(stage))


if __name__ == "__main__":
    main()
