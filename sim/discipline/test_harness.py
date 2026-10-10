"""Offline tests for sim/discipline/discipline_model.py (issue #120).  Every plant
and series here is a SYNTHETIC FIXTURE built in this file; nothing is measured
evidence and no simulator, klt, or cloud operation is invoked.  The tests never
read or write sim/discipline/results/ (results are append-only evidence) and
never call build() (which reads committed CSVs) or main() (which writes results).

Run:  python3 -I -m pytest -p no:cacheprovider sim/discipline/test_harness.py
"""
import importlib.util
import math
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


dm = _load("disc_model_t", "discipline_model.py")
OP = (27.0, 3.3)


@pytest.fixture
def no_sim(monkeypatch):
    """Offline guard: no subprocess of any kind may be spawned."""
    def guard(cmd, *a, **k):
        raise AssertionError(f"offline test must not run subprocesses: {cmd}")
    monkeypatch.setattr(subprocess, "run", guard)
    monkeypatch.setattr(subprocess, "Popen", guard)


# ------------------------------------------------------------ fixtures -----

def make_plant(fn, name="syn", side="sch"):
    """SYNTHETIC plant with F[c] = fn(c) and unity T/V gain (no CSV access)."""
    g = {(T, V): 1.0 for T in dm.TS for V in dm.VS}
    pl = dm.Plant.__new__(dm.Plant)
    pl.name, pl.side, pl.a, pl.b, pl.g, pl.anchors = name, side, 0.0, 0.0, g, {}
    pl.F = [fn(c) for c in range(256)]
    return pl


C_STAR = 100
SLOPE = 0.003   # 0.3 %/code, = 144 counts/code, well above the 75-count deadband


def linear_plant():
    """f = 48 MHz * (1 + 0.003*(c-100)); target exactly at code 100."""
    return make_plant(lambda c: dm.F_TARGET * (1 + SLOPE * (c - C_STAR)))


def run(pl, policy, c0, frames=12000, jitter=0.0, seed=1, profile=None):
    return dm.run_loop(pl, policy, c0, profile or [OP] * frames, jitter, random.Random(seed))


# ----------------------------------------------------------- plant gain ----

def test_unity_gain_plant_f_is_F(no_sim):
    pl = linear_plant()
    assert pl.f(77, -40.0, 3.0) == pl.F[77]
    assert pl.f(77, 200.0, 9.0) == pl.F[77]   # T/V clamped to the grid


# ---------------------------------------------------------- controllers ----

@pytest.mark.parametrize("policy", dm.POLICIES)
@pytest.mark.parametrize("c0", [20, 128, 240])
def test_converges_on_noiseless_linear_plant(no_sim, policy, c0):
    errs, codes = run(linear_plant(), policy, c0)
    tail = codes[-500:]
    assert all(abs(c - C_STAR) <= 1 for c in tail), (policy.name, min(tail), max(tail))
    assert all(abs(e) <= 1.01 * SLOPE * 100 for e in errs[-500:])
    assert codes[0] == c0


def test_deadband_and_avg_hold_exactly_at_target(no_sim):
    for policy in (dm.Deadband, dm.AvgStep):
        _, codes = run(linear_plant(), policy, 128)
        assert set(codes[-500:]) == {C_STAR}, policy.name


@pytest.mark.parametrize("policy", dm.POLICIES)
def test_saturates_low_when_always_too_fast(no_sim, policy):
    pl = make_plant(lambda c: dm.F_TARGET * (1.2 + 0.001 * c))   # never reaches target
    _, codes = run(pl, policy, 128, frames=12000)
    assert set(codes[-200:]) == {0}
    assert min(codes) == 0 and max(codes) <= 255


@pytest.mark.parametrize("policy", dm.POLICIES)
def test_saturates_high_when_always_too_slow(no_sim, policy):
    pl = make_plant(lambda c: dm.F_TARGET * (0.5 + 0.001 * c))
    _, codes = run(pl, policy, 128, frames=12000)
    assert set(codes[-200:]) == {255}
    assert min(codes) >= 0 and max(codes) == 255


@pytest.mark.parametrize("policy", dm.POLICIES)
def test_codes_never_leave_range_from_rail_starts(no_sim, policy):
    pl = make_plant(lambda c: dm.F_TARGET * (0.5 + 0.001 * c))
    for c0 in (0, 255):
        _, codes = run(pl, policy, c0, frames=500)
        assert all(0 <= c <= 255 for c in codes)


def test_bangbang_update_rule(no_sim):
    b = dm.BangBang(10)
    assert b.update(5) == 9 and b.update(-5) == 10 and b.update(0) == 10
    assert dm.BangBang(0).update(1) == 0
    assert dm.BangBang(255).update(-1) == 255


