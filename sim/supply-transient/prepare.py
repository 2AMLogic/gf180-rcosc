#!/usr/bin/env python3
"""Offline bench / `klt sim` request generator for the dynamic supply-transient
and ripple response characterization (issue #92, offline subset).

This script launches NO simulator and performs NO cloud operation.  It writes,
into a caller-selected directory, one testbench + one single-corner `klt sim`
request + one case description per condition, and a provenance file.  Executing
the requests is a later, separately approved campaign and must go through
`klt sim --backend batch` with a successful batch preflight (see
sim/supply-transient/README.md).  Nothing here is measured evidence.

Conditions (process/temperature are the bounding set of the issue):
    tt @ 27 C,  ss @ -40 C,  ff @ 85 C
Stimuli per condition:
    VDD step 3.3 -> 3.0 V and 3.3 -> 3.6 V, ramp duration 1 us and 100 us
    VDD ripple on a 3.3 V mean, 100 mV p-p, 10 kHz / 100 kHz / 1 MHz
    (ripple settings are illustrative engineering choices, non-exhaustive)
That is 3 x (4 + 3) = 21 single-corner requests.

Trim code: per process, the code that a COMMITTED campaign calibrated at that
process's own 27 C / 3.3 V point (sim/waveform/prepare.py:load_calibration) is
HELD at the proposed temperature and across the supply disturbance.  Nothing
is recalibrated at -40/85 C or after a supply step.  High trim inputs follow
VDD.  The calibration source must be named explicitly (--cal-run).

Usage:
    python3 -I sim/supply-transient/prepare.py --cal-run sim/pvt/results/20260923T030125Z --out /tmp/st
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_SIM = Path(__file__).resolve().parent.parent
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))
from _module_loader import load_module  # noqa: E402


def _load_waveform_prepare():
    return load_module('wf_prepare', REPO / "sim" / "waveform" / "prepare.py", reuse=False)


wf = _load_waveform_prepare()
PROCESS_CORNERS = wf.PROCESS_CORNERS
PROCESSES = wf.PROCESSES
MODELS = wf.MODELS
CAL_TARGETS = wf.CAL_TARGETS
TRIM_BITS = wf.TRIM_BITS
SRC = wf.SRC
sha256 = wf.sha256
PrepareError = wf.PrepareError


def load_calibration(cal_run: Path, target: str = "ratified", require_committed: bool = True) -> dict:
    """sim/waveform/prepare.py:load_calibration (manifest/CSV validation,
    unsaturated integer codes, full T/V coverage, source hashes), plus the
    campaign's own UTC stamp so the source age can be reported."""
    cal = wf.load_calibration(cal_run, target, require_committed)
    man = json.loads((Path(cal_run) / "manifest.json").read_text())
    cal["source"]["campaign_utc"] = man.get("utc")
    return cal

# (process, temperature C): each process's calibrated code is held here.
CONDITIONS = (("tt", 27.0), ("ss", -40.0), ("ff", 85.0))
VDD_NOM_V = 3.3
STEP_TARGETS_V = {"dn": 3.0, "up": 3.6}
STEP_RAMPS_NS = (1000.0, 100000.0)
RIPPLE_FREQS_HZ = (1e4, 1e5, 1e6)
RIPPLE_VPP_V = 0.1

# Defaults, all configurable on the command line and recorded in provenance.
# Units: ns for *_ns, volts, hertz, farads, fractions.
DEFAULTS = {
    "startup_ramp_ns": 1000.0,   # 0 -> 3.3 V rail ramp
    "disturb_ns": 10000.0,       # step / ripple starts here
    "baseline_ns": 2000.0,       # baseline window = final baseline_ns before disturb
    "post_ns": 20000.0,          # observation after the step ramp completes
    "endpoint_ns": 2000.0,       # endpoint window = final endpoint_ns of the record
    "ripple_discard": 5,         # ripple periods discarded
    "ripple_observe": 10,        # ripple periods observed
    "ripple_margin_ns": 100.0,   # extra record after the observed ripple periods
    "band": 0.01,                # +/-1 % settling band (engineering metric)
    "min_cycles": 20,
    "min_samples_per_cycle": 10.0,
    "tstep": "200p", "tmax": "200p",           # step benches
    "ripple_tstep": "500p", "ripple_tmax": "500p",
    "timeout_s": 3600, "ripple_timeout_s": 14400,
    # no extra clk load: the calibration bench has none (see waveform harness)
    "load_f": 0.0,
    "reltol": 1e-3, "abstol": 1e-12, "vntol": 1e-6,
}


