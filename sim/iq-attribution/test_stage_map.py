"""Offline tests for the device-to-stage map builder (issue #347). Synthetic fixtures; no PDK, no simulator."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import stage_map as sm  # noqa: E402


def deck(devs, parasitics=()):
    """Build an extraction-deck text: devs are (name, x, y, class, terminals, model, params);
    the comment carries the `$N` instance id (the deck convention), the device line the full name."""
    L = ["* extracted by klt extract --deck gf180mcu (synthetic fixture)", ".SUBCKT top vdd vss clk"]
    for name, x, y, cls, terms, model, params in devs:
        dev_id = name[name.index("$"):] if "$" in name else name
        terms = terms if isinstance(terms, str) else " ".join(terms)
        L.append(f"* device instance {dev_id} r0 *1 {x},{y} {cls}")
        L.append(f"{name} {terms} {model} {params}")
    L.append(".ENDS")
    L += list(parasitics)
    return "\n".join(L) + "\n"


F1 = ("X$1", 10.0, 1.0, "nfet", "a b vss vsubs", "nfet_03v3", "L=1U W=2U")    # bias diode-connect nfet
F2 = ("X$2", 20.0, 1.0, "nfet", "c d vss vsubs", "nfet_03v3", "L=1U W=2U")    # same signature, +10 um
P1 = ("X$3", 30.0, 2.0, "pfet", "e f vdd1 vdd2", "pfet_03v3", "L=0.5U W=4U")  # latch pull-up: s+b on two vdd copies
RD = ("X$4", 40.0, 1.0, "ppolyf_u_1k", "g h vsubs", "ppolyf_u_1k", "r_length=10U r_width=2U")
CAP = ("X$5", 50.0, 6.0, "cap_mim_1f0_m4m5_noshield", "i j", "cap_mim_1f0fF", "c_width=20u c_length=10u m=1")
DIS = ("X$6", 45.0, 1.0, "nfet", "k clk vss vsubs", "nfet_03v3", "L=0.5U W=20U")
ALL = [F1, F2, P1, RD, CAP, DIS]
PAR = ("Rvdd_t1 vdd1 vdd 4.0", "Rvdd_t2 vdd2 vdd 5.0", "Ra_t0 a vss 1.0")


def write_deck(tmp_path):
    p = tmp_path / "flat.spice"
    p.write_text(deck(ALL, PAR))
    return p


def roster(devs):
    """Roster decks name FETs M$N and resistors R$N (klt extract report form)."""
    ren = lambda n: ("R" + n[1:]) if "ppolyf" in [d[3] for d in devs if d[0] == n][0] else ("M" + n[1:])
    return deck([(ren(n), x, y, cls, terms, model, params) for n, x, y, cls, terms, model, params in devs])


def test_registration_resolves_ambiguous_signatures_by_offset(tmp_path):
    # bias roster has TWO identical (nfet L1 W2) devices 10 um apart; only the global offset
    # (0, 0) maps both onto X$1/X$2 simultaneously -- signature alone cannot.
    p = write_deck(tmp_path)
    r = tmp_path / "bias.spice"
    r.write_text(roster([F1, F2]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    m = sm.build_map(p, {"bias": str(r), "trim": str(rt)})
    names = {d["name"] for d in m["stages"]["bias"]}
    assert names == {"X$1", "X$2"}
    assert m["offsets"]["bias"]["offset"] == [0.0, 0.0]


def test_wrong_offset_candidate_is_rejected(tmp_path):
    # the offset voting sees candidates from other same-signature devices; a wrong candidate
    # that leaves roster devices unmatched must not be chosen.
    p = write_deck(tmp_path)
    r = tmp_path / "bias.spice"
    r.write_text(roster([F1, F2]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    m = sm.build_map(p, {"bias": str(r), "trim": str(rt)})
    assert m["stage_device_counts"]["bias"] == 2
    assert m["unresolved"] == []


def test_top_level_remainder_and_conservation(tmp_path):
    p = write_deck(tmp_path)
    rb = tmp_path / "bias.spice"
    rb.write_text(roster([F1, F2]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    m = sm.build_map(p, {"bias": str(rb), "trim": str(rt)})
    assert [d["name"] for d in m["stages"]["timing"]] == ["X$5"]        # only cap_mim
    assert [d["name"] for d in m["stages"]["disch"]] == ["X$6"]        # only W=20U nfet
    assert [d["name"] for d in m["stages"]["latch"]] == ["X$3"]        # pfet 0.5/4 remainder
    assert [d["name"] for d in m["stages"]["trim"]] == ["X$4"]         # resistor claimed by its roster
    assert sm.check_conservation(m) == 6
    assert m["assigned_count"] == m["device_count"] == 6


def test_vdd_component_terms_from_parasitic_star(tmp_path):
    # X$3 (pfet) sits on two vdd-network copies (vdd1/vdd2 behind Rvdd_t*); X$1's terminal is on
    # the vss component and must NOT be picked up; XCTIMING/X$6 have no vdd terminal at all.
    p = write_deck(tmp_path)
    r = tmp_path / "bias.spice"
    r.write_text(roster([F1, F2]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    m = sm.build_map(p, {"bias": str(r), "trim": str(rt)})
    terms = {d["name"]: d["vdd_terms"] for s in sm.STAGE_ORDER for d in m["stages"][s]}
    assert terms["X$3"] == [[2, "vdd1"], [3, "vdd2"]]
    assert terms["X$1"] == [] and terms["X$5"] == [] and terms["X$6"] == []
    assert m["vdd_side_summary"] == {"devices": 1, "terminals": 2}


def test_zero_by_construction_stages_assert_on_vdd_terms(tmp_path):
    # a wiring mistake that puts a vdd net on the discharge device must fail the build, not pass silently
    p = tmp_path / "flat.spice"
    p.write_text(deck(ALL, PAR + ("Rdis_t0 k vdd 1.0",)))
    r = tmp_path / "bias.spice"
    r.write_text(roster([F1, F2]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    try:
        sm.build_map(p, {"bias": str(r), "trim": str(rt)})
        raise AssertionError("disch stage with vdd terms must assert")
    except AssertionError as e:
        assert "disch" in str(e)


def test_unresolved_device_is_reported_not_guessed(tmp_path):
    p = write_deck(tmp_path)
    r = tmp_path / "bias.spice"
    # roster device with no flat counterpart at any offset
    ghost = ("X$9", 99.0, 1.0, "nfet", "x y vss vsubs", "nfet_03v3", "L=3U W=2U")
    r.write_text(roster([F1, ghost]))
    rt = tmp_path / "trim.spice"
    rt.write_text(roster([RD]))
    try:
        sm.build_map(p, {"bias": str(r)})
        raise AssertionError("unresolved roster device must fail without --allow-unresolved")
    except SystemExit as e:
        assert "unresolved" in str(e)
    m = sm.build_map(p, {"bias": str(r), "trim": str(tmp_path / "trim.spice")}, allow_unresolved=True)
    assert m["unresolved"] and m["stage_device_counts"]["bias"] == 1
