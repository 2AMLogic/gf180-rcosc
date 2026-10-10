"""Offline tests for sim/discipline/outage_model.py (issue #128).  SYNTHETIC fixtures only; no
PDK, simulator, cloud, or CSV access, and results/ is never read or written.

Run:  python3 -I -m pytest -p no:cacheprovider sim/discipline/test_outage.py
"""
import importlib.util
import random
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


om = _load("outage_model_t", "outage_model.py")
dm = om.dm
OP = (27.0, 3.3)


@pytest.fixture(autouse=True)
def no_sim(monkeypatch):
    def guard(cmd, *a, **k):
        raise AssertionError(f"offline test must not run subprocesses: {cmd}")
    monkeypatch.setattr(subprocess, "run", guard)
    monkeypatch.setattr(subprocess, "Popen", guard)


def make_plant(fn, gain=None):
    g = gain or {(T, V): 1.0 for T in dm.TS for V in dm.VS}
    pl = dm.Plant.__new__(dm.Plant)
    pl.name, pl.side, pl.a, pl.b, pl.g, pl.anchors = "syn", "sch", 0.0, 0.0, g, {}
    pl.F = [fn(c) for c in range(256)]
    return pl


def linear_plant():
    return make_plant(lambda c: dm.F_TARGET * (1 + 0.003 * (c - 100)))


class Spy:
    """Controller stub that records every error it is handed and never moves the code."""
    log = []
    def __init__(s, c0): s.c = c0; Spy.log = []
    def update(s, e): Spy.log.append(e); return s.c


def const_plant(ratio):
    return make_plant(lambda c: dm.F_TARGET * ratio)


# ---------------------------------------------------------- schedules -----

def test_valid_schedule_single_loss_invalidates_two_frames():
    lost = om.outage_schedule(8, 3, 1)
    assert om.valid_schedule(lost) == [True, True, True, False, False, True, True, True]


def test_valid_schedule_long_outage():
    v = om.valid_schedule(om.outage_schedule(10, 2, 4))
    assert [i for i, x in enumerate(v) if not x] == [2, 3, 4, 5, 6]   # L + 1 frames


# ------------------------------------------------- no-loss regression -----

@pytest.mark.parametrize("policy", dm.POLICIES)
@pytest.mark.parametrize("jitter", [0.0, 500.0])
def test_no_loss_reproduces_run_loop_exactly(policy, jitter):
    pl = linear_plant()
    prof = [OP] * 600 + [(85.0, 3.0)] * 100
    e0, c0 = dm.run_loop(pl, policy, 128, prof, jitter, random.Random(7))
    for lost in (None, [False] * len(prof)):
        r = om.run_loop_outage(pl, policy, 128, prof, jitter, random.Random(7), lost)
        assert r["errs"] == e0 and r["codes"] == c0      # tolerance 0
        assert set(r["ref_state"]) == {"tracking"}


# ------------------------------------------ hand-calculated fixtures -----

def test_missing_observation_never_becomes_nominal_frame_update():
    # f = 1.01 * 48 MHz: every one-frame count is 48 480 (error +480); a two-frame span is 96 960.
    pl = const_plant(1.01)
    n = 10
    r = om.run_loop_outage(pl, Spy, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, 4, 1))
    assert r["valid"] == [True] * 4 + [False, False] + [True] * 4
    seen = [o for o in r["obs"] if o is not None]
    assert len(seen) == 8                               # frames 4 and 5 deliver nothing
    assert all(abs(o - 480) <= 1 for o in seen)         # never 48 960 (span - nominal)
    assert max(Spy.log) < 1000


def test_naive_contrast_fixture_shows_the_hazard():
    pl = const_plant(1.01)
    n = 10
    r = om.run_loop_outage(pl, Spy, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, 4, 1), mode="naive_nominal")
    # frame 5 closes the 2-frame span 2*48 480 = 96 960 -> "error" 48 960 counts (~102 %)
    assert any(abs(o - 48960) <= 2 for o in r["obs"] if o is not None)