def _cfg_from(cfg: dict | None) -> dict:
    out = dict(DEFAULTS)
    out.update(cfg or {})
    for k in ("startup_ramp_ns", "disturb_ns", "baseline_ns", "post_ns", "endpoint_ns"):
        if not out[k] > 0:
            raise PrepareError(f"{k} must be positive")
    if out["disturb_ns"] - out["baseline_ns"] < out["startup_ramp_ns"]:
        raise PrepareError("baseline window must start after the startup rail ramp completes")
    if out["post_ns"] < out["endpoint_ns"]:
        raise PrepareError("post-ramp observation must cover the endpoint window")
    if not 0 < out["band"] < 1:
        raise PrepareError("band must be in (0, 1)")
    if out["min_cycles"] < 2:
        raise PrepareError("min_cycles must be >= 2")
    if out["ripple_discard"] < 0 or out["ripple_observe"] < 2:
        raise PrepareError("ripple needs discard >= 0 and observe >= 2 periods")
    if out["load_f"] < 0:
        raise PrepareError("load_f must be >= 0")
    return out


def _us(x_ns: float) -> str:
    return f"{x_ns:g}n"


def conditions() -> list[tuple[str, float]]:
    for p, _ in CONDITIONS:
        if p not in PROCESS_CORNERS:
            raise PrepareError(f"process {p!r} missing from sim/pvt/pvt_sweep.py PROCESS_CORNERS")
    return list(CONDITIONS)


def freq_tag(f: float) -> str:
    return f"{f / 1e6:g}MHz" if f >= 1e6 else f"{f / 1e3:g}kHz"


def ramp_tag(r_ns: float) -> str:
    return f"{r_ns / 1000:g}us"


def cases(cfg: dict) -> list[dict]:
    """Stimulus description (SI units) of every case, without codes."""
    out = []
    for proc, temp in conditions():
        for d, vto in STEP_TARGETS_V.items():
            for r in STEP_RAMPS_NS:
                out.append({
                    "tag": f"step_{d}_r{ramp_tag(r)}_{proc}", "kind": "step",
                    "process": proc, "temperature_c": temp,
                    "vdd_from_v": VDD_NOM_V, "vdd_to_v": vto, "ramp_s": r / 1e9,
                    "startup_ramp_s": cfg["startup_ramp_ns"] / 1e9,
                    "disturb_start_s": cfg["disturb_ns"] / 1e9,
                    "ramp_end_s": (cfg["disturb_ns"] + r) / 1e9,
                    "tstop_s": (cfg["disturb_ns"] + r + cfg["post_ns"]) / 1e9,
                    "baseline_window_s": cfg["baseline_ns"] / 1e9,
                    "endpoint_window_s": cfg["endpoint_ns"] / 1e9,
                    "band": cfg["band"],
                })
        for f in RIPPLE_FREQS_HZ:
            n = cfg["ripple_discard"] + cfg["ripple_observe"]
            td = cfg["disturb_ns"] / 1e9
            out.append({
                "tag": f"ripple_f{freq_tag(f)}_{proc}", "kind": "ripple",
                "process": proc, "temperature_c": temp,
                "vdd_mean_v": VDD_NOM_V, "ripple_vpp_v": RIPPLE_VPP_V, "ripple_hz": f,
                "startup_ramp_s": cfg["startup_ramp_ns"] / 1e9,
                "ripple_start_s": td,
                "discard_periods": cfg["ripple_discard"], "observe_periods": cfg["ripple_observe"],
                "observe_start_s": td + cfg["ripple_discard"] * (1 / f),
                "observe_end_s": td + n * (1 / f),
                "tstop_s": td + n * (1 / f) + cfg["ripple_margin_ns"] / 1e9,
                "baseline_window_s": cfg["baseline_ns"] / 1e9,
                "illustrative": "frequency/amplitude are illustrative engineering choices, non-exhaustive",
            })
    return out


