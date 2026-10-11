#!/usr/bin/env python3
"""Offline `klt sim` request generator for the dense trim-code campaign
(issue #98, offline subset of #87).

This script launches NO simulator and performs NO cloud operation.  It writes,
into a NEW directory, for every (netlist variant x corner) the full 8-bit trim
word set 0x00..0xFF as one testbench + one single-corner `klt sim` request per
code, plus `provenance.json` (input hashes, grid, solver settings) and
`manifest.template.json` (git/tool/PDK revision fields that MUST be filled in
at campaign execution).  Nothing written here is measured evidence.

Variants (explicit input netlists, hashed):
    sch  schematic DUT netlist   (--schematic-netlist)
    ext  extracted DUT netlist   (--extracted-netlist, a `klt extract` output)
Either input must define `.subckt rcosc_top clk t0 .. t7 vdd vss` (the
alphabetical pin order `klt extract` writes; see
sim/pvt-postlayout/klt-pex/gen_requests.py, from which the request shape and
the 20-period frequency measurement are taken).

Default corner grid (override with repeated --corner PROC:TEMP_C:VDD_V):
    tt  27 C  3.3 V   nominal
    ss -40 C  3.0 V   bounding corner (the supply-transient bounding set)
    ff  85 C  3.6 V   bounding corner (also the DR-0017 Row-4 guardrail cell)
Process/temperature/supply values must lie on the committed sim/pvt grid
(sim/pvt/pvt_sweep.py PROCESS_CORNERS, TEMPS_C, VDDS_V).

Requests are single-corner (the trim code is not a `klt sim` axis, and the
frequency `.meas` threshold needs VDD/2 at authoring time), so `klt sim` would
keep each unit local by default: the campaign MUST pass `--backend batch`
explicitly (README, "Campaign handoff").

Usage:
    python3 -I sim/trim-dense/prepare.py \\
        --schematic-netlist sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice \\
        --extracted-netlist <klt extract output .spice> --out /tmp/trim-dense
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
from _module_loader import load_module  # noqa: E402

N_CODES = 256
TRIM_BITS = 8
PINS = ["clk"] + [f"t{i}" for i in range(TRIM_BITS)] + ["vdd", "vss"]
MODELS = {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"}
VARIANTS = ("sch", "ext")
DEFAULT_CORNERS = (("tt", 27.0, 3.3), ("ss", -40.0, 3.0), ("ff", 85.0, 3.6))

# Solver / measurement settings: configurable, recorded, and written into every
# testbench (.options) so the deck itself carries them.  Defaults are ngspice's
# own defaults, i.e. what the committed sim/pvt campaigns used; sim/mc-groundwork
# /README.md shows reltol moves frequency by ~0.2 % at this resolution, so the
# campaign (#87) must choose and freeze them.
DEFAULTS = {
    "reltol": 1e-3, "abstol": 1e-12, "vntol": 1e-6,
    "tstep": "200p", "tstop": "2000n",
    "skip_edges": 5, "periods": 20,
    "timeout_s": 600, "capacity_wait_s": 1200,
    # recorded only (not enforceable offline): expected simulator build
    "engine_version_expected": "unspecified",
}

MANIFEST_REQUIRED = (
    "git_sha", "git_dirty", "klt_version", "engine", "engine_version", "pdk",
    "pdk_revision", "backend", "executed_utc", "provenance_sha256",
)


class PrepareError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def _pvt():
    return load_module("trim_dense_pvt_sweep", REPO / "sim" / "pvt" / "pvt_sweep.py", reuse=False)


def grid_definition() -> dict:
    m = _pvt()
    return {"process_corners": {k: list(v) for k, v in m.PROCESS_CORNERS.items()},
            "temps_c": list(m.TEMPS_C), "vdds_v": list(m.VDDS_V)}


def parse_corner(text: str) -> tuple[str, float, float]:
    try:
        p, t, v = text.split(":")
        return p, float(t), float(v)
    except ValueError:
        raise PrepareError(f"--corner must be PROC:TEMP_C:VDD_V, got {text!r}")


def validate_corners(corners, grid: dict) -> list[tuple[str, float, float]]:
    corners = [(p, float(t), float(v)) for p, t, v in corners]
    if not corners:
        raise PrepareError("no corners selected")
    if len(set(corners)) != len(corners):
        raise PrepareError("duplicate corner selected")
    for p, t, v in corners:
        if p not in grid["process_corners"]:
            raise PrepareError(f"unknown process {p!r}; known: {sorted(grid['process_corners'])}")
        if t not in grid["temps_c"]:
            raise PrepareError(f"temperature {t:g} C is not on the sim/pvt grid {grid['temps_c']}")
        if v not in grid["vdds_v"]:
            raise PrepareError(f"supply {v:g} V is not on the sim/pvt grid {grid['vdds_v']}")
    return corners


def corner_tag(proc: str, temp: float, vdd: float) -> str:
    t = f"m{abs(temp):g}" if temp < 0 else f"{temp:g}"
    return f"{proc}_{t}C_{f'{vdd:.1f}'.replace('.', 'p')}V"


def code_tag(code: int) -> str:
    return f"c{code:02X}"


def check_dut(text: str, label: str) -> None:
    """The testbench instance line is positional, so the header must match."""
    for line in text.splitlines():
        tok = line.split()
        if len(tok) >= 2 and tok[0].lower() == ".subckt" and tok[1].lower() == "rcosc_top":
            if [t.lower() for t in tok[2:]] != PINS:
                raise PrepareError(f"{label}: `.subckt rcosc_top` pins {tok[2:]} != required {PINS}")
            return
    raise PrepareError(f"{label}: no `.subckt rcosc_top` definition found")


def tb_text(variant: str, code: int, vdd: float, dut_name: str, cfg: dict) -> str:
    if not 0 <= code < N_CODES:
        raise PrepareError(f"code out of range: {code}")
    lines = [
        f"* rcosc_top dense-trim bench ({variant}), VDD={vdd:g} V, trim code 0x{code:02X} "
        "(generated by sim/trim-dense/prepare.py; NOT evidence)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".options reltol={cfg['reltol']:g} abstol={cfg['abstol']:g} vntol={cfg['vntol']:g}",
        f'.include "{dut_name}"',
        "XXDUT clk " + " ".join(f"t{i}" for i in range(TRIM_BITS)) + " vdd 0 rcosc_top",
        f"VDD vdd 0 DC {vdd:g}",
    ]
    for i in range(TRIM_BITS):   # static sources (not B-source decode): see mc-groundwork README
        lines.append(f"VT{i} t{i} 0 DC {vdd * ((code >> i) & 1):g}")
    return "\n".join(lines) + "\n"


def request(variant: str, tb_name: str, proc: str, temp: float, vdd: float, grid: dict, cfg: dict) -> dict:
    ta, tb = cfg["skip_edges"], cfg["skip_edges"] + cfg["periods"]
    vmid = vdd / 2
    return {
        "netlist": tb_name,
        "engine": "ngspice",
        "netlist_source": "schematic" if variant == "sch" else "extracted",
        "models": dict(MODELS),
        "corners": {
            "process": [{"name": proc, "sections": [*grid["process_corners"][proc], "cap_mim"]}],
            "temperature_c": [temp],
        },
        "analysis": {"kind": "tran", "args": f"{cfg['tstep']} {cfg['tstop']}"},
        "measurements": [
            {"name": "ta", "spice": f".meas tran ta WHEN v(clk)={vmid:.4f} RISE={ta}", "unit": "s"},
            {"name": "tb", "spice": f".meas tran tb WHEN v(clk)={vmid:.4f} RISE={tb}", "unit": "s"},
            {"name": "fosc", "spice": f".meas tran fosc PARAM='{cfg['periods']}/(tb-ta)'", "unit": "Hz"},
        ],
        "backend": "batch",
        "batch": {"capacity_wait_s": cfg["capacity_wait_s"]},
        "options": {"timeout_s": cfg["timeout_s"], "keep_artifacts": True,
                    "ngspice_init": ["set measureprec=8"]},
    }


def _rel(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def manifest_template(settings: dict) -> dict:
    t = {k: None for k in MANIFEST_REQUIRED}
    t |= {
        "_template": True,
        "_instructions": ("Copy, fill every null at campaign execution, drop the leading-underscore keys. "
                          "analyze.py fails a non-synthetic run whose manifest has a missing/null field. "
                          "pdk_revision is a 40-hex open_pdks commit or exactly 'unknown' with "
                          "pdk_revision_reason (sim/pdk_provenance.py, issue #65 convention)."),
        "issue": 87,
        "backend": "batch",
        "engine": "ngspice",
        "pdk_revision_source": None, "pdk_revision_reason": None, "model_dir": None,
        "solver": {k: settings[k] for k in ("reltol", "abstol", "vntol", "tstep", "tstop")},
        "engine_version_expected": settings["engine_version_expected"],
    }
    return t


def generate(out: Path, schematic: Path | None, extracted: Path | None,
             corners=DEFAULT_CORNERS, cfg: dict | None = None) -> dict:
    cfg = DEFAULTS | (cfg or {})
    if cfg["reltol"] <= 0 or cfg["abstol"] <= 0 or cfg["vntol"] <= 0:
        raise PrepareError("solver tolerances must be positive")
    if cfg["periods"] < 2 or cfg["skip_edges"] < 1:
        raise PrepareError("need periods >= 2 and skip_edges >= 1")
    inputs = {v: p for v, p in (("sch", schematic), ("ext", extracted)) if p is not None}
    if not inputs:
        raise PrepareError("at least one of --schematic-netlist / --extracted-netlist is required")
    texts = {}
    for v, p in inputs.items():
        try:
            texts[v] = Path(p).read_text()
        except OSError as e:
            raise PrepareError(f"{v} netlist unreadable: {e}")
        check_dut(texts[v], f"{v} netlist {p}")
    grid = grid_definition()
    corners = validate_corners(corners, grid)
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise PrepareError(f"output directory exists and is not empty: {out} (results are append-only)")
    out.mkdir(parents=True, exist_ok=True)

    entries = []
    for v in inputs:
        dut_name = f"rcosc_top_{v}.spice"
        for proc, temp, vdd in corners:
            ctag = corner_tag(proc, temp, vdd)
            d = out / v / ctag
            d.mkdir(parents=True)
            (d / dut_name).write_text(texts[v])
            dut_sha = sha256_bytes(texts[v].encode())
            for code in range(N_CODES):
                ct = code_tag(code)
                tb_name, req_name = f"tb_{ct}.spice", f"request_{ct}.json"
                tb = tb_text(v, code, vdd, dut_name, cfg)
                req = json.dumps(request(v, tb_name, proc, temp, vdd, grid, cfg), indent=2) + "\n"
                (d / tb_name).write_text(tb)
                (d / req_name).write_text(req)
                entries.append({
                    "tag": f"{v}_{ctag}_{ct}", "variant": v, "corner": ctag, "process": proc,
                    "temperature_c": temp, "vdd_v": vdd, "code": code, "code_hex": f"0x{code:02X}",
                    "request": f"{v}/{ctag}/{req_name}", "netlist": f"{v}/{ctag}/{tb_name}",
                    "corner_count": 1, "dut_sha256": dut_sha,
                    "sha256": {"request": sha256_bytes(req.encode()), "netlist": sha256_bytes(tb.encode())},
                })
    tags = [e["tag"] for e in entries]
    expect = len(inputs) * len(corners) * N_CODES
    if len(entries) != expect or len(set(tags)) != expect:
        raise PrepareError("internal: request set is not exactly 256 unique codes per corner and variant")

    settings = {k: cfg[k] for k in DEFAULTS}
    tmpl = manifest_template(settings)
    (out / "manifest.template.json").write_text(json.dumps(tmpl, indent=2) + "\n")
    prov = {
        "kind": "trim-dense-batch-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 98, "parent": 87,
        "inputs": {v: {"path": _rel(p), "sha256": sha256_file(p)} for v, p in inputs.items()},
        "pvt_grid_source": "sim/pvt/pvt_sweep.py",
        "pvt_grid_source_sha256": sha256_file(REPO / "sim" / "pvt" / "pvt_sweep.py"),
        "corners": [{"tag": corner_tag(*c), "process": c[0], "temperature_c": c[1], "vdd_v": c[2],
                     "sections": [*grid["process_corners"][c[0]], "cap_mim"]} for c in corners],
        "models": MODELS,
        "codes": {"first": 0, "last": N_CODES - 1, "count": N_CODES},
        "settings": settings,
        "units": {"time": "s", "frequency": "Hz", "temperature": "C", "voltage": "V"},
        "manifest_template": "manifest.template.json",
        "manifest_required_at_execution": list(MANIFEST_REQUIRED),
        "requests": entries,
        "execution": {
            "backend": "batch only: `klt sim <request> --backend batch` for every request (single-corner "
                       "requests are kept local by klt unless --backend is explicit)",
            "preflight_required": "a successful batch preflight must precede any submission; blocked while "
                                  "2AMLogic/klayout-tools#2851 is open",
            "local_grid_fallback": "forbidden; report refused submissions and per-request errors",
            "owner": "#87",
        },
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schematic-netlist", type=Path, default=None)
    ap.add_argument("--extracted-netlist", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path, help="NEW (or empty) output directory")
    ap.add_argument("--corner", action="append", default=None, metavar="PROC:TEMP_C:VDD_V",
                    help="repeatable; default tt:27:3.3 ss:-40:3.0 ff:85:3.6")
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), default=v, type=type(v))
    a = ap.parse_args()
    cfg = {k: getattr(a, k) for k in DEFAULTS}
    corners = [parse_corner(c) for c in a.corner] if a.corner else DEFAULT_CORNERS
    try:
        prov = generate(a.out, a.schematic_netlist, a.extracted_netlist, corners, cfg)
    except PrepareError as e:
        sys.exit(f"prepare.py: {e}")
    print(f"wrote {len(prov['requests'])} request(s) ({len(prov['inputs'])} variant(s) x "
          f"{len(prov['corners'])} corner(s) x {N_CODES} codes) to {a.out}; NOT submitted, NOT evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
