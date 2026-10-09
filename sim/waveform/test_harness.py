"""Offline tests for sim/waveform (issue #91).  Every waveform here is a
SYNTHETIC FIXTURE built in this file; nothing is measured evidence and no
simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/waveform
"""
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import prepare  # noqa: E402

VDD = 3.3
CAL_RUN = prepare.REPO / "sim" / "pvt" / "results" / "20260923T030125Z"
NS = 1e-9


# ------------------------------------------------------------- fixtures ----

def pwl_clock(periods, high, edge, vdd=VDD, t0=0.0, step=0.1 * NS, jitter=0.0, seed=1, lead=10 * NS):
    """Trapezoidal clock as a (t, clk, vdd) fixture.  The i-th rising 50%
    crossing is at lead + t0 + sum(periods[:i]); high is the 50%-to-50% high
    time; `edge` is the 0-100% transition time (10-90% = 0.8*edge).  The
    time grid contains every PWL corner, so linear interpolation of samples is
    exact; `jitter` adds irregularly spaced extra samples."""
    r = lead + t0
    knots = []
    for q in list(periods) + [periods[-1]]:
        knots.append(r)
        r += q
    pts = [(-1.0, 0.0)]
    for rr in knots:
        pts += [(rr - edge / 2, 0.0), (rr + edge / 2, vdd),
                (rr + high - edge / 2, vdd), (rr + high + edge / 2, 0.0)]
    pts.sort()
    tstop = knots[-1] - 1.0 * NS
    tt = {p[0] for p in pts if 0 <= p[0] <= tstop}
    x = 0.0
    rng = random.Random(seed)
    while x < tstop:
        tt.add(round(x, 15))
        x += step * (1 + jitter * rng.random())
    tt.add(tstop)
    ts = sorted(tt)

    def f(x):
        for (a, va), (b, vb) in zip(pts, pts[1:]):
            if a <= x <= b:
                return va if b == a else va + (vb - va) * (x - a) / (b - a)
        return 0.0
    return ts, [f(x) for x in ts], [vdd] * len(ts)


def steady(n=60, period=20 * NS, **kw):
    return pwl_clock([period] * n, high=4 * NS, edge=1 * NS, **kw)


P = analyze.Params(window_s=500 * NS, min_cycles=20)


def approx(a, b, tol=1e-12):
    return abs(a - b) <= tol


# ------------------------------------------------------------- analyzer ----

def test_trapezoid_pulse_duty_and_transitions():
    t, c, v = steady()
    m = analyze.analyse(t, c, v, VDD, P)
    assert m["n_complete_cycles"] >= 20
    assert approx(m["pulse_high_s"]["mean"], 4 * NS, 1e-13)
    assert approx(m["pulse_low_s"]["mean"], 16 * NS, 1e-13)
    assert approx(m["duty"]["mean"], 0.2, 1e-9)
    assert m["period_s"]["peak_to_peak"] < 1e-13
    assert m["period_s"]["std_deterministic"] < 1e-13
    # configured 0-100% edge 1 ns => 10-90% = 0.8 ns
    assert approx(m["rise_time_10_90_s"]["mean"], 0.8 * NS, 1e-12)
    assert approx(m["fall_time_90_10_s"]["mean"], 0.8 * NS, 1e-12)
    assert m["rise_time_10_90_s"]["peak_to_peak"] < 1e-12
    assert m["units"]["time"] == "s"
    assert "NOT stochastic RMS jitter" in m["spread_kind"]