def test_deadband_update_rule(no_sim):
    D = dm.Deadband.D
    assert D == 75
    d = dm.Deadband(50)
    assert d.update(D) == 50 and d.update(-D) == 50     # at the edge: hold
    assert d.update(D + 1) == 49 and d.update(-D - 1) == 50


def test_avgstep_updates_once_per_window(no_sim):
    a = dm.AvgStep(50)
    D = dm.AvgStep.D
    out = [a.update(D + 1) for _ in range(dm.AvgStep.M)]
    assert out[:-1] == [50] * (dm.AvgStep.M - 1) and out[-1] == 49
    out = [a.update(-(D + 1)) for _ in range(dm.AvgStep.M)]
    assert out[-1] == 50
    out = [a.update(D) for _ in range(dm.AvgStep.M)]   # mean == D: hold
    assert out[-1] == 50


def test_fracdither_integrates_and_clamps(no_sim):
    f = dm.FracDither(100)
    assert f.update(0) == 100
    for _ in range(10000):
        f.update(-dm.N_NOM)       # persistently too slow -> integrator to the top rail
    assert f.I == 255.0 and f.c == 255
    for _ in range(10000):
        f.update(dm.N_NOM)
    assert f.I == 0.0 and f.c == 0


# ------------------------------------------------------------- run_loop ----

def test_run_loop_shapes_and_error_definition(no_sim):
    pl = linear_plant()
    prof = [OP] * 7
    errs, codes = dm.run_loop(pl, dm.BangBang, 90, prof, 0.0, random.Random(0))
    assert len(errs) == len(codes) == 7 and codes[0] == 90
    assert errs[0] == pytest.approx((pl.F[90] / dm.F_TARGET - 1) * 100)
    assert errs[0] == pytest.approx(SLOPE * 100 * (90 - C_STAR))


def test_run_loop_deterministic_with_fixed_seed(no_sim):
    pl = linear_plant()
    for policy in dm.POLICIES:
        a = run(pl, policy, 128, frames=800, jitter=500.0, seed=dm.SEED)
        b = run(pl, policy, 128, frames=800, jitter=500.0, seed=dm.SEED)
        assert a == b
    other = run(pl, dm.FracDither, 128, frames=800, jitter=500.0, seed=dm.SEED + 1)
    assert other != run(pl, dm.FracDither, 128, frames=800, jitter=500.0, seed=dm.SEED)


def test_run_loop_zero_jitter_does_not_consume_rng(no_sim):
    rng = random.Random(5)
    dm.run_loop(linear_plant(), dm.Deadband, 128, [OP] * 50, 0.0, rng)
    assert rng.random() == random.Random(5).random()


def test_run_loop_follows_profile_gain(no_sim):
    g = {(T, V): 1.0 for T in dm.TS for V in dm.VS}
    pl = linear_plant()
    pl.g = {k: (1.01 if k[0] == 85.0 else 1.0) for k in g}
    errs, _ = dm.run_loop(pl, dm.BangBang, 100, [(85.0, 3.3)], 0.0, random.Random(0))
    assert errs[0] == pytest.approx(1.0)


# ------------------------------------------------------------ trim_math ----

def test_trim_math_exponential_plant_closed_form(no_sim):
    r = 1.00314
    f0 = 30e6
    pl = make_plant(lambda c: f0 * r ** c)
    t = dm.trim_math(pl)
    assert t["plant"] == "syn/sch"
    assert t["min_step_pct"] == pytest.approx((r - 1) * 100, rel=1e-9)
    assert t["max_step_pct"] == pytest.approx((r - 1) * 100, rel=1e-9)
    assert t["mean_step_pct"] == pytest.approx((r - 1) * 100, rel=1e-9)
    assert t["n_negative_steps"] == 0
    assert t["f0_mhz"] == pytest.approx(30.0) and t["f255_mhz"] == pytest.approx(30.0 * r ** 255 )
    assert len(t["grid"]) == 9
    # best code = nearest in ln f to the target; error bounded by half a step
    cbest = round(math.log(dm.F_TARGET / f0) / math.log(r))
    for g in t["grid"]:
        assert g["best_code"] == cbest
        assert abs(g["best_err_pct"]) <= (r - 1) * 100 / 2 + 1e-9
        assert g["crossings"] == 1 and not g["saturated"]
        assert g["local_step_pct"] == pytest.approx((r - 1) * 100, rel=1e-9)


def test_trim_math_linear_plant_hits_target_exactly(no_sim):
    t = dm.trim_math(linear_plant())
    for g in t["grid"]:
        assert g["best_code"] == C_STAR and g["best_err_pct"] == pytest.approx(0.0, abs=1e-9)
    # exact: step at code 0 is 0.003 / (1 - 0.3)
    assert t["min_step_pct"] == pytest.approx(0.003 / (1 + SLOPE * (255 - 1 - C_STAR)) * 100)
    assert t["max_step_pct"] == pytest.approx(0.003 / (1 - SLOPE * C_STAR) * 100)


