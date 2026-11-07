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

Variants (names are the run-campaign.sh case names):
  main_<p>     mismatch on (sw_stat_mismatch=1, mm_scale=1), N=500, p in tt/ff/ss
  inflated_<p> sw_stat_mismatch=3: MOS and injected sigma both 3x (DR-0022 s3)
  zero_<p>     sw_stat_mismatch=0: injected terms identically 0 (plumbing control)
  sens1_tt / sens10_tt   MOS off (sw_stat_mismatch=0), injected terms live at
               mm_scale 1 and 10 through a separate gate (sw_inj=1): the
               DR-0022 s3 sensitivity control
"""
import json
import sys
from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(here.parent / "mc-groundwork"))  # also works under python -I
from mismatch_inject import inject  # noqa: E402

SRC = here.parent / "recentre" / "p3" / "rcosc_top_p3.spice"
SEED = 20261008  # DR-0019: one recorded seed, appended to only, never re-drawn
N_MAIN = 500
N_INFLATED = 500
N_SENS = 100
N_ZERO = 3
TARGET_HZ = 48.0e6
VCAL = 3.3
PROC = {
    "tt": ["typical", "res_typical", "mimcap_typical", "cap_mim"],
    "ff": ["ff", "res_ff", "mimcap_ff", "cap_mim"],
    "ss": ["ss", "res_ss", "mimcap_ss", "cap_mim"],
}
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


def dut_text(mismatch_gate: str, mm_scale=None) -> tuple[str, list]:
    raw = SRC.read_text().splitlines()
    start = next(i for i, l in enumerate(raw) if l.upper().startswith(".SUBCKT RCOSC_TOP"))
    end = next(i for i, l in enumerate(raw) if l.upper().startswith(".ENDS"))
    body = "\n".join(raw[start:end + 1])
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


def probe(var: str, dest: str, temp: float, vdd: float) -> list[str]:
    """one transient at (temp, vdd) with the trim word `var`; frequency into `dest`."""
    mid = vdd / 2
    return [
        f"  option temp = {temp:g}",
        f"  alter vdd = {vdd:g}",
    ] + set_code(var, f"{vdd:g}") + [
        "  tran 200p 1200n",
        f"  meas tran ta when v(clk)={mid:.4f} rise=5",
        f"  meas tran tb when v(clk)={mid:.4f} rise=25",
        "  let fq = 20 / (tb - ta)",
        "  set fq_s = $&fq",
        "  setplot $sp",
        f"  let {dest} = $fq_s",
    ]


def bench(tag: str, header: str, gate: str, fixed: bool = False, mm_scale=None) -> tuple[str, list]:
    dut, manifest = dut_text(gate, mm_scale)
    L = [
        f"* rcosc_top item-6 Monte Carlo bench: {tag} (generated by gen_campaign.py; DUT = P3, DR-0023)",
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
    L += probe("mid", "fm", 27, VCAL)
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
    L += probe("cclamp", "fhold", 27, VCAL)
    for lab, t, v in POINTS:
        if (t, v) == (27, VCAL):
            L.append(f"let f_{lab} = fhold")
        else:
            L += probe("cclamp", f"f_{lab}", t, v)
    L += probe("cup", "fup", 27, VCAL)
    L += probe("cdn", "fdn", 27, VCAL)
    if fixed:
        # DR-0022 s3 sensitivity control: step sizes at FIXED transitions (the MSB
        # transition 0x7F -> 0x80 and its neighbour), independent of the code the
        # die's calibration picked.
        for c in (126, 127, 128):
            L.append(f"let cfix{c} = {c}")
            L += probe(f"cfix{c}", f"ffix{c}", 27, VCAL)
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


def request(netlist: str, proc: str, n: int, fixed: bool = False) -> dict:
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
        "options": {"timeout_s": 120, "keep_artifacts": False},
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


HDR = ".param sw_stat_global=0 sw_stat_mismatch={mm} mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0 mm_scale={sc}{extra}"


def main() -> None:
    cases = {}
    for p in PROC:
        cases[f"main_{p}"] = (HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch", p, N_MAIN)
        cases[f"zero_{p}"] = (HDR.format(mm=0, sc=1, extra=""), "sw_stat_mismatch", p, N_ZERO)
    for p in PROC:
        cases[f"inflated_{p}"] = (HDR.format(mm=3, sc=1, extra=""), "sw_stat_mismatch", p, N_INFLATED)
    # the injector's own `.param mm_scale=1` default line would override a bench-header
    # mm_scale (first sensitivity attempt ran 10x at 1x), so these cases bake the scale
    # into the sigmas as a literal
    cases["sens1_tt"] = (HDR.format(mm=0, sc=1, extra=" sw_inj=1"), "sw_inj", "tt", N_SENS, 1.0)
    cases["sens10_tt"] = (HDR.format(mm=0, sc=10, extra=" sw_inj=1"), "sw_inj", "tt", N_SENS, 10.0)
    # zero-mismatch baseline carrying the same fixed-code probes as the sensitivity pair
    cases["senszero_tt"] = (HDR.format(mm=0, sc=1, extra=" sw_inj=0"), "sw_inj", "tt", N_ZERO, 1.0)
    manifests = {}
    for name, (header, gate, proc, n, *scale) in cases.items():
        fixed = name.startswith("sens")
        text, man = bench(name, header, gate, fixed, scale[0] if scale else None)
        (here / f"tb_{name}.spice").write_text(text)
        (here / f"request_{name}.json").write_text(
            json.dumps(request(f"tb_{name}.spice", proc, n, fixed), indent=2) + "\n")
        manifests[name] = man
    # one manifest of injected terms: the evidence that the body injection is live (DR-0022 s4)
    (here / "mismatch-manifest.json").write_text(json.dumps(
        {"source": "sim/recentre/p3/rcosc_top_p3.spice", "injector": "sim/mc-groundwork/mismatch_inject.py",
         "terms": next(iter(manifests.values()))}, indent=2) + "\n")
    (here / "limits_main.json").write_text(json.dumps(limits(N_MAIN), indent=2) + "\n")


if __name__ == "__main__":
    main()