def test_alternating_periods_and_cycle_to_cycle_irregular_sampling():
    periods = [19 * NS, 21 * NS] * 40
    t, c, v = pwl_clock(periods, high=4 * NS, edge=1 * NS, jitter=0.7)
    gaps = {round(b - a, 14) for a, b in zip(t, t[1:])}
    assert len(gaps) > 20  # genuinely irregular
    even_seen = False
    for w in range(480, 561, 10):  # windows with odd and even complete-cycle counts
        m = analyze.analyse(t, c, v, VDD, analyze.Params(window_s=w * NS, min_cycles=20))
        n = m["n_complete_cycles"]
        if n % 2 == 0:  # whole 19/21 pairs: mean is exactly 20 ns, std exactly 1 ns
            even_seen = True
            assert approx(m["period_s"]["mean"], 20 * NS, 1e-12)
            assert approx(m["period_s"]["std_deterministic"], 1 * NS, 1e-12)
        assert approx(m["period_s"]["peak_to_peak"], 2 * NS, 1e-12)
        cc = m["cycle_to_cycle_s"]
        assert cc["count"] == n - 1
        assert approx(cc["max"], 2 * NS, 1e-12) and approx(cc["min"], -2 * NS, 1e-12)
        assert approx(cc["max_abs"], 2 * NS, 1e-12)
    assert even_seen


def test_incomplete_boundary_cycles_are_omitted():
    t, c, v = steady(n=40)
    # window start mid-high-pulse => a leading falling edge precedes the first rising edge
    tstop = t[-1]
    first_r = [x for x in analyze.crossings(t, c, VDD / 2) if x[1] == "r"]
    # place window start 2 ns after a rising edge so its falling edge leads the window
    rt = first_r[10][0]
    p = analyze.Params(window_s=tstop - (rt + 2 * NS), min_cycles=5)
    m = analyze.analyse(t, c, v, VDD, p)
    assert m["omitted_boundary"]["leading_falling_edges"] == 1
    n_r = len([x for x in analyze.crossings(t, c, VDD / 2) if x[0] >= tstop - p.window_s and x[1] == "r"])
    assert m["n_complete_cycles"] == n_r - 1  # only cycles bounded by two rising edges


def fails(t, c, v, match, p=P, vdd=VDD):
    with pytest.raises(analyze.AnalysisError, match=match):
        analyze.analyse(t, c, v, vdd, p)


def test_insufficient_cycles():
    t, c, v = steady(n=60)
    fails(t, c, v, "insufficient cycles", analyze.Params(window_s=300 * NS, min_cycles=20))


def test_missing_crossings_flat_clock():
    t, c, v = steady()
    fails(t, [0.0] * len(t), v, "missing crossings")


def test_insufficient_samples():
    t, c, v = pwl_clock([20 * NS] * 60, high=4 * NS, edge=1 * NS, step=20 * NS)
    fails(t, c, v, "insufficient samples")


def test_drifting_tail_is_unsettled():
    periods = [20 * NS + 0.05 * NS * i for i in range(60)]
    t, c, v = pwl_clock(periods, high=4 * NS, edge=1 * NS)
    fails(t, c, v, "unsettled tail", analyze.Params(window_s=600 * NS, min_cycles=20))


def test_unsettled_rail():
    t, c, v = steady()
    v = [3.0] * len(v)
    fails(t, c, v, "unsettled rail")


def test_invalid_crossing_order_is_rejected(monkeypatch):
    # Interpolated crossings of a continuous waveform alternate by construction;
    # the guard is defensive, so exercise it with a doctored crossing list.
    t, c, v = steady()
    real = analyze.crossings
    monkeypatch.setattr(analyze, "crossings",
                        lambda *a: [x if k != 5 else (x[0], "r", x[2]) for k, x in enumerate(real(*a))])
    monkeypatch.setattr(analyze, "crossings", lambda *a: [(x[0], "r", x[2]) for x in real(*a)])
    fails(t, c, v, "invalid crossing order")


def test_runt_pulse_cannot_pass(tmp_path):
    t, c, v = steady()
    j = next(i for i in range(len(t) - 150, len(t)) if c[i] == 0.0 and c[i - 1] == 0.0)
    c = list(c)
    c[j], c[j + 1], c[j + 2] = VDD, 0.0, VDD
    with pytest.raises(analyze.AnalysisError):
        analyze.analyse(t, c, v, VDD, analyze.Params(window_s=300 * NS, min_cycles=5))


