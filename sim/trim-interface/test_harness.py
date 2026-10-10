"""Offline tests for sim/trim-interface (issue #106).  Every waveform here is a
SYNTHETIC FIXTURE built in this file; nothing is measured evidence and no
simulator, klt, or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/trim-interface/test_harness.py
"""
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


prepare = _load("ti_prepare_t", "prepare.py")
analyze = _load("ti_analyze_t", "analyze.py")
P = analyze.Params()
VDD = 3.3
N = 101


@pytest.fixture
def no_sim(monkeypatch):
    """Offline guard: only `git` (revision lookup) may be spawned."""
    real = subprocess.run

    def guard(cmd, *a, **k):
        if not (isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git"):
            raise AssertionError(f"offline test must not run subprocesses: {cmd}")
        return real(cmd, *a, **k)
    monkeypatch.setattr(subprocess, "run", guard)


# ------------------------------------------------------------ fixtures -----

def sweep(s_of=lambda f: f, tb_of=lambda f: 1 - f, iin_of=lambda f: 0.0, vdd=VDD, mfrac=0.5,
          g0=1e-5, g1=1e-4):
    """SYNTHETIC sweep.  s_of/tb_of take x/VDD; tb_of returns a fraction of VDD;
    iin_of returns the current INTO the DUT (A); i(VTIN) is its negative."""
    dv = vdd - mfrac * vdd
    x, tb, ip, iin = [], [], [], []
    for k in range(N):
        f = k / 100
        x.append(f * vdd)
        tb.append(tb_of(f) * vdd)
        ip.append(-(g0 + (g1 - g0) * s_of(f)) * dv)  # I_into_p = -I(VP)
        iin.append(-iin_of(f))
    return x, tb, ip, iin


def ramp(lo, hi, flo=0.1, fhi=0.9):
    """s(f): linear through (lo, flo) and (hi, fhi), clipped to [0, 1]."""
    return lambda f: min(1.0, max(0.0, flo + (fhi - flo) * (f - lo) / (hi - lo)))


def pw(*pts):
    """Piecewise-linear s(f) through (f, s) points (must start at f=0, end at f=1)."""
    def fn(f):
        for (f0, s0), (f1, s1) in zip(pts, pts[1:]):
            if f0 <= f <= f1:
                return s0 + (s1 - s0) * (f - f0) / (f1 - f0)
        raise ValueError(f)
    return fn


def run(**kw):
    vdd = kw.get("vdd", VDD)
    mfrac = kw.get("mfrac", 0.5)
    return analyze.analyse_sweep(*sweep(**kw), vdd, mfrac, P)


def fails(match, **kw):
    with pytest.raises(analyze.AnalysisError, match=match):
        run(**kw)


# ------------------------------------------------------------- analyzer ----

def test_analytic_curve_bounds_and_trip():
    r = run()  # s = x, tb = VDD (1 - x)
    assert r["raw_low_frac"] == pytest.approx(0.10, abs=1e-9)
    assert r["raw_high_frac"] == pytest.approx(0.90, abs=1e-9)
    assert r["low_bound_frac"] == pytest.approx(0.05, abs=1e-9)
    assert r["high_bound_frac"] == pytest.approx(0.95, abs=1e-9)
    assert r["low_bound_v"] == pytest.approx(0.05 * VDD) and r["high_bound_v"] == pytest.approx(0.95 * VDD)
    assert r["inverter_trip_frac"] == pytest.approx(0.50, abs=1e-9)
    assert r["g0_s"] == pytest.approx(1e-5) and r["g1_s"] == pytest.approx(1e-4)
    assert r["status"] == "OK" and r["valid"]


def test_interpolated_crossings_between_samples():
    r = run(s_of=ramp(0.1234, 0.7777), tb_of=lambda f: 1 - min(1, max(0, (f - 0.2) / 0.6)))
    assert r["raw_low_frac"] == pytest.approx(0.1234, abs=1e-9)
    assert r["raw_high_frac"] == pytest.approx(0.7777, abs=1e-9)
    assert r["low_bound_frac"] == pytest.approx(0.1234 - 0.05, abs=1e-9)
    assert r["high_bound_frac"] == pytest.approx(0.7777 + 0.05, abs=1e-9)
    # tb crosses 0.5 VDD at f = 0.5 inside a segment boundary-free interval
    r2 = run(tb_of=lambda f: 1 - min(1, max(0, (f - 0.2335) / 0.5)))
    assert r2["inverter_trip_frac"] == pytest.approx(0.4835, abs=1e-9)


def test_inverter_trip_is_not_the_functional_bound():
    r = run(s_of=ramp(0.6, 0.9), tb_of=lambda f: 1 - f)
    assert r["inverter_trip_frac"] == pytest.approx(0.5, abs=1e-9)
    assert r["raw_low_frac"] == pytest.approx(0.6, abs=1e-9)  # bank selection, not the trip point


def test_margins_clamp_to_rails():
    r = run(s_of=pw((0, 0), (0.03, 0.1), (0.97, 0.9), (1, 1)))
    assert r["raw_low_frac"] == pytest.approx(0.03, abs=1e-9) and r["low_bound_v"] == 0.0
    assert r["raw_high_frac"] == pytest.approx(0.97, abs=1e-9) and r["high_bound_v"] == pytest.approx(VDD)


def test_configurable_screens_are_used():
    p = analyze.Params(sel_low=0.2, sel_high=0.8, margin_frac=0.0)
    r = analyze.analyse_sweep(*sweep(), VDD, 0.5, p)
    assert r["raw_low_frac"] == pytest.approx(0.2, abs=1e-9) and r["high_bound_frac"] == pytest.approx(0.8, abs=1e-9)


def test_supply_scaling():
    for v in (3.0, 3.6):
        r = run(vdd=v)
        assert r["low_bound_v"] == pytest.approx(0.05 * v) and r["inverter_trip_v"] == pytest.approx(0.5 * v)


def test_signed_input_current_and_max_abs():
    amps = {0.0: -2e-9, 0.25: 0.0, 0.5: 3e-12, 0.75: -7e-9, 1.0: 5e-9}

    def cur(f):
        return amps[round(f, 2)] if round(f, 2) in amps else 0.0
    r = run(iin_of=cur)
    assert r["i_in_000_a"] == pytest.approx(-2e-9)  # -I(VTIN): negative = out of the DUT
    assert r["i_in_025_a"] == 0.0 and r["abs_i_in_025_a"] == 0.0
    assert r["i_in_050_a"] == pytest.approx(3e-12)
    assert r["i_in_075_a"] == pytest.approx(-7e-9) and r["abs_i_in_075_a"] == pytest.approx(7e-9)
    assert r["i_in_100_a"] == pytest.approx(5e-9)
    assert r["max_abs_input_current_a"] == pytest.approx(7e-9)
    assert r["max_abs_input_current_bias_frac"] == 0.75


def test_current_sign_orientation_from_raw_source_current():
    x, tb, ip, iin = sweep()
    iin[100] = -4e-9  # i(VTIN) negative => current flows INTO the DUT
    r = analyze.analyse_sweep(x, tb, ip, iin, VDD, 0.5, P)
    assert r["i_in_100_a"] == pytest.approx(4e-9)


def test_all_zero_current_is_reported_not_invented():
    r = run()
    assert r["max_abs_input_current_a"] == 0.0 and all(r[f"i_in_{k}_a"] == 0.0 for k in ("000", "025", "050", "075", "100"))


def test_flat_endpoint_conductance_invalid():
    fails("unresolved", g0=1e-5, g1=1e-5)
    fails("unresolved", g0=1e-5, g1=1e-5 + 1e-13)        # below the absolute floor
    fails("unresolved", g0=1e-4, g1=1e-4 * (1 + 1e-7))   # below the relative floor
    fails("unresolved", g0=1e-4, g1=1e-5)                # negative separation


def test_missing_or_multiple_tb_crossings():
    fails("0 times", tb_of=lambda f: 0.9)
    fails("3 times", tb_of=lambda f: 0.5 + 0.4 * math.sin(f * 3 * math.pi))
    fails("0 times", tb_of=lambda f: 0.9 - 0.2 * f)  # stays above 0.5 VDD


def test_unresolved_selection_crossings():
    wiggle = {10: 0.105, 11: 0.095, 12: 0.12}  # dips back under 0.10 within the 0.01 tolerance

    def noisy(f):
        return wiggle.get(int(round(f * 100)), f)
    fails("sel_low.*crossed", s_of=noisy)


def test_nonmonotonic_selection():
    fails("nonmonotone", s_of=lambda f: f - (0.2 if 0.4 < f < 0.5 else 0.0))
    # a dip within the 0.01 tolerance is not rejected on that ground
    run(s_of=lambda f: f - (0.008 if 0.4 < f < 0.5 else 0.0))


def test_out_of_order_missing_or_duplicate_samples():
    x, tb, ip, iin = sweep()
    xs = list(x)
    xs[40], xs[41] = xs[41], xs[40]
    w = {"variables": [{"name": n} for n in ("v-sweep", "v(xbank.tb3)", "i(vp)", "i(vtin)")],
         "points": [[a, b, c, d] for a, b, c, d in zip(xs, tb, ip, iin)]}
    with pytest.raises(analyze.AnalysisError, match="strictly increasing"):
        analyze.parse_sweep(w, 3)
    w["points"][41][0] = w["points"][40][0]
    with pytest.raises(analyze.AnalysisError, match="strictly increasing"):
        analyze.parse_sweep(w, 3)
    with pytest.raises(analyze.AnalysisError, match="expected 101 sweep points"):
        analyze.analyse_sweep(x[:-1], tb[:-1], ip[:-1], iin[:-1], VDD, 0.5, P)
    with pytest.raises(analyze.AnalysisError, match="grid"):  # last sample short of the rail
        analyze.analyse_sweep(x[:-1] + [x[-1] * 0.9], tb, ip, iin, VDD, 0.5, P)


def test_nonfinite_and_malformed_waveforms():
    x, tb, ip, iin = sweep()
    names = [{"name": n} for n in ("v-sweep", "v(xbank.tb3)", "i(vp)", "i(vtin)")]
    pts = [[a, b, c, d] for a, b, c, d in zip(x, tb, ip, iin)]
    for bad in (float("nan"), float("inf"), "x"):
        q = [list(r) for r in pts]
        q[10][3] = bad
        with pytest.raises(analyze.AnalysisError, match="non-"):
            analyze.parse_sweep({"variables": names, "points": q}, 3)
    with pytest.raises(analyze.AnalysisError, match="exactly one"):
        analyze.parse_sweep({"variables": names[:3], "points": [r[:3] for r in pts]}, 3)
    with pytest.raises(analyze.AnalysisError, match="exactly one"):
        analyze.parse_sweep({"variables": names, "points": pts}, 5)  # wrong pin's tb
    with pytest.raises(analyze.AnalysisError):
        analyze.parse_sweep({"variables": names}, 3)


# ------------------------------------------------------------ aggregation --

EXP = prepare.all_cases()


def fake_rows(low=0.1, high=0.9, cur=1e-9, valid=True):
    rows = []
    for c in EXP:
        rows.append({"id": c["id"], "tag": c["tag"], "vdd_v": c["vdd_v"], "status": "OK", "valid": valid,
                     "low_bound_v": low * c["vdd_v"], "high_bound_v": high * c["vdd_v"],
                     "low_bound_frac": low, "high_bound_frac": high,
                     "max_abs_input_current_a": cur, "max_abs_input_current_bias_frac": 1.0})
    return rows


def test_expected_matrix_is_1296():
    assert len(EXP) == 1296 and len({c["id"] for c in EXP}) == 1296
    assert {c["pin"] for c in EXP} == set(range(8)) and {c["background"] for c in EXP} == {0, 1}
    assert {c["m_frac"] for c in EXP} == {0.25, 0.5, 0.75}


def test_limiting_cases_and_per_supply_separation():
    rows = fake_rows()
    by = {r["id"]: r for r in rows}
    lo = prepare.case_id("ss", -40.0, 3.0, 5, 1, 0.25)
    hi = prepare.case_id("ff", 85.0, 3.0, 2, 0, 0.75)
    cu = prepare.case_id("ff", 85.0, 3.6, 7, 0, 0.50)
    by[lo] |= {"low_bound_v": 0.02 * 3.0, "low_bound_frac": 0.02}
    by[hi] |= {"high_bound_v": 0.97 * 3.0, "high_bound_frac": 0.97}
    by[cu] |= {"max_abs_input_current_a": 4e-8}
    agg = {a["vdd_v"]: a for a in analyze.aggregate(rows, EXP)}
    assert all(a["complete"] for a in agg.values()) and set(agg) == {3.0, 3.3, 3.6}
    assert agg[3.0]["min_low_bound_case"] == lo and agg[3.0]["min_low_bound_frac"] == 0.02
    assert agg[3.0]["max_high_bound_case"] == hi
    assert agg[3.3]["min_low_bound_frac"] == 0.1 and agg[3.6]["min_low_bound_frac"] == 0.1  # not contaminated
    assert agg[3.6]["max_abs_input_current_case"] == cu and agg[3.6]["max_abs_input_current_a"] == 4e-8
    assert agg[3.0]["max_abs_input_current_a"] == 1e-9
    assert "PASS" not in agg[3.0]["verdict"]


def test_missing_duplicate_failed_and_unexpected_make_incomplete():
    base = fake_rows()
    miss = [r for r in base if r["id"] != EXP[0]["id"]]
    a = {x["vdd_v"]: x for x in analyze.aggregate(miss, EXP)}
    assert not a[EXP[0]["vdd_v"]]["complete"] and a[EXP[0]["vdd_v"]]["missing"] == [EXP[0]["id"]]
    assert a[EXP[0]["vdd_v"]]["verdict"] == "INCOMPLETE" and a[3.6]["complete"]
    dup = base + [dict(base[500])]
    a = {x["vdd_v"]: x for x in analyze.aggregate(dup, EXP)}
    assert a[base[500]["vdd_v"]]["duplicate"] == [base[500]["id"]] and not a[base[500]["vdd_v"]]["complete"]
    bad = fake_rows()
    bad[700] |= {"status": "FAIL: nonmonotone", "valid": False}
    a = {x["vdd_v"]: x for x in analyze.aggregate(bad, EXP)}
    assert not a[bad[700]["vdd_v"]]["complete"] and a[bad[700]["vdd_v"]]["failed"] == [bad[700]["id"]]
    extra = base + [{"id": "zz_bogus", "vdd_v": 3.3, "status": "OK", "valid": True}]
    a = {x["vdd_v"]: x for x in analyze.aggregate(extra, EXP)}
    assert not a[3.3]["complete"] and a[3.3]["unexpected"] == ["zz_bogus"]
    unattributed = base + [{"id": None, "vdd_v": 3.0, "status": "FAIL: report status 'error'", "valid": False}]
    a = {x["vdd_v"]: x for x in analyze.aggregate(unattributed, EXP)}
    assert not a[3.0]["complete"]
    assert not analyze.aggregate([], EXP)[0]["complete"]


# --------------------------------------------------------- report plumbing --

def write_wf(tmp, name, data, pin=3):
    d = tmp / name
    d.mkdir()
    x, tb, ip, iin = data
    (d / "waveform.raw.json").write_text(json.dumps({
        "variables": [{"name": n} for n in ("v-sweep", f"v(xbank.tb{pin})", "i(vp)", "i(vtin)")],
        "points": [list(r) for r in zip(x, tb, ip, iin)]}))
    return str(d / "waveform.raw.json")


def corner(proc, temp, wf=None, status="pass"):
    return {"process": proc, "temperature_c": temp, "status": status, "artifacts": {"waveform": wf} if wf else {}}


def write_report(tmp, corners, status="pass", **extra):
    p = tmp / "report.json"
    p.write_text(json.dumps({"schema_version": 3, "status": status, "corner_count": len(corners),
                             "synthetic": True, "corners": corners, **extra}))
    return p


META = {"vdd_v": VDD, "pin": 3, "background": 1, "m_frac": 0.5}


def test_report_rows_and_failures(tmp_path):
    good = write_wf(tmp_path, "g", sweep())
    flat = write_wf(tmp_path, "f", sweep(g0=1e-5, g1=1e-5))
    rep = write_report(tmp_path, [corner("tt", 27.0, good), corner("ss", 27.0, flat), corner("ff", 27.0),
                                  corner("tt", -40.0, good, status="error")])
    rows, meta = analyze.analyse_report("v33_t3_bg1_m50", rep, META, P)
    assert [r["status"] == "OK" for r in rows] == [True, False, False, False]
    assert rows[0]["id"] == prepare.case_id("tt", 27.0, 3.3, 3, 1, 0.5) and meta["synthetic"]
    assert "unresolved" in rows[1]["status"] and "no waveform" in rows[2]["status"]
    assert "klt corner status" in rows[3]["status"]


def test_failed_report_status_and_unreadable(tmp_path):
    good = write_wf(tmp_path, "g", sweep())
    rep = write_report(tmp_path, [corner("tt", 27.0, good)], status="error")
    rows, _ = analyze.analyse_report("t", rep, META, P)
    assert any("report status 'error'" in r["status"] for r in rows)
    assert analyze.analyse_report("t", tmp_path / "nope.json", META, P)[0][0]["status"].startswith("FAIL: report unreadable")
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    assert "not valid JSON" in analyze.analyse_report("t", bad, META, P)[0][0]["status"]
    assert analyze.analyse_report("t", write_report(tmp_path, []), META, P)[0][0]["status"] == "FAIL: report has no corners"
    rep = write_report(tmp_path, [corner("tt", 27.0, good)], corner_count=9)
    assert any("corner_count" in r["status"] for r in analyze.analyse_report("t", rep, META, P)[0])


def test_write_run_labels_synthetic_and_refuses_overwrite(tmp_path):
    good = write_wf(tmp_path, "g", sweep())
    rep = write_report(tmp_path, [corner("tt", 27.0, good)])
    rows, meta = analyze.analyse_report("v33_t3_bg1_m50", rep, META, P)
    out = tmp_path / "run"
    doc = analyze.write_run(out, rows, [meta], EXP, P, synthetic=False)
    assert doc["synthetic"] and "SYNTHETIC" in doc["label"] and doc["complete"] is False
    assert (out / "results.json").is_file() and (out / "summary.md").is_file()
    assert "INCOMPLETE" in (out / "summary.md").read_text() and "PASS" not in (out / "summary.md").read_text().replace("no verdict here is a PASS", "")
    header = (out / "results.csv").read_text().splitlines()[0].split(",")
    assert header == analyze.csv_fields(P) and "i_in_000_a" in header and "max_abs_input_current_a" in header
    with pytest.raises(SystemExit):
        analyze.write_run(out, rows, [meta], EXP, P, synthetic=True)


# --------------------------------------------------------------- prepare ---

def test_extraction_is_verbatim_and_strict():
    src = prepare.SRC.read_text()
    block = prepare.extract_bank(src)
    assert block.startswith(".subckt rcosc_trim_bank p m vss t0 t1 t2 t3 t4 t5 t6 t7 vdd")
    assert block.rstrip().endswith(".ends")
    for line in block.splitlines():  # every extracted line exists verbatim in the source
        assert line in src.splitlines()
    assert "W=24uu" in block and "r_length=17.198u" in block  # device parameters preserved as committed
    with pytest.raises(prepare.PrepareError, match="found 0"):
        prepare.extract_bank(src.replace(".subckt rcosc_trim_bank", ".subckt other_bank"))
    with pytest.raises(prepare.PrepareError, match="found 2"):
        prepare.extract_bank(src + "\n" + block)
    with pytest.raises(prepare.PrepareError, match="no .ends|unterminated"):
        prepare.extract_bank(block.replace(".ends", "* ends"))
    with pytest.raises(prepare.PrepareError, match="XSW3"):
        prepare.extract_bank(src.replace("\nXSW3 ", "\nXSWX3 "))
    with pytest.raises(prepare.PrepareError, match="pin list"):
        prepare.extract_bank(src.replace("p m vss t0 t1", "m p vss t0 t1"))


def test_bank_structure_matches_selection_model():
    block = prepare.extract_bank(prepare.SRC.read_text())
    for i in range(8):  # switch i gated by t<i>, shunts stage i; inverter makes tb<i>
        assert re.search(rf"^XSW{i} c\d t{i} \S+ vss nfet_03v3", block, re.M)
        assert re.search(rf"^XPW{i} \S+ tb{i} c\d vdd pfet_03v3", block, re.M)
        assert re.search(rf"^XNINV{i} tb{i} t{i} vss vss", block, re.M)
        assert re.search(rf"^XR{i} c\d \S+ vss ppolyf_u_1k", block, re.M)  # parallel resistor present


def test_generate_requests_offline(tmp_path, no_sim):
    prov = prepare.generate(tmp_path)
    assert len(prov["requests"]) == 144 and prov["grid"]["cases"] == 1296
    ids, held, mbias = [], set(), set()
    for r in prov["requests"]:
        req = json.loads((tmp_path / r["request"]).read_text())
        assert req["analysis"]["kind"] == "dc" and req["options"]["waveforms"]
        vdd = r["vdd_v"]
        a = req["analysis"]["args"].split()
        assert a[0] == "VTIN" and float(a[1]) == 0.0 and float(a[2]) == pytest.approx(vdd)  # both endpoints
        assert float(a[3]) == pytest.approx(0.01 * vdd, rel=1e-4)
        assert r["sweep"]["points"] == 101 and r["sweep"]["endpoints_included"]
        assert {c["name"] for c in req["corners"]["process"]} == {"tt", "ss", "ff"}
        assert req["corners"]["temperature_c"] == [-40.0, 27.0, 85.0]
        for c in req["corners"]["process"]:
            fets, res, mim = prepare.PROCESS_CORNERS[c["name"]]
            assert c["sections"] == [fets, res, mim, "cap_mim"]
        tb = (tmp_path / req["netlist"]).read_text()
        pin, bg = r["pin"], r["background"]
        assert f"VTIN t{pin} 0 DC 0" in tb and f".save v(xbank.tb{pin})" in tb
        for i in range(8):
            if i != pin:
                assert f"VT{i} t{i} 0 DC {vdd:g}\n" in tb if bg else f"VT{i} t{i} 0 DC 0\n" in tb
        assert f"VP p 0 DC {vdd:g}" in tb and "XBANK p m 0 t0 t1 t2 t3 t4 t5 t6 t7 vdd rcosc_trim_bank" in tb
        assert f"VM m 0 DC {r['m_frac'] * vdd:.6g}" in tb
        held.add(bg); mbias.add(r["m_frac"]); ids += r["cases"]
    assert len(ids) == len(set(ids)) == 1296 and set(ids) == {c["id"] for c in EXP}
    assert held == {0, 1} and mbias == {0.25, 0.5, 0.75}
    assert {r["pin"] for r in prov["requests"]} == set(range(8))


def test_provenance_metadata_and_hashes(tmp_path, no_sim):
    prov = prepare.generate(tmp_path)
    assert prov["dut"]["source_sha256"] == prepare.sha256(prepare.SRC)
    assert prov["dut"]["extracted_sha256"] == prepare.sha256(tmp_path / prepare.BANK_FILE)
    assert prov["models"] == prepare.MODELS and prov["git_revision"]
    assert set(prov["process_library_mapping"]) == {"tt", "ss", "ff"}
    s = prov["settings"]
    assert s["screens"]["sel_low"] == 0.10 and s["screens"]["sel_high"] == 0.90 and s["screens"]["margin_frac"] == 0.05
    assert s["leak_fracs"] == [0.0, 0.25, 0.5, 0.75, 1.0] and "-i(VTIN)" in s["sign_convention"]
    assert prov["grid"]["vdd_v"] == [3.0, 3.3, 3.6] and prov["grid"]["temperature_c"] == [-40.0, 27.0, 85.0]
    assert "NOT EVIDENCE" in prov["evidence"]
    assert json.loads((tmp_path / "provenance.json").read_text()) == prov


def test_generation_is_reproducible(tmp_path, no_sim):
    a, b = tmp_path / "a", tmp_path / "b"
    prepare.generate(a)
    prepare.generate(b)
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir()) and len(names) == 144 * 2 + 2
    for n in names:
        assert (a / n).read_bytes() == (b / n).read_bytes()


