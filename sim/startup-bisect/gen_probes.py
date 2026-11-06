#!/usr/bin/env python3
"""Bisect of the three P3 changes at the failing corner fs / -40 C / 3.3 V (issue #229).

DUT variants are derived from the settled P3 netlist by reverting one P3 edit at a time
(ladder lengths back to the committed extracted values; XCTIMING back to the fixed
2.172e-13 F card).  Every probe is one corner, so `klt sim --backend local` is correct.
Usage: python3 -I gen_probes.py [--out DIR]     (default: sim/startup-bisect/probes)
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim" / "startup-fs-m40c"))
import gen_probes as g  # noqa: E402

P3 = g.SRC.read_text()
LADDER = {"12.03860U": "17.198U", "0.52360U": "0.748U", "1.04790U": "1.497U", "2.09510U": "2.993U",
          "4.19020U": "5.986U", "8.38040U": "11.972U", "16.76080U": "23.944U",
          "33.52160U": "47.888U", "67.04250U": "95.775U"}
MIM_P3 = "XCTIMING vss__t7 \\$26__t8 cap_mim_1f0fF c_width=20u c_length=10u m=1"
MIM_OLD = "C$86 vss__t7 \\$26__t8 2.172e-13"


def revert_ladder(t):
    for new, old in LADDER.items():
        if old:
            assert f"r_length={new} " in t, new
            t = t.replace(f"r_length={new} ", f"r_length={old} ")
    return t


def revert_mim(t):
    assert MIM_P3 in t
    return t.replace(MIM_P3, MIM_OLD)


def drop_c(t):  # remove extracted net capacitors (C_*), keep the timing MiM
    return "\n".join(l for l in t.split("\n") if not l.startswith("C_"))


def tiny_r(t):  # extracted series R -> 1 mOhm
    return re.sub(r"^(R_\S+ \S+ \S+) \S+$", r"\1 1m", t, flags=re.M)


def no_geom(t):  # drop layout AS/AD/PS/PD on devices
    return re.sub(r" (AS|AD|PS|PD)=\S+", "", t)


def no_geom_on(t, names):  # drop AS/AD/PS/PD on the named device instances only
    out = []
    for l in t.split("\n"):
        if l.split(" ")[0] in names:
            l = re.sub(r" (AS|AD|PS|PD)=\S+", "", l)
        out.append(l)
    return "\n".join(out)


CMPH_PAIR = {"X$19", "X$20"}
CMPH_LOAD = {"X$65", "X$66"}
CMPH_OUT = {"X$21", "X$67"}
CMPH_TAIL = {f"X${i}" for i in range(39, 47)}
ALL_CMPH = CMPH_PAIR | CMPH_LOAD | CMPH_OUT | CMPH_TAIL

def resize(t, inst, w=None, l=None):
    """Re-size one extracted device; AS/AD/PS/PD follow the extractor's own pattern (0.42 um diffusion)."""
    out = []
    for ln in t.split("\n"):
        if ln.split(" ")[0] == inst:
            ln = re.sub(r"L=\S+", f"L={l}" if l else r"\g<0>", ln)
            if w:
                wv = float(w.rstrip("uU"))
                ln = re.sub(r"W=\S+", f"W={w}", ln)
                ln = re.sub(r"A([SD])=\S+", lambda m: f"A{m.group(1)}={wv*0.42:.4g}P", ln)
                ln = re.sub(r"P([SD])=\S+", lambda m: f"P{m.group(1)}={2*wv+0.84:.4g}U", ln)
        out.append(ln)
    return "\n".join(out)


def cand(t, n=None, p=None, nl=None):
    t = resize(t, "X$21", w=n, l=nl)
    return resize(t, "X$67", w=p)


CANDS = {"c1": dict(n="1u"), "c2": dict(p="8u"), "c3": dict(nl="1u"), "c4": dict(n="1u", p="8u")}
BASES = {"p3": P3, "pex": revert_mim(revert_ladder(P3))}

FIX = REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"
VARIANTS = {"cmphfix": FIX.read_text(), "g_cmph": no_geom_on(P3, ALL_CMPH),
            "g_notcmph": no_geom_on(P3, {w for w in re.findall(r"^(X\$\d+) ", P3, flags=re.M)} - ALL_CMPH),
            "g_pair": no_geom_on(P3, CMPH_PAIR), "g_load": no_geom_on(P3, CMPH_LOAD),
            "g_out": no_geom_on(P3, CMPH_OUT), "g_tail": no_geom_on(P3, CMPH_TAIL),
            "p3": P3, "noladder": revert_ladder(P3), "nomim": revert_mim(P3),
            "pex_orig": revert_mim(revert_ladder(P3)),
            **{f"{b}_{k}": cand(bt, **kw) for b, bt in BASES.items() for k, kw in CANDS.items()},
            "noC": drop_c(P3), "noR": tiny_r(P3), "nogeom": no_geom(P3)}
PROCS = [("fs", -40.0, 3.3), ("fs", -40.0, 3.6)]


def generate(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for v, text in VARIANTS.items():
        (out / f"dut_{v}.spice").write_text(text)
    for v in VARIANTS:
        for proc, temp, vdd in PROCS:
            name = f"{v}_{proc}_m40_v{int(vdd*10)}"
            p = dict(process=proc, temp=temp, vdd=vdd, tstop="1200n", ramp=None)
            tb = g.testbench(name, p).replace(f'.include "{g.DUT}"', f'.include "dut_{v}.spice"')
            (out / f"tb_{name}.spice").write_text(tb)
            (out / f"request_{name}.json").write_text(json.dumps(g.request(name, p), indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=HERE / "probes")
    generate(ap.parse_args().out)
