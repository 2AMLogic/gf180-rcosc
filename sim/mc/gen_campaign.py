#!/usr/bin/env python3
"""Generate the item-6 Monte Carlo campaign benches, requests and limits
(issue #202; DR-0019 section 2, DR-0022).  Offline: this script never runs a
simulator.  Output goes next to this script; run-campaign.sh copies it into a
NEW results/<runid>/ and submits it through `klt sim` (batch fleet).

DUT: the P3 proposed sizing of decision record 0023 -- the committed extracted
netlist with the ladder re-centred (sim/recentre/p3/rcosc_top_p3.spice), the
sizing #66 settled.  The schematic in design/ still carries the pre-recentre
sizing and is NOT the campaign DUT (DR-0019 section 4: no Monte Carlo on a
design known to miss its mean).  The DUT text is inlined into every bench
(the batch fleet does not reliably stage sibling .include files) after the
DR-0022 section 4 injector (`mismatch_inject.inject`) rewrites the ladder
resistors and the MIM capacitor.

Per sample (one die) the body `.control` does, inside ONE ngspice session so
every solve sees the same mismatch draw:

  1. calibrate: bisection over the 8-bit code for the frequency nearest
     48.000 MHz at 27 C / 3.3 V (the single-point trim the accuracy rows assume),
  2. hold the code and re-measure it (repeatability check),
  3. hold the SAME code at the other conditions: 27 C at 3.0 / 3.6 V (row 4,
     S2) and -40 / 27 / 85 C at 3.0 / 3.3 / 3.6 V (row 5, S3),
  4. measure the two neighbouring codes at 27 C / 3.3 V (step sizes, S1).

Exposed measurements (`set` variables harvested by klt sim `expr`):
  code_sel, e_cal_pct (residual at calibration), e_<T>_<V> (signed % error
  vs 48 MHz at each held condition), step_up_hz, step_dn_hz, hold_gap_hz, and
  the graded derived margins:
    s1_resid_abs_pct  |e_cal|                                     limit <= S1_RESID_MAX
    s1_headroom       min(code, 255-code) after clamping           limit >= 1
    s2_margin_pct     min(+2.0 - max(e), min(e) + 2.9) over the three 27 C points   >= 0
    s3_margin_pct     min(+8.8 - max(e), min(e) + 10.8) over all nine T/V points    >= 0
  (rows 4 and 5 are signed limits, so one margin per claim carries both.)

Options (issue #236): `--dut PATH` points the generator at another DUT netlist
(e.g. sim/cmph-fix/rcosc_top_p3_cmphfix.spice, the DR-0028 netlist) and `--out DIR`
writes the benches/requests/limits there instead of next to this script, so the
committed top-level inputs of earlier campaigns are never regenerated in place.
With neither option the output is byte-identical to the committed files.

Variants (names are the run-campaign.sh case names):
  main_<p>     mismatch on (sw_stat_mismatch=1, mm_scale=1), N=500, p in tt/ff/ss
  inflated_<p> sw_stat_mismatch=3: MOS and injected sigma both 3x (DR-0022 s3)
  zero_<p>     sw_stat_mismatch=0: injected terms identically 0 (plumbing control)
  sens1_tt / sens10_tt   MOS off (sw_stat_mismatch=0), injected terms live at
               mm_scale 1 and 10 through a separate gate (sw_inj=1): the
               DR-0022 s3 sensitivity control
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(here.parent / "mc-groundwork"))  # also works under python -I
from mismatch_inject import inject  # noqa: E402
sys.path.insert(0, str(here.parent / "pvt"))
from pvt_sweep import PROCESS_CORNERS  # noqa: E402

SRC = here.parent / "recentre" / "p3" / "rcosc_top_p3.spice"  # default DUT; --dut overrides (issue #236)
SEED = 20261008  # DR-0019: one recorded seed, appended to only, never re-drawn
N_MAIN = 500
N_INFLATED = 500
N_SENS = 100
N_ZERO = 3
TSTEP = "200p"  # the committed campaign timestep (DR-0030 sensitivity miss, issue #461)
TSTEP_FINE = "50p"  # the finer-timing sensitivity arm
N_PILOT = 40  # issue #461 pilot: reduced draws per corner (production claim stays N_MAIN)
TARGET_HZ = 48.0e6
VCAL = 3.3
PROC = {n: [*PROCESS_CORNERS[n], "cap_mim"] for n in ("tt", "ff", "ss")}
# Ratified limits (README target-specification table; DR-0003 Row 3, DR-0017).
ROW4 = (-2.9, 2.0)
ROW5 = (-10.8, 8.8)
# S1 harness limit: DR-0019 s2 "half-LSB plus the mismatch budget of DR-0003 Row 3"
# = 0.157 (quantization) + 0.300 (trim-DAC mismatch) + 0.300 (comparator offset).
S1_RESID_MAX = 0.157 + 0.300 + 0.300
TARGET_YIELD = 0.99
CONFIDENCE = 0.95
# (label, temperature C, supply V); the calibration point is measured first.
POINTS = [(f"{'n40' if t < 0 else t}_{int(v * 10)}", t, v)
          for t in (-40, 27, 85) for v in (3.0, 3.3, 3.6)]
S2_POINTS = [p for p in POINTS if p[1] == 27]


# Seeded known-bad variants (issue #461; DR-0051).  Each is a deterministic physical
# defect written into the DUT text BEFORE the injector and BEFORE the per-die
# calibration, so the die calibrates around it exactly as it would a real fault.
# Magnitudes are fixed in sim/mc/results/<derivation run>/ before any pilot draw.
DEFECTS = {
    # row 2 (S1): the fixed base segment of the trim ladder (X$91, the segment in
    # series with the nine binary-weighted ones) drawn `scale` x too long.  The
    # calibration bisection then runs off one end of the code range: the residual
    # stays large (s1_resid_abs_pct) and the chosen code sits on a rail
    # (s1_headroom).
    "trimbank": {"kind": "scale_length", "inst": "X$91", "scale": 4.0,
                 "observables": ["s1_resid_abs_pct", "s1_headroom"]},
    # row 4 (S2): a parasitic conduction path from the supply to the timing capacitor's top
    # plate -- a resistor and a diode-connected nfet_03v3 (source follower).  Its current is
    # square-law in (vdd - V_plate - Vt): not proportional to the supply (unlike the charging
    # current, so a plain resistor to vdd or vss, tried first, left the supply span
    # unchanged -- see the derivation runs).  The 27 C / 3.3 V calibration trims
    # out its static effect; its supply and temperature dependence survives calibration.
    "leak": {"kind": "leak_nfet", "rail": "vdd", "node": "\\$26__t8", "rvalue": 7.0e4,
             "observables": ["s2_margin_pct"]},
    # row 5 (S3): a reverse-biased junction leak from the timing capacitor's top plate to
    # vss (diode cathode on the plate).  Its saturation current rises roughly two orders of
    # magnitude between 27 C and 85 C (XTI=3, EG=1.11), so the 27 C calibration trims out
    # its static effect and the hot corner slows the oscillator: a temperature-dependent
    # error that survives calibration.  (The nfet leak above moved s3 by < 1 point.)
    "diode": {"kind": "leak_diode", "node": "\\$26__t8", "is_a": 1.0e-8,
              "observables": ["s3_margin_pct"]},
}


def apply_defect(body: str, defect: dict | None) -> str:
    """Return the DUT subcircuit text with `defect` seeded (None: unchanged)."""
    if defect is None:
        return body
    lines = body.splitlines()
    if defect["kind"] == "scale_length":
        card = next((i for i, l in enumerate(lines)
                     if l.split() and l.split()[0] == defect["inst"]), None)
        if card is None:
            raise ValueError(f"defect instance {defect['inst']} not in the DUT")
        m = re.search(r"r_length=([0-9.]+)([uU])", lines[card])
        if not m:
            raise ValueError(f"{defect['inst']}: no r_length= in {lines[card]!r}")
        new = f"{float(m.group(1)) * defect['scale']:.5f}{m.group(2)}"
        lines[card] = lines[card].replace(m.group(0), f"r_length={new}")
    elif defect["kind"] == "leak_nfet":
        if defect["node"] not in body:
            raise ValueError(f"defect node {defect['node']} not in the DUT")
        end = max(i for i, l in enumerate(lines) if l.upper().startswith(".ENDS"))
        card = "L=1U W=2U AS=0.84P AD=0.84P PS=4.84U PD=4.84U"
        if defect.get("rail", "vss") == "vss":  # plate -> R -> diode-connected nfet -> vss
            lines[end:end] = [f"RDEF_LEAK {defect['node']} ndef_leak {defect['rvalue']:g}",
                              f"XDEF_LEAK ndef_leak ndef_leak vss vsubs nfet_03v3 {card}"]
        else:  # vdd -> R -> diode-connected nfet (source follower) -> plate
            lines[end:end] = [f"RDEF_LEAK vdd ndef_leak {defect['rvalue']:g}",
                              f"XDEF_LEAK ndef_leak ndef_leak {defect['node']} vsubs nfet_03v3 {card}"]
    elif defect["kind"] == "leak_diode":
        if defect["node"] not in body:
            raise ValueError(f"defect node {defect['node']} not in the DUT")
        end = max(i for i, l in enumerate(lines) if l.upper().startswith(".ENDS"))
        lines[end:end] = [
            f".model DDEF_LEAK D(IS={defect['is_a']:g} N=1 XTI=3 EG=1.11)",
            f"DDEF_LEAK vss {defect['node']} DDEF_LEAK",
        ]
    else:
        raise ValueError(f"unknown defect kind {defect['kind']!r}")
    return "\n".join(lines)


def dut_text(mismatch_gate: str, mm_scale=None, src: Path | None = None,
             defect: dict | None = None) -> tuple[str, list]:
    raw = (src or SRC).read_text().splitlines()
    start = next(i for i, l in enumerate(raw) if l.upper().startswith(".SUBCKT RCOSC_TOP"))
    end = next(i for i, l in enumerate(raw) if l.upper().startswith(".ENDS"))
    body = apply_defect("\n".join(raw[start:end + 1]), defect)
    return inject(body, mm_scale=mm_scale, gate=mismatch_gate)


def pmin(a: str, b: str) -> str:
    """two-argument min as arithmetic (ngspice minimum()/maximum() reduce one vector)."""
    return f"(({a}) + ({b}) - abs(({a}) - ({b}))) / 2"


def pmax(a: str, b: str) -> str:
    return f"(({a}) + ({b}) + abs(({a}) - ({b}))) / 2"


def set_code(var: str, vexpr: str) -> list[str]:
    out = []
    for i in range(8):
        out.append(f"  let vb = {vexpr} * (floor({var} / {1 << i}) - 2 * floor({var} / {1 << (i + 1)}))")
        out.append(f"  alter vt{i} = $&vb")
    return out


def probe(var: str, dest: str, temp: float, vdd: float, tstep: str = TSTEP) -> list[str]:
    """one transient at (temp, vdd) with the trim word `var`; frequency into `dest`."""
    mid = vdd / 2
    return [
        f"  option temp = {temp:g}",
        f"  alter vdd = {vdd:g}",
    ] + set_code(var, f"{vdd:g}") + [
        f"  tran {tstep} 1200n",
        f"  meas tran ta when v(clk)={mid:.4f} rise=5",
        f"  meas tran tb when v(clk)={mid:.4f} rise=25",
        "  let fq = 20 / (tb - ta)",
        "  set fq_s = $&fq",
        "  setplot $sp",
        f"  let {dest} = $fq_s",
    ]


def bench(tag: str, header: str, gate: str, fixed: bool = False, mm_scale=None,
          src: Path | None = None, defect: dict | None = None,
          tstep: str = TSTEP) -> tuple[str, list]:
    dut, manifest = dut_text(gate, mm_scale, src, defect)
    dut_label = "P3, DR-0023" if src is None else f"{src.name}"
    L = [
        f"* rcosc_top item-6 Monte Carlo bench: {tag} (generated by gen_campaign.py; DUT = {dut_label})",
        header,
        dut,
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 DC {VCAL:g}",
    ] + [f"VT{i} t{i} 0 DC 0" for i in range(8)]
    L += [
        ".control",
        "set noaskquit",
        "set measureprec=8",
        "setplot new",
        "set sp = $curplot",
        f"let tgt = {TARGET_HZ:g}",
        "let lo = -1",
        "let hi = 256",
        "let flo = -1e12",
        "let fhi = 1e12",
        "while hi - lo > 1",
        "  let mid = floor((lo + hi) / 2)",
    ]
    L += probe("mid", "fm", 27, VCAL, tstep=tstep)
    L += [
        "  if fm < tgt",
        "    let lo = mid",
        "    let flo = fm",
        "  else",
        "    let hi = mid",
        "    let fhi = fm",
        "  end",
        "end",
        "if abs(flo - tgt) <= abs(fhi - tgt)",
        "  let csel = lo",
        "  let fsel = flo",
        "else",
        "  let csel = hi",
        "  let fsel = fhi",
        "end",
        "* a search that ran off a rail ends on the virtual code -1 / 256: clamp for the solves",
        f"let cclamp = {pmax('0', '(' + pmin('255', 'csel') + ')')}",
        f"let cup = {pmin('255', 'cclamp + 1')}",
        f"let cdn = {pmax('0', 'cclamp - 1')}",
    ]
    L += probe("cclamp", "fhold", 27, VCAL, tstep=tstep)
    for lab, t, v in POINTS:
        if (t, v) == (27, VCAL):
            L.append(f"let f_{lab} = fhold")
        else:
            L += probe("cclamp", f"f_{lab}", t, v, tstep=tstep)
    L += probe("cup", "fup", 27, VCAL, tstep=tstep)
    L += probe("cdn", "fdn", 27, VCAL, tstep=tstep)
    if fixed:
        # DR-0022 s3 sensitivity control: step sizes at FIXED transitions (the MSB
        # transition 0x7F -> 0x80 and its neighbour), independent of the code the
        # die's calibration picked.
        for c in (126, 127, 128):
            L.append(f"let cfix{c} = {c}")
            L += probe(f"cfix{c}", f"ffix{c}", 27, VCAL, tstep=tstep)
        L += ["let st127 = ffix128 - ffix127", "let st126 = ffix127 - ffix126",
              "set v_st127 = $&st127", "set v_st126 = $&st126"]
    for lab, _, _ in POINTS:
        L.append(f"let e_{lab} = (f_{lab} - tgt) / tgt * 100")
    s2 = [f"e_{lab}" for lab, _, _ in S2_POINTS]
    s3 = [f"e_{lab}" for lab, _, _ in POINTS]

    def running(prefix: str, names: list[str]) -> list[str]:
        """running max/min as short statements (a one-line nest overflows ngspice's line buffer)."""
        out = [f"let {prefix}max = {names[0]}", f"let {prefix}min = {names[0]}"]
        for n in names[1:]:
            out.append(f"let {prefix}max = {pmax(prefix + 'max', n)}")
            out.append(f"let {prefix}min = {pmin(prefix + 'min', n)}")
        return out

    L += running("a2", s2) + running("a3", s3)
    L += [
        f"let s2_margin = {pmin(f'{ROW4[1]} - a2max', f'a2min - ({ROW4[0]})')}",
        f"let s3_margin = {pmin(f'{ROW5[1]} - a3max', f'a3min - ({ROW5[0]})')}",
        "let s1_resid = abs(e_27_33)",
        f"let s1_head = {pmin('cclamp', '255 - cclamp')}",
        "if csel < 0 or csel > 255",
        "  let s1_head = -1",
        "end",
        "let step_up = fup - fhold",
        "let step_dn = fhold - fdn",
        "let fgap = abs(fhold - fsel)",
        "set v_code = $&csel",
        "set v_fhold = $&fhold",
        "set v_gap = $&fgap",
        "set v_up = $&step_up",
        "set v_dn = $&step_dn",
        "set v_s1r = $&s1_resid",
        "set v_s1h = $&s1_head",
        "set v_s2 = $&s2_margin",
        "set v_s3 = $&s3_margin",
    ]
    for lab, _, _ in POINTS:
        L.append(f"set v_e_{lab} = $&e_{lab}")
    L.append(".endc")
    return "\n".join(L) + "\n", manifest


def measurements(fixed: bool = False) -> list[dict]:
    m = [
        {"name": "code_sel", "expr": "$v_code", "unit": ""},
        {"name": "f_hold_hz", "expr": "$v_fhold", "unit": "Hz"},
        {"name": "hold_gap_hz", "expr": "$v_gap", "unit": "Hz"},
        {"name": "step_up_hz", "expr": "$v_up", "unit": "Hz"},
        {"name": "step_dn_hz", "expr": "$v_dn", "unit": "Hz"},
        {"name": "s1_resid_abs_pct", "expr": "$v_s1r", "unit": "%"},
        {"name": "s1_headroom", "expr": "$v_s1h", "unit": "codes"},
        {"name": "s2_margin_pct", "expr": "$v_s2", "unit": "%"},
        {"name": "s3_margin_pct", "expr": "$v_s3", "unit": "%"},
    ]
    for lab, _, _ in POINTS:
        m.append({"name": f"e_{lab}_pct", "expr": f"$v_e_{lab}", "unit": "%"})
    if fixed:
        m += [{"name": "step_0x7f_0x80_hz", "expr": "$v_st127", "unit": "Hz"},
              {"name": "step_0x7e_0x7f_hz", "expr": "$v_st126", "unit": "Hz"}]
    return m


def request(netlist: str, proc: str, n: int, fixed: bool = False, timeout_s: int = 120) -> dict:
    return {
        "netlist": netlist,
        "engine": "ngspice",
        "netlist_source": "extracted",
        "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
        "corners": {
            "process": [{"name": proc, "sections": PROC[proc]}],
            "temperature_c": [27],
        },
        "analysis": {"kind": "op", "args": ""},
        "measurements": measurements(fixed),
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": timeout_s, "keep_artifacts": False},
        "monte_carlo": {"n": n, "seed": SEED, "vary": "mismatch"},
    }


def limits(min_samples: int) -> dict:
    return {
        "confidence": CONFIDENCE,
        "min_samples": min_samples,
        "measurements": {
            "s1_resid_abs_pct": {"max": S1_RESID_MAX, "target_yield": TARGET_YIELD},
            "s1_headroom": {"min": 1, "target_yield": TARGET_YIELD},
            "s2_margin_pct": {"min": 0.0, "target_yield": TARGET_YIELD},
            "s3_margin_pct": {"min": 0.0, "target_yield": TARGET_YIELD},
        },
    }


# Derivation sweep (issue #461): each seeded defect is probed at several magnitudes on the
# zero-mismatch (deterministic) bench at each corner BEFORE any pilot draw.  The selection
# rule is fixed here, ahead of the run:
#   trimbank: the weakest scale for which every corner (tt/ff/ss) is measurable and has
#             s1_headroom <= 0 (the calibrated code on a rail) -- row 2 fails by construction;
#   leak:     (row 4) the largest resistance (weakest leak) for which every corner that is
#             measurable has s2_margin_pct <= -1.0 on the deterministic draw (a full point
#             beyond the limit edge, so a die-to-die spread cannot rescue it); the ss value is
#             reported but not required (ss row 4 already fails nominally, DR-0043);
#   diode:    (row 5) the same rule on s3_margin_pct, weakest saturation current, all corners.
# Round 1 (results/20261123T170809Z-ctrl-derivation, 2e5/1e6 ohm resistor to vdd) and round 2
# (results/20261123T171911Z-ctrl-derivation, diode-connected nfet at 5e4/2e5/1e6 ohm) are kept
# and round 3 (20261123T173030Z: the same nfet to vss at 7e4/1e5 ohm -- tt s2 stayed >= +0.66 -- and the
# junction leak, which is kept for row 5) are rejected candidates for row 4; round 4 (20261123T173706Z: the same nfet from vdd at 1e5/3e5/1e6 ohm, tt s2 >= +0.01) did not reach the criterion either; this grid is round 5.
# A magnitude that leaves a corner unmeasurable is rejected: an unmeasurable die is a dropped
# sample, not a detection.
DERIVE_GRID = {
    "trimbank": [("scale", v) for v in (4.0, 13.0)],
    "leak": [("rvalue", v) for v in (5.0e4, 7.0e4)],
    "diode": [("is_a", v) for v in (3.0e-9, 1.0e-8, 3.0e-8)],
}


def derive_cases() -> dict:
    out = {}
    for name, grid in DERIVE_GRID.items():
        for key, val in grid:
            for p in PROC:
                out[f"derive_{name}_{val:g}_{p}"] = (dict(DEFECTS[name], **{key: val}), p)
    return out


def pilot_limits(n: int) -> dict:
    """Pilot-only copy of the claim limits: identical limits, target yield and confidence;
    only the sample floor is the pilot N, so the grader can process the reduced population.
    The production floor (N_MAIN, limits_main.json) is untouched."""
    return limits(n)


HDR = ".param sw_stat_global=0 sw_stat_mismatch={mm} mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0 mm_scale={sc}{extra}"


def repo_rel(path: Path) -> str:
    root = here.parent.parent.resolve()
    p = path.resolve()
    return str(p.relative_to(root)) if p.is_relative_to(root) else str(p)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dut", type=Path, default=None,
                    help="DUT netlist (default: the DR-0023 P3 netlist, sim/recentre/p3/rcosc_top_p3.spice)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output directory (default: next to this script); created if missing")
    ap.add_argument("--pilot", type=int, default=None, metavar="N",
                    help="issue #461 control pilot: N draws per corner for the main, inflated and "
                         "seeded-defect cases, plus the finer-timing sensitivity arms and "
                         "limits_pilot.json (sample floor N).  Without it the default campaign "
                         "output is unchanged.")
    ap.add_argument("--derive", action="store_true",
                    help="write only the defect-magnitude derivation sweep (zero mismatch, 2 draws "
                         "per request); see DERIVE_GRID for the pre-fixed selection rule")
    a = ap.parse_args(argv)
    src = a.dut.resolve() if a.dut else None
    out = a.out if a.out else here
    out.mkdir(parents=True, exist_ok=True)
    if a.derive:
        for name, (defect, proc) in derive_cases().items():
            text, _ = bench(name, HDR.format(mm=0, sc=1, extra=""), "sw_stat_mismatch", False,
                            None, src, defect)
            (out / f"tb_{name}.spice").write_text(text)
            (out / f"request_{name}.json").write_text(
                json.dumps(request(f"tb_{name}.spice", proc, 2), indent=2) + "\n")
        (out / "defects.json").write_text(json.dumps(DEFECTS, indent=2) + "\n")
        return
    n_main = a.pilot or N_MAIN
    n_infl = a.pilot or N_INFLATED
    cases = {}
    for p in PROC:
        cases[f"main_{p}"] = (HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch", p, n_main)
        cases[f"zero_{p}"] = (HDR.format(mm=0, sc=1, extra=""), "sw_stat_mismatch", p, N_ZERO)
    for p in PROC:
        cases[f"inflated_{p}"] = (HDR.format(mm=3, sc=1, extra=""), "sw_stat_mismatch", p, n_infl)
    # the injector's own `.param mm_scale=1` default line would override a bench-header
    # mm_scale (first sensitivity attempt ran 10x at 1x), so these cases bake the scale
    # into the sigmas as a literal
    cases["sens1_tt"] = (HDR.format(mm=0, sc=1, extra=" sw_inj=1"), "sw_inj", "tt", N_SENS, 1.0)
    cases["sens10_tt"] = (HDR.format(mm=0, sc=10, extra=" sw_inj=1"), "sw_inj", "tt", N_SENS, 10.0)
    # zero-mismatch baseline carrying the same fixed-code probes as the sensitivity pair
    cases["senszero_tt"] = (HDR.format(mm=0, sc=1, extra=" sw_inj=0"), "sw_inj", "tt", N_ZERO, 1.0)
    extra_opts = {}
    if a.pilot:
        # seeded known-bad variants: same header, seed and draw identities as main_<p>
        for p in PROC:
            for tag, dk in (("ctrlr2", "trimbank"), ("ctrlr4", "leak"), ("ctrlr5", "diode")):
                cases[f"{tag}_{p}"] = (HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch", p, n_main)
                extra_opts[f"{tag}_{p}"] = {"defect": DEFECTS[dk]}
        # matched sensitivity arms at the finer timestep (same draws as sens1/sens10)
        for nm, hdr, sc in (("sens1", HDR.format(mm=0, sc=1, extra=" sw_inj=1"), 1.0),
                            ("sens10", HDR.format(mm=0, sc=10, extra=" sw_inj=1"), 10.0)):
            cases[f"{nm}fine_tt"] = (hdr, "sw_inj", "tt", N_SENS, sc)
        cases["senszerofine_tt"] = (HDR.format(mm=0, sc=1, extra=" sw_inj=0"), "sw_inj", "tt", N_ZERO, 1.0)
        for nm in ("sens1fine_tt", "sens10fine_tt", "senszerofine_tt"):
            extra_opts[nm] = {"tstep": TSTEP_FINE}
    manifests = {}
    for name, (header, gate, proc, n, *scale) in cases.items():
        fixed = name.startswith("sens")
        eo = extra_opts.get(name, {})
        text, man = bench(name, header, gate, fixed, scale[0] if scale else None, src, **eo)
        (out / f"tb_{name}.spice").write_text(text)
        timeout_s = 480 if eo.get("tstep") else 120  # the finer timestep costs ~4x per probe
        (out / f"request_{name}.json").write_text(
            json.dumps(request(f"tb_{name}.spice", proc, n, fixed, timeout_s), indent=2) + "\n")
        manifests[name] = man
    # one manifest of injected terms: the evidence that the body injection is live (DR-0022 s4)
    manifest = {"source": "sim/recentre/p3/rcosc_top_p3.spice" if src is None else repo_rel(src),
                "injector": "sim/mc-groundwork/mismatch_inject.py",
                "terms": next(iter(manifests.values()))}
    if src is not None:
        manifest["source_sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
    (out / "mismatch-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "limits_main.json").write_text(json.dumps(limits(N_MAIN), indent=2) + "\n")
    if a.pilot:
        (out / "limits_pilot.json").write_text(json.dumps(pilot_limits(a.pilot), indent=2) + "\n")
        (out / "defects.json").write_text(json.dumps(DEFECTS, indent=2) + "\n")


if __name__ == "__main__":
    main()
