#!/usr/bin/env python3
"""Device-to-stage map for the flat rcosc_top extraction (issue #347).

Both netlists in play are flat parasitic extractions with no stage hierarchy and no instance
names (`* device instance $N r0 *1 X,Y class` carries geometry only), so stage identity cannot
be read off the netlist text.  This builder recovers it from the committed per-block rosters
(`layout/reports/rcosc_*.extracted.spice`): each block's devices carry their in-block placement
coordinates, so a single translation per block registers the block's devices 1:1 onto the flat
extraction's devices by (class, L, W) signature and coordinates (resistors and caps carry a
class-only signature, so at a candidate offset any two single-element-signature devices within
`tol` are interchangeable -- a MiM cap could register against a poly resistor sitting within
0.05 um; the candidate must be unique and the conservation count re-checks the total, and roster
resistor values are reported Ohms while the flat deck's are r_length/r_width, so their lengths
are not comparable).  The 10-device remainder is assigned
from `design/netlist/rcosc_top.spice`'s top-level devices: the timing MiM (only cap_mim device),
the discharge nfet (only W=20U nfet) and the eight latch devices as one group (XMG1A-D /
XMG2A-D are not individually distinguishable, but they are one stage, so the group assignment
is exact for attribution).

Supply-entry analysis: the extraction splits every net into per-terminal copies star-connected
through parasitic resistors (`Rvdd_t0 vdd__t0 vdd ...`), so the VDD parasitic network is the
union-find component of `vdd` over those R lines.  Every device terminal landing in that
component is a point where supply current enters its stage; those are the terminals the probed
DUT re-terminates onto `vdd_<stage>` behind a 0 V source (see gen_stage_iq_requests.py).

Emits the map as committed JSON data (stage -> devices with coordinates and vdd-side terminals,
per-block offsets, conservation).  Nothing is guessed: a device that cannot be registered is
listed as unresolved and, unless --allow-unresolved, fails the build.  Usage:

    python3 -I stage_map.py FLAT_DECK OUT_JSON --roster bias=layout/reports/rcosc_bias.extracted.spice ... [--label NAME] [--allow-unresolved]
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEV_COMMENT = re.compile(r"\* device instance (\S+) (r\d+) \*1 (-?[\d.]+),(-?[\d.]+) (\w+)")
PARASITIC_R = re.compile(r"^R\S*\s+(\S+)\s+(\S+)\s+[\d.eE+-]+\s*$")
MODELS = ("nfet_03v3", "pfet_03v3", "ppolyf_u_1k", "cap_mim_1f0fF")
CURRENT_STAGES = ("bias", "cmp_h", "cmp_l", "latch", "trim")
ZERO_STAGES = ("timing", "disch")          # no vdd terminal in the schematic netlist
STAGE_ORDER = CURRENT_STAGES + ZERO_STAGES


def parse_deck(path):
    """Devices of an extraction deck: comment `$N` instance ids only (parasitic R/C entries use
    `_net_tK` ids and R_/C_ lines and are skipped).  Returns [{name, x, y, cclass, line}]."""
    devs, coord = [], None
    for raw in Path(path).read_text().splitlines():
        m = DEV_COMMENT.match(raw)
        if m:
            coord = (float(m.group(3)), float(m.group(4)), m.group(5), m.group(1)) if m.group(1).startswith("$") else None
            continue
        if coord and raw.strip() and not raw.startswith("*") and re.match(r"^[XMR]\S+\s", raw):
            devs.append({"name": raw.split()[0], "x": coord[0], "y": coord[1], "cclass": coord[2], "line": raw.strip()})
            coord = None
    return devs


def fet_sig(cclass, line):
    base = "nfet" if "nfet" in cclass else "pfet" if "pfet" in cclass else None
    if base is None:
        return None
    L = re.search(r"L=([\d.]+)U", line, re.I).group(1)
    W = re.search(r"W=([\d.]+)U", line, re.I).group(1)
    return (base, "L" + L, "W" + W)


def dev_sig(d):
    """Match signature: FETs (class, L, W); resistors and caps class only (roster resistor
    values are Ohms, flat-deck values r_length/r_width -- not comparable, and the x0.70
    poly rescale means even lengths differ between roster generations)."""
    if d["cclass"].startswith("cap_mim"):
        return ("cap_mim",)
    s = fet_sig(d["cclass"], d["line"])
    return s if s else ("ppolyf",)


def register_block(roster, flat, claimed, tol=0.05):
    """Find the translation registering every roster device 1:1 onto unclaimed flat devices of
    equal signature.  Returns (offset, {roster_name: flat_name}, unresolved_names)."""
    free = [d for d in flat if d["name"] not in claimed]
    by_sig = {}
    for d in free:
        by_sig.setdefault(dev_sig(d), []).append(d)
    offsets = Counter()
    for rd in roster:
        s = dev_sig(rd)
        for fd in by_sig.get(s, ()):
            offsets[(round(fd["x"] - rd["x"], 3), round(fd["y"] - rd["y"], 3))] += 1

    def try_offset(off):
        used, assign, unresolved = set(), {}, []
        for rd in roster:
            rx, ry, s = rd["x"] + off[0], rd["y"] + off[1], dev_sig(rd)
            cands = [fd for fd in free if fd["name"] not in used and abs(fd["x"] - rx) < tol and abs(fd["y"] - ry) < tol
                     and (dev_sig(fd) == s or (len(s) == 1 and len(dev_sig(fd)) == 1))]
            if len(cands) == 1:
                assign[rd["name"]] = cands[0]["name"]
                used.add(cands[0]["name"])
            else:
                unresolved.append(rd["name"])
        return assign, unresolved

    best = None
    for off, _ in offsets.most_common():
        assign, unresolved = try_offset(off)
        if not unresolved:
            return off, assign, []
        if best is None or len(unresolved) < len(best[2]):
            best = (off, assign, unresolved)
    return best if best else ((0.0, 0.0), {}, [d["name"] for d in roster])


def vdd_side_terms(devs, deck_text):
    """Union-find over the extraction's parasitic star resistors; the VDD network is the
    component of `vdd`.  Returns {device_name: [(term_index, orig_net), ...]}."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for raw in deck_text.splitlines():
        m = PARASITIC_R.match(raw)
        if m:
            a, b = find(m.group(1)), find(m.group(2))
            if a != b:
                parent[a] = b
    root = find("vdd")
    terms = {}
    for d in devs:
        toks = d["line"].split()
        mi = [i for i, t in enumerate(toks) if t in MODELS]
        assert len(mi) == 1, f"{d['name']}: model token not found in {d['line']}"
        hits = [(i, n) for i, n in enumerate(toks[1:mi[0]]) if n in parent and find(n) == root]
        if hits:
            terms[d["name"]] = hits
    return terms


