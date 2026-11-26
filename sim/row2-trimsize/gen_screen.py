#!/usr/bin/env python3
"""Offline sparse-code screen bench generator for the row-2 trim-bank sizings (issue #460).

Builds, for each named variant, one extracted-DUT netlist copy plus one
testbench and one single-corner `klt sim` request per screened trim code, in
the layout `sim/trim-dense/run_batch.py` and `run_set.py` read
(`<bench>/<variant>/<corner>/{rcosc_top_<variant>.spice, tb_cXX.spice,
request_cXX.json}`).  The testbench and request bytes come from
`sim/trim-dense/prepare.py` unchanged (same measurement, solver settings and
corner sections as the committed #87 dense campaign), so a `ctrl` variant
reproduces the campaign's own numbers.  Nothing here runs a simulator.

Sizing names are `s<RFIX>-<r0>-...-<r7>[w<K>]` (see variant.py).  They are
generated from a fit_weights.py proposal (`--fit fit.json`), or listed
explicitly with `--sizing NAME[,NAME...]` (repeatable).  `ctrl` is always
generated first.

    python3 -I sim/row2-trimsize/gen_screen.py --fit <run>/fit.json --out /tmp/bench
    python3 -I sim/row2-trimsize/gen_screen.py --sizing s30.8-0.18-... --out /tmp/bench
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim"))
sys.path.insert(0, str(HERE))
from _module_loader import load_module  # noqa: E402
import evidence_common  # noqa: E402  shared sha256/banner/new-run guard (#260)
import variant  # noqa: E402

prepare = load_module("trim_dense_prepare", REPO / "sim" / "trim-dense" / "prepare.py", reuse=False)

SRC = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"   # the #87 campaign `ext` netlist
L_MIN_UM = 0.15   # DRC-ish floor for the smallest re-sized segments (see sizing_from)

# Screened codes: endpoints, +/-1 around every power-of-two carry (bit b flips
# at 2^b-1 -> 2^b), +/-1 around the four measured DR-0021 top-of-range carries
# (0x7F->0x80, 0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0), some mid-block carries
# (0x2F->0x30, 0x5F->0x60, 0x9F->0xA0), single-bit codes, and calibration /
# pattern-spread codes.
CARRY_CODES = sorted({0x00, 0xFF}
                     | {c for b in range(1, 8) for c in (2 ** b - 2, 2 ** b - 1, 2 ** b, 2 ** b + 1)}
                     | {c for t in (0x80, 0xC0, 0xE0, 0xF0) for c in (t - 2, t - 1, t, t + 1)}
                     | {0x2F, 0x30, 0x5F, 0x60, 0x9F, 0xA0}
                     | {0x01, 0x55, 0x5C, 0x90, 0xA5, 0xA9, 0xAA, 0xB0, 0xCC, 0xD4, 0xE8, 0xF5, 0xF8})


def sizing_from(fit_path: Path, prop_name: str, comp_corner: str) -> str:
    """Ratio-rule sizing name for one proposal compensated at one corner.

    Lengths are floored at L_MIN_UM: the ratio rule assumes beta_b scales with
    the drawn r_b, which breaks for the two smallest segments where the bypass
    switch's transient Ron is a comparable size (the rule then wants sub-DRC
    lengths).  A floored low bit keeps a positive, in-band step (its 128 steps
    are each ~rho_0 * W, far inside the half-LSB band); the high bits, which
    own the carries and the monotonicity risk, are never floored.
    """
    doc = json.loads(fit_path.read_text())
    prop = doc["proposals"][prop_name]
    comp_fit = doc["curves"][comp_corner]
    L = ["%.5f" % max(prop["rfix_len_um"], 0.0)]
    for b in range(8):
        r_drawn = doc["drawn"]["seg_r_ohm"][b]
        r_new = r_drawn * (prop["W_s"] * (2 ** b)) / abs(comp_fit["beta_s"][b])
        L.append("%.5f" % max((r_new - doc["drawn"]["r_head_ohm"]) / doc["drawn"]["r_per_um"], L_MIN_UM))
    return "s" + "-".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="row-2 screen bench generator (offline)")
    ap.add_argument("--fit", type=Path, default=None, help="fit.json from fit_weights.py")
    ap.add_argument("--comp-map", default=None,
                    help="prop=corner pairs, e.g. F1.85=ext_tt_27C_3p3V,F1.85=ext_ss_m40C_3p0V "
                         "(default: F1.85 at tt and ss, F1.95 at tt, F2.50 at tt, plus F1.85 tt with 2x switches)")
    ap.add_argument("--sizing", action="append", default=None,
                    help="explicit sizing name (repeatable); skips --fit")
    ap.add_argument("--corner", default="tt:27:3.3", help="PROC:TEMP_C:VDD_V (single screen corner)")
    ap.add_argument("--source-netlist", type=Path, default=SRC)
    ap.add_argument("--out", required=True, type=Path, help="NEW (or empty) bench directory")
    args = ap.parse_args()

    if args.sizing:
        names = ["ctrl"] + list(args.sizing)
    else:
        if not args.fit or not args.fit.is_file():
            print("error: --fit or --sizing required", file=sys.stderr)
            return 1
        if args.comp_map:
            fam = [(p, c, 1.0) for p, c in (kv.split("=") for kv in args.comp_map.split(","))]
        else:
            fam = [("F1.85", "ext_tt_27C_3p3V", 1.0),   # step-true, tt-compensated
                   ("F1.85", "ext_ss_m40C_3p0V", 1.0),  # step-true, ss-compensated (monotone margin)
                   ("F1.95", "ext_tt_27C_3p3V", 1.0),   # margin variant
                   ("F2.50", "ext_tt_27C_3p3V", 1.0),   # range-true pole
                   ("F1.85", "ext_tt_27C_3p3V", 2.0)]   # + 2x switch widths (Ron / #337 probe)
        names = ["ctrl"] + [n + ("w2" if w == 2.0 else "")
                            for n, w in ((sizing_from(args.fit, p, c), w) for p, c, w in fam)]

    proc, temp, vdd = (lambda p, t, v: (p, float(t), float(v)))(*args.corner.split(":"))
    out = args.out
    if not prepare.ensure_bench_dir(out):
        print(f"error: {out} exists and is not empty", file=sys.stderr)
        return 1

    grid = prepare.grid_definition()
    corners = prepare.validate_corners([(proc, temp, vdd)], grid)
    cfg = dict(prepare.DEFAULTS)
    src_text = args.source_netlist.read_text()
    pin_order = prepare.check_dut(src_text, str(args.source_netlist))
    ctag = prepare.corner_tag(*corners[0])

    entries = []
    for name in names:
        d = out / name / ctag
        d.mkdir(parents=True)
        dut = variant.build(src_text, name)
        dut_name = f"rcosc_top_{name}.spice"
        (d / dut_name).write_text(dut)
        dut_sha = evidence_common.sha256_bytes(dut.encode())
        for code in CARRY_CODES:
            ct = prepare.code_tag(code)
            tb = prepare.tb_text("screen", code, vdd, dut_name, cfg, pin_order)
            req = json.dumps(prepare.request("ext", f"tb_{ct}.spice", proc, temp, vdd, grid, cfg), indent=2) + "\n"
            (d / f"tb_{ct}.spice").write_text(tb)
            (d / f"request_{ct}.json").write_text(req)
            entries.append({
                "tag": f"{name}_{ctag}_{ct}", "variant": name, "corner": ctag,
                "process": proc, "temperature_c": temp, "vdd_v": vdd,
                "code": code, "code_hex": f"0x{code:02X}",
                "request": f"{name}/{ctag}/request_{ct}.json",
                "netlist": f"{name}/{ctag}/tb_{ct}.spice",
                "dut_sha256": dut_sha,
                "sw_mult": variant.sw_mult(name),
                "sha256": {"request": evidence_common.sha256_bytes(req.encode()),
                           "netlist": evidence_common.sha256_bytes(tb.encode())},
            })

    prov = {
        "kind": "row2-trimsize-screen-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 460,
        "source_netlist": {
            "path": str(args.source_netlist.relative_to(REPO)),
            "sha256": evidence_common.sha256_file(args.source_netlist)},
        "fit": str(args.fit.relative_to(REPO)) if args.fit and args.fit.is_relative_to(REPO) else None,
        "corner": {"tag": ctag, "process": proc, "temperature_c": temp, "vdd_v": vdd},
        "codes": CARRY_CODES,
        "settings": {k: cfg[k] for k in prepare.DEFAULTS},
        "variants": names,
        "requests": entries,
        "execution": {"backend": "batch only (run_set.py); local grids forbidden (host rule)"},
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    print(f"{len(entries)} requests across {len(names)} variants -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