def test_clock_not_reaching_ten_ninety():
    t, c, v = steady()
    c = [x * 0.6 for x in c]  # peak 1.98 V: crosses 50 % (1.65) but never reaches 90 %
    fails(t, c, v, "10-90|transition end")


def test_invalid_waveforms():
    ok = {"variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
          "points": [[0, 0, 0], [1, 1, 1]]}
    analyze.parse_waveform(ok)
    bad = {"variables": [{"name": "time"}, {"name": "v(clk)"}], "points": [[0, 0], [1, 1]]}
    with pytest.raises(analyze.AnalysisError, match="missing signal v\\(vdd\\)"):
        analyze.parse_waveform(bad)
    for pts, msg in [([[0, 0, 0], [1, float("nan"), 1]], "non-finite"),
                     ([[0, 0, 0], [1, float("inf"), 1]], "non-finite"),
                     ([[0, 0, 0], [0, 1, 1]], "strictly increasing"),
                     ([[1, 0, 0], [0, 1, 1]], "strictly increasing"),
                     ([[0, 0, 0]], "fewer than 2"),
                     ([[0, 0, 0], [1, "x", 1]], "non-numeric"),
                     ([[0, 0], [1, 1]], "values for")]:
        with pytest.raises(analyze.AnalysisError, match=msg):
            analyze.parse_waveform({"variables": ok["variables"], "points": pts})


# -------------------------------------------------------- report flow ------

def write_report(tmp, corners, status="pass", **extra):
    rep = {"schema_version": 3, "status": status, "corner_count": len(corners),
           "synthetic": True, "corners": corners, **extra}
    p = tmp / "report.json"
    p.write_text(json.dumps(rep))
    return p


def write_wf(tmp, name, tcv, drop=None):
    t, c, v = tcv
    d = tmp / name
    d.mkdir()
    variables = [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}]
    if drop:
        variables = [x for x in variables if x["name"] != drop]
    pts = [[a, b, e] if not drop else [a, b] for a, b, e in zip(t, c, v)]
    (d / "waveform.raw.json").write_text(json.dumps({"variables": variables, "points": pts}))
    return str(d / "waveform.raw.json")


def corner(proc, temp, wf=None, status="pass"):
    return {"process": proc, "temperature_c": temp, "status": status,
            "artifacts": {"waveform": wf} if wf else {}}


def test_report_ok_failed_missing_and_exit_labels(tmp_path):
    good = write_wf(tmp_path, "g", steady())
    short = write_wf(tmp_path, "s", steady(n=15, period=80 * NS))
    nosig = write_wf(tmp_path, "n", steady(), drop="v(vdd)")
    rep = write_report(tmp_path, [corner("tt", 27.0, good), corner("ss", 27.0, short),
                                  corner("ff", 27.0, nosig), corner("tt", 85.0, None),
                                  corner("tt", -40.0, str(tmp_path / "gone" / "waveform.raw.json")),
                                  corner("ss", 85.0, good, status="error")])
    rows, meta = analyze.analyse_report(rep, VDD, P)
    st = [r["status"] for r in rows]
    assert st[0] == "OK" and "metrics" in rows[0]
    assert "insufficient cycles" in st[1]
    assert "missing signal" in st[2]
    assert "no waveform artifact" in st[3]
    assert "unreadable" in st[4]
    assert "klt corner status" in st[5]
    assert all("metrics" not in r for r in rows[1:])
    out = tmp_path / "run"
    doc = analyze.write_run(out, rows, [meta], P, synthetic=False)
    assert doc["synthetic"] is True  # propagated from the synthetic report
    assert not doc["all_ok"] and doc["n_fail"] == 5
    assert "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE" in (out / "summary.md").read_text()
    assert (out / "results.csv").read_text().count("FAIL") == 5
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        analyze.write_run(out, rows, [meta], P, synthetic=True)


