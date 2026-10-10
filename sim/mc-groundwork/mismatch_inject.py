#!/usr/bin/env python3
"""DR-0022 section 4 mismatch injector (issue #135).  Offline, text-only.

Pure text transformation: rewrites the ``m=1`` multiplier on every
``ppolyf_u_1k`` / ``cap_mim_1f0fF`` X card of a DUT text and adds the
``.param`` draw lines.  Nothing here runs a simulator, reads the PDK, or
writes to design/ or results/.  It has produced no evidence; the sigma
coefficients are DR-0022's flagged engineering assumptions (no public
source), not tuned values.

    resistor:   m='1/(1+d_<inst>)'      capacitor:  m='(1+d_<inst>)'
    d_<inst> = sw_stat_mismatch * agauss(0, mm_scale*A_x/sqrt(W*L)/100, 1)

so d_<inst> is identically 0 when sw_stat_mismatch=0.  W, L in um, A_x in
%.um.  With a LITERAL mm_scale of 0 the baseline is kept verbatim: cards are
not rewritten, only the .param lines (all d_<inst> = 0) are added.

The generator fails loudly (UnmappedCardError) on any covered-model X card
that is neither mapped nor on the explicit exclusion list.
"""
import math
import re

A_R = 1.0  # %.um, DR-0022 section 2, engineering assumption
A_C = 1.0  # %.um, DR-0022 section 2, engineering assumption

RES_MODEL = "ppolyf_u_1k"
CAP_MODEL = "cap_mim_1f0fF"
# model -> (kind, coefficient, W param, L param)
MODELS = {
    RES_MODEL: ("res", A_R, "r_width", "r_length"),
    CAP_MODEL: ("cap", A_C, "c_width", "c_length"),
}
# Instances (without the X prefix, lower case) that are covered models but
# deliberately not injected.  DR-0022 names none: empty by default.
DEFAULT_EXCLUDE = frozenset()

_NUM = re.compile(r"^([0-9.]+(?:e[-+]?[0-9]+)?)(meg|mil|[tgkmunpfa])?$", re.I)
_SCALE = {"t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3, "m": 1e-3, "u": 1e-6,
          "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18}


class UnmappedCardError(ValueError):
    """A covered-model X card is neither mapped nor excluded."""


def _spice_um(tok: str) -> float:
    """SPICE length token (e.g. '17.198u', '2u') -> micrometres."""
    m = _NUM.match(tok.strip())
    if not m:
        raise ValueError(f"cannot parse length {tok!r}")
    val = float(m.group(1)) * _SCALE.get((m.group(2) or "").lower(), 1.0)
    return val * 1e6


def _parse_card(line: str):
    """Return (inst, model, params dict) for an X card, else None."""
    toks = line.split()
    if not toks or not toks[0][:1] in "xX" or line.lstrip().startswith("*"):
        return None
    model = next((t for t in toks[1:] if t in MODELS), None)
    if model is None:
        return None
    params = {}
    for t in toks[toks.index(model) + 1:]:
        if "=" in t:
            k, v = t.split("=", 1)
            params[k.lower()] = v
    return toks[0], model, params


def inject(dut_text: str, mm_scale=None, exclude=DEFAULT_EXCLUDE):
    """Return (text, manifest).

    mm_scale: None -> symbolic (netlist ``.param mm_scale`` supplied by the
    bench, default line added as 1); a number -> literal baked into sigmas;
    a literal 0 -> baseline cards kept verbatim.
    """
    literal_zero = mm_scale is not None and float(mm_scale) == 0.0
    scale_expr = "mm_scale" if mm_scale is None else repr(float(mm_scale))
    exclude = {e.lower() for e in exclude}
    out, params, manifest = [], [], []
    seen = set()
    for line in dut_text.splitlines():
        card = _parse_card(line)
        if card is None:
            out.append(line)
            continue
        name, model, p = card
        inst = name[1:].lower()
        if inst in exclude:
            out.append(line)
            continue
        kind, coeff, wk, lk = MODELS[model]
        if line.lstrip().startswith("+") or wk not in p or lk not in p:
            raise UnmappedCardError(f"{name}: cannot read {wk}/{lk}")
        if p.get("m") != "1":
            raise UnmappedCardError(f"{name}: expected m=1, found m={p.get('m')}")
        if inst in seen:
            raise UnmappedCardError(f"{name}: duplicate instance")
        seen.add(inst)
        w, l = _spice_um(p[wk]), _spice_um(p[lk])
        sigma = coeff / math.sqrt(w * l) / 100.0  # relative, at mm_scale=1
        d = f"d_{inst}"
        expr = f"1/(1+{d})" if kind == "res" else f"(1+{d})"
        if literal_zero:
            out.append(line)
            sigma_expr = "0"
        else:
            out.append(re.sub(r"\bm=1\b", f"m='{expr}'", line))
            sigma_expr = f"{scale_expr}*{sigma!r}"
        params.append(f".param {d}='sw_stat_mismatch*agauss(0,{sigma_expr},1)'"
                      if not literal_zero else f".param {d}=0")
        manifest.append({"instance": name, "param": d, "model": model,
                         "kind": kind, "w_um": w, "l_um": l,
                         "sigma_rel_at_unit_scale": sigma,
                         "mm_scale": "mm_scale" if mm_scale is None else float(mm_scale),
                         "m_expr": "1" if literal_zero else expr})
    header = ["* DR-0022 section 4 injected mismatch (flagged assumption; no evidence)"]
    if mm_scale is None:
        header.append(".param mm_scale=1")
    return "\n".join(header + params + out), manifest
