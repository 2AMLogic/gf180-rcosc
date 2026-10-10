"""Offline tests for the pure analysis cores of the legacy sim drivers
(issue #121): sim/pvt/pvt_sweep.py (calibrate, pct, spread),
sim/startup/startup_report.py (rising_edges, analyse) and
sim/iq/iq_sweep.py (verdict, _grab).

Every input here is a SYNTHETIC FIXTURE built in memory or in pytest's tmp_path.
Nothing is measured evidence; no ngspice, PDK, klt or network is used and
nothing is written under sim/*/results/.

Run:  python3 -I -m pytest -p no:cacheprovider sim/legacy-analysis/test_analysis_cores.py
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


pvt = _load("pvt_sweep", SIM / "pvt" / "pvt_sweep.py")
startup = _load("startup_report_t", SIM / "startup" / "startup_report.py")
iq = _load("iq_sweep_t", SIM / "iq" / "iq_sweep.py")


# ---------------------------------------------------------------- pvt: pct

def test_pct_sign_and_reference():
    assert pvt.pct(110.0, 100.0) == pytest.approx(10.0)
    assert pvt.pct(90.0, 100.0) == pytest.approx(-10.0)
    assert pvt.pct(100.0, 100.0) == 0.0
    # the reference is the denominator, not the value
    assert pvt.pct(50.0, 100.0) == pytest.approx(-50.0)
    assert pvt.pct(100.0, 50.0) == pytest.approx(100.0)


# -------------------------------------------------------------- pvt: spread

def _res(f_hz, code=0x80):
    pt = pvt.Point("tt", 27.0, 3.3, code)
    return pvt.Result(pt, f_hz, None, "ok", "", 1200)


def _results(freqs):
    out = {}
    for i, f in enumerate(freqs):
        r = _res(f, code=i)
        out[r.point] = r
    return out


def test_spread_hand_computed():
    s = pvt.spread(_results([90e6, 100e6, 120e6]), 100e6)
    assert s["n"] == 3
    assert s["min_hz"] == 90e6 and s["max_hz"] == 120e6
    assert s["mean_hz"] == pytest.approx(310e6 / 3)
    assert s["ref_hz"] == 100e6
    assert s["lo_pct"] == pytest.approx(-10.0)
    assert s["hi_pct"] == pytest.approx(20.0)
    # half span is relative to (hi+lo), NOT to the reference
    assert s["half_span_pct"] == pytest.approx(30.0 / 210.0 * 100.0)


def test_spread_ignores_missing_and_zero_measurements():
    s = pvt.spread(_results([None, 100e6, 0.0, 110e6]), 100e6)
    assert s["n"] == 2
    assert s["min_hz"] == 100e6 and s["max_hz"] == 110e6


@pytest.mark.parametrize("freqs,ref", [([], 100e6), ([None, None], 100e6),
                                       ([100e6], None), ([100e6], 0.0)])
def test_spread_empty_or_no_reference_is_nan_not_error(freqs, ref):
    s = pvt.spread(_results(freqs), ref)
    assert s["n"] == 0
    assert s["min_hz"] is None and s["max_hz"] is None and s["mean_hz"] is None
    assert s["ref_hz"] == ref
    for k in ("lo_pct", "hi_pct", "half_span_pct"):
        assert math.isnan(s[k])


def test_spread_single_point_has_zero_half_span():
    s = pvt.spread(_results([100e6]), 100e6)
    assert s["half_span_pct"] == 0.0 and s["lo_pct"] == s["hi_pct"] == 0.0


# ----------------------------------------------------------- pvt: calibrate

class FakeSim:
    """Stands in for pvt_sweep.simulate: f_hz = fn(code); counts calls."""

    def __init__(self, fn, none_codes=()):
        self.fn, self.none_codes, self.calls = fn, set(none_codes), []

    def __call__(self, camp, netlist_text, points):
        out = {}
        for pt in points:
            assert (pt.process, pt.temp_c, pt.vdd_v) == ("ss", pvt.REF_TEMP_C, pvt.REF_VDD_V)
            self.calls.append(pt.code)
            f = None if pt.code in self.none_codes else self.fn(pt.code)
            out[pt] = pvt.Result(pt, f, None, "ok" if f else "nomeas", "", 1200)
        return out


def _calibrate(monkeypatch, fake, target):
    monkeypatch.setattr(pvt, "simulate", fake)
    return pvt.calibrate(None, "", "ss", target)


def linear(code):  # 10 MHz .. 265 MHz, 1 MHz/code
    return 10e6 + code * 1e6


def test_calibrate_exact_hit(monkeypatch):
    code, f, sat = _calibrate(monkeypatch, FakeSim(linear), 100e6)
    assert (code, f, sat) == (90, 100e6, False)


def test_calibrate_lands_on_nearest_code_both_sides(monkeypatch):
    # 100.4 MHz is between code 90 (100) and 91 (101): nearer to 90
    assert _calibrate(monkeypatch, FakeSim(linear), 100.4e6)[0] == 90
    # 100.6 MHz: nearer to 91
    assert _calibrate(monkeypatch, FakeSim(linear), 100.6e6)[0] == 91
    # exact midpoint tie resolves to the lower code (<=)
    assert _calibrate(monkeypatch, FakeSim(linear), 100.5e6)[0] == 90


@pytest.mark.parametrize("target", [1e6, 10e6])
def test_calibrate_below_range_reports_saturation_at_0x00(monkeypatch, target):
    code, f, sat = _calibrate(monkeypatch, FakeSim(linear), target)
    assert (code, f, sat) == (0x00, 10e6, True)


@pytest.mark.parametrize("target", [265e6, 900e6])
def test_calibrate_above_range_reports_saturation_at_0xFF(monkeypatch, target):
    code, f, sat = _calibrate(monkeypatch, FakeSim(linear), target)
    assert (code, f, sat) == (0xFF, 265e6, True)


def test_calibrate_in_range_is_not_saturated_at_extremes(monkeypatch):
    code, _, sat = _calibrate(monkeypatch, FakeSim(linear), 11e6)
    assert (code, sat) == (1, False)
    code, _, sat = _calibrate(monkeypatch, FakeSim(linear), 264e6)
    assert (code, sat) == (254, False)


def test_calibrate_terminates_in_bounded_simulations(monkeypatch):
    fake = FakeSim(linear)
    _calibrate(monkeypatch, fake, 123.4e6)
    # 2 endpoints + <=8 bisection steps + 2 final reads
    assert len(fake.calls) <= 12


def test_calibrate_non_monotone_terminates_and_reports_own_f(monkeypatch):
    # a local dip at the 0x0F -> 0x10 block boundary (the documented case)
    def dippy(code):
        return linear(code) - (3e6 if code >= 0x10 and code < 0x20 else 0.0)

    fake = FakeSim(dippy)
    target = 30e6
    code, f, sat = _calibrate(monkeypatch, fake, target)
    assert sat is False
    assert f == dippy(code)  # the returned f is the returned code's own f
    assert len(fake.calls) <= 12
    # locally suboptimal at most by the dip magnitude
    best = min(abs(dippy(c) - target) for c in range(256))
    assert abs(f - target) <= best + 3e6


def test_calibrate_fully_non_monotone_still_terminates(monkeypatch):
    # f descending in the middle: endpoints define the range, search must stop
    def wild(code):
        return 10e6 + (code % 7) * 30e6 + (255 if code == 255 else 0)

    fake = FakeSim(wild)
    code, f, sat = _calibrate(monkeypatch, fake, 100e6)
    assert 0 <= code <= 0xFF and f == wild(code)
    assert len(fake.calls) <= 12


def test_calibrate_exits_when_a_point_has_no_measurement(monkeypatch):
    with pytest.raises(SystemExit) as e:
        _calibrate(monkeypatch, FakeSim(linear, none_codes={0x00}), 100e6)
    assert "no measurement" in str(e.value)


# ----------------------------------------------------- startup: rising_edges

def test_rising_edges_interpolates_linearly():
    t = [0.0, 1.0, 2.0, 3.0]
    v = [0.0, 0.0, 2.0, 2.0]
    assert startup.rising_edges(t, v, 1.0) == [pytest.approx(1.5)]


def test_rising_edges_ignores_falling_and_flat():
    t = [0, 1, 2, 3, 4]
    v = [2.0, 0.0, 0.0, 2.0, 0.0]
    e = startup.rising_edges(t, v, 1.0)
    assert e == [pytest.approx(2.5)]


def test_rising_edges_threshold_touch_counts_once():
    # v[i] == vmid exactly counts as a crossing at that sample (<=)
    assert startup.rising_edges([0, 1, 2], [0.0, 1.0, 2.0], 1.0) == [pytest.approx(1.0)]
    # starting exactly at vmid and staying there is not a rising edge
    assert startup.rising_edges([0, 1, 2], [1.0, 1.0, 1.0], 1.0) == []


def test_rising_edges_no_edges_and_short_input():
    assert startup.rising_edges([], [], 1.0) == []
    assert startup.rising_edges([0.0], [0.0], 1.0) == []
    assert startup.rising_edges([0, 1], [0.0, 0.5], 1.0) == []


# ------------------------------------------------------------ startup: analyse

VDD = 3.3


def _write_wf(tmp_path, t, clk, vdd):
    w = {"variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
         "points": [[a, b, c] for a, b, c in zip(t, clk, vdd)]}
    p = tmp_path / "wf.json"
    p.write_text(json.dumps(w))
    return str(p)


def _square(tmp_path, edge_times, tstop, vdd_fn=None, dt=0.1e-9):
    """Clock that rises through VDD/2 at each edge_times entry (1 ns rise,
    returns low half way to the next edge). Sampled at dt."""
    n = int(round(tstop / dt)) + 1
    t = [i * dt for i in range(n)]
    clk = []
    for x in t:
        level = 0.0
        for k, e in enumerate(edge_times):
            nxt = edge_times[k + 1] if k + 1 < len(edge_times) else e + 1e-6
            if e - 0.5e-9 <= x < e + 0.5e-9:
                level = VDD * (x - (e - 0.5e-9)) / 1e-9
                break
            if e + 0.5e-9 <= x < (e + nxt) / 2:
                level = VDD
                break
        clk.append(level)
    vdd = [vdd_fn(x) if vdd_fn else VDD for x in t]
    return _write_wf(tmp_path, t, clk, vdd)


PER = 40e-9


def test_analyse_steady_clock_starts_and_settles_immediately(tmp_path):
    edges = [100e-9 + k * PER for k in range(120)]  # to 4.9 us
    wf = _square(tmp_path, edges, 5.0e-6, dt=0.5e-9)
    r, e = startup.analyse(wf, VDD)
    assert r["status"] == "STARTED"
    assert len(e) == r["n_edges"] == 120
    assert r["f_settled_mhz"] == pytest.approx(25.0, rel=1e-3)
    assert r["tail_dev_pct"] < 0.5
    for lab, _ in startup.BANDS:
        assert r[f"t_settle_{lab}_ns"] == pytest.approx(e[0] * 1e9)
    assert r["tstop_ns"] == pytest.approx(5000.0)


def test_analyse_late_first_edge_reports_late_settle_time(tmp_path):
    # no clk activity until 6 us; steady afterwards. Run to 8.5 us so the tail
    # (last 2 us) is all steady. Settle time == first edge, i.e. 6 us.
    edges = [6.0e-6 + k * PER for k in range(60)]  # to 8.4 us
    wf = _square(tmp_path, edges, 8.5e-6, dt=0.5e-9)
    r, e = startup.analyse(wf, VDD)
    assert r["n_edges"] == 60 and r["status"] == "STARTED"
    assert r["t_settle_1.1%_ns"] == pytest.approx(6000.0, abs=1.0)
    assert r["t_settle_1.1%_ns"] / 1e3 <= startup.SPEC_US  # still within 10 us


def test_analyse_slow_initial_cycles_set_band_dependent_settle(tmp_path):
    # first 10 cycles are 20% slow, then steady: settles after the slow cycles
    # in the 1.1% and 2.9% bands, but the +/-10.8% band sees them as bad too.
    edges, t = [], 100e-9
    for k in range(130):
        edges.append(t)
        t += PER * (1.2 if k < 10 else 1.0)
    wf = _square(tmp_path, edges, edges[-1] + 20e-9, dt=0.5e-9)
    r, e = startup.analyse(wf, VDD)
    assert r["status"] == "STARTED"
    for lab, _ in startup.BANDS:
        ts = r[f"t_settle_{lab}_ns"]
        assert ts is not None and ts > e[0] * 1e9
    # the wider the band, no later the settle time
    s = [r[f"t_settle_{lab}_ns"] for lab, _ in startup.BANDS]
    assert s == sorted(s, reverse=True)


def test_analyse_no_edges_is_non_start_not_missing_number(tmp_path):
    t = [i * 1e-9 for i in range(5001)]
    wf = _write_wf(tmp_path, t, [0.0] * len(t), [VDD] * len(t))
    r, e = startup.analyse(wf, VDD)
    assert e == []
    assert r["status"] == "NON-START"
    assert r["n_edges"] == 0 and r["n_tail_edges"] == 0
    assert "t_settle_1.1%_ns" not in r


def test_analyse_glitch_edges_are_non_start(tmp_path):
    # a handful of early glitches then silence: < MIN_EDGES overall
    edges = [50e-9 + k * 5e-9 for k in range(5)]
    wf = _square(tmp_path, edges, 5.0e-6, dt=0.5e-9)
    r, _ = startup.analyse(wf, VDD)
    assert r["n_edges"] == 5 and r["status"] == "NON-START"


def test_analyse_enough_edges_but_dead_tail_is_non_start(tmp_path):
    # 40 edges all in the first 2 us, nothing in the last 2 us of a 5 us run
    edges = [100e-9 + k * PER for k in range(40)]
    wf = _square(tmp_path, edges, 5.0e-6, dt=0.5e-9)
    r, _ = startup.analyse(wf, VDD)
    assert r["n_edges"] >= startup.MIN_EDGES
    assert r["n_tail_edges"] < startup.MIN_TAIL_EDGES
    assert r["status"] == "NON-START"


def test_analyse_unsteady_tail_is_not_settled(tmp_path):
    # drift the period slowly (a pure 2-cycle alternation would be averaged
    # away by the WIN=8 window)
    edges, t = [], 100e-9
    for k in range(120):
        edges.append(t)
        t += 40e-9 * (1.0 + 0.002 * k)
    wf = _square(tmp_path, edges, edges[-1] + 20e-9, dt=0.5e-9)
    r, _ = startup.analyse(wf, VDD)
    assert r["status"].startswith("NOT-SETTLED")
    assert r["tail_dev_pct"] > startup.TAIL_TOL * 100


def test_analyse_t_vdd90_and_clk_extrema(tmp_path):
    edges = [100e-9 + k * PER for k in range(120)]
    ramp = lambda x: min(VDD, VDD * x / 1000e-9)
    wf = _square(tmp_path, edges, 5.0e-6, vdd_fn=ramp, dt=0.5e-9)
    r, _ = startup.analyse(wf, VDD)
    assert r["t_vdd90_ns"] == pytest.approx(900.0, abs=1.0)
    assert r["clk_min_v"] == 0.0 and r["clk_max_v"] == pytest.approx(VDD)


# --------------------------------------------------------------- iq: verdict

def test_verdict_boundary_at_exactly_the_limit():
    assert iq.TARGET_UA == 500.0
    assert iq.verdict(499.999) == "met"
    assert iq.verdict(500.0) == "**exceeds**"  # strict <, the limit itself fails
    assert iq.verdict(500.001) == "**exceeds**"


def test_verdict_none_and_extremes():
    assert iq.verdict(None) == "no measurement"
    assert iq.verdict(0.0) == "met"  # zero is a measurement, not "missing"
    assert iq.verdict(1e9) == "**exceeds**"


# ----------------------------------------------------------------- iq: _grab

def test_grab_parses_ngspice_style_values():
    out = "iq_ua = 4.123456e+02\nother = 1\n"
    assert iq._grab(r"iq_ua\s*=\s*" + iq.NUM, out) == pytest.approx(412.3456)


def test_grab_negative_and_signed_exponent():
    assert iq._grab(r"x\s*=\s*" + iq.NUM, "x = -1.5e-09\n") == pytest.approx(-1.5e-9)
    assert iq._grab(r"x\s*=\s*" + iq.NUM, "x = +2E+3\n") == 2000.0


def test_grab_missing_returns_none():
    assert iq._grab(r"iq_ua\s*=\s*" + iq.NUM, "nothing here\n") is None


def test_grab_does_not_confuse_iq_ua_with_iq_run_ua():
    out = "iq_run_ua = 111.0\niq_ua = 222.0\n"
    assert iq._grab(r"iq_ua\s*=\s*" + iq.NUM, out) == 222.0
    assert iq._grab(r"iq_run_ua\s*=\s*" + iq.NUM, out) == 111.0


def test_grab_first_match_wins_and_is_line_anchored_search():
    out = "t_avg_start = 1e-9\nt_avg_start = 2e-9\n"
    assert iq._grab(r"t_avg_start\s*=\s*" + iq.NUM, out) == pytest.approx(1e-9)
