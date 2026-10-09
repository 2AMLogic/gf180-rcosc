"""Offline tests for sim/supply-transient (issue #92).  Every waveform here is
a SYNTHETIC FIXTURE built in this file; nothing is measured evidence and no
simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/supply-transient/test_harness.py
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import prepare  # noqa: E402

CAL_RUN = prepare.REPO / "sim" / "pvt" / "results" / "20260923T030125Z"
NS, US = 1e-9, 1e-6
F0 = 48e6
CFG = prepare._cfg_from(None)
CASES = {c["tag"]: c for c in prepare.cases(CFG)}
P = analyze.Params()


# ------------------------------------------------------------- fixtures ----

def shape(ph):
    """Normalised clock level for phase ph in [0,1): rising 50% crossing at
    ph=0, falling at ph=0.5, 10% of a period per edge."""
    if ph < 0.05:
        return 0.5 + ph / 0.1
    if ph < 0.45:
        return 1.0
    if ph < 0.55:
        return 1.0 - (ph - 0.45) / 0.1
    if ph < 0.95:
        return 0.0
    return (ph - 0.95) / 0.1


def make_clock(vdd_fn, f_fn, t_from, t_to, spc=20):
    """clk(t) = vdd(t) * shape(phase) so the rising edge of cycle i sits at
    r_i with 1/(r_{i+1}-r_i) = f_fn(r_i) exactly, whatever the rail does."""
    ts, r = [], t_from
    while r <= t_to:
        P_ = 1.0 / f_fn(r)
        for k in range(spc):
            x = r + k / spc * P_
            if x <= t_to:
                ts.append((x, shape(k / spc)))
        r += P_
    if ts[-1][0] < t_to:   # closing sample exactly at t_to (level held from the last sample)
        ts.append((t_to, ts[-1][1]))
    t = [x for x, _ in ts]
    return t, [vdd_fn(x) * s for x, s in ts], [vdd_fn(x) for x in t]


def step_vdd(case):
    sr, td, tr = case["startup_ramp_s"], case["disturb_start_s"], case["ramp_end_s"]
    v0, v1 = case["vdd_from_v"], case["vdd_to_v"]

    def v(t):
        if t < sr:
            return v0 * t / sr
        if t < td:
            return v0
        if t < tr:
            return v0 + (v1 - v0) * (t - td) / (tr - td)
        return v1
    return v


def step_fixture(case, f_base, f_end, overshoot=0.03, tau=1 * US, t_end=None, fn=None):
    """Frequency: f_base until the disturbance, linear to f_end*(1+overshoot)
    across the ramp, then an exponential return to f_end with time constant tau."""
    td, tr = case["disturb_start_s"], case["ramp_end_s"]

    def f(t):
        if fn is not None:
            return fn(t)
        if t < td:
            return f_base
        f_r = f_end * (1 + overshoot)
        if t < tr:
            return f_base + (f_r - f_base) * (t - td) / (tr - td)
        return f_end + (f_r - f_end) * math.exp(-(t - tr) / tau)
    t_from = td - case["baseline_window_s"]
    return make_clock(step_vdd(case), f, t_from, case["tstop_s"] if t_end is None else t_end)


def ripple_case(f_r, f_clk):
    """Real prepare.py ripple case; for a slow f_r the fixture clock is scaled
    down (f_clk) and the baseline window widened so the test stays small."""
    c = dict(CASES[f"ripple_f{prepare.freq_tag(f_r)}_tt"])
    if f_clk < F0:
        c["baseline_window_s"] = 8 * US    # 38 cycles at 4.8 MHz; still after the 1 us startup ramp
    return c


def ripple_fixture(case, f_clk, a, spc=20, t_end=None):
    td, f_r = case["ripple_start_s"], case["ripple_hz"]
    vpp, vm, sr = case["ripple_vpp_v"], case["vdd_mean_v"], case["startup_ramp_s"]

    def ph(t):
        return math.sin(2 * math.pi * f_r * (t - td)) if t >= td else 0.0

    def v(t):
        return vm * t / sr if t < sr else vm + vpp / 2 * ph(t)
    t_from = td - case["baseline_window_s"]
    return make_clock(v, lambda t: f_clk * (1 + a * ph(t)), t_from,
                      case["tstop_s"] if t_end is None else t_end, spc)


# ------------------------------------------------------------- analyzer ----

def test_moving_vdd_threshold_uses_vdd_relative_crossing():
    case = CASES["step_up_r1us_tt"]
    t, c, v = step_fixture(case, F0, F0, overshoot=0.0, t_end=case["ramp_end_s"] + 3 * US, fn=lambda x: F0)
    cyc = analyze.cycle_list(t, c, v, t[0], 10)
    periods = [b - a for a, b in cyc]
    assert max(periods) - min(periods) < 1e-13           # constant frequency through the ramp
    true_edges = [a for a, _ in cyc]
    naive = [x[0] for x in analyze.wfa.crossings(t, c, 1.65) if x[1] == "r"]   # fixed 50 % of 3.3 V
    err = max(min(abs(n - e) for e in true_edges) for n in naive[-20:])
    assert err > 50e-12     # a fixed threshold misplaces the edges once the rail has moved to 3.6 V


def test_constant_frequency_step_has_no_deviation_and_settles_immediately():
    case = CASES["step_dn_r1us_tt"]
    t, c, v = step_fixture(case, F0, F0, overshoot=0.0)
    m, series = analyze.analyse_step(t, c, v, case, P)
    assert m["baseline_frequency_hz"] == pytest.approx(F0, rel=1e-9)
    assert m["endpoint_frequency_hz"] == pytest.approx(F0, rel=1e-9)
    assert m["peak_deviation"]["fraction_of_endpoint"] < 1e-9
    s = m["settling"]
    assert s["status"] == "settled" and 0 <= s["elapsed_s"] < 1 / F0 * 1.01
    assert m["baseline_cycles"] >= 20 and m["endpoint_cycles"] >= 20
    assert m["band_fraction"] == 0.01 and m["units"]["time"] == "s"
    assert series and not m["record_shorter_than_designed"]


@pytest.mark.parametrize("tag", ["step_dn_r1us_tt", "step_up_r1us_ss", "step_dn_r100us_ff", "step_up_r100us_tt"])
def test_known_settling_overshoot_and_peak(tag):
    case = CASES[tag]
    f_end = F0 * (0.9875 if "dn" in tag else 1.0125)
    t, c, v = step_fixture(case, F0, f_end, overshoot=0.03, tau=1 * US)
    m, _ = analyze.analyse_step(t, c, v, case, P)
    assert m["endpoint_frequency_hz"] == pytest.approx(f_end, rel=1e-6)
    assert m["static_shift_fraction"] == pytest.approx((f_end - F0) / F0, rel=1e-3)
    pk = m["peak_deviation"]
    assert pk["fraction_of_endpoint"] == pytest.approx(0.03, abs=1e-3)   # overshoot at ramp end
    assert pk["time_after_disturb_start_s"] == pytest.approx(case["ramp_s"], abs=60 * NS)
    s = m["settling"]
    assert s["status"] == "settled"
    assert s["elapsed_s"] == pytest.approx(1 * US * math.log(3), abs=60 * NS)   # |dev| = 3% e^(-t/tau) = 1%
    assert s["qualifying_cycles"] >= 20 and s["remaining_s"] >= 2 * US


def test_undershoot_from_far_side_and_band_is_configurable():
    case = CASES["step_dn_r1us_tt"]
    t, c, v = step_fixture(case, F0, 0.99 * F0, overshoot=-0.03, tau=1 * US)
    m, _ = analyze.analyse_step(t, c, v, case, P)
    assert m["peak_deviation"]["signed_fraction_of_endpoint"] < 0
    wide = analyze.analyse_step(t, c, v, case, analyze.Params(band=0.02))[0]["settling"]["elapsed_s"]
    tight = analyze.analyse_step(t, c, v, case, analyze.Params(band=0.005))[0]["settling"]["elapsed_s"]
    assert wide < m["settling"]["elapsed_s"] < tight


def test_never_settling_is_not_settled_not_zero():
    case = CASES["step_dn_r1us_tt"]
    t_end = case["tstop_s"]

    def fn(t):  # persistent +/-5 % modulation, final cycle at a crest
        return F0 * (1 + 0.05 * math.cos(2 * math.pi * 500e3 * (t - t_end))) if t >= case["ramp_end_s"] else F0
    t, c, v = step_fixture(case, F0, F0, fn=fn)
    s = analyze.analyse_step(t, c, v, case, P)[0]["settling"]
    assert s["status"] == "not_settled" and s["elapsed_s"] is None


@pytest.mark.parametrize("extra_us, endpoint_known", [(2.5, True), (1.0, False)])
def test_truncated_tail_is_censored(extra_us, endpoint_known):
    case = CASES["step_dn_r1us_tt"]
    t, c, v = step_fixture(case, F0, 0.9875 * F0, tau=1 * US, t_end=case["ramp_end_s"] + extra_us * US)
    m, _ = analyze.analyse_step(t, c, v, case, P)
    s = m["settling"]
    assert s["status"] == "censored" and s["elapsed_s"] is None and s["reason"]
    assert m["record_shorter_than_designed"] is True
    assert (m["endpoint_frequency_hz"] is not None) == endpoint_known


def test_step_failures_are_explicit():
    case = CASES["step_dn_r1us_tt"]
    t, c, v = step_fixture(case, F0, 0.9875 * F0)

    def fails(msg, tt=t, cc=c, vv=v, cs=case, p=P):
        with pytest.raises(analyze.AnalysisError, match=msg):
            analyze.analyse_step(tt, cc, vv, cs, p)
    fails("insufficient baseline cycles", p=analyze.Params(min_cycles=500))
    fails("insufficient samples", p=analyze.Params(min_samples_per_cycle=40))
    # record starts after the baseline window
    k = next(i for i, x in enumerate(t) if x > t[0] + 10 * NS)
    fails("starts after the baseline", tt=t[k:], cc=c[k:], vv=v[k:])
    # rail never reaches the target
    fails("endpoint rail", vv=[3.3] * len(t))
    # wrong baseline rail
    fails("baseline rail", vv=[3.0] * len(t))
    # clock stuck low: no crossings
    fails("missing crossings", cc=[0.0] * len(t))
    # a glitch makes two rising crossings in a row
    g = list(c)
    j = next(i for i in range(len(t) // 3, len(t)) if g[i] == 0.0 and g[i + 1] == 0.0 and g[i + 2] == 0.0)
    g[j] = g[j + 1] = 3.3
    fails("invalid crossing order|non-positive|insufficient samples", cc=g)
    # record ends before the disturbance
    n = next(i for i, x in enumerate(t) if x > case["disturb_start_s"])
    fails("ends before the disturbance", tt=t[:n], cc=c[:n], vv=v[:n])
    # sample-starved fixture
    ts, cs_, vs = make_clock(step_vdd(case), lambda x: F0, case["disturb_start_s"] - 2 * US, case["tstop_s"], spc=8)
    fails("insufficient samples", tt=ts, cc=cs_, vv=vs)
    with pytest.raises(analyze.AnalysisError, match="not a step case"):
        analyze.analyse_step(t, c, v, CASES["ripple_f1MHz_tt"], P)
    bad = dict(case); bad["baseline_window_s"] = float("nan")
    fails("case field", cs=bad)


@pytest.mark.parametrize("f_r, f_clk", [(1e6, F0), (1e5, F0), (1e4, 4.8e6)])
def test_ripple_modulation_depth_and_normalized_sensitivity(f_r, f_clk):
    case = ripple_case(f_r, f_clk)
    a = 0.001
    t, c, v = ripple_fixture(case, f_clk, a)
    m, _ = analyze.analyse_ripple(t, c, v, case, P)
    assert m["modulation_depth"] == pytest.approx(2 * a, rel=0.02)
    assert m["normalized_sensitivity"] == pytest.approx(2 * a / (0.1 / 3.3), rel=0.02)
    assert m["baseline_frequency_hz"] == pytest.approx(f_clk, rel=1e-6)
    assert m["observed_frequency_mean_hz"] == pytest.approx(f_clk, rel=1e-4)
    assert m["observe_periods"] == 10 and m["discard_periods"] == 5
    lo, hi = m["observation_window_s"]
    assert (hi - lo) * f_r == pytest.approx(10) and lo - m["ripple_start_s"] == pytest.approx(5 / f_r)
    assert m["measured_rail"]["peak_to_peak_v"] == pytest.approx(0.1, rel=0.02)
    assert "not a dB PSRR" in m["normalized_sensitivity_definition"]
    assert m["cycles_per_ripple_period"] >= 8
    # zero modulation reports zero depth, not an error
    t, c, v = ripple_fixture(case, f_clk, 0.0)
    assert analyze.analyse_ripple(t, c, v, case, P)[0]["modulation_depth"] < 1e-9


def test_ripple_observation_duration_adapts_to_frequency():
    d = {f: CASES[f"ripple_f{prepare.freq_tag(f)}_tt"] for f in (1e4, 1e5, 1e6)}
    for f, c in d.items():
        assert c["observe_end_s"] - c["observe_start_s"] == pytest.approx(10 / f)
        assert c["observe_start_s"] - c["ripple_start_s"] == pytest.approx(5 / f)
        assert c["tstop_s"] > c["observe_end_s"]
    assert d[1e4]["tstop_s"] > d[1e5]["tstop_s"] > d[1e6]["tstop_s"]
    assert d[1e4]["tstop_s"] == pytest.approx(10e-6 + 15 / 1e4 + 100e-9)


def test_ripple_failures_are_explicit():
    case = ripple_case(1e6, F0)
    t, c, v = ripple_fixture(case, F0, 0.001)

    def fails(msg, tt=t, cc=c, vv=v, cs=case, p=P):
        with pytest.raises(analyze.AnalysisError, match=msg):
            analyze.analyse_ripple(tt, cc, vv, cs, p)
    # record ends before ten full periods have been observed
    n = next(i for i, x in enumerate(t) if x > case["observe_end_s"] - 2 * US)
    fails("insufficient observation duration", tt=t[:n], cc=c[:n], vv=v[:n])
    # ripple (8 MHz) cannot be resolved by a 48 MHz clock: 6 cycles per ripple period
    c8 = dict(CASES["ripple_f1MHz_tt"]); c8["ripple_hz"] = 8e6
    c8["observe_start_s"] = c8["ripple_start_s"] + 5 / 8e6
    c8["observe_end_s"] = c8["ripple_start_s"] + 15 / 8e6
    t8, cc8, vv8 = ripple_fixture(c8, F0, 0.001)
    fails("inadequate resolution", tt=t8, cc=cc8, vv=vv8, cs=c8)
    fails("insufficient baseline cycles", p=analyze.Params(min_cycles=2000))
    o0 = case["observe_start_s"]
    fails("ripple mean rail", vv=[3.3 if x < o0 else 3.6 for x in t])
    fails("measured rail ripple", vv=[x if tx < o0 else 3.3 + (x - 3.3) * 5 for tx, x in zip(t, v)])
    fails("insufficient samples", p=analyze.Params(min_samples_per_cycle=40))
    ts, cs_, vs = ripple_fixture(case, F0, 0.001, spc=8)
    fails("insufficient samples", tt=ts, cc=cs_, vv=vs)
    bad = dict(case); bad["observe_end_s"] = case["observe_end_s"] + 3 / 1e6
    fails("full ripple periods", cs=bad)
    with pytest.raises(analyze.AnalysisError, match="not a ripple case"):
        analyze.analyse_ripple(t, c, v, CASES["step_dn_r1us_tt"], P)


def test_invalid_waveforms_rejected_by_parser():
    ok = {"variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}], "points": [[0, 0, 0], [1, 1, 1]]}
    analyze.parse_waveform(ok)
    for pts, msg in [([[0, 0, 0], [1, float("nan"), 1]], "non-finite"),
                     ([[0, 0, 0], [0, 1, 1]], "strictly increasing"),
                     ([[0, 0, 0]], "fewer than 2")]:
        with pytest.raises(analyze.AnalysisError, match=msg):
            analyze.parse_waveform({"variables": ok["variables"], "points": pts})
    with pytest.raises(analyze.AnalysisError, match="missing signal v\\(vdd\\)"):
        analyze.parse_waveform({"variables": ok["variables"][:2], "points": [[0, 0], [1, 1]]})


# -------------------------------------------------------- report flow ------

@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    d = tmp_path_factory.mktemp("bench") / "b"
    prepare.generate(d, prepare.load_calibration(CAL_RUN))
    return d


def write_wf(tmp, name, tcv):
    t, c, v = tcv
    d = tmp / name
    d.mkdir()
    (d / "waveform.raw.json").write_text(json.dumps({
        "variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
        "points": [list(p) for p in zip(t, c, v)]}))
    return str(d / "waveform.raw.json")


def write_report(tmp, tag, case, wf, status="pass", synthetic=True, remote="job-1", corner=None, **extra):
    c = {"process": case["process"], "temperature_c": case["temperature_c"], "status": "pass",
         "artifacts": {"waveform": wf} if wf else {}}
    rep = {"schema_version": 3, "status": status, "corner_count": 1, "corners": [corner or c],
           "environment": {"remote": remote} if remote else {}, **extra}
    if synthetic:
        rep["synthetic"] = True
    p = tmp / f"report_{tag}.json"
    p.write_text(json.dumps(rep))
    return p


def test_report_flow_ok_fail_and_missing_cases(tmp_path, bench):
    tag = "step_dn_r1us_tt"
    case = CASES[tag]
    wf = write_wf(tmp_path, "good", step_fixture(case, F0, 0.9875 * F0))
    reports = {tag: write_report(tmp_path, tag, case, wf)}
    # refused batch submission
    t2 = "step_up_r1us_tt"
    reports[t2] = write_report(tmp_path, t2, CASES[t2], None, status="refused", error="runner/client version mismatch")
    # per-corner error
    t3 = "step_dn_r100us_tt"
    cr = {"process": "tt", "temperature_c": 27.0, "status": "error", "error": "ngspice crashed", "artifacts": {}}
    reports[t3] = write_report(tmp_path, t3, CASES[t3], None, corner=cr)
    # missing artifact, wrong corner, unreadable waveform, local (non-remote) execution
    t4 = "step_up_r100us_tt"
    reports[t4] = write_report(tmp_path, t4, CASES[t4], None)
    t5 = "ripple_f1MHz_tt"
    reports[t5] = write_report(tmp_path, t5, CASES[t5], wf, corner={"process": "ss", "temperature_c": 27.0,
                                                                      "status": "pass", "artifacts": {"waveform": wf}})
    t6 = "ripple_f100kHz_tt"
    reports[t6] = write_report(tmp_path, t6, CASES[t6], str(tmp_path / "gone" / "waveform.raw.json"))
    t7 = "step_dn_r1us_ss"
    reports[t7] = write_report(tmp_path, t7, CASES[t7], wf, synthetic=False, remote=None)
    reports["bogus_tag"] = reports[tag]
    rows, metas, series = analyze.analyse_all(reports, bench, P)
    by = {r["tag"]: r["status"] for r in rows if r["tag"] in reports and r["tag"] != "bogus_tag"}
    assert by[tag] == "OK"
    assert "refused" in by[t2] and "version mismatch" in by[t2]
    assert "klt corner status" in by[t3] and "ngspice crashed" in by[t3]
    assert "no waveform artifact" in by[t4]
    assert "does not match case" in by[t5]
    assert "unreadable" in by[t6]
    assert "batch fleet" in by[t7]
    assert "not a case of the bench" in next(r["status"] for r in rows if r["tag"] == "bogus_tag")
    missing = [r for r in rows if "missing corner" in r["status"]]
    assert len(missing) == 21 - 7 and not any(r["tag"] in reports for r in missing)
    out = tmp_path / "run"
    doc = analyze.write_run(out, rows, metas, P, synthetic=False, series=series)
    assert doc["synthetic"] is True and doc["measured_evidence"] is False   # propagated from the report
    assert not doc["all_ok"] and doc["n_fail"] == len(rows) - 1
    assert analyze.SYN_BANNER in (out / "summary.md").read_text()
    assert json.loads((out / "results.json").read_text())["label"] == analyze.SYN_BANNER
    assert (out / f"cycles_{tag}.csv").read_text().startswith("cycle_start_s,period_s,frequency_hz")
    assert "settled" in (out / "results.csv").read_text()
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        analyze.write_run(out, rows, metas, P, synthetic=True)


def test_real_report_without_synthetic_flag_is_not_labelled_synthetic(tmp_path, bench):
    tag = "step_dn_r1us_tt"
    wf = write_wf(tmp_path, "g", step_fixture(CASES[tag], F0, 0.9875 * F0))
    rep = write_report(tmp_path, tag, CASES[tag], wf, synthetic=False)
    rows, meta, series = analyze.analyse_report(tag, rep, bench, P)
    assert rows[0]["status"] == "OK"
    doc = analyze.write_run(tmp_path / "o", rows, [meta], P, synthetic=False, series={tag: series})
    assert doc["synthetic"] is False and "measured_evidence" not in doc
    # a local probe is only accepted when explicitly allowed
    local = write_report(tmp_path, "l", CASES[tag], wf, synthetic=False, remote=None)
    assert "batch fleet" in analyze.analyse_report(tag, local, bench, P)[0][0]["status"]
    assert analyze.analyse_report(tag, local, bench, P, allow_local=True)[0][0]["status"] == "OK"


def test_report_shape_errors(tmp_path, bench):
    tag = "step_dn_r1us_tt"
    case = CASES[tag]
    assert "unreadable" in analyze.analyse_report(tag, tmp_path / "nope.json", bench, P)[0][0]["status"]
    bad = tmp_path / "bad.json"; bad.write_text("{not json")
    assert "not valid JSON" in analyze.analyse_report(tag, bad, bench, P)[0][0]["status"]
    empty = write_report(tmp_path, "e", case, None, corner=None); d = json.loads(empty.read_text())
    d["corners"] = []; empty.write_text(json.dumps(d))
    assert "no corners" in analyze.analyse_report(tag, empty, bench, P)[0][0]["status"]
    two = json.loads(empty.read_text()); two["corners"] = [{}, {}]; two["corner_count"] = 2; empty.write_text(json.dumps(two))
    assert "exactly 1 corner" in analyze.analyse_report(tag, empty, bench, P)[0][0]["status"]
    assert "case file unreadable" in analyze.analyse_report("nope", bad, bench, P)[0][0]["status"]
    wf = write_wf(tmp_path, "g", step_fixture(case, F0, 0.9875 * F0))
    rep = write_report(tmp_path, tag, case, wf)
    rows, _, _ = analyze.analyse_report(tag, rep, bench, analyze.Params(min_cycles=900))
    assert rows[0]["status"].startswith("FAIL: insufficient baseline cycles") and "metrics" not in rows[0]
    # missing provenance in the bench directory
    rows, _, _ = analyze.analyse_all({tag: rep}, tmp_path / "nobench", P)
    assert any("provenance.json unreadable" in r["status"] for r in rows)


def test_artifacts_root_and_cli_exit_code(tmp_path, bench):
    tag = "step_dn_r1us_tt"
    case = CASES[tag]
    write_wf(tmp_path, "tt_run", step_fixture(case, F0, 0.9875 * F0))
    rep = write_report(tmp_path, tag, case, "/elsewhere/tt_run/waveform.raw.json")
    rows, _, _ = analyze.analyse_report(tag, rep, bench, P, artifacts_root=tmp_path)
    assert rows[0]["status"] == "OK"
    base = [sys.executable, "-I", str(HERE / "analyze.py"), f"{tag}={rep}", "--bench-dir", str(bench),
            "--artifacts-root", str(tmp_path), "--synthetic"]
    r = subprocess.run(base + ["--outdir", str(tmp_path / "o1")], capture_output=True, text=True)
    assert r.returncode == 1 and "SYNTHETIC" in r.stdout   # the other 20 cases have no report
    r = subprocess.run([sys.executable, "-I", str(HERE / "analyze.py"), "notatag", "--bench-dir", str(bench),
                        "--outdir", str(tmp_path / "o2")], capture_output=True, text=True)
    assert r.returncode == 2 and "TAG=report.json" in r.stderr


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
    monkeypatch.setattr(subprocess, "run", guard)
    return calls


def test_generate_requests_offline(tmp_path, no_sim):
    cal = prepare.load_calibration(CAL_RUN)
    assert cal["codes"] == {"tt": 163, "ss": 205, "ff": 89} and cal["source"]["campaign_utc"]
    prov = prepare.generate(tmp_path / "o", cal)
    out = tmp_path / "o"
    reqs = prov["requests"]
    assert len(reqs) == 21 and len({r["tag"] for r in reqs}) == 21
    assert {(r["process"], r["temperature_c"]) for r in reqs} == {("tt", 27.0), ("ss", -40.0), ("ff", 85.0)}
    kinds = [(r["process"], r["kind"]) for r in reqs]
    assert all(kinds.count((p, "step")) == 4 and kinds.count((p, "ripple")) == 3 for p in ("tt", "ss", "ff"))
    steps = {(c["process"], c["vdd_to_v"], c["ramp_s"]) for c in CASES.values() if c["kind"] == "step"}
    assert steps == {(p, v, r) for p in ("tt", "ss", "ff") for v in (3.0, 3.6) for r in (1e-6, 1e-4)}
    assert {c["ripple_hz"] for c in CASES.values() if c["kind"] == "ripple"} == {1e4, 1e5, 1e6}
    for r in reqs:
        req = json.loads((out / r["request"]).read_text())
        (proc,) = req["corners"]["process"]
        assert req["corners"]["temperature_c"] == [r["temperature_c"]] and r["corner_count"] == 1
        fets, res, mim = prepare.PROCESS_CORNERS[proc["name"]]
        assert proc["sections"] == [fets, res, mim, "cap_mim"]
        assert req["analysis"]["kind"] == "tran" and req["netlist"] == r["netlist"]
        assert req["options"]["waveforms"] and req["options"]["save_mode"] == "netlist"
        assert req["models"] == prepare.MODELS and req["netlist_source"] == "schematic"
        tb = (out / r["netlist"]).read_text()
        assert '.include "rcosc_top_schematic.spice"' in tb and ".save v(clk) v(vdd)" in tb
        assert "CLOAD" not in tb
        code = r["trim_code"]
        assert code == cal["codes"][r["process"]]           # fixed per-process code, no recalibration
        vdd_line = next(l for l in tb.splitlines() if l.startswith(("VDD ", "VRIP ")))
        for i in range(8):
            line = next(l for l in tb.splitlines() if l.startswith((f"VT{i} ", f"ET{i} ")))
            high = bool((code >> i) & 1)
            if r["kind"] == "step":      # high trim pins carry exactly the VDD waveform
                assert (line.split(None, 3)[3] == vdd_line.split(None, 3)[3]) == high
                assert high or line.endswith("DC 0")
            else:                        # ... and follow the rippled VDD node
                assert high == line.startswith(f"ET{i} t{i} 0 vdd 0 1")
        case = json.loads((out / r["case"]).read_text())
        assert case["trim_code"] == code and case["trim_high_pins_follow_vdd"] is True
        for name, h in r["sha256"].items():
            assert prepare.sha256(out / name) == h
        if r["kind"] == "step":
            assert "PWL(0 0 1000n 3.3 10000n 3.3" in tb
            assert f"{case['ramp_end_s'] * 1e9:g}n {case['vdd_to_v']:g})" in tb
            assert req["analysis"]["args"].startswith("200p ") and f"{case['tstop_s'] * 1e9:g}n" in req["analysis"]["args"]
        else:
            assert f"SIN(0 0.05 {case['ripple_hz']:g} 10000n 0 0)" in tb
    pv = prov
    assert pv["calibration"]["campaign_dir"] == "sim/pvt/results/20260923T030125Z"
    assert pv["calibration"]["target"] == "ratified" and pv["calibration"]["manifest_sha256"]
    assert pv["calibration"]["committing_hash"] and pv["calibration"]["campaign_git_sha"]
    assert pv["dut"]["source_sha256"] == prepare.sha256(prepare.SRC)
    assert pv["dut"]["extracted_sha256"] == prepare.sha256(out / "rcosc_top_schematic.spice")
    assert pv["dut"]["relation"] and "dut_changed_since_calibration" in pv["dut"]
    s = pv["settings"]
    assert (s["startup_ramp_ns"], s["disturb_ns"], s["baseline_ns"], s["post_ns"], s["endpoint_ns"]) == \
        (1000.0, 10000.0, 2000.0, 20000.0, 2000.0)
    assert s["ripple_discard"] == 5 and s["ripple_observe"] == 10 and s["band"] == 0.01 and s["load_f"] == 0
    assert s["load_matches_calibration_bench"] is True and "not the ratified" in s["band_note"]
    assert "NOT EVIDENCE" in pv["evidence"]
    assert "forbidden" in pv["execution"]["local_grid_fallback"] and "2851" in pv["execution"]["preflight_required"]
    assert "--backend batch" in pv["execution"]["backend"]
    assert all(cm[0] == "git" for cm in no_sim)
    # the existing startup tooling's request keys are the same shape
    st = json.loads((prepare.REPO / "sim" / "startup" / "request_v33.json").read_text())
    assert set(st) == set(req)


def test_generation_is_deterministic_and_append_only(tmp_path):
    cal = prepare.load_calibration(CAL_RUN)
    prepare.generate(tmp_path / "a", cal)
    prepare.generate(tmp_path / "b", cal)
    fa = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert fa == sorted(p.name for p in (tmp_path / "b").iterdir()) and len(fa) == 21 * 3 + 2
    for n in fa:
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes(), n
    with pytest.raises(prepare.PrepareError, match="not empty"):
        prepare.generate(tmp_path / "a", cal)
    # nothing is written beside the generator
    before = sorted(p.name for p in HERE.iterdir())
    prepare.generate(tmp_path / "c", cal)
    assert sorted(p.name for p in HERE.iterdir()) == before


def test_config_is_recorded_and_validated(tmp_path):
    cal = prepare.load_calibration(CAL_RUN)
    prov = prepare.generate(tmp_path / "x", cal, {"load_f": 1e-12, "band": 0.02, "post_ns": 30000})
    assert prov["settings"]["load_matches_calibration_bench"] is False and prov["settings"]["band"] == 0.02
    assert "CLOAD clk 0 1e-12" in (tmp_path / "x" / prov["requests"][0]["netlist"]).read_text()
    assert json.loads((tmp_path / "x" / "case_step_dn_r1us_tt.json").read_text())["tstop_s"] == pytest.approx(41e-6)
    for bad in ({"baseline_ns": 9500}, {"post_ns": 1000}, {"band": 0}, {"band": 1.5}, {"min_cycles": 1},
                {"ripple_observe": 1}, {"disturb_ns": -1}, {"load_f": -1e-12}):
        with pytest.raises(prepare.PrepareError):
            prepare.generate(tmp_path / ("bad" + str(sorted(bad.items()))), cal, bad)


def test_dut_relation_reported_and_strict_mode(tmp_path):
    cal = prepare.load_calibration(CAL_RUN)
    rel = prepare.dut_vs_calibration(cal["source"])
    assert rel["relation"].split(":")[0] in ("CHANGED", "UNVERIFIED", "UNKNOWN", "unchanged since the calibration campaign commit")
    unknown = prepare.dut_vs_calibration(cal["source"] | {"campaign_git_sha": "0" * 40})
    assert unknown["relation"].startswith("UNKNOWN") and unknown["dut_changed_since_calibration"] is None
    with pytest.raises(prepare.PrepareError, match="strict-dut"):
        prepare.generate(tmp_path / "s", cal | {"source": cal["source"] | {"campaign_git_sha": "0" * 40}}, strict_dut=True)


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
    for edit, msg in [(lambda m: m["calibration_spec_target"]["ss"].__setitem__("code", 300), "invalid"),
                      (lambda m: m["calibration_spec_target"]["ss"].__setitem__("code", True), "invalid"),
                      (lambda m: m["calibration_spec_target"]["ff"].__setitem__("saturated", True), "saturated"),
                      (lambda m: m["calibration_spec_target"].pop("tt"), "lacks process"),
                      (lambda m: m["calibration_spec_target"]["tt"].__setitem__("code", 164), "holds code"),
                      (lambda m: m.pop("calibration_spec_target"), "calibration campaign manifest")]:
        m = json.loads(json.dumps(man)); edit(m); put(m)
        with pytest.raises(prepare.PrepareError, match=msg):
            load()
    put(man)
    with pytest.raises(prepare.PrepareError, match="unknown calibration target"):
        load(target="bogus")
    (d / "manifest.json").write_text("{not json")
    with pytest.raises(prepare.PrepareError, match="not valid JSON"):
        load()
    put(man)
    (d / "results.csv").write_text("\n".join((d / "results.csv").read_text().splitlines()[:-300]) + "\n")
    with pytest.raises(prepare.PrepareError, match="does not cover"):
        load()
    (d / "results.csv").unlink()
    with pytest.raises(prepare.PrepareError, match="no results.csv"):
        load()
    (d / "manifest.json").unlink()
    with pytest.raises(prepare.PrepareError, match="no manifest"):
        load()


def test_uncommitted_calibration_rejected(tmp_path):
    with pytest.raises(prepare.PrepareError, match="not a committed"):
        prepare.load_calibration(cal_copy(tmp_path))


def test_cli_requires_explicit_calibration_and_output(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(HERE / "prepare.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "--cal-run" in r.stderr
    r = subprocess.run([sys.executable, "-I", str(HERE / "prepare.py"), "--cal-run", str(CAL_RUN)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "--out" in r.stderr
    r = subprocess.run([sys.executable, "-I", str(HERE / "prepare.py"), "--cal-run", str(tmp_path / "nocal"),
                        "--out", str(tmp_path / "o")], capture_output=True, text=True)
    assert r.returncode != 0 and "no manifest.json" in r.stderr
    r = subprocess.run([sys.executable, "-I", str(HERE / "prepare.py"), "--cal-run", str(CAL_RUN),
                        "--out", str(tmp_path / "ok")], capture_output=True, text=True)
    assert r.returncode == 0 and "wrote 21 request(s)" in r.stdout and "calibration source age" in r.stderr