def build_map(flat_path, rosters, allow_unresolved=False):
    flat = parse_deck(flat_path)
    deck_text = Path(flat_path).read_text()
    claimed, offsets, unresolved_all = set(), {}, []
    stages = {s: [] for s in STAGE_ORDER}
    for stage in sorted(rosters):
        roster = parse_deck(rosters[stage])
        off, assign, unresolved = register_block(roster, flat, claimed)
        offsets[stage] = {"offset": list(off), "devices": len(roster), "registered": len(assign)}
        by_name = {d["name"]: d for d in flat}
        for rn, fn in sorted(assign.items()):
            claimed.add(fn)
            stages[stage].append(by_name[fn])
        if unresolved:
            unresolved_all += [(stage, n) for n in unresolved]
            continue

    rem = [d for d in flat if d["name"] not in claimed]
    caps = [d for d in rem if d["cclass"].startswith("cap_mim")]
    disch = [d for d in rem if fet_sig(d["cclass"], d["line"]) == ("nfet", "L0.5", "W20")]
    if len(caps) != 1 or len(disch) != 1:
        unresolved_all += [("timing", d["name"]) for d in caps] + [("disch", d["name"]) for d in disch]
    else:
        stages["timing"].append(caps[0])
        stages["disch"].append(disch[0])
        rem = [d for d in rem if d not in caps + disch]
    latch_sigs = {("nfet", "L0.5", "W2"), ("pfet", "L0.5", "W4")}
    latch_cands = [d for d in rem if dev_sig(d) in latch_sigs]
    stages["latch"] += latch_cands
    rem = [d for d in rem if d not in latch_cands]
    unresolved_all += [("<top-level>", d["name"]) for d in rem]

    if unresolved_all and not allow_unresolved:
        raise SystemExit(f"unresolved devices (no guessing): {unresolved_all}")

    terms = vdd_side_terms(flat, deck_text)
    for stage in STAGE_ORDER:
        for d in stages[stage]:
            d["vdd_terms"] = [[i, n] for i, n in terms.get(d["name"], [])]
    for stage in ZERO_STAGES:
        assert all(not d["vdd_terms"] for d in stages[stage]), f"{stage} has vdd-side terminals -- not zero by construction"

    assigned = [d for s in STAGE_ORDER for d in stages[s]]
    assert len({d["name"] for d in assigned}) == len(assigned), "a flat device was assigned twice"
    return {
        "flat_deck": str(flat_path),
        "flat_deck_sha256": hashlib.sha256(Path(flat_path).read_bytes()).hexdigest(),
        "device_count": len(flat),
        "assigned_count": len(assigned),
        "unresolved": [f"{s}:{n}" for s, n in unresolved_all],
        "offsets": offsets,
        "stage_device_counts": {s: len(stages[s]) for s in STAGE_ORDER},
        "vdd_side_summary": {"devices": sum(1 for d in assigned if d["vdd_terms"]),
                             "terminals": sum(len(d["vdd_terms"]) for d in assigned)},
        "stages": {s: stages[s] for s in STAGE_ORDER},
    }


def check_conservation(m):
    """The committed conservation assertion: every flat device assigned exactly once."""
    total = sum(m["stage_device_counts"].values())
    assert total == m["device_count"] == m["assigned_count"], \
        f"conservation: stages sum {total} != device count {m['device_count']}"
    assert not m["unresolved"], f"unresolved devices: {m['unresolved']}"
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("flat_deck")
    ap.add_argument("out_json")
    ap.add_argument("--roster", action="append", required=True, metavar="STAGE=PATH")
    ap.add_argument("--label", default="")
    ap.add_argument("--allow-unresolved", action="store_true")
    a = ap.parse_args()
    rosters = {}
    for r in a.roster:
        stage, path = r.split("=", 1)
        assert stage in STAGE_ORDER, f"unknown stage {stage}"
        rosters[stage] = path
    m = build_map(a.flat_deck, rosters, a.allow_unresolved)
    m["label"] = a.label
    check_conservation(m)
    Path(a.out_json).write_text(json.dumps(m, indent=1) + "\n")
    print(f"stage map -> {a.out_json}: {m['assigned_count']}/{m['device_count']} devices, "
          f"stage counts {m['stage_device_counts']}, vdd-side {m['vdd_side_summary']}")


if __name__ == "__main__":
    main()