def test_multi_frame_outage_span_is_not_delivered():
    pl = const_plant(1.01)
    n = 40
    r = om.run_loop_outage(pl, Spy, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, 10, 16))
    assert [i for i, o in enumerate(r["obs"]) if o is None] == list(range(10, 27))   # 16 lost + 1 baseline
    assert all(abs(o - 480) <= 1 for o in r["obs"] if o is not None)


@pytest.mark.parametrize("policy", dm.POLICIES)
def test_state_frozen_during_outage_and_resumes_after_fresh_interval(policy):
    pl = linear_plant()
    s, L, n = 300, 16, 700
    r = om.run_loop_outage(pl, policy, 104, [OP] * n, 0.0, random.Random(1), om.outage_schedule(n, s, L), trace_state=True)
    # state after frame s-1's update is the reference; frozen through the L lost + 1 baseline frames
    ref = r["states"][s - 1]
    for i in range(s, s + L + 1):
        assert r["states"][i] == ref, (policy.name, i)
        assert r["obs"][i] is None
    assert all(r["codes"][i] == r["codes"][s] for i in range(s, s + L + 2))
    # first delivered observation after the outage is frame s+L+1 (second arrival), one nominal frame
    first = next(i for i in range(s, n) if r["obs"][i] is not None)
    assert first == s + L + 1
    assert abs(r["obs"][first]) < 2000                 # a single-frame count error, not a span


def test_frozen_code_gives_unchanged_trim_but_drifting_true_frequency():
    # plant gain steps +1 % at 85 C; the profile switches at the outage start
    g = {(T, V): (1.01 if T == 85.0 else 1.0) for T in dm.TS for V in dm.VS}
    pl = make_plant(lambda c: dm.F_TARGET * (1 + 0.003 * (c - 100)), g)
    s, L = 2000, 16
    prof = [OP] * (s + 5) + [(85.0, 3.3)] * 3000
    n = len(prof)
    run = om.run_loop_outage(pl, dm.BangBang, 128, prof, 0.0, random.Random(0), om.outage_schedule(n, s, L))
    base = om.run_loop_outage(pl, dm.BangBang, 128, prof, 0.0, random.Random(0))
    a = om.analyze(pl, run, base, s, L, (85.0, 3.3))
    assert a["observed_during_outage"] == "none"
    assert a["true_drift_during_holdover"] == pytest.approx(1.0, abs=0.35)   # about +1 % true drift
    assert a["frozen_code"] == run["codes"][s]
    assert a["update_resume_frames_after_outage_end"] == 1
    assert a["status_avg16"] == "recovered"


# ------------------------------------------------ recovery outcomes -----

def test_saturated_plant_is_plant_unreachable_not_controller_failure():
    pl = make_plant(lambda c: dm.F_TARGET * (0.5 + 0.001 * c))     # even 0xFF is far too slow
    s, L, n = 500, 16, 500 + 16 + om.TAIL
    run = om.run_loop_outage(pl, dm.Deadband, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, s, L))
    base = om.run_loop_outage(pl, dm.Deadband, 128, [OP] * n, 0.0, random.Random(0))
    a = om.analyze(pl, run, base, s, L, OP)
    assert a["rail_contact"] and a["final_code"] == 255
    assert a["reacq_inst_frames"] is None and a["reacq_avg16_frames"] is None
    assert a["status_inst"] == a["status_avg16"] == "plant_unreachable"
    assert a["baseline_status_avg16"] == "plant_unreachable"


class Stuck:
    """Reachable plant but a controller that never corrects: explicit never-recovers outcome."""
    def __init__(s, c0): s.c = c0
    def update(s, e): return s.c


