"""Offline tests for mismatch_inject (issue #135). Pure text; SYNTHETIC
fixtures, no simulator/PDK. Not evidence."""
import hashlib
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mismatch_inject as mi  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PVT = ROOT / "design" / "netlist" / "pvt_tb.spice"

FIXTURE = """\
** expanding   symbol:  rcosc_top.sym
XRA a b vss ppolyf_u_1k r_width=2u r_length=100u m=1
XR0 c1 c2 vss ppolyf_u_1k r_width=2u r_length=0.7482u m=1
XCT vss vc cap_mim_1f0fF c_width=20u c_length=10u m=1
XM1 d g s b nfet_03v3 W=1u L=1u m=1
* XCOMMENT x vss ppolyf_u_1k r_width=2u r_length=1u m=1"""


def test_exact_m_expressions_and_other_cards_untouched():
    text, man = mi.inject(FIXTURE)
    assert "XRA a b vss ppolyf_u_1k r_width=2u r_length=100u m='1/(1+d_ra)'" in text
    assert "XR0 c1 c2 vss ppolyf_u_1k r_width=2u r_length=0.7482u m='1/(1+d_r0)'" in text
    assert "XCT vss vc cap_mim_1f0fF c_width=20u c_length=10u m='(1+d_ct)'" in text
    assert "XM1 d g s b nfet_03v3 W=1u L=1u m=1" in text
    assert "* XCOMMENT x vss ppolyf_u_1k r_width=2u r_length=1u m=1" in text
    assert [m["instance"] for m in man] == ["XRA", "XR0", "XCT"]


def test_sigma_is_pelgrom_and_gated_by_sw_stat_mismatch():
    text, man = mi.inject(FIXTURE)
    by = {m["instance"]: m for m in man}
    assert by["XR0"]["sigma_rel_at_unit_scale"] == pytest.approx(0.01 / math.sqrt(2 * 0.7482))
    assert by["XR0"]["sigma_rel_at_unit_scale"] == pytest.approx(0.0082, abs=5e-5)
    assert by["XCT"]["sigma_rel_at_unit_scale"] == pytest.approx(0.01 / math.sqrt(200))
    for m in man:
        line = next(l for l in text.splitlines() if l.startswith(f".param {m['param']}="))
        assert "sw_stat_mismatch*agauss(0," in line  # zero when switch is 0
        assert "mm_scale*" in line
    assert ".param mm_scale=1" in text


def test_numeric_scale_baked_in():
    text, man = mi.inject(FIXTURE, mm_scale=3)
    assert "mm_scale" not in text.replace("sw_stat_mismatch", "")
    assert all(m["mm_scale"] == 3.0 for m in man)
    assert "3.0*" in text


def test_literal_zero_scale_equals_baseline_modulo_param_lines():
    text, man = mi.inject(FIXTURE, mm_scale=0)
    kept = [l for l in text.splitlines() if not l.startswith((".param", "* DR-0022"))]
    assert kept == FIXTURE.splitlines()
    params = [l for l in text.splitlines() if l.startswith(".param")]
    assert len(params) == len(man) == 3
    assert all(re.fullmatch(r"\.param d_\w+=0", l) for l in params)


@pytest.mark.parametrize("bad", [
    "XRX a b vss ppolyf_u_1k r_width=2u r_length=1u m=2",
    "XRX a b vss ppolyf_u_1k r_width=2u m=1",
    "XCX a b cap_mim_1f0fF c_width=2u m=1",
])
def test_unmappable_card_fails_loudly(bad):
    with pytest.raises(mi.UnmappedCardError):
        mi.inject(bad)


def test_exclusion_list_skips_card_and_manifest():
    text, man = mi.inject(FIXTURE, exclude={"ra"})
    assert "XRA a b vss ppolyf_u_1k r_width=2u r_length=100u m=1" in text
    assert "XRA" not in [m["instance"] for m in man]
    assert mi.DEFAULT_EXCLUDE == frozenset()


def test_duplicate_instance_raises():
    with pytest.raises(mi.UnmappedCardError):
        mi.inject(FIXTURE + "\nXRA a b vss ppolyf_u_1k r_width=2u r_length=1u m=1")


def test_manifest_lists_every_injected_instance_sigma_scale():
    _, man = mi.inject(FIXTURE, mm_scale=3)
    for m in man:
        assert {"instance", "param", "kind", "sigma_rel_at_unit_scale", "mm_scale"} <= set(m)


def _dut_block():
    lines = PVT.read_text().splitlines()
    s = next(i for i, l in enumerate(lines) if "expanding" in l and "rcosc_top.sym" in l)
    e = next(i for i, l in enumerate(lines) if l.strip() == ".end")
    return "\n".join(lines[s:e])


def test_real_netlist_full_coverage_and_dr0022_instances():
    block = _dut_block()
    text, man = mi.inject(block)
    got = {m["instance"] for m in man}
    assert got == {"XCTIMING", "XRBA", "XRBB", "XRBC", "XRZ", "XRFIX",
                   *{f"XR{i}" for i in range(8)}}
    # no covered-model card left unrewritten
    for l in text.splitlines():
        if re.search(r"\b(ppolyf_u_1k|cap_mim_1f0fF)\b", l) and not l.startswith("*"):
            assert "m='" in l
    sig = {m["instance"]: m["sigma_rel_at_unit_scale"] * 100 for m in man}
    assert sig["XR0"] == pytest.approx(0.82, abs=0.01)
    assert sig["XR7"] == pytest.approx(0.07, abs=0.01)
    assert sig["XRFIX"] == pytest.approx(0.17, abs=0.01)
    assert sig["XCTIMING"] == pytest.approx(0.07, abs=0.01)


def test_committed_netlist_not_modified_by_injection():
    before = hashlib.sha256(PVT.read_bytes()).hexdigest()
    mi.inject(_dut_block())
    assert hashlib.sha256(PVT.read_bytes()).hexdigest() == before
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "--",
                           "design"], check=False)
    assert diff.returncode == 0
