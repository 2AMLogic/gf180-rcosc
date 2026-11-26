#!/usr/bin/env python3
"""Offline full-curve (256 codes x the three dense-campaign corners) bench
generator for the row-2 finalists (issue #460, step 3).

Same mechanism as gen_screen.py (sizing names from variant.py, testbench and
request bytes from sim/trim-dense/prepare.py unchanged, so a `ctrl` variant
reproduces the committed #87 campaign numbers), but the full 0x00..0xFF code
set at all three dense-campaign corners, in the layout run_set.py reads
(<bench>/<variant>/<corner>/{rcosc_top_<variant>.spice, tb_cXX.spice,
request_cXX.json}).  provenance.json uses the trim-dense request-entry shape,
so sim/trim-dense/analyze.py consumes the bench directly (with a filled
manifest).  Nothing here runs a simulator.

    python3 -I sim/row2-trimsize/gen_full.py --sizing NAME [--sizing NAME] \
        --out /tmp/full-bench
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
CORNERS = (("tt", 27.0, 3.3), ("ss", -40.0, 3.0), ("ff", 85.0, 3.6))   # dense-campaign corners


def main() -> int:
    ap = argparse.ArgumentParser(description="row-2 full-curve bench generator (offline)")
    ap.add_argument("--sizing", action="append", required=True, help="sizing name (repeatable)")
    ap.add_argument("--source-netlist", type=Path, default=SRC)
    ap.add_argument("--out", required=True, type=Path, help="NEW (or empty) bench directory")
    args = ap.parse_args()

    names = list(dict.fromkeys(args.sizing))
    with prepare.claim_bench_dir(args.out) as claimed:
        if not claimed:
            print(f"error: {args.out} exists and is not empty", file=sys.stderr)
            return 1
        return _write_bench(args, names)


def _write_bench(args, names) -> int:
    out = args.out
    grid = prepare.grid_definition()
    corners = prepare.validate_corners(list(CORNERS), grid)
    cfg = dict(prepare.DEFAULTS)
    src_text = args.source_netlist.read_text()
    pin_order = prepare.check_dut(src_text, str(args.source_netlist))

    entries = []
    for name in names:
        dut = variant.build(src_text, name)
        for proc, temp, vdd in corners:
            ctag = prepare.corner_tag(proc, temp, vdd)
            d = out / name / ctag
            d.mkdir(parents=True)
            dut_name = f"rcosc_top_{name}.spice"
            # one DUT copy per (variant, corner) dir: the tb .include is relative
            (d / dut_name).write_text(dut)
            dut_sha = evidence_common.sha256_bytes(dut.encode())
            for code in range(256):
                ct = prepare.code_tag(code)
                tb = prepare.tb_text("ext", code, vdd, dut_name, cfg, pin_order)
                req = json.dumps(prepare.request("ext", f"tb_{ct}.spice", proc, temp, vdd, grid, cfg), indent=2) + "\n"
                (d / f"tb_{ct}.spice").write_text(tb)
                (d / f"request_{ct}.json").write_text(req)
                entries.append({
                    "tag": f"{name}_{ctag}_{ct}", "variant": name, "corner": ctag,
                    "process": proc, "temperature_c": temp, "vdd_v": vdd,
                    "code": code, "code_hex": f"0x{code:02X}",
                    "request": f"{name}/{ctag}/request_{ct}.json",
                    "netlist": f"{name}/{ctag}/tb_{ct}.spice",
                    "corner_count": 1, "dut_sha256": dut_sha,
                    "sw_mult": variant.sw_mult(name),
                    "sha256": {"request": evidence_common.sha256_bytes(req.encode()),
                               "netlist": evidence_common.sha256_bytes(tb.encode())},
                })

    expect = len(names) * len(corners) * 256
    if len(entries) != expect or len({e["tag"] for e in entries}) != expect:
        print("internal: request set is not exactly 256 unique codes per corner and variant", file=sys.stderr)
        return 1
    prov = {
        "kind": "row2-trimsize-full-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 460,
        "source_netlist": {
            "path": str(args.source_netlist.relative_to(REPO)),
            "sha256": evidence_common.sha256_file(args.source_netlist)},
        "corners": [{"tag": prepare.corner_tag(*c), "process": c[0], "temperature_c": c[1], "vdd_v": c[2]}
                    for c in corners],
        "settings": {k: cfg[k] for k in prepare.DEFAULTS},
        "variants": names,
        "requests": entries,
        "execution": {"backend": "batch only (run_set.py); local grids forbidden (host rule)"},
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    print(f"{len(entries)} requests across {len(names)} variants x {len(corners)} corners -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