def _pwl(points: list[tuple[float, float]]) -> str:
    return "PWL(" + " ".join(f"{t:g}n {v:g}" if i else f"0 {v:g}" for i, (t, v) in enumerate(points)) + ")"


def tb_text(case: dict, code: int, cfg: dict) -> str:
    sr, td = cfg["startup_ramp_ns"], cfg["disturb_ns"]
    lines = [
        f"* rcosc_top supply-transient bench ({case['tag']}): fixed trim code 0x{code:02X}, "
        f"{case['kind']} (generated by prepare.py)",
        ".param sw_stat_global=0 sw_stat_mismatch=0 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
        f".options reltol={cfg['reltol']:g} abstol={cfg['abstol']:g} vntol={cfg['vntol']:g}",
        '.include "rcosc_top_schematic.spice"',
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
    ]
    if case["kind"] == "step":
        pts = [(0.0, 0.0), (sr, VDD_NOM_V), (td, VDD_NOM_V), (td + case["ramp_s"] * 1e9, case["vdd_to_v"])]
        pwl = _pwl(pts)
        lines.append(f"VDD vdd 0 {pwl}")
        for i in range(TRIM_BITS):
            lines.append(f"VT{i} t{i} 0 {pwl}" if (code >> i) & 1 else f"VT{i} t{i} 0 DC 0")
    else:
        lines.append(f"VRAIL rail 0 {_pwl([(0.0, 0.0), (sr, VDD_NOM_V)])}")
        lines.append(f"VRIP vdd rail SIN(0 {case['ripple_vpp_v'] / 2:g} {case['ripple_hz']:g} {_us(td)} 0 0)")
        for i in range(TRIM_BITS):   # high trim inputs follow the (rippled) VDD
            lines.append(f"ET{i} t{i} 0 vdd 0 1" if (code >> i) & 1 else f"VT{i} t{i} 0 DC 0")
    if cfg["load_f"] > 0:
        lines.append(f"CLOAD clk 0 {cfg['load_f']:g}")
    lines.append(".save v(clk) v(vdd)")
    return "\n".join(lines) + "\n"


def request(case: dict, cfg: dict) -> dict:
    proc = case["process"]
    ripple = case["kind"] == "ripple"
    tstop_ns = case["tstop_s"] * 1e9
    vmid = (case["vdd_from_v"] if case["kind"] == "step" else case["vdd_mean_v"]) / 2
    return {
        "netlist": f"tb_{case['tag']}.spice",
        "engine": "ngspice",
        "netlist_source": "schematic",
        "models": dict(MODELS),
        "corners": {
            "process": [{"name": proc, "sections": [PROCESS_CORNERS[proc][0], PROCESS_CORNERS[proc][1],
                                                    PROCESS_CORNERS[proc][2], "cap_mim"]}],
            "temperature_c": [case["temperature_c"]],
        },
        "analysis": {"kind": "tran",
                     "args": f"{cfg['ripple_tstep' if ripple else 'tstep']} {tstop_ns:.10g}n 0 "
                             f"{cfg['ripple_tmax' if ripple else 'tmax']}"},
        "measurements": [
            {"name": "t_first_edge", "unit": "s",
             "spice": f".meas tran t_first_edge WHEN v(clk)={vmid:.4f} RISE=1"},
        ],
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": cfg["ripple_timeout_s" if ripple else "timeout_s"],
                    "keep_artifacts": True, "waveforms": True, "save_mode": "netlist",
                    "ngspice_init": ["set measureprec=8"]},
    }


