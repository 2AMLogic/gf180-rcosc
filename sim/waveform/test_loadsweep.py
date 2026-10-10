"""Offline tests for sim/waveform/loadsweep.py (issue #122).  All waveforms are
SYNTHETIC FIXTURES; no simulator, PDK, cloud credential or network is used.
Measured load sensitivity is a deferred campaign.
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import loadsweep as ls  # noqa: E402
import prepare  # noqa: E402
from test_harness import CAL_RUN, NS, P, pwl_clock, no_sim  # noqa: E402,F401


@pytest.fixture(scope="module")
def cal():
    return prepare.load_calibration(CAL_RUN)


@pytest.fixture
def swept(tmp_path, cal, no_sim):  # noqa: F811
    out = tmp_path / "sweep"
    return out, ls.prepare_sweep(out, cal)


def test_grid_and_manifest(swept, cal):
    out, man = swept
    assert man["n_points"] == 45 and len({p["id"] for p in man["points"]}) == 45
    assert "NOT EVIDENCE" in man["evidence"]
    assert man["calibration"]["manifest_sha256"] and man["calibration"]["committing_hash"]
    assert man["calibration"]["target"] == "ratified"
    assert man["calibration"]["campaign_dir"] == "sim/pvt/results/20260923T030125Z"
    assert {(p["process"], p["vdd_v"], p["load_f"]) for p in man["points"]} == set(ls.grid())
    for p in man["points"]:
        assert p["temperature_c"] == 27.0
        assert p["trim_code"] == cal["codes"][p["process"]]
        req = json.loads((out / p["request"]).read_text())
        assert len(req["corners"]["process"]) == 1 and req["corners"]["process"][0]["name"] == p["process"]
        assert req["corners"]["temperature_c"] == [27.0]
        tb = (out / p["netlist"]).read_text()
        assert f"PWL(0 0 1000n {p['vdd_v']:g})" in tb
        for i in range(8):
            line = next(l for l in tb.splitlines() if l.startswith(f"VT{i} "))
            assert ("PWL" in line) == bool((p["trim_code"] >> i) & 1)
        if p["load_f"] == 0:
            assert "CLOAD" not in tb and p["load_matches_calibration_bench"] is True
        else:
            assert f"CLOAD clk 0 {p['load_f']:g}" in tb and p["load_matches_calibration_bench"] is False
            assert "NON-ZERO" in p["load_kind"]
        assert json.loads((out / p["provenance"]).read_text())["settings"]["load_f"] == p["load_f"]
    # the same process keeps one code at every supply and load
    assert {(p["process"], p["trim_code"]) for p in man["points"]} == {(k, v) for k, v in cal["codes"].items()}


def test_overwrite_refused_and_load_validation(tmp_path, cal):
    d = tmp_path / "exists"
    d.mkdir()
    with pytest.raises(ls.SweepError, match="refusing"):
        ls.prepare_sweep(d, cal)
    with pytest.raises(ls.SweepError, match="per point"):
        ls.prepare_sweep(tmp_path / "x", cal, {"load_f": 1e-12})
    for bad in (-1e-12, float("nan"), float("inf"), 3e-12, None, True, "1p"):
        with pytest.raises(ls.SweepError):
            ls.check_load(bad)


# ------------------------------------------------------------ comparison ---

def row(f=48e6, duty=0.2, rise=1e-9, fall=1e-9, status="OK"):
    if status != "OK":
        return {"status": status}
    s = lambda x: {"mean": x}  # noqa: E731
    return {"status": "OK", "metrics": {"frequency_mean_hz": f, "duty": s(duty),
                                        "rise_time_10_90_s": s(rise), "fall_time_90_10_s": s(fall)}}


def rows_for(points, fn):
    return {p["id"]: fn(p) for p in points}


@pytest.fixture
def pts(swept):
    return ls.validate_manifest(swept[1]["points"] and swept[1])


def test_relative_shift_slopes_and_budget(pts):
    # f falls 0.5 %/pF for the first 2 pF, then 1 %/pF
    def fn(p):
        pf = p["load_f"] * 1e12
        shift = -0.005 * pf if pf <= 2 else -0.01 - 0.01 * (pf - 2)
        return row(f=48e6 * (1 + shift), duty=0.2 + 0.001 * pf, rise=1e-9 * (1 + 0.1 * pf), fall=2e-9)
    res = ls.compare(pts, rows_for(pts, fn))
    e = next(x for x in res["points"] if x["process"] == "tt" and x["vdd_v"] == 3.3 and x["load_pf"] == 5)
    assert e["rel_freq_shift_pct"] == pytest.approx(-4.0)
    assert e["duty_delta"] == pytest.approx(0.005)
    assert e["rise_rel_change_pct"] == pytest.approx(50.0) and e["fall_delta_s"] == pytest.approx(0)
    g = next(x for x in res["groups"] if x["process"] == "tt" and x["vdd_v"] == 3.3)
    sl = {(s["from_pf"], s["to_pf"]): s["slope_pct_per_pF"] for s in g["slopes"]}
    assert sl[(0, 1)] == pytest.approx(-0.5) and sl[(2, 5)] == pytest.approx(-1.0)
    # absolute errors: -1.0 % at 2 pF is inside, -4.0 % at 5 pF is the first outside -2.9 %
    assert g["budget_status"] == "first sampled load outside budget: 5 pF"
    assert g["first_outside_budget_pf"] == 5


def test_budget_upper_side_not_reached_and_baseline_already_failing(pts):
    res = ls.compare(pts, rows_for(pts, lambda p: row(f=48e6 * (1 + 0.019 * (p["load_f"] > 0)))))
    assert all(g["budget_status"] == "not reached through 10 pF" for g in res["groups"])
    res = ls.compare(pts, rows_for(pts, lambda p: row(f=48e6 * (1.0201 + 0.001 * p["load_f"] * 1e12))))
    assert all(g["budget_status"] == "zero-load baseline already outside budget" for g in res["groups"])
    res = ls.compare(pts, rows_for(pts, lambda p: row(f=48e6 * (1 + 0.021 * (p["load_f"] >= 5e-12)))))
    assert all(g["first_outside_budget_pf"] == 5 for g in res["groups"])


def test_failed_rows_never_become_passes(pts):
    def fn(p):
        if p["process"] == "ss" and p["vdd_v"] == 3.0 and p["load_f"] == 2e-12:
            return row(status="FAIL: missing crossings: 0 in the steady window")
        return row(f=48e6 * (1 - 0.001 * p["load_f"] * 1e12))
    res = ls.compare(pts, rows_for(pts, fn))
    bad = next(x for x in res["points"] if x["process"] == "ss" and x["vdd_v"] == 3.0 and x["load_pf"] == 2)
    assert bad["comparison"].startswith("FAIL") and "rel_freq_shift_pct" not in bad
    g = next(x for x in res["groups"] if x["process"] == "ss" and x["vdd_v"] == 3.0)
    s = {(x["from_pf"], x["to_pf"]): x for x in g["slopes"]}
    assert s[(1, 2)]["slope_pct_per_pF"] is None and s[(2, 5)]["slope_pct_per_pF"] is None
    assert s[(0, 1)]["slope_pct_per_pF"] == pytest.approx(-0.1)
    assert g["budget_status"].startswith("indeterminate")
    # a failed zero-load baseline poisons every comparison in its group only
    res = ls.compare(pts, rows_for(pts, lambda p: row(status="FAIL: x") if p["load_f"] == 0 and p["process"] == "ff" else row()))
    assert all(x["comparison"].startswith("FAIL") for x in res["points"] if x["process"] == "ff")
    assert all(x["comparison"] == "OK" for x in res["points"] if x["process"] == "tt")


def test_missing_baseline_missing_row_and_bad_manifest(pts, swept):
    rows = rows_for(pts, lambda p: row())
    with pytest.raises(ls.SweepError, match="no analysis row"):
        ls.compare(pts, {k: v for k, v in rows.items() if k != pts[3]["id"]})
    with pytest.raises(ls.SweepError, match="baseline"):
        ls.compare([p for p in pts if not (p["process"] == "tt" and p["vdd_v"] == 3.0 and p["load_f"] == 0)], rows)
    man = swept[1]
    dup = json.loads(json.dumps(man)); dup["points"][1]["id"] = dup["points"][0]["id"]
    with pytest.raises(ls.SweepError, match="duplicate point id"):
        ls.validate_manifest(dup)
    dup = json.loads(json.dumps(man)); dup["points"][1] = dict(dup["points"][0], id="other")
    with pytest.raises(ls.SweepError, match="duplicate mapping"):
        ls.validate_manifest(dup)
    miss = json.loads(json.dumps(man)); miss["points"].pop()
    with pytest.raises(ls.SweepError, match="45-point"):
        ls.validate_manifest(miss)
    bad = json.loads(json.dumps(man)); bad["points"][0]["load_f"] = 3e-12
    with pytest.raises(ls.SweepError, match="ladder"):
        ls.validate_manifest(bad)
    nokey = json.loads(json.dumps(man)); del nokey["points"][0]["report"]
    with pytest.raises(ls.SweepError, match="lacks"):
        ls.validate_manifest(nokey)


# ------------------------------------------------- reports end to end ------

def _write_wf(d, name, tcv):
    t, c, v = tcv
    (d / name).mkdir()
    f = d / name / "waveform.raw.json"
    f.write_text(json.dumps({"variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
                             "points": [list(x) for x in zip(t, c, v)]}))
    return str(f)


def _report(rdir, pt, wf, proc=None, temp=27.0):
    c = {"process": proc or pt["process"], "temperature_c": temp, "status": "pass",
         "artifacts": {"waveform": wf} if wf else {}}
    (rdir / pt["report"]).write_text(json.dumps(
        {"status": "pass", "corner_count": 1, "synthetic": True, "corners": [c]}))


def test_reports_end_to_end_synthetic_label_and_failures(tmp_path, pts, swept):
    man = swept[1]
    rdir = tmp_path / "reports"
    rdir.mkdir()
    wfs = tmp_path / "wf"
    wfs.mkdir()
    for pt in pts:
        pf = pt["load_f"] * 1e12
        period = 20 * NS * (1 + 0.004 * pf)
        vdd = pt["vdd_v"]
        wf = _write_wf(wfs, pt["id"], pwl_clock([period] * 60, high=4 * NS, edge=(1 + 0.05 * pf) * NS, vdd=vdd))
        if pt["id"] == "tt_v33_c01000f":
            wf = None  # missing waveform artifact
        if pt["id"] == "ss_v30_c02000f":
            _report(rdir, pt, wf, proc="tt")  # wrong corner
        elif pt["id"] != "ff_v36_c05000f":  # report missing
            _report(rdir, pt, wf)
    # vdd in the waveform differs per point, so analyse with the manifest vdd
    rows, metas = ls.analyse_points(tmp_path, pts, rdir, P)
    assert "unreadable" in rows["ff_v36_c05000f"]["status"]
    assert "does not match" in rows["ss_v30_c02000f"]["status"]
    assert "no waveform artifact" in rows["tt_v33_c01000f"]["status"]
    res = ls.compare(pts, rows)
    ok = next(x for x in res["points"] if x["id"] == "tt_v33_c10000f")
    assert ok["comparison"] == "OK" and ok["rel_freq_shift_pct"] == pytest.approx(100 * (1 / 1.04 - 1), abs=1e-6)
    assert ok["rise_rel_change_pct"] > 0
    doc = ls.write_results(tmp_path / "res", man, res, metas, False, P)
    assert doc["synthetic"] is True and doc["label"] == ls.SYNTH and doc["all_ok"] is False and doc["n_fail"] == 3
    for f in ("results.json", "summary.md"):
        assert ls.SYNTH in (tmp_path / "res" / f).read_text()
    assert (tmp_path / "res" / "results.csv").read_text().count(ls.SYNTH) == 45
    with pytest.raises(ls.SweepError, match="refusing"):
        ls.write_results(tmp_path / "res", man, res, metas, False, P)


def test_cli_prepare_requires_cal_and_refuses_overwrite(tmp_path):
    import subprocess
    r = subprocess.run([sys.executable, "-I", str(HERE / "loadsweep.py"), "prepare", "--out", str(tmp_path / "o")],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "--cal-run" in r.stderr
    r = subprocess.run([sys.executable, "-I", str(HERE / "loadsweep.py"), "prepare", "--cal-run", str(CAL_RUN),
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing" in r.stderr
