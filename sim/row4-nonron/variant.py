"""Knock-out variants of the extracted P3 DUT to isolate the non-Ron part of the ss charge RC term (issue #320).

Each variant edits the netlist text only (layout NOT re-extracted); one thing is removed or added per variant so the change
in the charge time constant tau = t_chg / ln((VDD-v0)/(VDD-vh)) versus VDD is attributable to it.
  ctrl    unmodified DUT (control, same bench as the others)
  nojb    the 16 bank pass devices (L=0.28U) get AS=AD=PS=PD=0: bank switch junction C removed from the timing node
  nojd    the discharge device (W=20U L=0.5U, drain on vc) gets AS=AD=PS=PD=0
  nojall  nojb + nojd
  capx    +200 fF linear capacitor on vc (dilutes any voltage-dependent parasitic C by 2x; adds nothing supply dependent)
  w<K>    bank pass devices at K x W with the code NOT re-derived (212): isolates width from the code shift of DR-0034
  w<K>r<P> w<K> and the base resistor X$91 (12.0386 um, VDD -> bank) at P % of its length so f at code 212 is re-centred
  ideal<N> all 16 bank pass devices replaced by ideal switches for trim code N (bit set: 1 mOhm between the nfet D/S, clear:
          1 GOhm; the pfet of each pair is deleted): the bank is then the poly ladder only, so what remains of the supply
          dependence of tau is not the bank switches
"""
import re
import sys
from pathlib import Path

BANK = re.compile(r"^(X\$\d+ .* (?:nfet|pfet)_03v3 L=0\.28U W=[\d.]+U) AS=[\d.]+P AD=[\d.]+P PS=[\d.]+U PD=[\d.]+U$")
DISCH = re.compile(r"^(X\$26 .* nfet_03v3 L=0\.5U W=20U) AS=[\d.]+P AD=[\d.]+P PS=[\d.]+U PD=[\d.]+U$")
VARIANTS = ["ctrl", "nojb", "nojd", "nojall", "capx"]
NFET = re.compile(r"^X\$\d+ (\S+) t(\d)__t\d (\S+) vsubs nfet_03v3 L=0\.28U W=[\d.]+U ")
PFET = re.compile(r"^X\$\d+ \S+ \S+ \S+ \S+ pfet_03v3 L=0\.28U ")


def _zero(text: str, rx, expect: int) -> str:
    out, n = [], 0
    for line in text.split("\n"):
        m = rx.match(line)
        if m:
            line = f"{m.group(1)} AS=0P AD=0P PS=0U PD=0U"
            n += 1
        out.append(line)
    assert n == expect, (n, expect)
    return "\n".join(out)


def _ideal(text: str, code: int) -> str:
    out, n_n, n_p = [], 0, 0
    for line in text.split("\n"):
        m = NFET.match(line)
        if m:
            r = "1m" if (code >> int(m.group(2))) & 1 else "1G"
            line = f"RSW{m.group(2)} {m.group(1)} {m.group(3)} {r}"
            n_n += 1
        elif PFET.match(line):
            n_p += 1
            continue
        out.append(line)
    assert (n_n, n_p) == (8, 8), (n_n, n_p)
    return "\n".join(out)


def build(text: str, name: str) -> str:
    m = re.fullmatch(r"w(\d+)r(\d+)", name)
    if m:  # w<K>r<P>: w<K> plus the fixed base resistor X$91 (VDD -> bank) shortened to P % of its length (re-centres f at code 212)
        text = build(text, f"w{m.group(1)}")
        n = text.count("r_length=12.03860U")
        assert n == 1, n
        return text.replace("r_length=12.03860U", f"r_length={12.0386 * int(m.group(2)) / 100:.5f}U")
    if re.fullmatch(r"w\d+", name):  # w<K>: all 16 bank pass devices at K x W (row45-rerun/variant.py rule), code left as is
        import importlib.util
        spec = importlib.util.spec_from_file_location("variant317", Path(__file__).resolve().parent.parent / "row45-rerun" / "variant.py")
        v317 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v317)
        return v317.double_bank_switches(text, float(name[1:]))
    if name.startswith("ideal"):
        return _ideal(text, int(name[5:]))
    if name.startswith("ctrl"):
        return text  # ctrl<N>: unmodified DUT at code N (code set by gen_knockout.py)
    assert name in VARIANTS, name
    if name in ("nojb", "nojall"):
        text = _zero(text, BANK, 16)
    if name in ("nojd", "nojall"):
        text = _zero(text, DISCH, 1)
    if name == "capx":
        head, tail = text.split(".ENDS", 1)
        text = head + "* knock-out: +200 fF linear on vc (issue #320)\nCXVC \\$24 vss 200f\n.ENDS" + tail
    return text
