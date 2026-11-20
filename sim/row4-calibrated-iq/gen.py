#!/usr/bin/env python3
"""Matched-die calibrated-code running-Iq campaign for the `w3r65` / `w2.5r75` bank candidates (issue #337, operator rulings 2026-11-18 q136 / q178).

Population: the DR-0032 draws (500 per process, seed 20261008, `vary: mismatch`, derived seeds, one corner per request), realized on the
candidate DUT = the extraction of the rebuilt layout (`sim/row45-rerun/results/20261112T200335Z-extract-l07/`, the DR-0043/0044 basis)
with the bank variant applied as netlist text via the `row45-rerun/variant.py` rule (layout NOT re-extracted; no `design/*` file touched).

Per candidate x process the campaign runs two phases (this script only generates inputs; every SPICE run is
`klt sim --batch-set ... --backend batch --wait-for-capacity 600`):

  phase 1 - candidate: one monte_carlo request (n=500, seed 20261008, derived seeds - bit-identical to DR-0032's per-sample seeds,
    same single-corner request shape).  Per die, inside ONE ngspice session so every solve sees the same mismatch draw:
    bisection of the 8-bit code to the frequency nearest 48.000 MHz at 27 C / 3.3 V (the DR-0032 rule, verbatim), then the held
    code across the DR-0044 grid (3.0/3.3/3.6 V x -40/27/85 C) measuring running Iq with DR-0044's integrator bench (20-period
    window, clk rising edges 5..25).  The report yields per-die `code_sel` AND the per-die derived ngspice seed
    (`corners[i].monte_carlo.seed`).

  phase 2 - control: per-die decks on the DR-0044 L=1 um control (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, the old-layout
    extraction) at the SAME per-die code, carrying the SAME per-die realization: the deck writes the candidate die's derived seed
    as `.options seed=<rndseed>`.  ngspice's random stream is fully determined by that seed plus the draw sequence, and the two
    DUT texts consume the identical sequence - same 98 X cards in the same order (PDK per-instance mis draws), same 28 injected
    `d_` params in the same order (only X$91's sigma differs, which is the physical mismatch scaling of the shorter resistor).
    So control die i carries die i's exact mismatch realization; this is checked by the probe decks (mode `probe`).

The ratified Iq row (README "Quiescent current (Iq)", DR-0003 row 4, "< 500 uA (running)") names no trim code; the campaign
measures the code each die actually uses, plus every cell needed to compare against DR-0044's fixed-code sweep.

Usage (offline; launches nothing):
  python3 -I sim/row4-calibrated-iq/gen.py cand  OUTDIR w3r65|w2.5r75 tt|ff|ss
  python3 -I sim/row4-calibrated-iq/gen.py ctrl  OUTDIR w3r65|w2.5r75 tt|ff|ss CAND_REPORT.json [PER_REQ]
  python3 -I sim/row4-calibrated-iq/gen.py probe OUTDIR SEED
  python3 -I sim/row4-calibrated-iq/tables.py CAND_REPORT... CTRL_OUTDIR...   (see tables.py --help)
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "mc"))
sys.path.insert(0, str(REPO / "sim" / "mc-groundwork"))
sys.path.insert(0, str(REPO / "sim" / "row45-rerun"))
sys.path.insert(0, str(REPO / "sim" / "pvt"))
from mismatch_inject import inject  # noqa: E402
from pvt_sweep import PROCESS_CORNERS  # noqa: E402
import gen_campaign as gmc  # noqa: E402  (DR-0032 harness: probe/set_code/HDR/POINTS/PROC semantics)

import gen_row5_iq_schematic as gi  # noqa: E402  (INTEG_LINES: DR-0044's integrator)

CAND_BASE = REPO / "sim" / "row45-rerun" / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice"
CTRL_BASE = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"
SEED = gmc.SEED  # 20261008, DR-0019's recorded seed: the campaign re-draws the DR-0032 population exactly
TARGET_HZ = gmc.TARGET_HZ
VCAL = gmc.VCAL
CAND_NAME = re.compile(r"w(\d+(?:\.\d+)?)r(\d+)")
X91_LEN = 12.0386  # um, the base resistor's committed length (DR-0037)


def candidate_text(name: str) -> str:
    """The candidate as netlist text on the rebuilt-layout extraction (the DR-0047 search rule; equals DR-0037's w3r65)."""
    m = CAND_NAME.fullmatch(name)
    if not m:
        raise SystemExit(f"candidate name must be w<K>r<P>: {name}")
    text = gi_variant().double_bank_switches(CAND_BASE.read_text(), float(m.group(1)))
    n = text.count("r_length=12.03860U")
    assert n == 1, n
    return text.replace("r_length=12.03860U", f"r_length={X91_LEN * int(m.group(2)) / 100:.5f}U")


def gi_variant():
    spec = importlib.util.spec_from_file_location("variant317", REPO / "sim" / "row45-rerun" / "variant.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dut_subckt(text: str) -> tuple[str, list]:
    """Extract the rcosc_top subckt and apply the DR-0022 injector (the DR-0032 body treatment).

    The injector's sigma argument is written `mm_scale*<sigma>` (symbolic scale).  On ngspice-47 - the current
    batch-fleet image, moved from 46 since DR-0032 - an `agauss` sigma that is any expression other than one folded
    literal draws **0 and consumes no RNG** (fleet probe: `agauss(0,mm_scale*0.0025,1)` -> 0, `agauss(0,var,1)` and
    `agauss(0,0.0025,1)` live).  The committed DR-0032 benches therefore no longer produce their committed realization
    on the current image (re-run of `sim/mc/tb_main_tt.spice` with sample 0's seed: code 168 vs committed 163), and
    neither does the injector's own literal-scale path (`1.0*<sigma>` is still an expression).  So the sigma is folded
    to a single literal here - the same 1x values DR-0022/DR-0032 define, in the form ngspice-47 actually draws - and
    every folded line is asserted.  Candidate and control decks share the identical folded text treatment, so the
    matched-draw contract holds either way."""
    raw = text.splitlines()
    start = next(i for i, l in enumerate(raw) if l.upper().startswith(".SUBCKT RCOSC_TOP"))
    end = next(i for i, l in enumerate(raw) if l.upper().startswith(".ENDS"))
    body, manifest = inject("\n".join(raw[start:end + 1]), mm_scale=None, gate="sw_stat_mismatch")
    folded, n = re.subn(r"agauss\(0,mm_scale\*([0-9.eE+-]+),1\)", r"agauss(0,\1,1)", body)
    drawn = sum(1 for line in folded.splitlines() if re.search(r"agauss\(0,[0-9.eE+-]+,1\)", line) and ".param d_" in line)
    assert n == len(manifest), (n, len(manifest))
    assert drawn == len(manifest), (drawn, len(manifest))
    assert "mm_scale*" not in folded.split(".subckt", 1)[0].replace("mm_scale=1", "")
    return folded, manifest


def header(proc: str | None = None, pdk_rel: bool = True) -> list[str]:
    """Deck head: seed/bookkeeping cards go BEFORE the model libs (klt's own deck order); DR-0032 bench header verbatim.

    pdk_rel names the fleet image's gf180mcuC install as `$PDK_ROOT/gf180mcuC/...`: the image's `$PDK_ROOT` is the
    VARIANT-FAMILY root (probe `results/20261120T034000Z-libpath/`: `/opt/pdk/libs.tech/...` does not exist,
    `/opt/pdk/gf180mcuC/libs.tech/...` and `/opt/pdk/gf180mcuD/...` both do), and klt ships deck bytes unchanged,
    expanding only `$PDK_ROOT`.  The corner-mode requests never hit this: klt composes those decks itself and
    resolves the image install internally."""
    out = []
    if proc is not None:
        lib = "$PDK_ROOT/gf180mcuC/libs.tech/ngspice/sm141064.ngspice" if pdk_rel else str(_pdk_lib())
        out += [f".lib {lib} {s}" for s in gmc.PROC[proc]]
    return out


def _pdk_lib() -> Path:
    """The submitting host's gf180mcuC model lib, for local probe decks only."""
    import os
    root = os.environ.get("KLT_PDK_ROOT") or os.environ.get("PDK_ROOT") or ""
    for base in filter(None, [root] + [
        "/home/ubuntu/.ciel/ciel/gf180mcu/versions/f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7",
    ]):
        p = Path(base) / "gf180mcuC" / "libs.tech" / "ngspice" / "sm141064.ngspice"
        if p.exists():
            return p
    raise SystemExit("gf180mcuC sm141064.ngspice not found; set KLT_PDK_ROOT")


def iq_probe(code: str, temp: float, vdd: float, lab: str) -> list[str]:
    """One held-code grid point: DR-0044's 20-period integrator window (clk rising edges 5..25).

    The meas scalars and the first lets land in the tran's own plot; the results are copied into the
    session-stable plot `$sp` with gen_campaign's `set x_s = $&x` / `let dest = $x_s` pattern, so later
    probes (and wrdata) still see them."""
    mid = vdd / 2
    return [
        f"  option temp = {temp:g}",
        f"  alter vdd = {vdd:g}",
    ] + gmc.set_code(code, f"{vdd:g}") + [
        "  tran 200p 4000n",
        f"  meas tran ta when v(clk)={mid:.4f} rise=5",
        f"  meas tran tb when v(clk)={mid:.4f} rise=25",
        f"  meas tran qa find v(qint) when v(clk)={mid:.4f} rise=5",
        f"  meas tran qb find v(qint) when v(clk)={mid:.4f} rise=25",
        "  let fx = 20 / (tb - ta)",
        "  let iqx = (qb - qa) * 1e-9 / (tb - ta)",
        "  set fs = $&fx",
        "  set iqs = $&iqx",
        "  setplot $sp",
        f"  let f_{lab} = $fs",
        f"  let iq_{lab} = $iqs",
    ]


def cand_bench(name: str, proc: str) -> str:
    """Phase-1 bench: DR-0032's bisection (verbatim rule) + the 9-point held-code running-Iq grid, one session per die."""
    dut, _manifest = dut_subckt(candidate_text(name))
    L = [
        f"* row4 calibrated-Iq candidate bench: {name} {proc} (generated by sim/row4-calibrated-iq/gen.py; DUT = rebuilt-layout"
        f" extraction + {name}, DR-0032 injection, seed {SEED})",
        gmc.HDR.format(mm=1, sc=1, extra=""),
        dut,
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 DC {VCAL:g}",
    ] + [f"VT{i} t{i} 0 DC 0" for i in range(8)] + [gi.INTEG_LINES.rstrip("\n"), ".control",
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
    ] + gmc.probe("mid", "fm", 27, VCAL) + [
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
        f"let cclamp = {gmc.pmax('0', '(' + gmc.pmin('255', 'csel') + ')')}",
    ]
    for lab, t, v in gmc.POINTS:
        L += iq_probe("cclamp", t, v, lab)
    L += [
        "let fgap = abs(f_27_33 - fsel)",
        "let ecal = (fsel - tgt) / tgt * 100",
        "set v_code = $&csel",
        "set v_fsel = $&fsel",
        "set v_flo = $&flo",
        "set v_fhi = $&fhi",
        "set v_gap = $&fgap",
        "set v_ecal = $&ecal",
    ]
    for lab, _, _ in gmc.POINTS:
        L += [f"set v_f_{lab} = $&f_{lab}", f"set v_iq_{lab} = $&iq_{lab}"]
    L.append(".endc")
    return "\n".join(L) + "\n"


def cand_request(name: str, proc: str, netlist: str) -> dict:
    """Phase-1 request: DR-0032's request shape (derived seeds reproduce the DR-0032 per-sample seeds bit-for-bit)."""
    m = [
        {"name": "code_sel", "expr": "$v_code", "unit": ""},
        {"name": "f_cal_hz", "expr": "$v_fsel", "unit": "Hz"},
        {"name": "e_cal_pct", "expr": "$v_ecal", "unit": "%"},
        {"name": "hold_gap_hz", "expr": "$v_gap", "unit": "Hz"},
    ]
    for lab, _, _ in gmc.POINTS:
        m += [
            {"name": f"f_{lab}_hz", "expr": f"$v_f_{lab}", "unit": "Hz"},
            {"name": f"iq_{lab}_a", "expr": f"$v_iq_{lab}", "unit": "A"},
        ]
    return {
        "netlist": netlist,
        "engine": "ngspice",
        "netlist_source": "extracted",
        "models": {"pdk": "gf180mcuC", "lib": "libs.tech/ngspice/sm141064.ngspice"},
        "corners": {
            "process": [{"name": proc, "sections": gmc.PROC[proc]}],
            "temperature_c": [27],
        },
        "analysis": {"kind": "op", "args": ""},
        "measurements": m,
        "batch": {"capacity_wait_s": 1200},
        "options": {"timeout_s": 1800, "keep_artifacts": False},
        "monte_carlo": {"n": 500, "seed": SEED, "vary": "mismatch"},
    }


def ctrl_deck(name: str, proc: str, unit: str, code: int, seed: int, sample_index: int,
              process_seed: int, mismatch_seed: int) -> str:
    """Phase-2 control deck: the DR-0044 L=1 um control at die i's held code, carrying die i's realization.

    `.options seed=` reproduces die i's derived ngspice seed (klt `_mc_sample_seed`'s combined rndseed), so ngspice's random
    stream - and therefore every injected and PDK-per-instance draw - is identical to the candidate die's, each scaled by its
    own device's sigma (physically: the same die, different bank)."""
    dut, _manifest = dut_subckt(CTRL_BASE.read_text())
    L = [
        f"* row4 calibrated-Iq control deck: {name} {proc} {unit} code {code} (generated by sim/row4-calibrated-iq/gen.py;"
        f" DUT = {CTRL_BASE.relative_to(REPO)}, the DR-0044 L=1um control; seed = candidate die's derived rndseed)",
        f".options seed={seed}",
        f"* candidate die bookkeeping: sample_index={sample_index} process_seed={process_seed} mismatch_seed={mismatch_seed}",
        gmc.HDR.format(mm=1, sc=1, extra=""),
    ] + header(proc) + [
        dut,
        "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
        f"VDD vdd 0 DC {VCAL:g}",
    ] + [f"VT{i} t{i} 0 DC 0" for i in range(8)] + [gi.INTEG_LINES.rstrip("\n"), ".control",
        "set noaskquit",
        "set measureprec=8",
        "setplot new",
        "set sp = $curplot",
        f"let cclamp = {code}",
    ]
    for lab, t, v in gmc.POINTS:
        L += iq_probe("cclamp", t, v, lab)
    L += [
        "set v_code = $&cclamp",
    ]
    for lab, _, _ in gmc.POINTS:
        L += [f"set v_f_{lab} = $&f_{lab}", f"set v_iq_{lab} = $&iq_{lab}"]
    L += [
        "wrdata meas.csv " + " ".join(
            [f"f_{lab}" for lab, _, _ in gmc.POINTS] + [f"iq_{lab}" for lab, _, _ in gmc.POINTS]),
        ".endc",
    ]
    return "\n".join(L) + "\n"


def ctrl_requests(name: str, proc: str, report: dict, out: Path, per_req: int = 25) -> int:
    """Phase-2 inputs from the phase-1 report: one deck per die (code + derived seed), grouped `per_req` decks per request."""
    corners = [c for c in report["corners"]
               if c.get("status") == "pass" and c.get("monte_carlo") is not None]
    if len(corners) != report.get("corner_count", len(corners)):
        raise SystemExit(f"phase-1 report has non-pass corners: {report.get('corner_count')} declared, {len(corners)} usable")
    decks = []
    for c in sorted(corners, key=lambda c: c["monte_carlo"]["sample_index"]):
        mc = c["monte_carlo"]
        meas = {m["name"]: m["value"] for m in c["measurements"]}
        code = int(meas["code_sel"])
        if not (0 <= code <= 255):
            raise SystemExit(f"sample {mc['sample_index']}: unclamped code {code}")
        unit = f"u{mc['sample_index']:03d}"
        deck = f"deck_{name}_{proc}_{unit}.spice"
        (out / deck).write_text(ctrl_deck(name, proc, unit, code, mc["seed"], mc["sample_index"],
                                          mc["process_seed"], mc["mismatch_seed"]))
        decks.append({"id": unit, "deck": deck, "outputs": ["meas.csv"], "timeout_s": 900})
    n_req = 0
    for k in range(0, len(decks), per_req):
        group = decks[k:k + per_req]
        req = {
            "models": {"pdk": "gf180mcuC"},
            "decks": group,
            "options": {"timeout_s": 900},
            "batch": {"capacity_wait_s": 1200},
        }
        (out / f"dreq_{name}_{proc}_{k // per_req:02d}.json").write_text(json.dumps(req, indent=2) + "\n")
        n_req += 1
    return n_req


def probe_decks(out: Path, seed: int) -> None:
    """Draw-matching probe decks (run locally, one ngspice each): d__91 must scale by exactly the X$91 sigma ratio."""
    decks = {}
    for tag, src_text, sd in (("cand_w3r65", candidate_text("w3r65"), seed),
                              ("ctrl_l1", CTRL_BASE.read_text(), seed),
                              ("ctrl_alt", CTRL_BASE.read_text(), seed + 1)):
        dut, _manifest = dut_subckt(src_text)
        L = [
            f"* draw-matching probe: {tag}, seed {sd} (generated by sim/row4-calibrated-iq/gen.py probe)",
            f".options seed={sd}",
            gmc.HDR.format(mm=1, sc=1, extra=""),
        ] + header("tt", pdk_rel=False) + [
            dut,
            "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top",
            f"VDD vdd 0 DC {VCAL:g}",
        ] + [f"VT{i} t{i} 0 DC {VCAL * ((0xD4 >> i) & 1):g}" for i in range(8)] + [
            "* probe-only: the injected X$91 draw as a node voltage (a .param is not a control-space vector)",
            "BD91 p91 0 V='d__91'",
            gi.INTEG_LINES.rstrip("\n"), ".control",
            "set noaskquit",
            "set measureprec=8",
            "setplot new",
            "set sp = $curplot",
            "  option temp = 27",
            "tran 200p 4000n",
            "meas tran ta when v(clk)=1.6500 rise=5",
            "meas tran tb when v(clk)=1.6500 rise=25",
            "meas tran qa find v(qint) when v(clk)=1.6500 rise=5",
            "meas tran qb find v(qint) when v(clk)=1.6500 rise=25",
            "let iqx = (qb - qa) * 1e-9 / (tb - ta)",
            "set iqs = $&iqx",
            "setplot $sp",
            "let iq1 = $iqs",
            "tran 200p 4000n",
            "meas tran ta when v(clk)=1.6500 rise=5",
            "meas tran tb when v(clk)=1.6500 rise=25",
            "meas tran qa find v(qint) when v(clk)=1.6500 rise=5",
            "meas tran qb find v(qint) when v(clk)=1.6500 rise=25",
            "let iqx = (qb - qa) * 1e-9 / (tb - ta)",
            "meas tran d91m find v(p91) at=400n",
            "set iqs = $&iqx",
            "set d91s = $&d91m",
            "setplot $sp",
            "let iq2 = $iqs",
            "let d91v = $d91s",
            "wrdata probe.csv iq1 iq2 d91v",
            ".endc",
        ]
        (out / f"probe_{tag}.spice").write_text("\n".join(L) + "\n")
        decks[tag] = f"probe_{tag}.spice"
    (out / "probe-README.txt").write_text(
        "Run each deck with ngspice -b (local, one at a time). Expected:\n"
        f"- probe.csv: iq1 ~= iq2 (the integrator re-zeros per tran; .ic applies at every tran start),\n"
        "  and d__91 = that die's injected X$91 draw.\n"
        "- d__91(ctrl_l1) / d__91(cand_w3r65) = sigma_ctrl / sigma_w3r65 = 0.0020379663547086 / 0.0025278...\n"
        "  = sqrt(7.82509/12.0386) = 0.80622 for the SAME seed (matched realization, different scaling).\n"
        "- a different seed gives an unrelated d__91 (seed sensitivity control).\n")


def main(argv: list[str] | None = None) -> None:
    a = argv if argv is not None else sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    mode, out = a[0], Path(a[1])
    out.mkdir(parents=True, exist_ok=True)
    if mode == "cand":
        name, proc = a[2], a[3]
        (out / f"dut_{name}_src.spice").write_text(candidate_text(name))
        bench = f"tb_{name}_{proc}.spice"
        (out / bench).write_text(cand_bench(name, proc))
        (out / f"request_{name}_{proc}.json").write_text(
            json.dumps(cand_request(name, proc, bench), indent=2) + "\n")
    elif mode == "ctrl":
        name, proc, report_path = a[2], a[3], Path(a[4])
        per_req = int(a[5]) if len(a) > 5 else 25
        report = json.loads(report_path.read_text())
        n = ctrl_requests(name, proc, report, out, per_req)
        print(f"{n} deck-list requests, {len(report['corners'])} decks, -> {out}")
    elif mode == "probe":
        probe_decks(out, int(a[2]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