def dut_vs_calibration(cal_source: dict) -> dict:
    """Explicit source/DUT relation.  Deterministic (no wall-clock values)."""
    sha = cal_source.get("campaign_git_sha")
    rel = str(SRC.relative_to(REPO))
    known = bool(sha) and bool(wf._git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"))
    if not known:
        return {"relation": "UNKNOWN: calibration campaign commit is not in this repository",
                "dut_changed_since_calibration": None, "commits_touching_dut": []}
    def log(rng: str) -> list[str]:
        return [h for h in wf._git("log", "--format=%H", rng, "--", rel).split() if h]
    anchor = cal_source.get("committing_hash")
    if anchor:
        after = log(f"{anchor}..HEAD")
        if after:
            return {"relation": ("CHANGED: the DUT netlist was modified after the calibration results were "
                                 "committed; legacy calibration cannot imply signoff of the changed DUT"),
                    "dut_changed_since_calibration": True, "commits_touching_dut": after}
        before = log(f"{sha}..{anchor}")
        if before:
            return {"relation": ("UNVERIFIED: the DUT netlist changed between the campaign's recorded git_sha and "
                                 "the commit that committed its results; the manifest records no DUT hash, so "
                                 "the results cannot be tied to this DUT version from hashes alone"),
                    "dut_changed_since_calibration": None, "commits_touching_dut": before}
        return {"relation": "unchanged since the calibration campaign commit",
                "dut_changed_since_calibration": False, "commits_touching_dut": []}
    touching = log(f"{sha}..HEAD")
    if touching:
        return {"relation": ("CHANGED: the DUT netlist was modified after the calibration campaign; "
                             "legacy calibration cannot imply signoff of the changed DUT"),
                "dut_changed_since_calibration": True, "commits_touching_dut": touching}
    return {"relation": "unchanged since the calibration campaign commit",
            "dut_changed_since_calibration": False, "commits_touching_dut": []}


def generate(out: Path, cal: dict, cfg: dict | None = None, strict_dut: bool = False) -> dict:
    """Write benches, requests, case files and provenance.json into the NEW
    directory `out`; return provenance.  Refuses a non-empty directory."""
    cfg = _cfg_from(cfg)
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise PrepareError(f"output directory exists and is not empty: {out} (results are append-only)")
    codes = cal["codes"]
    rel = dut_vs_calibration(cal["source"])
    if strict_dut and rel["dut_changed_since_calibration"] is not False:
        raise PrepareError(f"--strict-dut: {rel['relation']}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "rcosc_top_schematic.spice").write_text(wf.dut_block())
    allcases = cases(cfg)
    if len(allcases) != 21 or len({c["tag"] for c in allcases}) != 21:
        raise PrepareError("case list is not 21 unique cases")
    entries = []
    for case in allcases:
        code = codes[case["process"]]
        case = case | {"trim_code": code, "trim_hex": f"0x{code:02X}",
                       "trim_high_pins_follow_vdd": True, "load_f": cfg["load_f"]}
        tag = case["tag"]
        req = request(case, cfg)
        files = {f"tb_{tag}.spice": tb_text(case, code, cfg),
                 f"request_{tag}.json": json.dumps(req, indent=2) + "\n",
                 f"case_{tag}.json": json.dumps(case, indent=2) + "\n"}
        for name, text in files.items():
            (out / name).write_text(text)
        entries.append({"tag": tag, "kind": case["kind"], "process": case["process"],
                        "temperature_c": case["temperature_c"], "trim_code": code,
                        "request": f"request_{tag}.json", "netlist": f"tb_{tag}.spice",
                        "case": f"case_{tag}.json", "corner_count": 1,
                        "sha256": {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items()}})
    prov = {
        "kind": "supply-transient-bench-requests",
        "evidence": "NOT EVIDENCE: offline request generation, no simulation was run",
        "issue": 92,
        "conditions": [{"process": p, "temperature_c": t} for p, t in CONDITIONS],
        "process_library_mapping": {p: {"fets": PROCESS_CORNERS[p][0], "res": PROCESS_CORNERS[p][1],
                                        "mimcap": PROCESS_CORNERS[p][2], "extra": "cap_mim"}
                                    for p, _ in CONDITIONS},
        "models": MODELS,
        "calibration": cal["source"] | {"codes": {p: f"0x{c:02X}" for p, c in codes.items()},
                                        "held_policy": ("each process's code, calibrated at its own 27 C/3.3 V point, "
                                                        "is held at the proposed temperature and across the supply "
                                                        "disturbance; no recalibration")},
        "dut": {"source": "design/netlist/pvt_tb.spice", "source_sha256": sha256(SRC),
                "extracted_sha256": sha256(out / "rcosc_top_schematic.spice"),
                "inlined_in_each_request_directory": True, **rel},
        "settings": {
            **{k: cfg[k] for k in ("startup_ramp_ns", "disturb_ns", "baseline_ns", "post_ns", "endpoint_ns",
                                   "ripple_discard", "ripple_observe", "ripple_margin_ns", "band",
                                   "min_cycles", "min_samples_per_cycle", "tstep", "tmax",
                                   "ripple_tstep", "ripple_tmax", "load_f", "reltol", "abstol", "vntol")},
            "step_ramps_ns": list(STEP_RAMPS_NS), "step_targets_v": STEP_TARGETS_V,
            "ripple_hz": list(RIPPLE_FREQS_HZ), "ripple_vpp_v": RIPPLE_VPP_V, "vdd_nominal_v": VDD_NOM_V,
            "band_note": "configurable engineering metric, not the ratified trimmed-accuracy band or a threshold",
            "load_note": ("no explicit clk capacitance, matching the calibration bench"
                          if cfg["load_f"] == 0 else "NON-NOMINAL load: calibration codes were set unloaded"),
            "load_matches_calibration_bench": cfg["load_f"] == 0,
            "saved_signals": ["v(clk)", "v(vdd)"],
            "units": {"time": "s (settings *_ns in ns)", "voltage": "V", "frequency": "Hz", "temperature": "C"},
        },
        "requests": entries,
        "execution": {
            "backend": "batch only: `klt sim <request> --backend batch` for every request (single-corner "
                       "requests included, since klt keeps single units local by default)",
            "preflight_required": "a successful batch preflight must precede any submission; blocked while "
                                  "2AMLogic/klayout-tools#2851 is open",
            "local_grid_fallback": "forbidden; report refused submissions and per-corner errors",
        },
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cal-run", required=True, type=Path,
                    help="committed sim/pvt results dir whose 27C/3.3V calibration supplies the codes")
    ap.add_argument("--cal-target", choices=sorted(CAL_TARGETS), default="ratified")
    ap.add_argument("--out", required=True, type=Path, help="NEW (or empty) output directory")
    ap.add_argument("--strict-dut", action="store_true",
                    help="fail unless the DUT netlist is unchanged since the calibration campaign commit")
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), default=v, type=type(v))
    a = ap.parse_args()
    cfg = {k: getattr(a, k) for k in DEFAULTS}
    try:
        cal = load_calibration(a.cal_run, a.cal_target)
        prov = generate(a.out, cal, cfg, a.strict_dut)
    except PrepareError as e:
        sys.exit(f"prepare.py: {e}")
    d = prov["dut"]
    if d["dut_changed_since_calibration"] is not False:
        print(f"prepare.py: WARNING: {d['relation']}", file=sys.stderr)
    utc = prov["calibration"].get("campaign_utc")
    if utc:
        try:
            age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(utc)).days
            print(f"prepare.py: calibration source age: {age} day(s) (campaign {utc})", file=sys.stderr)
        except ValueError:
            print(f"prepare.py: WARNING: calibration utc not parseable: {utc!r}", file=sys.stderr)
    print(f"wrote {len(prov['requests'])} request(s) to {a.out}; calibration {prov['calibration']['campaign_dir']} "
          f"(runid {prov['calibration']['campaign_runid']}, utc {prov['calibration'].get('campaign_utc')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