def test_missing_or_bad_reports_fail_explicitly(tmp_path):
    rows, _ = analyze.analyse_report(tmp_path / "nope.json", VDD, P)
    assert rows[0]["status"].startswith("FAIL: report unreadable")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert analyze.analyse_report(bad, VDD, P)[0][0]["status"].startswith("FAIL: report is not valid JSON")
    empty = write_report(tmp_path, [])
    assert analyze.analyse_report(empty, VDD, P)[0][0]["status"] == "FAIL: report has no corners"
    good = write_wf(tmp_path, "g", steady())
    mism = write_report(tmp_path, [corner("tt", 27.0, good)])
    d = json.loads(mism.read_text()); d["corner_count"] = 9; mism.write_text(json.dumps(d))
    rows, _ = analyze.analyse_report(mism, VDD, P)
    assert any("corner_count" in r["status"] for r in rows)


def test_artifacts_root_override(tmp_path):
    wf = write_wf(tmp_path, "tt_27", steady())
    rep = write_report(tmp_path, [corner("tt", 27.0, "/elsewhere/tt_27/waveform.raw.json")])
    rows, _ = analyze.analyse_report(rep, VDD, P, artifacts_root=tmp_path)
    assert rows[0]["status"] == "OK", rows[0]


def test_cli_exit_code(tmp_path):
    good = write_wf(tmp_path, "g", steady())
    rep = write_report(tmp_path, [corner("tt", 27.0, good)])
    base = [sys.executable, "-I", str(HERE / "analyze.py"), str(rep), "--vdd", "3.3",
            "--window-ns", "500", "--synthetic"]
    r = subprocess.run(base + ["--outdir", str(tmp_path / "o1")], capture_output=True, text=True)
    assert r.returncode == 0 and "SYNTHETIC" in r.stdout
    r = subprocess.run(base + ["--outdir", str(tmp_path / "o2"), "--min-cycles", "500"],
                       capture_output=True, text=True)
    assert r.returncode == 1


# ------------------------------------------------------------- prepare -----

@pytest.fixture
def no_sim(monkeypatch):
    """Fail if prepare shells out to anything but read-only git."""
    real = subprocess.run
    calls = []

    def guard(cmd, *a, **k):
        calls.append(cmd)
        assert cmd[0] == "git" and cmd[1] in ("ls-files", "log", "rev-parse"), cmd
        return real(cmd, *a, **k)
    monkeypatch.setattr(prepare.subprocess, "run", guard)
    return calls


def test_generate_requests_offline(tmp_path, no_sim):
    cal = prepare.load_calibration(CAL_RUN)
    prov = prepare.generate(tmp_path, cal)
    assert cal["codes"] == {"tt": 163, "ss": 205, "ff": 89}
    reqs = prov["requests"]
    assert len(reqs) == 9
    pts = set()
    for r in reqs:
        req = json.loads((tmp_path / r["request"]).read_text())
        (proc,) = req["corners"]["process"]
        for tc in req["corners"]["temperature_c"]:
            pts.add((proc["name"], tc, r["vdd_v"]))
        fets, res, mim = prepare.PROCESS_CORNERS[proc["name"]]
        assert proc["sections"] == [fets, res, mim, "cap_mim"]
        assert req["analysis"]["kind"] == "tran" and req["analysis"]["args"].startswith("200p 20000n")
        assert req["options"]["waveforms"] and req["options"]["save_mode"] == "netlist"
        assert req["models"] == prepare.MODELS and req["netlist_source"] == "schematic"
        tb = (tmp_path / req["netlist"]).read_text()
        assert ".save v(clk) v(vdd)" in tb
        code = r["trim_code"]
        for i in range(8):
            line = next(l for l in tb.splitlines() if l.startswith(f"VT{i} "))
            assert ("PWL" in line) == bool((code >> i) & 1)
        assert f"PWL(0 0 1000n {r['vdd_v']:g})" in tb
        assert "CLOAD" not in tb
    assert len(pts) == 27
    assert pts == {(p, t, v) for p in ("tt", "ss", "ff") for t in (-40.0, 27.0, 85.0) for v in (3.0, 3.3, 3.6)}
    assert {r["vdd_v"] for r in reqs} == {3.0, 3.3, 3.6}
    s = prov["settings"]
    assert s["ramp_ns"] == 1000 and s["tstop_ns"] == 20000 and s["window_ns"] == 2000
    assert s["min_cycles"] == 20 and s["load_matches_calibration_bench"] is True
    assert s["tmax_time_step"] and s["reltol"] and prov["models"]
    c = prov["calibration"]
    assert c["campaign_dir"] == "sim/pvt/results/20260923T030125Z" and c["manifest_sha256"]
    assert c["committing_hash"] and c["campaign_git_sha"]
    assert "NOT EVIDENCE" in prov["evidence"]
    assert all(cm[0] == "git" for cm in no_sim)
    # the existing startup tooling's request keys are a superset-compatible shape
    st = json.loads((prepare.REPO / "sim" / "startup" / "request_v33.json").read_text())
    assert set(st) == set(req)


