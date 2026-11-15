"""Offline tests for the per-stage Iq attribution report (issue #347). Synthetic fixtures; no simulator."""
import json
import math
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import iq_report as ir  # noqa: E402
import stage_map  # noqa: E402


def fake_meas(total_u, split):
    """Measurements dict with iq_run (A) and per-stage iq_<stage> summing to it."""
    rem = total_u - sum(split.values())
    d = {"iq_run": total_u * 1e-6}
    for s, v in split.items():
        d[f"iq_{s}"] = v * 1e-6
    # put the residue on an extra stage name the report knows (bias) so the sum is exact
    d["iq_bias"] = (split.get("bias", 0) + rem) * 1e-6
    return d


def fake_map(tmp_path):
    """A minimal conservation-passing map shaped like the real one."""
    dev = lambda n, st, terms: {"name": n, "x": 0, "y": 0, "cclass": "nfet", "line": f"{n} a b vss vsubs nfet_03v3 L=1U W=2U",
                                "vdd_terms": terms}
    stages = {"bias": [dev("X1", "bias", [])], "cmp_h": [dev("X2", "cmp_h", [])],
              "cmp_l": [dev("X3", "cmp_l", [])], "latch": [dev("X4", "latch", [])],
              "trim": [dev("X5", "trim", [])],
              "timing": [dev("XCT", "timing", [])], "disch": [dev("XD", "disch", [])]}
    m = {"flat_deck": "x", "flat_deck_sha256": "0", "device_count": 7, "assigned_count": 7, "unresolved": [],
         "offsets": {}, "stage_device_counts": {s: len(v) for s, v in stages.items()},
         "vdd_side_summary": {"devices": 0, "terminals": 0}, "stages": stages}
    p = tmp_path / "map.json"
    p.write_text(json.dumps(m))
    return p


def test_cell_rows_sum_and_residue():
    m = fake_meas(460.0, {"bias": 45.0, "cmp_h": 117.0, "cmp_l": 73.0, "latch": 47.0, "trim": 178.0})
    r = ir.cell_rows(m)
    assert math.isclose(r["sum"], r["total"], abs_tol=1e-9)
    assert abs(r["residue"]) < 1e-9


def test_cell_rows_reports_residue_not_hidden():
    d = {"iq_run": 500.0e-6, "iq_bias": 45.0e-6, "iq_cmp_h": 117.0e-6, "iq_cmp_l": 73.0e-6,
         "iq_latch": 47.0e-6, "iq_trim": 200.0e-6}      # stages sum to 482, total is 500
    r = ir.cell_rows(d)
    assert abs(r["sum"] - 482.0) < 1e-6
    assert abs(r["residue"] - 18.0) < 1e-6              # the 18 uA residue must surface
    assert abs(r["residue_pct"] - 3.6) < 1e-9


def test_report_back_to_back_and_sum_checks(tmp_path):
    mp = fake_map(tmp_path)
    env = {}
    for cell, tot, split in [
        (("0xFF", 3.3, "tt", 27.0), 462.1, {"cmp_h": 117.0, "cmp_l": 73.0, "latch": 47.0, "trim": 180.0}),
        (("0xFF", 3.6, "ff", 85.0), 759.0, {"cmp_h": 218.0, "cmp_l": 142.0, "latch": 70.0, "trim": 252.0}),
    ]:
        env[cell] = fake_meas(tot, split)
    L, checks = ir.report(env, mp, "fixture")
    assert checks["b2b"] and all(v == "OK" for v in checks["b2b"].values())
    assert checks["cells"] == 2 and not checks["sum_fails"]
    assert any("exactly 0 A" in line for line in L)          # zero-by-construction stated
    assert any("20 whole oscillation periods" in line for line in L)   # window stated
    assert any("559.4" in line for line in L)                # item-5 non-comparability labelled


def test_report_flags_b2b_drift(tmp_path):
    mp = fake_map(tmp_path)
    env = {("0xFF", 3.3, "tt", 27.0): fake_meas(480.0, {"cmp_h": 117.0, "cmp_l": 73.0, "latch": 47.0, "trim": 227.0})}
    L, checks = ir.report(env, mp, "fixture")
    assert checks["b2b"][str(("0xFF", 3.3, "tt", 27.0))] == "FAIL"
    assert checks["b2b"][str(("0xFF", 3.6, "ff", 85.0))] == "MISSING"


def test_report_flags_sum_break(tmp_path):
    mp = fake_map(tmp_path)
    env = {("0xFF", 3.3, "tt", 27.0): fake_meas(462.1, {"cmp_h": 117.0, "cmp_l": 73.0, "latch": 47.0, "trim": 180.0})}
    env[("0xFF", 3.3, "tt", 27.0)]["iq_trim"] = 100.0 * 1e-6   # stages no longer sum
    L, checks = ir.report(env, mp, "fixture")
    assert checks["sum_fails"]


def test_map_conservation_assert(tmp_path):
    mp = fake_map(tmp_path)
    m = json.loads(mp.read_text())
    assert stage_map.check_conservation(m) == 7
    m["stage_device_counts"]["bias"] = 2                        # break the count
    mp2 = tmp_path / "broken.json"; mp2.write_text(json.dumps(m))
    with pytest.raises(AssertionError, match="conservation"):
        stage_map.check_conservation(json.loads(mp2.read_text()))
