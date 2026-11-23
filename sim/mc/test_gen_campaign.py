"""Offline tests for the item-6 campaign generator (issue #202).  Synthetic:
builds benches in memory; runs no simulator and writes nothing under sim/."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_campaign as gc  # noqa: E402


def test_bench_injects_every_ladder_resistor_and_the_mim():
    text, manifest = gc.bench("t", gc.HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch")
    assert len(manifest) == 14  # 13 ppolyf_u_1k + the timing MiM in the P3 netlist
    assert text.count("m='1/(1+d_") == 13 and text.count("m='(1+d_") == 1
    assert "$" not in "".join(re.findall(r"d_[^=\s)']+", text))  # param names are ngspice-safe


def test_no_two_argument_minimum_maximum_left_in_the_control_block():
    # ngspice minimum()/maximum() reduce ONE vector; two-argument use silently
    # returned a wrong margin in the first validation run
    text, _ = gc.bench("t", gc.HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch")
    assert "minimum(" not in text and "maximum(" not in text


def test_every_control_line_fits_ngspice_line_buffer():
    text, _ = gc.bench("t", gc.HDR.format(mm=1, sc=1, extra=""), "sw_stat_mismatch", fixed=True)
    ctl = text.split(".control", 1)[1]
    assert max(len(l) for l in ctl.splitlines()) < 300


def test_requests_are_sized_for_the_fleet_job_ceiling():
    r = gc.request("tb.spice", "tt", gc.N_MAIN)
    assert r["monte_carlo"] == {"n": 500, "seed": 20261008, "vary": "mismatch"}
    # klt sim bound = timeout_s x units + 120 must stay under the 3600 s fleet ceiling
    assert r["options"]["timeout_s"] * 25 + 120 <= 3600


def test_limits_are_the_ratified_rows_and_dr0019_targets():
    assert gc.ROW4 == (-2.9, 2.0) and gc.ROW5 == (-10.8, 8.8)
    assert gc.S1_RESID_MAX == 0.157 + 0.300 + 0.300
    lim = gc.limits(500)["measurements"]
    assert gc.limits(500)["min_samples"] == 500 and gc.limits(500)["confidence"] == 0.95
    assert all(v["target_yield"] == 0.99 for v in lim.values())
    assert set(lim) == {"s1_resid_abs_pct", "s1_headroom", "s2_margin_pct", "s3_margin_pct"}


def test_sensitivity_pair_uses_a_separate_gate_and_fixed_probes():
    t1, _ = gc.bench("s", gc.HDR.format(mm=0, sc=1, extra=" sw_inj=1"), "sw_inj", fixed=True)
    assert "sw_stat_mismatch=0" in t1 and ".param d__87='sw_inj*agauss(" in t1
    assert "set v_st127" in t1
    names = {m["name"] for m in gc.measurements(True)}
    assert {"step_0x7f_0x80_hz", "step_0x7e_0x7f_hz"} <= names
    assert not {"step_0x7f_0x80_hz"} & {m["name"] for m in gc.measurements(False)}


def test_s2_uses_only_27c_points_and_s3_all_nine():
    assert [p[0] for p in gc.S2_POINTS] == ["27_30", "27_33", "27_36"]
    assert len(gc.POINTS) == 9


def test_sensitivity_scale_is_baked_in_not_overridden_by_the_injector_default():
    # regression: the injector's own `.param mm_scale=1` line overrode a bench-header
    # mm_scale, so the first "10x" arm ran at 1x and the control measured nothing
    t10, _ = gc.bench("s10", gc.HDR.format(mm=0, sc=10, extra=" sw_inj=1"), "sw_inj", True, 10.0)
    t1, _ = gc.bench("s1", gc.HDR.format(mm=0, sc=1, extra=" sw_inj=1"), "sw_inj", True, 1.0)
    assert "agauss(0,10.0*" in t10 and "agauss(0,1.0*" in t1
    assert ".param mm_scale=1\n" not in t10


def test_default_dut_regenerates_the_committed_inputs_byte_identically(tmp_path):
    # issue #236: --dut/--out must not change what the default campaign writes
    gc.main(["--out", str(tmp_path)])
    here = Path(gc.__file__).parent
    for f in sorted(tmp_path.iterdir()):
        assert f.read_text() == (here / f.name).read_text(), f.name
    assert len(list(tmp_path.iterdir())) == 12 * 2 + 2


def test_dut_option_swaps_the_netlist_and_writes_only_to_out(tmp_path):
    here = Path(gc.__file__).parent
    dut = here.parent / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"
    before = {f.name: f.read_text() for f in here.glob("tb_*.spice")}
    gc.main(["--dut", str(dut), "--out", str(tmp_path)])
    assert {f.name: f.read_text() for f in here.glob("tb_*.spice")} == before
    man = json.loads((tmp_path / "mismatch-manifest.json").read_text())
    assert man["source"] == "sim/cmph-fix/rcosc_top_p3_cmphfix.spice"
    import hashlib
    assert man["source_sha256"] == hashlib.sha256(dut.read_bytes()).hexdigest()
    assert "rcosc_top_p3_cmphfix.spice" in (tmp_path / "tb_main_tt.spice").read_text().splitlines()[0]
    assert (tmp_path / "tb_main_tt.spice").read_text() != (here / "tb_main_tt.spice").read_text()


# ---- issue #461: seeded-defect controls, pilot floor, finer-timing arms -------------------

PILOT_DUT = Path(gc.__file__).parent.parent / "row45-rerun" / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice"


def _pilot(tmp_path, n=40):
    gc.main(["--dut", str(PILOT_DUT), "--out", str(tmp_path), "--pilot", str(n)])
    return tmp_path


def test_default_campaign_is_unchanged_by_the_pilot_machinery(tmp_path):
    # no --pilot: no control cases, no pilot limits, no defects ledger
    gc.main(["--out", str(tmp_path)])
    names = {f.name for f in tmp_path.iterdir()}
    assert not any(n.startswith(("tb_ctrl", "request_ctrl")) for n in names)
    assert "limits_pilot.json" not in names and "defects.json" not in names


def test_defect_cards_are_the_only_difference_from_the_nominal_deck(tmp_path):
    d = _pilot(tmp_path)
    main = (d / "tb_main_tt.spice").read_text().splitlines()
    r2 = (d / "tb_ctrlr2_tt.spice").read_text().splitlines()
    r45 = (d / "tb_ctrlr45_tt.spice").read_text().splitlines()
    diff2 = [(a, b) for a, b in zip(main, r2) if a != b]
    # title line, the one seeded card, and that card's own matching sigma (the injector derives it
    # from the drawn W x L; the draw identity d__91 and its seed are unchanged)
    assert len(main) == len(r2) and len(diff2) == 3
    card = [x for x in diff2 if x[0].startswith("X$91")][0]
    assert "r_length=12.03860U" in card[0] and "r_length=12.03860U" not in card[1]
    assert [x for x in diff2 if x[0].startswith(".param d__91=")]
    extra = [l for l in r45 if l not in main]
    assert [l for l in extra if l.startswith("RDEF_LEAK")] == [f"RDEF_LEAK vdd {gc.DEFECTS['leak']['node']} 1e+06"]
    assert len(r45) == len(main) + 1 and len(extra) == 2  # the title line + the one added card


def test_control_probes_and_grading_expressions_match_the_nominal(tmp_path):
    # a measurement stuck at its nominal value must make the control miss: the
    # control block (probes, margins, harvested variables) is byte-identical
    d = _pilot(tmp_path)
    ctl = lambda n: (d / n).read_text().split(".control", 1)[1]
    assert ctl("tb_main_tt.spice") == ctl("tb_ctrlr2_tt.spice") == ctl("tb_ctrlr45_tt.spice")
    mm = lambda n: json.loads((d / n).read_text())["measurements"]
    assert mm("request_main_tt.json") == mm("request_ctrlr2_tt.json") == mm("request_ctrlr45_tt.json")


def test_control_requests_reuse_the_nominal_seed_and_draw_count(tmp_path):
    d = _pilot(tmp_path, 40)
    for p in ("tt", "ff", "ss"):
        ref = json.loads((d / f"request_main_{p}.json").read_text())
        assert ref["monte_carlo"] == {"n": 40, "seed": gc.SEED, "vary": "mismatch"}
        for c in ("ctrlr2", "ctrlr45", "inflated"):
            r = json.loads((d / f"request_{c}_{p}.json").read_text())
            assert r["monte_carlo"] == ref["monte_carlo"] and r["corners"] == ref["corners"]
        # header (the mismatch gate/scale parameters) of the defect decks equals main's
        hdr = lambda n: [l for l in (d / n).read_text().splitlines() if l.startswith(".param sw_stat_global")]
        assert hdr(f"tb_main_{p}.spice") == hdr(f"tb_ctrlr2_{p}.spice") == hdr(f"tb_ctrlr45_{p}.spice")


def test_pilot_floor_is_pilot_only_and_the_production_floor_is_untouched(tmp_path):
    d = _pilot(tmp_path, 40)
    pilot, prod = (json.loads((d / f).read_text()) for f in ("limits_pilot.json", "limits_main.json"))
    assert pilot["min_samples"] == 40 and prod["min_samples"] == 500
    strip = lambda x: {k: v for k, v in x.items() if k != "min_samples"}
    assert strip(pilot) == strip(prod)  # same limits, target yield 0.99, confidence 0.95


def test_the_3x_and_zero_controls_stay_in_the_pilot(tmp_path):
    d = _pilot(tmp_path)
    for p in ("tt", "ff", "ss"):
        assert "sw_stat_mismatch=3" in (d / f"tb_inflated_{p}.spice").read_text()
        assert "sw_stat_mismatch=0" in (d / f"tb_zero_{p}.spice").read_text()


def test_fine_timing_arms_change_only_the_transient_step(tmp_path):
    d = _pilot(tmp_path)
    for nm in ("sens1", "sens10", "senszero"):
        coarse = (d / f"tb_{nm}_tt.spice").read_text()
        fine = (d / f"tb_{nm}fine_tt.spice").read_text()
        assert coarse.count("tran 200p 1200n") == fine.count("tran 50p 1200n") > 0
        assert fine.replace("tran 50p", "tran 200p").splitlines()[1:] == coarse.splitlines()[1:]
        rf = json.loads((d / f"request_{nm}fine_tt.json").read_text())
        assert rf["options"]["timeout_s"] * 7 + 120 <= 3600


def test_defect_ledger_names_component_and_observables(tmp_path):
    led = json.loads((_pilot(tmp_path) / "defects.json").read_text())
    assert led["trimbank"]["inst"] == "X$91" and led["trimbank"]["observables"] == ["s1_resid_abs_pct", "s1_headroom"]
    assert led["leak"]["observables"] == ["s2_margin_pct", "s3_margin_pct"]


def test_apply_defect_fails_loudly_on_a_missing_target():
    import pytest
    with pytest.raises(ValueError):
        gc.apply_defect(".SUBCKT rcosc_top vdd vss\n.ENDS rcosc_top", dict(gc.DEFECTS["trimbank"]))
    with pytest.raises(ValueError):
        gc.apply_defect(".SUBCKT rcosc_top vdd vss\n.ENDS rcosc_top", dict(gc.DEFECTS["leak"]))
