"""Sim-only variant of the extracted P3 DUT carrying the issue-#317 changes (the layout is NOT re-extracted here).

row4: the 16 bank pass devices (the only L=0.28U devices) get W x2 with AS/AD/PS/PD re-derived from the extractor's own
rule (area = W x 0.42 um, perimeter = 2 (W + 0.42 um)), so a variant device is what the extractor would emit at 2W.
row5: see ROW5 below (filled in by the comparator change).
"""
import re

SRC_LINE = re.compile(r"^(X\$\d+ .* (?:nfet|pfet)_03v3 L=0\.28U W=)([\d.]+)U AS=([\d.]+)P AD=([\d.]+)P PS=([\d.]+)U PD=([\d.]+)U$")


def fmt(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".")


def double_bank_switches(text: str, k: float = 2.0) -> str:
    out, n = [], 0
    for line in text.split("\n"):
        m = SRC_LINE.match(line)
        if m:
            w, as_, ad, ps, pd = (float(m.group(i)) for i in range(2, 7))
            assert abs(as_ - w * 0.42) < 1e-6 and abs(ps - 2 * (w + 0.42)) < 1e-6, line
            line = f"{m.group(1)}{fmt(w * k)}U AS={fmt(as_ * k)}P AD={fmt(ad * k)}P PS={fmt(2 * (w * k + 0.42))}U PD={fmt(2 * (w * k + 0.42))}U"
            n += 1
        out.append(line)
    assert n == 16, n
    return "\n".join(out)


BUF_N = re.compile(r"^(X\$21 \S+ \S+ \S+ \S+ nfet_03v3 L=)([\d.]+)U W=([\d.]+)U AS=\S+ AD=\S+ PS=\S+ PD=\S+$")
BUF_P = re.compile(r"^(X\$67 \S+ \S+ \S+ \S+ pfet_03v3 L=)([\d.]+)U W=([\d.]+)U AS=\S+ AD=\S+ PS=\S+ PD=\S+$")


def comparator_h_buffer(text: str, wn: float = 1.0, wp: float = 4.0, ln: float = 0.5, lp: float = 0.5) -> str:
    """Row-5 candidates: resize the comparator-H output inverter (X$21 = MBUFN, X$67 = MBUFP in the flat extraction).
    AS/AD/PS/PD are re-derived by the extractor's rule (area = W x 0.42 um, perimeter = 2 (W + 0.42 um))."""
    out, n = [], 0
    for line in text.split("\n"):
        for rx, w, l in ((BUF_N, wn, ln), (BUF_P, wp, lp)):
            m = rx.match(line)
            if m:
                head = m.group(0).split(" L=")[0]
                line = f"{head} L={fmt(l)}U W={fmt(w)}U AS={fmt(w * 0.42)}P AD={fmt(w * 0.42)}P PS={fmt(2 * (w + 0.42))}U PD={fmt(2 * (w + 0.42))}U"
                n += 1
        out.append(line)
    assert n == 2, n
    return "\n".join(out)


DEV = re.compile(r"^(X\$(\d+) \S+ \S+ \S+ \S+ (?:nfet|pfet)_03v3) L=([\d.]+)U W=([\d.]+)U AS=([\d.]+)P AD=([\d.]+)P PS=([\d.]+)U PD=([\d.]+)U$")

# Comparator-H first stage in the flat extraction: pair X$19 (gate = integrator node) / X$20 (gate = reference),
# mirror load X$65 (diode) / X$66, tail = the eight L=1 W=2 fingers X$39..X$46 on the bias node.
PAIR, LOAD, TAIL = (19, 20), (65, 66), tuple(range(39, 47))


def resize(text: str, devs, w: float = None, l: float = None, wk: float = None) -> str:
    """Set W (absolute `w`, or factor `wk` on the present W) and/or L of the listed X$ devices.  AS/AD scale with W; PS/PD keep their
    shared-diffusion count n = P/(W + 0.42 um) (n = 1 shared edge, 2 free), so the result is what the extractor's rule gives."""
    out, n = [], 0
    for line in text.split("\n"):
        m = DEV.match(line)
        if m and int(m.group(2)) in devs:
            w0, as_, ad, ps, pd = (float(m.group(i)) for i in (4, 5, 6, 7, 8))
            w1 = w if w is not None else w0 * (wk if wk is not None else 1.0)
            l1 = l if l is not None else float(m.group(3))
            line = (f"{m.group(1)} L={fmt(l1)}U W={fmt(w1)}U AS={fmt(as_ * w1 / w0)}P AD={fmt(ad * w1 / w0)}P "
                    f"PS={fmt(ps / (w0 + 0.42) * (w1 + 0.42))}U PD={fmt(pd / (w0 + 0.42) * (w1 + 0.42))}U")
            n += 1
        out.append(line)
    assert n == len(devs), (n, devs)
    return "\n".join(out)


def first_stage(text: str, pair_w: float = None, load_l: float = None, tail_k: float = None) -> str:
    """Row-5 first-stage candidates on comparator H: pair W (absolute um), mirror-load L (um), tail W factor (the 8:1 mirror ratio)."""
    if pair_w is not None:
        text = resize(text, PAIR, w=pair_w)
    if load_l is not None:
        text = resize(text, LOAD, l=load_l)
    if tail_k is not None:
        text = resize(text, TAIL, wk=tail_k)
    return text


def build(text: str) -> str:
    """Apply every #317 variant change to the extracted P3 netlist text."""
    return double_bank_switches(text)
