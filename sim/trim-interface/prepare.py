#!/usr/bin/env python3
"""Offline bench / `klt sim` request generator for the trim-pin DC selection and
static input-current characterization (issue #106, offline increment).

This script launches NO simulator and performs NO cloud operation.  It extracts
the committed `rcosc_trim_bank` subcircuit from design/netlist/pvt_tb.spice
verbatim, writes DC benches, `klt sim` requests (batch backend) and a
provenance file.  Executing the requests is a later, separately approved
campaign (see sim/trim-interface/README.md).

Case matrix (1296 cases):
    8 target pins t0..t7  x  2 held backgrounds (other 7 pins all 0 / all VDD)
    x 3 bank-terminal bias points (m = 0.25/0.50/0.75 VDD, p = VDD)
    x 27 PVT points (process tt/ss/ff x -40/27/85 C x VDD 3.0/3.3/3.6 V)
One netlist + request per (VDD, pin, background, m-bias) = 144 requests, each
carrying 9 process x temperature corners.  Process-section definitions, TEMPS_C
and VDDS_V come from sim/pvt/pvt_sweep.py (not re-typed); model identity comes
from sim/waveform/prepare.py.

Usage:
    python3 -I sim/trim-interface/prepare.py --out /tmp/trim-interface-req
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_SIM = Path(__file__).resolve().parent.parent
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))
from _module_loader import load_module  # noqa: E402
sys.path.insert(0, str(REPO / "sim" / "pvt"))
from pvt_sweep import PROCESS_CORNERS, TEMPS_C, VDDS_V  # noqa: E402


def _load_waveform_prepare():
    return load_module('wf_prepare_for_ti', REPO / "sim" / "waveform" / "prepare.py", reuse=False)


wf = _load_waveform_prepare()
PROCESSES = wf.PROCESSES
MODELS = wf.MODELS
SRC = REPO / "design" / "netlist" / "pvt_tb.spice"
SUBCKT = "rcosc_trim_bank"
BANK_PINS = ["p", "m", "vss"] + [f"t{i}" for i in range(8)] + ["vdd"]
TRIM_BITS = 8
BANK_FILE = "trim_bank_schematic.spice"

# Characterization screens and stimulus settings.  All are configurable and are
# RECORDED in provenance.json; none is a ratified spec value.
DEFAULTS = {
    "step_frac": 0.01,                 # sweep step, fraction of VDD (endpoints included)
    "m_fracs": (0.25, 0.50, 0.75),     # bank terminal m bias, fraction of VDD (p = VDD)
    "backgrounds": (0, 1),             # other seven pins held at 0 or at VDD
    "leak_fracs": (0.0, 0.25, 0.50, 0.75, 1.0),  # input-current report biases
    "sel_low": 0.10,                   # low-selected: s <= sel_low
    "sel_high": 0.90,                  # high-selected: s >= sel_high
    "margin_frac": 0.05,               # inward screening margin, fraction of VDD
    "mono_tol": 0.01,                  # nonmonotone tolerance in s
    "g_abs_min_s": 1e-12,              # endpoint resolvability floor (S)
    "g_rel_min": 1e-6,                 # endpoint resolvability relative floor
    "trip_frac": 0.5,                  # inverter diagnostic level
    "reltol": 1e-3, "abstol": 1e-12, "vntol": 1e-6,
}


class PrepareError(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    return r.stdout.strip() if r.returncode == 0 else ""


# ------------------------------------------------------------- extraction --

def extract_bank(text: str) -> str:
    """Return the rcosc_trim_bank .subckt...ends block verbatim.  Missing,
    multiple, unterminated or nested definitions are rejected; nothing is
    synthesized."""
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines)
              if re.match(rf"^\.subckt\s+{SUBCKT}\b", l.strip(), re.I) and not l.startswith("*")]
    if len(starts) != 1:
        raise PrepareError(f".subckt {SUBCKT}: expected exactly 1 definition in source, found {len(starts)}")
    s = starts[0]
    if lines[s].split()[1:] != [SUBCKT] + BANK_PINS:
        raise PrepareError(f".subckt {SUBCKT} pin list changed: {lines[s].split()[2:]}")
    end = None
    for j in range(s + 1, len(lines)):
        w = lines[j].strip().lower()
        if w.startswith(".subckt"):
            raise PrepareError(f".subckt {SUBCKT} is unterminated before the next .subckt (line {j + 1})")
        if w.startswith(".ends"):
            end = j
            break
    if end is None:
        raise PrepareError(f".subckt {SUBCKT} has no .ends")
    block = lines[s:end + 1]
    body = "\n".join(block)
    for i in range(TRIM_BITS):
        for dev in ("XR", "XSW", "XPW", "XNINV", "XPINV"):
            if len(re.findall(rf"^{dev}{i}\s", body, re.M)) != 1:
                raise PrepareError(f"{SUBCKT}: device {dev}{i} missing or ambiguous")
    if len(re.findall(r"^XRFIX\s", body, re.M)) != 1:
        raise PrepareError(f"{SUBCKT}: XRFIX missing or ambiguous")
    return "\n".join(block) + "\n"


def bank_block() -> str:
    return (f"* {SUBCKT} extracted VERBATIM from design/netlist/pvt_tb.spice by "
            "sim/trim-interface/prepare.py\n* (no device, parameter or connection edited)\n"
            + extract_bank(SRC.read_text()))


# ------------------------------------------------------------------- grid --

def grid() -> list[tuple[str, float, float]]:
    """The exactly-27-point grid (process, temp_c, vdd_v)."""
    for p in PROCESSES:
        if p not in PROCESS_CORNERS:
            raise PrepareError(f"process {p!r} missing from sim/pvt/pvt_sweep.py PROCESS_CORNERS")
    pts = [(p, t, v) for p in PROCESSES for t in TEMPS_C for v in VDDS_V]
    if len(pts) != 27 or len(set(pts)) != 27:
        raise PrepareError(f"grid is not 27 unique points ({len(pts)})")
    return pts


def tag_of(vdd: float) -> str:
    return f"v{int(round(vdd * 10)):02d}"


def request_tag(vdd: float, pin: int, bg: int, mfrac: float) -> str:
    return f"{tag_of(vdd)}_t{pin}_bg{bg}_m{int(round(mfrac * 100)):02d}"


def case_id(proc: str, temp_c: float, vdd: float, pin: int, bg: int, mfrac: float) -> str:
    return f"{proc}_T{temp_c:g}_V{vdd:g}_pin{pin}_bg{bg}_m{mfrac:.2f}"


def sweep_points(vdd: float, step_frac: float) -> int:
    n = round(1.0 / step_frac)
    if abs(n * step_frac - 1.0) > 1e-9:
        raise PrepareError("step_frac must divide 1 exactly (endpoint-inclusive sweep)")
    return n + 1


def all_cases(cfg: dict | None = None) -> list[dict]:
    """Every required case, in deterministic order."""
    cfg = _cfg_from(cfg)
    out = []
    for vdd in VDDS_V:
        for pin in range(TRIM_BITS):
            for bg in cfg["backgrounds"]:
                for mf in cfg["m_fracs"]:
                    for proc in PROCESSES:
                        for t in TEMPS_C:
                            out.append({"id": case_id(proc, t, vdd, pin, bg, mf), "tag": request_tag(vdd, pin, bg, mf),
                                        "process": proc, "temp_c": t, "vdd_v": vdd, "pin": pin,
                                        "background": bg, "m_frac": mf})
    return out


def _cfg_from(cfg: dict | None) -> dict:
    out = dict(DEFAULTS)
    out.update(cfg or {})
    out["m_fracs"] = tuple(out["m_fracs"])
    out["backgrounds"] = tuple(out["backgrounds"])
    out["leak_fracs"] = tuple(out["leak_fracs"])
    sweep_points(1.0, out["step_frac"])
    if not 0 < out["sel_low"] < out["sel_high"] < 1:
        raise PrepareError("need 0 < sel_low < sel_high < 1")
    if out["margin_frac"] < 0:
        raise PrepareError("margin_frac must be >= 0")
    for f in out["leak_fracs"]:
        if abs(f / out["step_frac"] - round(f / out["step_frac"])) > 1e-9:
            raise PrepareError(f"leak bias {f} is not on the sweep grid")
    return out


# ------------------------------------------------------------------ bench --

def tb_text(vdd: float, pin: int, bg: int, mfrac: float, cfg: dict) -> str:
    lines = [
        f"* trim-bank DC bench: target t{pin}, other pins held at {'VDD' if bg else '0'}, "
        f"p=VDD, m={mfrac:g} VDD, VDD={vdd:g} V (generated by prepare.py)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".options reltol={cfg['reltol']:g} abstol={cfg['abstol']:g} vntol={cfg['vntol']:g}",
        f'.include "{BANK_FILE}"',
        f"XBANK p m 0 {' '.join(f't{i}' for i in range(TRIM_BITS))} vdd {SUBCKT}",
        f"VDD vdd 0 DC {vdd:g}",
        f"VP p 0 DC {vdd:g}",
        f"VM m 0 DC {mfrac * vdd:.6g}",
    ]
    for i in range(TRIM_BITS):
        if i == pin:
            lines.append(f"VTIN t{i} 0 DC 0")
        else:
            lines.append(f"VT{i} t{i} 0 DC {vdd:g}" if bg else f"VT{i} t{i} 0 DC 0")
    lines.append(f".save v(xbank.tb{pin}) v(t{pin}) i(VP) i(VTIN)")
    return "\n".join(lines) + "\n"


def request(name: str, vdd: float, cfg: dict) -> dict:
    step = cfg["step_frac"] * vdd
    return {
        "netlist": name,
        "engine": "ngspice",
        "netlist_source": "schematic",
        "models": dict(MODELS),
        "corners": {
            "process": [{"name": n, "sections": [PROCESS_CORNERS[n][0], PROCESS_CORNERS[n][1],
                                                 PROCESS_CORNERS[n][2], "cap_mim"]} for n in PROCESSES],
            "temperature_c": list(TEMPS_C),
        },
        "analysis": {"kind": "dc", "args": f"VTIN 0 {vdd:g} {step:.6g}"},
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": 3600, "keep_artifacts": True, "waveforms": True,
                    "save_mode": "netlist", "ngspice_init": ["set measureprec=8"]},
    }


def generate(out: Path, cfg: dict | None = None) -> dict:
    """Write bank netlist, benches, requests and provenance.json into `out`."""
    cfg = _cfg_from(cfg)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pts = grid()
    (out / BANK_FILE).write_text(bank_block())
    reqs = []
    seen = []
    for vdd in VDDS_V:
        for pin in range(TRIM_BITS):
            for bg in cfg["backgrounds"]:
                for mf in cfg["m_fracs"]:
                    tag = request_tag(vdd, pin, bg, mf)
                    (out / f"tb_{tag}.spice").write_text(tb_text(vdd, pin, bg, mf, cfg))
                    req = request(f"tb_{tag}.spice", vdd, cfg)
                    (out / f"request_{tag}.json").write_text(json.dumps(req, indent=2) + "\n")
                    ids = [case_id(p, t, vdd, pin, bg, mf) for p in PROCESSES for t in TEMPS_C]
                    seen += ids
                    reqs.append({"tag": tag, "request": f"request_{tag}.json", "netlist": f"tb_{tag}.spice",
                                 "vdd_v": vdd, "pin": pin, "background": bg, "m_frac": mf,
                                 "sweep": {"source": "VTIN", "start_v": 0.0, "stop_v": vdd,
                                           "step_v": cfg["step_frac"] * vdd,
                                           "points": sweep_points(vdd, cfg["step_frac"]), "endpoints_included": True},
                                 "cases": ids})
    expected = [c["id"] for c in all_cases(cfg)]
    if len(seen) != len(set(seen)) or set(seen) != set(expected):
        raise PrepareError("generated requests do not cover the case matrix exactly once")
    n_expected = len(PROCESSES) * len(TEMPS_C) * len(VDDS_V) * TRIM_BITS * len(cfg["backgrounds"]) * len(cfg["m_fracs"])
    if len(seen) != n_expected or len(pts) != 27:
        raise PrepareError("case count does not match the matrix")
    dirty = bool(_git("status", "--porcelain", "--", "design/netlist/pvt_tb.spice"))
    prov = {
        "kind": "trim-interface-dc-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 106,
        "git_revision": _git("rev-parse", "HEAD") or None,
        "source_dirty": dirty,
        "grid": {"processes": list(PROCESSES), "temperature_c": TEMPS_C, "vdd_v": VDDS_V, "pvt_points": len(pts),
                 "pins": TRIM_BITS, "backgrounds": list(cfg["backgrounds"]), "m_fracs": list(cfg["m_fracs"]),
                 "cases": len(seen), "requests": len(reqs),
                 "case_list_sha256": sha256_text("\n".join(expected))},
        "process_library_mapping": {p: {"fets": PROCESS_CORNERS[p][0], "res": PROCESS_CORNERS[p][1],
                                        "mimcap": PROCESS_CORNERS[p][2], "extra": "cap_mim"}
                                    for p in PROCESSES},
        "models": MODELS,
        "dut": {"source": "design/netlist/pvt_tb.spice", "source_sha256": sha256(SRC),
                "subckt": SUBCKT, "extracted_file": BANK_FILE,
                "extracted_sha256": sha256(out / BANK_FILE)},
        "settings": {
            "bank_terminals": {"p": "VDD", "m": "m_frac x VDD", "vss": "0 V (ideal)"},
            "vdd": "ideal source, per request",
            "observed": ["v(xbank.tb<pin>)", "v(t<pin>)", "i(VP)", "i(VTIN)"],
            "sign_convention": "bank current into p = -i(VP); input current into DUT = -i(VTIN) (A)",
            "screens": {k: cfg[k] for k in ("step_frac", "sel_low", "sel_high", "margin_frac", "mono_tol",
                                            "g_abs_min_s", "g_rel_min", "trip_frac")},
            "leak_fracs": list(cfg["leak_fracs"]),
            "reltol": cfg["reltol"], "abstol_a": cfg["abstol"], "vntol_v": cfg["vntol"],
            "units": {"voltage": "V", "current": "A", "conductance": "S", "temperature": "C"},
            "note": "screens are recorded characterization choices pending ratification, not spec values",
        },
        "requests": reqs,
        "execution": "later campaign only, via `klt sim --backend batch`; never a local multi-corner loop",
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path, help="output directory (generated files are not committed)")
    ap.add_argument("--step-frac", type=float, default=DEFAULTS["step_frac"])
    ap.add_argument("--sel-low", type=float, default=DEFAULTS["sel_low"])
    ap.add_argument("--sel-high", type=float, default=DEFAULTS["sel_high"])
    ap.add_argument("--margin-frac", type=float, default=DEFAULTS["margin_frac"])
    a = ap.parse_args()
    cfg = {"step_frac": a.step_frac, "sel_low": a.sel_low, "sel_high": a.sel_high, "margin_frac": a.margin_frac}
    try:
        prov = generate(a.out, cfg)
    except PrepareError as e:
        sys.exit(f"prepare.py: {e}")
    print(f"wrote {len(prov['requests'])} request(s) / {prov['grid']['cases']} cases to {a.out}")


if __name__ == "__main__":
    main()