def test_stuck_controller_on_reachable_plant_is_controller_not_recovered():
    pl = linear_plant()        # target at code 100, reachable; Stuck stays at 128 (+8.4 %)
    s, L, n = 500, 16, 500 + 16 + om.TAIL
    run = om.run_loop_outage(pl, Stuck, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, s, L))
    base = om.run_loop_outage(pl, Stuck, 128, [OP] * n, 0.0, random.Random(0))
    a = om.analyze(pl, run, base, s, L, OP)
    assert a["status_inst"] == a["status_avg16"] == "controller_not_recovered"
    assert a["reachable_inst"] and a["reachable_avg16"]
    assert a["max_excursion_pct"] == pytest.approx(8.4, abs=0.01)


@pytest.mark.parametrize("policy", dm.POLICIES)
@pytest.mark.parametrize("L", [1, 16, 256])
def test_locked_loop_recovers_after_outage_at_constant_conditions(policy, L):
    pl = linear_plant()
    s = 6000
    n = s + L + om.TAIL
    run = om.run_loop_outage(pl, policy, 128, [OP] * n, 0.0, random.Random(0), om.outage_schedule(n, s, L))
    base = om.run_loop_outage(pl, policy, 128, [OP] * n, 0.0, random.Random(0))
    a = om.analyze(pl, run, base, s, L, OP)
    assert a["status_avg16"] == "recovered"
    if policy is not dm.FracDither:                   # dither's own 16-frame mean is not always in band
        assert a["reacq_avg16_frames"] == 0           # frozen on-target code stays in band
    assert a["true_drift_during_holdover"] == 0.0
    assert not a["rail_contact"]


def test_no_locked_label_anywhere():
    r = om.run_loop_outage(linear_plant(), dm.Deadband, 128, [OP] * 50, 0.0, random.Random(0), om.outage_schedule(50, 10, 5))
    assert set(r["ref_state"]) == {"tracking", "holdover", "reacquiring"}
    assert r["ref_state"][10:15] == ["holdover"] * 5 and r["ref_state"][15] == "reacquiring"
    assert not any("lock" in s for s in r["ref_state"])


def test_reach_distinguishes_inst_and_avg_readings():
    # codes are 0.8 % apart and straddle the target at +/-0.4 %: dithering can reach the band, no single code can
    pl = make_plant(lambda c: dm.F_TARGET * (1 + 0.008 * (c - 100) + 0.004))
    rc = om.reach(pl, *OP)
    assert rc == {"inst": False, "avg": True}
    assert om.reach(const_plant(1.1), *OP) == {"inst": False, "avg": False}


def test_deterministic_and_zero_jitter_consumes_no_rng():
    pl = linear_plant()
    a = om.run_loop_outage(pl, dm.FracDither, 128, [OP] * 300, 500.0, random.Random(3), om.outage_schedule(300, 100, 16))
    b = om.run_loop_outage(pl, dm.FracDither, 128, [OP] * 300, 500.0, random.Random(3), om.outage_schedule(300, 100, 16))
    assert a["errs"] == b["errs"] and a["obs"] == b["obs"]
    rng = random.Random(5)
    om.run_loop_outage(pl, dm.Deadband, 128, [OP] * 50, 0.0, rng, om.outage_schedule(50, 10, 5))
    assert rng.random() == random.Random(5).random()


def test_bad_arguments_rejected():
    with pytest.raises(ValueError):
        om.run_loop_outage(linear_plant(), dm.Deadband, 128, [OP] * 5, 0.0, random.Random(0), [False] * 4)
    with pytest.raises(ValueError):
        om.run_loop_outage(linear_plant(), dm.Deadband, 128, [OP] * 5, 0.0, random.Random(0), None, mode="bogus")


@pytest.mark.parametrize("case", om.CASES)
def test_profiles_have_outage_inside_and_tail_after(case):
    prof, s = om.make_profile(case, 256 + om.TAIL)
    assert 0 < s and len(prof) == s + 256 + om.TAIL