def test_bad_settings_rejected():
    with pytest.raises(prepare.PrepareError):
        prepare._cfg_from({"step_frac": 0.03})
    with pytest.raises(prepare.PrepareError):
        prepare._cfg_from({"sel_low": 0.9, "sel_high": 0.1})
    with pytest.raises(prepare.PrepareError):
        prepare._cfg_from({"leak_fracs": (0.123,)})


def test_end_to_end_synthetic_complete_aggregate(tmp_path):
    """Full 1296-row synthetic campaign through analyse_sweep + aggregate."""
    rows = []
    for c in EXP:
        r = analyze.analyse_sweep(*sweep(vdd=c["vdd_v"], mfrac=c["m_frac"]), c["vdd_v"], c["m_frac"], P)
        rows.append(r | {"id": c["id"], "tag": c["tag"], "vdd_v": c["vdd_v"]})
    agg = analyze.aggregate(rows, EXP)
    assert all(a["complete"] for a in agg)
    assert all(a["min_low_bound_frac"] == pytest.approx(0.05) and a["max_high_bound_frac"] == pytest.approx(0.95) for a in agg)


def test_readme_schema_correspondence():
    readme = (HERE / "README.md").read_text()
    for f in analyze.csv_fields(P):
        key = re.sub(r"_\d{3}_", "_<bias>_", f)
        assert key in readme, f"README does not document {key}"
    prov_keys = ["kind", "evidence", "git_revision", "source_dirty", "grid", "process_library_mapping", "models",
                 "dut", "settings", "requests", "execution"]
    for k in prov_keys:
        assert f"`{k}`" in readme
    for word in ("characterized", "ratified", "capacitance", "deferred", "SYNTHETIC", "-I(VTIN)"):
        assert word in readme
    for k in ("min_low_bound_case", "max_high_bound_case", "max_abs_input_current_case", "complete", "missing", "duplicate"):
        assert k in readme