def test_probe_option_single_corner(tmp_path, no_sim):
    cal = prepare.load_calibration(CAL_RUN)
    prov = prepare.generate(tmp_path, cal, probe="tt:27:3.3")
    assert len(prov["requests"]) == 1 and prov["grid"]["points"] == 1
    req = json.loads((tmp_path / "request_probe.json").read_text())
    assert req["corners"]["temperature_c"] == [27.0] and len(req["corners"]["process"]) == 1
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "x", cal, probe="tt:30:3.3")
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "y", cal, probe="garbage")


def test_load_and_config_are_recorded(tmp_path):
    cal = prepare.load_calibration(CAL_RUN)
    prov = prepare.generate(tmp_path, cal, {"load_f": 1e-12, "tstop_ns": 30000, "tmax": "100p"})
    assert prov["settings"]["load_matches_calibration_bench"] is False
    assert "CLOAD clk 0 1e-12" in (tmp_path / prov["requests"][0]["netlist"]).read_text()
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "bad", cal, {"window_ns": 25000})
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "bad2", cal, {"ramp_ns": 19500})


def cal_copy(tmp_path):
    d = tmp_path / "cal"
    shutil.copytree(CAL_RUN, d)
    return d


def test_calibration_validation_failures(tmp_path):
    d = cal_copy(tmp_path)
    load = lambda **k: prepare.load_calibration(d, require_committed=False, **k)  # noqa: E731
    assert load()["codes"]["tt"] == 163
    man = json.loads((d / "manifest.json").read_text())

    def put(m):
        (d / "manifest.json").write_text(json.dumps(m))
    m = json.loads(json.dumps(man)); m["calibration_spec_target"]["ss"]["code"] = 300; put(m)
    with pytest.raises(prepare.PrepareError, match="invalid"):
        load()
    m = json.loads(json.dumps(man)); m["calibration_spec_target"]["ff"]["saturated"] = True; put(m)
    with pytest.raises(prepare.PrepareError, match="saturated"):
        load()
    m = json.loads(json.dumps(man)); del m["calibration_spec_target"]["tt"]; put(m)
    with pytest.raises(prepare.PrepareError, match="lacks process"):
        load()
    m = json.loads(json.dumps(man)); m["calibration_spec_target"]["tt"]["code"] = 164; put(m)
    with pytest.raises(prepare.PrepareError, match="holds code"):
        load()
    put(man)
    (d / "results.csv").write_text("\n".join((d / "results.csv").read_text().splitlines()[:-300]) + "\n")
    with pytest.raises(prepare.PrepareError, match="does not cover"):
        load()
    (d / "manifest.json").unlink()
    with pytest.raises(prepare.PrepareError, match="no manifest"):
        load()


def test_cli_requires_explicit_calibration_source():
    r = subprocess.run([sys.executable, "-I", str(HERE / "prepare.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "--cal-run" in r.stderr


def test_uncommitted_calibration_rejected(tmp_path):
    d = cal_copy(tmp_path)
    with pytest.raises(prepare.PrepareError, match="not a committed"):
        prepare.load_calibration(d)
