"""Offline tests for sim/temperature (issue #125).  Every frequency curve,
waveform and klt report here is a SYNTHETIC FIXTURE built in this file;
nothing is measured evidence.  No simulator, PDK, klt or network is used: the
only subprocess allowed is `git` (committed-source validation).  Generation
and analysis outputs go to pytest temporary directories only.

Named test_temperature.py (not test_harness.py) so that
`pytest sim/temperature sim/waveform` can collect both directories in one
session without a module-basename clash; modules are imported under unique
names for the same reason.

Run:  python3 -I -m pytest -p no:cacheprovider sim/temperature sim/waveform
"""
import bisect
import csv
import importlib.util
import json
import math
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tp = _load("rcosc_temperature_prepare", HERE / "prepare.py")
ta = _load("rcosc_temperature_analyze", HERE / "analyze.py")
wp = tp.wp
wa = ta.wa

CAL_RUN = tp.REPO / "sim" / "pvt" / "results" / "20260923T030125Z"
PROBE_RUN = tp.REPO / "sim" / "pvt" / "results" / "20260923T030905Z"
T = tp.TEMPS_C
F27 = 48.0e6
NS = 1e-9
SYN = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No simulator / klt / network: only `git` may be spawned, no socket may connect."""
    real_popen = subprocess.Popen

    class GuardPopen(real_popen):
        def __init__(self, args, *a, **k):
            argv = [args] if isinstance(args, str) else list(args)
            if Path(str(argv[0])).name != "git":
                raise AssertionError(f"offline test must not run {argv[0]!r}")
            super().__init__(args, *a, **k)

    def no_connect(*a, **k):
        raise AssertionError("offline test must not open network connections")

    monkeypatch.setattr(subprocess, "Popen", GuardPopen)
    monkeypatch.setattr(socket.socket, "connect", no_connect)
    monkeypatch.setattr(socket, "create_connection", no_connect)


@pytest.fixture(scope="module")
def cal():
    return tp.load_held_calibration(CAL_RUN)


# ------------------------------------------------------------- prepare -----

def test_grid_is_36_unique_points_on_fixed_axis():
    assert T == [-40, -27.5, -15, -2.5, 10, 22.5, 27, 35, 47.5, 60, 72.5, 85]
    pts = tp.grid()
    assert len(pts) == 36 and len(set(pts)) == 36
    assert {p for p, _, _ in pts} == {"tt", "ss", "ff"}
    assert {v for _, _, v in pts} == {3.3}


def test_calibration_is_the_ratified_held_codes(cal):
    assert cal["codes"] == {"tt": 0xA3, "ss": 0xCD, "ff": 0x59}
    s = cal["source"]
    assert s["campaign_runid"] == "20260923T030125Z" and s["target"] == "ratified"
    assert s["manifest_key"] == "calibration_spec_target"
    assert s["campaign_git_sha"] == "ed26786191202a85a71b6938563c45a1eaaa5582"
    assert len(s["manifest_sha256"]) == 64 and len(s["results_csv_sha256"]) == 64
    assert s["committing_hash"]


def test_generate_three_requests_36_points(tmp_path, cal):
    out = tmp_path / "gen"
    prov = tp.generate(out, cal)
    reqs = sorted(out.glob("request_*.json"))
    assert [r.name for r in reqs] == ["request_t12_ff.json", "request_t12_ss.json", "request_t12_tt.json"]
    seen = []
    for r in prov["requests"]:
        req = json.loads((out / r["request"]).read_text())
        assert req["corners"]["temperature_c"] == T
        assert [p["name"] for p in req["corners"]["process"]] == [r["process"]]
        assert req["netlist"] == r["netlist"] and r["corner_count"] == 12
        assert r["request_sha256"] == wp.sha256(out / r["request"])
        assert r["netlist_sha256"] == wp.sha256(out / r["netlist"])
        tb = (out / r["netlist"]).read_text()
        code = tp.EXPECTED_CODES[r["process"]]
        assert f"trim code 0x{code:02X}" in tb and r["trim_hex"] == f"0x{code:02X}"
        for i in range(8):
            pwl = f"VT{i} t{i} 0 PWL(0 0 1000n 3.3)"
            assert (pwl in tb) == bool((code >> i) & 1)
        assert "VDD vdd 0 PWL(0 0 1000n 3.3)" in tb and "CLOAD" not in tb
        seen += [(req["corners"]["process"][0]["name"], t) for t in req["corners"]["temperature_c"]]
    assert len(seen) == 36 and len(set(seen)) == 36
    assert len(prov["corners"]) == 36
    assert {(c["process"], c["temp_c"]) for c in prov["corners"]} == set(seen)
    for c in prov["corners"]:
        assert c["vdd_v"] == 3.3 and c["load_f"] == 0.0 and c["target"] == "ratified"
        assert c["calibration_runid"] == "20260923T030125Z" and c["target_hz"] == 48e6
        assert c["trim_code"] == tp.EXPECTED_CODES[c["process"]]
        assert c["settings"]["reltol"] == 1e-3 and c["settings"]["tmax_time_step"] == "200p"
    assert prov["dut"]["extracted_sha256"] == wp.sha256(out / "rcosc_top_schematic.spice")
    assert prov["dut"]["source_sha256"] == wp.sha256(wp.SRC)
    assert prov["grid"]["points"] == 36 and prov["kind"] == tp.KIND
    assert prov["calibration"]["codes"] == {"tt": "0xA3", "ss": "0xCD", "ff": "0x59"}


def test_design_revision_recorded_separately_and_equivalence_unverified(tmp_path, cal):
    prov = tp.generate(tmp_path / "gen", cal)
    rev = prov["design_revision"]
    assert len(rev["head"]) == 40
    assert rev["calibration_git_sha"] == tp.CAL_GIT_SHA
    assert rev["same_revision_as_calibration"] is (rev["head"] == tp.CAL_GIT_SHA)
    assert prov["calibration"]["campaign_git_sha"] == tp.CAL_GIT_SHA
    assert prov["schematic_equivalence"]["status"] == "UNVERIFIED"


def test_generate_refuses_overwrite(tmp_path, cal):
    out = tmp_path / "gen"
    out.mkdir()
    with pytest.raises(tp.PrepareError, match="overwrite"):
        tp.generate(out, cal)
    assert list(out.iterdir()) == []
    out2 = tmp_path / "gen2"
    tp.generate(out2, cal)
    before = {p.name: p.read_bytes() for p in out2.iterdir()}
    with pytest.raises(tp.PrepareError, match="overwrite"):
        tp.generate(out2, cal)
    assert {p.name: p.read_bytes() for p in out2.iterdir()} == before


def test_generate_rejects_added_load(tmp_path, cal):
    with pytest.raises(tp.PrepareError, match="zero added"):
        tp.generate(tmp_path / "g", cal, {"load_f": 1e-15})


def test_cli_requires_cal_run_and_generates(tmp_path, capsys):
    with pytest.raises(SystemExit):
        tp.main(["--out", str(tmp_path / "x")])
    assert tp.main(["--cal-run", str(CAL_RUN), "--out", str(tmp_path / "ok")]) == 0
    assert (tmp_path / "ok" / "provenance.json").is_file()
    assert tp.main(["--cal-run", str(CAL_RUN), "--out", str(tmp_path / "ok")]) == 2
    assert "overwrite" in capsys.readouterr().err


def test_delay_probe_run_is_not_a_calibration(tmp_path):
    with pytest.raises(tp.PrepareError, match="not a calibration"):
        tp.load_held_calibration(PROBE_RUN)
    assert tp.main(["--cal-run", str(PROBE_RUN), "--out", str(tmp_path / "p")]) == 2
    assert not (tmp_path / "p").exists()


def _cal_copy(tmp_path, edit_manifest=None, edit_rows=None):
    d = tmp_path / "20260923T030125Z"
    d.mkdir()
    man = json.loads((CAL_RUN / "manifest.json").read_text())
    if edit_manifest:
        edit_manifest(man)
    (d / "manifest.json").write_text(json.dumps(man))
    with open(CAL_RUN / "results.csv", newline="") as fh:
        rd = csv.DictReader(fh)
        rows, fields = list(rd), rd.fieldnames
    if edit_rows:
        for r in rows:
            edit_rows(r)
    with open(d / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return d


def test_uncommitted_calibration_copy_rejected(tmp_path):
    d = _cal_copy(tmp_path)
    with pytest.raises(tp.PrepareError, match="committed"):
        tp.load_held_calibration(d)
    # identical bytes, committed-check off: accepted (the copy is otherwise valid)
    assert tp.load_held_calibration(d, require_committed=False)["codes"] == tp.EXPECTED_CODES


def test_saturated_calibration_rejected(tmp_path):
    def sat(m):
        m["calibration_spec_target"]["ss"]["saturated"] = True
    with pytest.raises(tp.PrepareError, match="saturated"):
        tp.load_held_calibration(_cal_copy(tmp_path, sat), require_committed=False)


@pytest.mark.parametrize("bad", [256, -1, "0xA3", True, None])
def test_invalid_calibration_code_rejected(tmp_path, bad):
    def edit(m):
        m["calibration_spec_target"]["tt"]["code"] = bad
    with pytest.raises(tp.PrepareError, match="invalid"):
        tp.load_held_calibration(_cal_copy(tmp_path, edit), require_committed=False)


def test_other_valid_code_rejected_as_not_held_code(tmp_path):
    def m(man):
        man["calibration_spec_target"]["tt"]["code"] = 0xA4

    def r(row):
        if row["pass"] == "posttrim_ratif" and row["process"] == "tt":
            row["trim_code"] = str(0xA4)
    with pytest.raises(tp.PrepareError, match="held codes"):
        tp.load_held_calibration(_cal_copy(tmp_path, m, r), require_committed=False)


def test_calibration_provenance_mismatch_rejected(tmp_path):
    def sha(m):
        m["git_sha"] = "0" * 40
    with pytest.raises(tp.PrepareError, match="git_sha"):
        tp.load_held_calibration(_cal_copy(tmp_path, sha), require_committed=False)


def test_existing_waveform_modes_unchanged(tmp_path):
    """The historical PVT axes, the 27-point waveform grid and its probe
    validation are untouched; off-axis temperatures are still rejected there."""
    assert wp.TEMPS_C == [-40.0, 27.0, 85.0] and wp.VDDS_V == [3.0, 3.3, 3.6]
    assert len(wp.grid()) == 27
    c = wp.load_calibration(CAL_RUN)
    prov = wp.generate(tmp_path / "wf", c, probe="tt:27:3.3")
    assert prov["grid"]["points"] == 1
    with pytest.raises(wp.PrepareError, match="not one of the 27"):
        wp.generate(tmp_path / "wf2", c, probe="tt:22.5:3.3")


# ------------------------------------------------------- curve analysis ----

def pts(fn, temps=T):
    return [{"temp_c": t, "f_hz": fn(t), "status": "OK"} for t in temps]


def lin(a):
    return lambda t: F27 * (1 + a * (t - 27.0))


def quad(b, a=0.0):
    return lambda t: F27 * (1 + a * (t - 27.0) + b * (t - 27.0) ** 2)


def close(x, y, tol=1e-6):
    return abs(x - y) <= tol


def test_linear_rising_curve():
    c = ta.analyse_curve(pts(lin(50e-6)))
    assert c["status"] == "COMPLETE" and c["f27_hz"] == F27
    for iv in c["intervals"]:
        assert close(iv["slope_ppm_per_c"], 50.0)
        assert close(iv["diff_ppm"], 50.0 * (iv["t1_c"] - iv["t0_c"]))
        assert close(iv["diff_hz"], F27 * 50e-6 * (iv["t1_c"] - iv["t0_c"]), 1e-4)
        assert iv["class"] == "rising"
    assert close(c["endpoint_slope_ppm_per_c"], 50.0)
    assert c["max_abs_residual_ppm"] < 1e-6
    assert c["monotonicity"] == "monotone increasing"
    assert c["curvature_verdict"] == "WITHIN_TOLERANCE"
    norm = {r["temp_c"]: r["norm_ppm"] for r in c["rows"]}
    assert norm[27.0] == 0.0 and close(norm[85.0], 50.0 * 58)


def test_linear_decreasing_curve():
    c = ta.analyse_curve(pts(lin(-80e-6)))
    assert all(iv["class"] == "falling" for iv in c["intervals"])
    assert c["monotonicity"] == "monotone decreasing"
    assert close(c["endpoint_slope_ppm_per_c"], -80.0)


def test_flat_curve():
    c = ta.analyse_curve(pts(lin(1e-6)))  # at most 12.5 ppm per interval
    assert all(iv["class"] == "flat" for iv in c["intervals"])
    assert c["monotonicity"] == "flat" and c["curvature_verdict"] == "WITHIN_TOLERANCE"


def test_quadratic_curvature_analytic():
    b = 2e-7
    c = ta.analyse_curve(pts(quad(b)))
    res = {r["temp_c"]: r["residual_ppm"] for r in c["residuals"]}
    assert set(res) == set(T)
    for t in T:
        t0, t1 = (-40.0, 27.0) if t <= 27 else (27.0, 85.0)
        assert close(res[t], 1e6 * b * (t - t0) * (t - t1)), t
    assert res[-40.0] == res[27.0] == res[85.0] == 0.0
    assert c["max_residual_temp_c"] == -2.5
    assert close(c["max_residual_signed_ppm"], -221.25)
    assert close(c["max_abs_residual_ppm"], 221.25)
    assert c["curvature_verdict"] == "EXCEEDS_TOLERANCE"
    assert c["monotonicity"] == "nonmonotone"  # falls to 27 C then rises
    cls = {(iv["t0_c"], iv["t1_c"]): iv["class"] for iv in c["intervals"]}
    assert cls[(22.5, 27.0)] == "flat" and cls[(-40.0, -27.5)] == "falling"
    assert cls[(72.5, 85.0)] == "rising"
    assert close(c["endpoint_slope_ppm_per_c"], 1e6 * b * (58 ** 2 - 67 ** 2) / 125)


def test_curved_but_monotone_within_tolerance():
    c = ta.analyse_curve(pts(quad(-1e-8, a=60e-6)))  # max |r| = 1e-2*37.5*29.5 = 11 ppm
    assert c["monotonicity"] == "monotone increasing"
    assert c["curvature_verdict"] == "WITHIN_TOLERANCE"
    assert 0 < c["max_abs_residual_ppm"] < 100


def _bump(delta_hz, at=10.0):
    return [{"temp_c": t, "f_hz": F27 + (delta_hz if t == at else 0.0), "status": "OK"} for t in T]


def test_tolerance_boundary_exactly_100ppm_is_inside():
    c = ta.analyse_curve(_bump(4800.0))  # exactly 100 ppm of 48 MHz
    cls = {iv["t0_c"]: iv for iv in c["intervals"]}
    assert cls[-2.5]["diff_ppm"] == 100.0 and cls[-2.5]["class"] == "flat"
    assert cls[10.0]["diff_ppm"] == -100.0 and cls[10.0]["class"] == "flat"
    assert c["monotonicity"] == "flat"
    assert c["max_abs_residual_ppm"] == 100.0 and c["max_residual_temp_c"] == 10.0
    assert c["curvature_verdict"] == "WITHIN_TOLERANCE"


def test_tolerance_boundary_just_over_100ppm():
    c = ta.analyse_curve(_bump(4801.0))
    cls = {iv["t0_c"]: iv["class"] for iv in c["intervals"]}
    assert cls[-2.5] == "rising" and cls[10.0] == "falling"
    assert c["monotonicity"] == "nonmonotone"
    assert c["curvature_verdict"] == "EXCEEDS_TOLERANCE"
    c2 = ta.analyse_curve(_bump(-4801.0))
    assert c2["max_residual_signed_ppm"] < -100 and c2["curvature_verdict"] == "EXCEEDS_TOLERANCE"


def test_flat_interval_inside_rising_curve_and_reversal():
    f = {t: F27 * (1 + 50e-6 * (t - 27)) for t in T}
    f[35.0] = f[27.0]  # plateau 27 -> 35, still non-decreasing
    c = ta.analyse_curve([{"temp_c": t, "f_hz": f[t]} for t in T])
    assert {iv["t0_c"]: iv["class"] for iv in c["intervals"]}[27.0] == "flat"
    assert c["monotonicity"] == "monotone increasing"
    f[60.0] = f[47.5] - 0.01 * F27  # reversal
    c = ta.analyse_curve([{"temp_c": t, "f_hz": f[t]} for t in T])
    assert c["monotonicity"] == "nonmonotone"


def _not_evaluated(c, status):
    assert c["status"] == status
    assert c["monotonicity"].startswith("NOT EVALUATED")
    assert c["curvature_verdict"].startswith("NOT EVALUATED")


def test_missing_interior_row_incomplete_no_interpolation():
    p = [x for x in pts(lin(50e-6)) if x["temp_c"] != 47.5]
    c = ta.analyse_curve(p)
    _not_evaluated(c, "INCOMPLETE")
    by = {iv["t0_c"]: iv for iv in c["intervals"]}
    assert "skipped" in by[35.0] and "skipped" in by[47.5]
    assert "slope_ppm_per_c" not in by[35.0]
    assert close(by[60.0]["slope_ppm_per_c"], 50.0)  # valid diagnostics kept
    assert 47.5 not in {r["temp_c"] for r in c["residuals"]}
    assert any("47.5" in r for r in c["incomplete_reasons"])


def test_missing_27c_reference():
    c = ta.analyse_curve([x for x in pts(lin(50e-6)) if x["temp_c"] != 27.0])
    _not_evaluated(c, "INCOMPLETE")
    assert c["f27_hz"] is None and c["missing_anchors_c"] == [27.0]
    assert c["residuals"] == [] and c["max_abs_residual_ppm"] is None
    assert c["endpoint_slope_ppm_per_c"] is None
    assert all("slope_ppm_per_c" not in iv for iv in c["intervals"])
    assert any("diff_hz" in iv for iv in c["intervals"])  # raw differences still reported


@pytest.mark.parametrize("end", [-40.0, 85.0])
def test_missing_endpoint_anchor(end):
    c = ta.analyse_curve([x for x in pts(quad(2e-7)) if x["temp_c"] != end])
    _not_evaluated(c, "INCOMPLETE")
    assert c["missing_anchors_c"] == [end] and c["endpoint_slope_ppm_per_c"] is None
    temps = {r["temp_c"] for r in c["residuals"]}
    assert temps == ({t for t in T if t >= 27} if end == -40.0 else {t for t in T if t <= 27})


def test_duplicate_point_invalid():
    p = pts(lin(50e-6)) + [{"temp_c": 35.0, "f_hz": F27, "status": "OK"}]
    c = ta.analyse_curve(p)
    _not_evaluated(c, "INVALID")
    assert sum(r["status"] == "INVALID: duplicate point" for r in c["rows"]) == 2
    assert any("duplicate" in r for r in c["invalid_reasons"])


def test_off_grid_and_provenance_rows_invalid():
    c = ta.analyse_curve(pts(lin(50e-6)) + [{"temp_c": 30.0, "f_hz": F27}])
    _not_evaluated(c, "INVALID")
    p = pts(lin(50e-6))
    p[3]["invalid"] = "provenance mismatch: test"
    c = ta.analyse_curve(p)
    _not_evaluated(c, "INVALID")
    assert c["rows"][3]["status"].startswith("INVALID: provenance mismatch")


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf"), float("-inf"), None, "48e6", True])
def test_bad_frequency_incomplete(bad):
    p = pts(lin(50e-6))
    p[4]["f_hz"] = bad
    c = ta.analyse_curve(p)
    _not_evaluated(c, "INCOMPLETE")
    assert c["rows"][4]["status"].startswith("FAIL:")
    assert c["n_valid"] == 11


def test_failed_row_incomplete():
    p = pts(lin(50e-6))
    p[0] = {"temp_c": -40.0, "f_hz": None, "status": "FAIL: unsettled tail"}
    c = ta.analyse_curve(p)
    _not_evaluated(c, "INCOMPLETE")
    assert c["missing_anchors_c"] == [-40.0]


def test_classify_and_monotonicity_units():
    assert ta.classify(100.0) == "flat" and ta.classify(-100.0) == "flat"
    assert ta.classify(100.0000001) == "rising" and ta.classify(-100.0000001) == "falling"
    assert ta.monotonicity(["flat", "flat"]) == "flat"
    assert ta.monotonicity(["flat", "rising"]) == "monotone increasing"
    assert ta.monotonicity(["falling", "flat"]) == "monotone decreasing"
    assert ta.monotonicity(["rising", "falling"]) == "nonmonotone"


# -------------------------------------------- end-to-end synthetic reports --

P_TEST = wa.Params(window_s=300 * NS, min_cycles=10)
CLI_P = ["--window-ns", "300", "--min-cycles", "10"]


def clock_waveform(f_hz, vdd=3.3, n=16, edge=1 * NS, step=1 * NS, lead=10 * NS):
    """SYNTHETIC trapezoid clock: every PWL corner is a sample, so the 50 %
    crossings (and hence the period) are exact under linear interpolation."""
    per = 1.0 / f_hz
    knots = []
    for k in range(n + 1):
        r = lead + k * per
        knots += [(r - edge / 2, 0.0), (r + edge / 2, vdd),
                  (r + per / 2 - edge / 2, vdd), (r + per / 2 + edge / 2, 0.0)]
    tstop = lead + n * per + per / 4
    ts = {0.0, tstop} | {x for x, _ in knots if x < tstop}
    x = 0.0
    while x < tstop:
        ts.add(x)
        x += step
    ts = sorted(ts)
    kx = [k[0] for k in knots]

    def v(t):
        j = bisect.bisect_right(kx, t)
        if j == 0:
            return 0.0
        if j >= len(knots):
            return knots[-1][1]
        (a, va), (b, vb) = knots[j - 1], knots[j]
        return va + (vb - va) * (t - a) / (b - a)
    return {"synthetic": SYN, "variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
            "points": [[t, v(t), vdd] for t in ts]}


def make_reports(tmp, prov, fn, edit=None):
    """One SYNTHETIC klt-like report per manifest request.  fn(proc, T) -> f."""
    paths = {}
    for r in prov["requests"]:
        corners = []
        for t in r["temperature_c"]:
            wf = tmp / "art" / f"{r['process']}_{t:g}" / "waveform.raw.json"
            wf.parent.mkdir(parents=True)
            wf.write_text(json.dumps(clock_waveform(fn(r["process"], t))))
            corners.append({"process": r["process"], "temperature_c": t, "status": "pass",
                            "artifacts": {"waveform": str(wf)}})
        rep = {"synthetic": True, "status": "pass", "corner_count": len(corners),
               "environment": {"netlist_sha256": r["netlist_sha256"], "remote": None,
                               "netlist_closure": [
                                   {"path": f"x/{r['netlist']}", "sha256": r["netlist_sha256"]},
                                   {"path": "x/rcosc_top_schematic.spice", "sha256": r["dut_sha256"]}]},
               "corners": corners}
        if edit:
            edit(r["process"], rep)
        p = tmp / f"rep_{r['process']}.json"
        p.write_text(json.dumps(rep))
        paths[r["process"]] = p
    return paths


@pytest.fixture(scope="module")
def manifest(tmp_path_factory):
    out = tmp_path_factory.mktemp("prep") / "gen"
    prov = tp.generate(out, tp.load_held_calibration(CAL_RUN))
    return out / "provenance.json", prov


def lin_by_proc(proc, t):
    return {"tt": 48e6, "ss": 47.9e6, "ff": 48.05e6}[proc] * (1 + 50e-6 * (t - 27.0))


def test_end_to_end_complete_synthetic(tmp_path, manifest):
    mpath, prov = manifest
    reps = make_reports(tmp_path, prov, lin_by_proc)
    out = tmp_path / "run"
    rc = ta.main([*map(str, reps.values()), "--manifest", str(mpath), "--outdir", str(out), *CLI_P])
    assert rc == 0
    doc = json.loads((out / "results.json").read_text())
    assert doc["status"] == "COMPLETE" and doc["label"] == SYN and doc["synthetic"] is True
    assert doc["schematic_equivalence"] == "UNVERIFIED"
    for p, c in doc["curves"].items():
        assert c["status"] == "COMPLETE" and c["monotonicity"] == "monotone increasing"
        assert abs(c["f27_hz"] / lin_by_proc(p, 27.0) - 1) < 1e-9
        assert all(abs(iv["slope_ppm_per_c"] - 50.0) < 1e-3 for iv in c["intervals"])
        assert c["max_abs_residual_ppm"] < 1e-3
    assert SYN in (out / "summary.md").read_text()
    with open(out / "results.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 36 and all(r["evidence_label"] == SYN for r in rows)
    # refuses to overwrite
    rc = ta.main([*map(str, reps.values()), "--manifest", str(mpath), "--outdir", str(out), *CLI_P])
    assert rc == 2


def test_synthetic_label_from_flag(tmp_path, manifest):
    mpath, prov = manifest

    def unmark(proc, rep):
        rep.pop("synthetic")
    reps = make_reports(tmp_path, prov, lin_by_proc, unmark)
    out = tmp_path / "run"
    ta.main([*map(str, reps.values()), "--manifest", str(mpath), "--outdir", str(out), "--synthetic", *CLI_P])
    assert json.loads((out / "results.json").read_text())["label"] == SYN


def _run(tmp_path, mpath, reps):
    out = tmp_path / "run"
    rc = ta.main([*map(str, reps), "--manifest", str(mpath), "--outdir", str(out), *CLI_P])
    return rc, json.loads((out / "results.json").read_text())


def test_missing_report_incomplete(tmp_path, manifest):
    mpath, prov = manifest
    reps = make_reports(tmp_path, prov, lin_by_proc)
    rc, doc = _run(tmp_path, mpath, [reps["tt"], reps["ss"]])
    assert rc == 1 and doc["status"] == "INCOMPLETE"
    assert doc["curves"]["ff"]["status"] == "INCOMPLETE" and doc["curves"]["tt"]["status"] == "COMPLETE"
    assert doc["curves"]["ff"]["monotonicity"].startswith("NOT EVALUATED")


def test_failed_corner_and_unreadable_report(tmp_path, manifest):
    mpath, prov = manifest

    def fail(proc, rep):
        if proc == "ss":
            rep["corners"][6]["status"] = "error"  # the 27 C anchor
    reps = make_reports(tmp_path, prov, lin_by_proc, fail)
    (tmp_path / "bad.json").write_text("{not json")
    rc, doc = _run(tmp_path, mpath, [reps["tt"], reps["ss"], reps["ff"], tmp_path / "bad.json"])
    assert rc == 1 and doc["status"] == "INCOMPLETE"
    ss = doc["curves"]["ss"]
    assert ss["status"] == "INCOMPLETE" and ss["f27_hz"] is None and ss["missing_anchors_c"] == [27.0]
    assert any("unreadable" in f["status"] for f in doc["report_failures"])


def test_zero_frequency_waveform_fails(tmp_path, manifest):
    """A clk stuck low (no crossings) is a waveform FAIL, never a frequency."""
    mpath, prov = manifest
    reps = make_reports(tmp_path, prov, lin_by_proc)
    rep = json.loads(reps["tt"].read_text())
    wf = Path(rep["corners"][3]["artifacts"]["waveform"])
    d = json.loads(wf.read_text())
    for pt in d["points"]:
        pt[1] = 0.0
    wf.write_text(json.dumps(d))
    rc, doc = _run(tmp_path, mpath, reps.values())
    tt = doc["curves"]["tt"]
    assert tt["status"] == "INCOMPLETE" and tt["rows"][3]["status"].startswith("FAIL:")


def test_provenance_mismatch_invalid(tmp_path, manifest):
    mpath, prov = manifest

    def wrong(proc, rep):
        if proc == "ff":
            rep["environment"]["netlist_sha256"] = "f" * 64
        if proc == "ss":
            rep["environment"]["netlist_closure"][1]["sha256"] = "0" * 64
    reps = make_reports(tmp_path, prov, lin_by_proc, wrong)
    rc, doc = _run(tmp_path, mpath, reps.values())
    assert rc == 1 and doc["status"] == "INVALID"
    assert doc["curves"]["ff"]["status"] == "INVALID" and doc["curves"]["ss"]["status"] == "INVALID"
    assert doc["curves"]["tt"]["status"] == "COMPLETE"
    assert all(r["status"].startswith("INVALID: provenance mismatch") for r in doc["curves"]["ss"]["rows"])


def test_wrong_process_and_duplicate_report_invalid(tmp_path, manifest):
    mpath, prov = manifest

    def swap(proc, rep):
        if proc == "tt":
            rep["corners"][2]["process"] = "ss"
    reps = make_reports(tmp_path, prov, lin_by_proc, swap)
    rc, doc = _run(tmp_path, mpath, [*reps.values(), reps["ff"]])
    assert doc["curves"]["ss"]["status"] == "INVALID"
    assert doc["curves"]["ff"]["status"] == "INVALID"  # second report for the same request


def test_tampered_manifest_rejected(tmp_path, manifest):
    mpath, prov = manifest
    for edit in (lambda m: m["calibration"]["codes"].update(tt="0xA4"),
                 lambda m: m["grid"]["temperature_c"].pop(),
                 lambda m: m["calibration"].update(campaign_runid="20260923T030905Z"),
                 lambda m: m.update(kind="waveform-bench-requests")):
        m = json.loads(mpath.read_text())
        edit(m)
        bad = tmp_path / "m.json"
        bad.write_text(json.dumps(m))
        with pytest.raises(ta.ProvenanceError):
            ta.load_manifest(bad)
    rc = ta.main([str(tmp_path / "x.json"), "--manifest", str(bad), "--outdir", str(tmp_path / "o")])
    assert rc == 2 and not (tmp_path / "o").exists()
