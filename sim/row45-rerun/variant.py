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


def build(text: str) -> str:
    """Apply every #317 variant change to the extracted P3 netlist text."""
    return double_bank_switches(text)
