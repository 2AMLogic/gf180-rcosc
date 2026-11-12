"""Offline tests for the stage-attribution analysis (issue #314). Synthetic fixtures; no simulator."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import stage_attribution as sa  # noqa: E402


def point(T, gaps, v, v0=0.01, vh=None, fosc=None):
    """Build a measurement dict from stage gaps (s): ev_a=0 then cumulative events, period T."""
    vh = vh if vh is not None else 2 * v / 3
    t, ev = 0.0, {}
    for name, g in zip(sa.EVENTS, gaps):
        ev[name] = 1e-6 + t
        t += g
    ev["ev_a3"] = ev["ev_a"] + 2 * T
    return {**ev, "v0": v0, "vh": vh, "vl": vh / 2, "vib": 0.8, "vpb": 2.0, "fosc": fosc or 1 / T}


def test_contributions_sum_to_measured_error_exactly():
    a = sa.pt(point(20e-9, [2e-9, 1e-9, 0.1e-9, 2e-9, 0.4e-9, 14.5e-9], 3.3), 3.3)
    b = sa.pt(point(21e-9, [2.2e-9, 1.1e-9, 0.1e-9, 2.1e-9, 0.4e-9, 15.1e-9], 3.0, vh=1.95), 3.0)
    s = sa.step(a, b)
    assert math.isclose(s["total"], s["eps"], abs_tol=1e-9)
    assert math.isclose(s["eps"], (20 / 21 - 1) * 100, abs_tol=1e-9)


def test_gaps_sum_to_period_and_charge_split_has_no_residual():
    p = sa.pt(point(20e-9, [2e-9, 1e-9, 0.1e-9, 2e-9, 0.4e-9, 14.5e-9], 3.3), 3.3)
    assert math.isclose(p["gap_sum"], p["T"], rel_tol=1e-9)
    assert math.isclose(p["tau"] * p["L"], p["chg"], rel_tol=1e-12)


def test_negative_discharge_gap_is_signed_not_wrapped():
    # vc passes vl before clk reaches mid-rail (fast ff discharge): the gap must be -0.02 ns, not T-0.02 ns
    p = sa.pt(point(20e-9, [2e-9, 1e-9, -0.02e-9, 2e-9, 0.4e-9, 14.62e-9], 3.3), 3.3)
    assert math.isclose(p["dis"], -0.02e-9, abs_tol=1e-15)
    assert math.isclose(p["gap_sum"], p["T"], rel_tol=1e-9)


def test_identical_points_attribute_zero():
    a = sa.pt(point(20e-9, [2e-9, 1e-9, 0.1e-9, 2e-9, 0.4e-9, 14.5e-9], 3.3), 3.3)
    s = sa.step(a, a)
    assert all(abs(s[k]) < 1e-12 for k in sa.KEYS + ["total", "eps"])