def test_trim_math_flags_saturation_and_negative_steps(no_sim):
    slow = dm.trim_math(make_plant(lambda c: dm.F_TARGET * (0.5 + 0.001 * c)))
    assert all(g["best_code"] == 255 and g["saturated"] for g in slow["grid"])
    fast = dm.trim_math(make_plant(lambda c: dm.F_TARGET * (1.2 + 0.001 * c)))
    assert all(g["best_code"] == 0 and g["saturated"] for g in fast["grid"])
    # one non-monotone dip -> exactly one negative step, reported as the worst one
    pl = make_plant(lambda c: 40e6 * (1 + 0.003 * c) * (0.99 if c >= 130 else 1.0))
    t = dm.trim_math(pl)
    assert t["n_negative_steps"] == 1
    assert t["worst_negative_step_pct"] == t["min_step_pct"] < 0


def test_half_lsb_constants(no_sim):
    # ratified nominal step 0.314 %/code; half-LSB 0.157 %; deadband in frame counts
    assert dm.HALF_LSB == pytest.approx(0.314 / 2)
    assert dm.N_NOM == round(dm.F_TARGET * dm.FRAME_S)
    assert dm.Deadband.D == dm.AvgStep.D == round(0.157 / 100 * 48000) == 75


# ------------------------------------------- lock_frame / movavg / stats ----

def test_lock_frame_basic_and_empty(no_sim):
    assert dm.lock_frame([5, 5, 0, 0, 0, 0], 1, 3) == 2
    assert dm.lock_frame([0, 0, 0], 1, 3) == 0
    assert dm.lock_frame([], 1, 1) is None


def test_lock_frame_band_edge_inclusive(no_sim):
    assert dm.lock_frame([0.25] * 4, 0.25, 4) == 0
    assert dm.lock_frame([-0.25] * 4, 0.25, 4) == 0
    assert dm.lock_frame([0.2501] * 4, 0.25, 4) is None


def test_lock_frame_hold_longer_than_series_never_locks(no_sim):
    assert dm.lock_frame([0.0] * 5, 1, 6) is None


def test_lock_frame_never_locks(no_sim):
    assert dm.lock_frame([2.0] * 50, 1, 3) is None
    assert dm.lock_frame([0, 0, 2.0] * 10, 1, 3) is None   # runs always one short


def test_lock_frame_locks_then_unlocks_returns_first_lock(no_sim):
    x = [9, 0, 0, 0, 9, 9, 0, 0, 0, 0]
    assert dm.lock_frame(x, 1, 3) == 1
    assert dm.lock_frame(x[4:], 1, 4) == 2   # excursion resets the run


def test_lock_frame_run_reset_by_excursion(no_sim):
    x = [0, 0, 9, 0, 0, 0]
    assert dm.lock_frame(x, 1, 3) == 3


def test_movavg_values_and_length(no_sim):
    out = dm.movavg([1, 2, 3, 4, 5], 2)
    assert out == pytest.approx([1.5, 2.5, 3.5, 4.5])
    assert dm.movavg([1, 2, 3], 1) == pytest.approx([1, 2, 3])
    assert dm.movavg([1, 2, 3], 3) == pytest.approx([2.0])
    x = list(range(40))
    assert len(dm.movavg(x, 16)) == len(x) - 15


def test_movavg_window_larger_than_series_is_empty(no_sim):
    assert dm.movavg([1, 2, 3], 4) == []
    assert dm.movavg([], 1) == []
    # ... and composes with lock_frame as "never locks"
    assert dm.lock_frame(dm.movavg([0.0] * 3, 16), 1, 1) is None


def test_movavg_matches_naive_window_mean(no_sim):
    rng = random.Random(3)
    x = [rng.uniform(-1, 1) for _ in range(100)]
    w = 7
    ref = [sum(x[i - w + 1:i + 1]) / w for i in range(w - 1, len(x))]
    assert dm.movavg(x, w) == pytest.approx(ref, abs=1e-12)


def test_stats(no_sim):
    s = dm.stats([-0.1, 0.2, 0.3, -0.4])
    assert s["min"] == -0.4 and s["max"] == 0.3
    assert s["pp"] == pytest.approx(0.7) and s["absmax"] == 0.4
    assert s["frac_in_band"] == 0.5            # only -0.1 and 0.2 are inside the 0.25 % band
    assert dm.stats([dm.BAND, -dm.BAND])["frac_in_band"] == 1.0
    assert dm.stats([1.5])["pp"] == 0.0
