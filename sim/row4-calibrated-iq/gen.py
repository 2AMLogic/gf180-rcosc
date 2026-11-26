#!/usr/bin/env python3
"""Matched-die running-Iq at per-die calibrated trim codes (issue #337, operator ruling q178). Sim-only; launches nothing.

For each bank candidate (DR-0037 `w3r65` = 16 bank pass devices at 3x W + base resistor X$91 at 65 %, and DR-0047
`w2.5r75` = 2.5x W + 75 %) the DR-0032 population (500 mismatch draws per process, seed 20261008, `vary: mismatch`)
is re-drawn on the extraction of the rebuilt layout with the variant applied as netlist text (same DUT construction
as sim/row4-w3r65/gen.py and sim/row4-iq-variant/gen.py; layout NOT re-extracted).  Each die calibrates inside ONE
ngspice session (`.control` bisection over the 8-bit code for the frequency nearest 48.000 MHz at 27 C / 3.3 V, the
DR-0032 method in sim/mc/gen_campaign.py), then holds that code across the DR-0044 supply/temperature grid
(3.0/3.3/3.6 V x -40/27/85 C), measuring frequency AND running supply current at every point.  Running Iq is the
DR-0044 integrator bench (sim/row45-rerun/gen_row5_iq_schematic.py): -i(VDD) integrated on a 1 nF capacitor,
window = clk rising edges 5..25, iq = dQ/dt over the same window.  The DR-0044 nominal-cell benches ran
`tran 200p 4000n`; the window is edge-indexed from t=0, so a 1200n stop (the established extraction probe length,
sim/row45-rerun/gen_calib_requests.py and gen_stage_requests.py) contains the identical edges 5..25 and does not
change the measured window.

The L=1 um control is the DR-0044 same-recipe extraction of the previous layout (sim/cmph-fix/rcosc_top_p3_cmphfix.spice),
run as a PRE-COMPOSED DECK LIST (`klt sim` `decks[]`): deck k carries `.options seed=<rndseed_k>` -- the exact combined
seed the candidate's k-th Monte Carlo sample ran with, read from the candidate report's `corners[k].monte_carlo.seed` --
and the candidate's calibrated code for die k, so control and candidate see the same draw at the same code, supply and
temperature.  Draw matching rests on: identical derived seeds (klt's SHA-256 seed contract), identical injected-mismatch
term lists (DR-0022 injector, 14 terms in the same order on all three DUTs -- gen.py asserts this), structurally
parallel device card sequences between the two extractions (same card count and order; the rebuild changed only the
comparator-H mirror-load L text), and the same engine build (checked in tables.py from the reports).

Usage:
  gen.py cand  VARIANT OUTDIR [N]        VARIANT = w3r65 | w2.5r75 ; Monte Carlo campaign benches+requests
                                         (tt/ff/ss, n = N samples, default 500; N=10 is the fleet pilot)
  gen.py ctl   OUTDIR CANDRUNDIR [N]     control deck list from a finished candidate run dir (reads
                                         art_<proc>/report.json or report_<proc>.json), first N dice (default all)
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "mc-groundwork"))
from mismatch_inject import inject  # noqa: E402

EXTRACT_L07 = REPO / "sim" / "row45-rerun" / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice"
CONTROL_L1 = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"  # DR-0044 control extraction
SEED = 20261008  # DR-0019/DR-0032: the one recorded seed, never re-drawn
TARGET_HZ = 48.0e6
VCAL = 3.3
PROCS = ("tt", "ff", "ss")
POINTS = [(f"{'n40' if t < 0 else t}_{int(v * 10)}", t, v)
          for t in (-40, 27, 85) for v in (3.0, 3.3, 3.6)]
HDR = ".param sw_stat_global=0 sw_stat_mismatch=1 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0 mm_scale=1"
INTEG = ("* supply-current integrator (analysis only): v(qint) = integral of -i(VDD) dt / 1 nF (DR-0044 bench)\n"
         "Bint 0 qint I=-i(VDD)\nCint qint 0 1n\nRint qint 0 1e15\n.ic v(qint)=0\n")
# Deck-mode control decks name the runner's PDK explicitly: on the fleet $PDK_ROOT is the PDK root
# (/opt/pdk), so the gf180mcuC package component is part of the relative path (fleet-pilot verified;
# the corner path composes the same file from models.pdk + models.lib).
LIBS = {p: [f".lib $PDK_ROOT/gf180mcuC/libs.tech/ngspice/sm141064.ngspice {s}" for s in
            {"tt": ("typical", "res_typical", "mimcap_typical"),
             "ff": ("ff", "res_ff", "mimcap_ff"),
             "ss": ("ss", "res_ss", "mimcap_ss")}[p]] + [
            ".lib $PDK_ROOT/gf180mcuC/libs.tech/ngspice/sm141064.ngspice cap_mim"] for p in PROCS}


def _spec(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def dut_body(src: Path, variant: str | None) -> str:
    """subckt body of `src`, variant applied as netlist text, DR-0022 mismatch injected."""
    raw = src.read_text().splitlines()
    start = next(i for i, l in enumerate(raw) if l.upper().startswith(".SUBCKT RCOSC_TOP"))
    end = next(i for i, l in enumerate(raw) if l.upper().startswith(".ENDS"))
    body = "\n".join(raw[start:end + 1])
    if variant:
        m = re.fullmatch(r"w(\d+(?:\.\d+)?)r(\d+)", variant)
        if not m:
            raise SystemExit(f"unknown variant {variant!r}")
        v = _spec("v317", REPO / "sim" / "row45-rerun" / "variant.py")
        body = v.double_bank_switches(body, float(m.group(1)))
        assert body.count("r_length=12.03860U") == 1
        body = body.replace("r_length=12.03860U", f"r_length={12.0386 * int(m.group(2)) / 100:.5f}U")
    out, manifest = inject(body)
    return out, manifest


def probe(var: str, flab: str, ilab: str, temp: float, vdd: float) -> list[str]:
    """one transient at (temp, vdd) with trim word `var`; edges 5..25 give f into flab and Iq into ilab."""
    mid = vdd / 2
    out = [f"  option temp = {temp:g}", f"  alter vdd = {vdd:g}"]
    for i in range(8):
        out.append(f"  let vb = {vdd:g} * (floor({var} / {1 << i}) - 2 * floor({var} / {1 << (i + 1)}))")
        out.append(f"  alter vt{i} = $&vb")
    out += [
        "  tran 200p 1200n",
        f"  meas tran ta when v(clk)={mid:.4f} rise=5",
        f"  meas tran tb when v(clk)={mid:.4f} rise=25",
        f"  meas tran qa find v(qint) when v(clk)={mid:.4f} rise=5",
        f"  meas tran qb find v(qint) when v(clk)={mid:.4f} rise=25",
        "  let fqr = 20 / (tb - ta)",
        "  let iqr = (qb - qa) * 1n / (tb - ta)",
        "  set fq_s = $&fqr",
        "  set iq_s = $&iqr",
        "  setplot $sp",
        f"  let {flab} = $fq_s",
        f"  let {ilab} = $iq_s",
    ]
    return out


def pmin(a: str, b: str) -> str:
    return f"(({a}) + ({b}) - abs(({a}) - ({b}))) / 2"


def pmax(a: str, b: str) -> str:
    return f"(({a}) + ({b}) + abs(({a}) - ({b}))) / 2"


def control_calib(npoints: bool = True) -> list[str]:
    """bisection for the code nearest TARGET_HZ at 27 C / 3.3 V (DR-0032 method), then the 9-point grid at cclamp."""
    L = [
        ".control",
        "set noaskquit",
        "set measureprec=8",
        "set numdgt=10",
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
    L += probe("mid", "fm", "imd", 27, VCAL)
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
        f"let cclamp = {pmax('0', '(' + pmin('255', 'csel') + ')')}",
    ]
    for lab, t, v in POINTS:
        L += probe("cclamp", f"f_{lab}", f"iq_{lab}", t, v)
    L += [
        "set v_code = $&csel",
        "set v_ccode = $&cclamp",
        "set v_fcal = $&fsel",
    ]
    for lab, _, _ in POINTS:
        L += [f"set v_f_{lab} = $&f_{lab}", f"set v_iq_{lab} = $&iq_{lab}"]
    L += [".endc"]
    return L


def control_fixed(code: int) -> list[str]:
    """the 9-point grid at a fixed per-die code (control deck)."""
    L = [
        ".control",
        "set noaskquit",
        "set measureprec=8",
        "set numdgt=10",
        "setplot new",
        "set sp = $curplot",
        f"let ccode = {code}",
    ]
    for lab, t, v in POINTS:
        L += probe("ccode", f"f_{lab}", f"iq_{lab}", t, v)
    for lab, _, _ in POINTS:
        L += [f"set v_f_{lab} = $&f_{lab}", f"set v_iq_{lab} = $&iq_{lab}"]
    L += ["print iq_n40_30[0] iq_n40_33[0] iq_n40_36[0] iq_27_30[0] iq_27_33[0] iq_27_36[0] iq_85_30[0] iq_85_33[0] iq_85_36[0]",
          "print f_n40_30[0] f_n40_33[0] f_n40_36[0] f_27_30[0] f_27_33[0] f_27_36[0] f_85_30[0] f_85_33[0] f_85_36[0]",
          ".endc"]
    return L


def tb_skeleton(proc: str, dut_inline: str, control_lines: list[str], libs: bool = False) -> str:
    # corner-mode benches (cand) carry NO .lib lines: klt composes the model sections from
    # corners.process.sections, exactly as sim/mc/gen_campaign.py does.  Deck-mode control
    # decks (ctl) carry them explicitly ($PDK_ROOT is expanded by the executing host).
    L = [f"* row4-calibrated-iq bench {proc} (generated by gen.py; DUT inline, DR-0022 injected)",
         *([] if not libs else LIBS[proc]), HDR, dut_inline,
         "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
         f"VDD vdd 0 DC {VCAL:g}"] + [f"VT{i} t{i} 0 DC 0" for i in range(8)] + [
         INTEG.rstrip(), *control_lines, ".end"]
    return "\n".join(L) + "\n"


def cand(variant: str, out: Path, n: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    body, manifest = dut_body(EXTRACT_L07, variant)
    (out / "mismatch-manifest.json").write_text(json.dumps(
        {"source": "sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice",
         "variant": variant, "injector": "sim/mc-groundwork/mismatch_inject.py", "terms": manifest}, indent=2) + "\n")
    meas = [{"name": "code_sel", "expr": "$v_code", "unit": ""},
            {"name": "code_clamped", "expr": "$v_ccode", "unit": ""},
            {"name": "f_cal_hz", "expr": "$v_fcal", "unit": "Hz"}]
    for lab, _, _ in POINTS:
        meas.append({"name": f"f_{lab}_hz", "expr": f"$v_f_{lab}", "unit": "Hz"})
        meas.append({"name": f"iq_{lab}_a", "expr": f"$v_iq_{lab}", "unit": "A"})
    for proc in PROCS:
        (out / f"tb_{proc}.spice").write_text(tb_skeleton(proc, body, control_calib()))
        (out / f"request_{proc}.json").write_text(json.dumps({
            "netlist": f"tb_{proc}.spice", "engine": "ngspice", "netlist_source": "extracted",
            "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
            "corners": {"process": [{"name": proc, "sections": [
                *{"tt": ("typical", "res_typical", "mimcap_typical"),
                  "ff": ("ff", "res_ff", "mimcap_ff"),
                  "ss": ("ss", "res_ss", "mimcap_ss")}[proc], "cap_mim"]}],
                "temperature_c": [27]},
            "analysis": {"kind": "op", "args": ""},
            "measurements": meas,
            "batch": {"capacity_wait_s": 600},
            "options": {"timeout_s": 900, "keep_artifacts": False},
            "monte_carlo": {"n": n, "seed": SEED, "vary": "mismatch"}}, indent=2) + "\n")
    print(f"wrote {out}: tb_{{tt,ff,ss}}.spice request_{{tt,ff,ss}}.json (n={n}, seed={SEED}, variant={variant})")


def _read_report(rundir: Path, proc: str) -> dict:
    for cand in (rundir / f"art_{proc}" / "report.json", rundir / f"report_{proc}.json"):
        if cand.exists():
            return json.loads(cand.read_text())
    raise SystemExit(f"no report for {proc} under {rundir} (looked at art_{proc}/report.json, report_{proc}.json)")


def ctl(out: Path, canddir: Path, n: int | None) -> None:
    """control deck list: one deck per (proc, die) with the candidate's seed and calibrated code baked in."""
    out.mkdir(parents=True, exist_ok=True)
    body, manifest = dut_body(CONTROL_L1, None)
    (out / "mismatch-manifest.json").write_text(json.dumps(
        {"source": "sim/cmph-fix/rcosc_top_p3_cmphfix.spice", "variant": None,
         "injector": "sim/mc-groundwork/mismatch_inject.py", "terms": manifest}, indent=2) + "\n")
    (out / "dut_control.spice").write_text(body)
    codes = {}
    for proc in PROCS:
        rep = _read_report(canddir, proc)
        decks = []
        codes[proc] = []
        dd = out  # decks sit NEXT TO dut_control.spice: a deck-list .include resolves against the deck's own directory
        for c in rep["corners"]:
            k = c["monte_carlo"]["sample_index"]
            if n is not None and k >= n:
                continue
            get = lambda nm: next(m["value"] for m in c["measurements"] if m["name"] == nm)
            code = int(get("code_clamped"))
            seed = int(c["monte_carlo"]["seed"])
            codes[proc].append({"sample_index": k, "seed": seed, "code": code})
            deck = (f"* row4-calibrated-iq control deck {proc} die {k} (code {code}, seed {seed})\n"
                    f".options seed={seed}\n" + "\n".join(LIBS[proc]) + "\n" + HDR + "\n"
                    + '.include "dut_control.spice"\n'
                    + "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top\n"
                    + f"VDD vdd 0 DC {VCAL:g}\n"
                    + "\n".join(f"VT{i} t{i} 0 DC 0" for i in range(8)) + "\n"
                    + INTEG.rstrip() + "\n"
                    + "\n".join(control_fixed(code)) + "\n.end\n")
            (dd / f"{proc}_die{k:03d}.spice").write_text(deck)
            decks.append({"id": f"{proc}_die{k:03d}", "deck": f"{proc}_die{k:03d}.spice",
                          "inputs": ["dut_control.spice"], "timeout_s": 300})
        (out / f"request_decks_{proc}.json").write_text(json.dumps({
            "backend": "batch", "engine": "ngspice",
            "models": {"pdk": "gf180mcuC"},
            "decks": decks,
            "batch": {"capacity_wait_s": 600}}, indent=2) + "\n")
        print(f"{proc}: {len(decks)} control decks")
    (out / "codes.json").write_text(json.dumps(codes, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "cand":
        cand(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 500)
    elif len(sys.argv) >= 4 and sys.argv[1] == "ctl":
        ctl(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else None)
    else:
        sys.exit(__doc__)
