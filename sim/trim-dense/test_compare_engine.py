"""Offline tests for compare_engine.py (issue #378).  Every report here is a
SYNTHETIC FIXTURE built in this file; nothing is measured evidence and no
simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/trim-dense/test_compare_engine.py
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_engine as ce  # noqa: E402
import prepare  # noqa: E402

SCH = prepare.REPO / "sim" / "pvt-postlayout" / "klt-pex" / "rcosc_top_schematic.spice"
CORNER = (("tt", 27.0, 3.3),)
CURVE = "ext_tt_27C_3p3V"


def write_report(rdir, curve, code, freq, engine="46", binary=None, models=None, job=None,
                 status="pass", cstatus="pass", mstatus="pass", diag=None):
    rep = {"schema_version": 3, "status": status, "corner_count": 1,
           "diagnostic_counts": {"by_code": diag or {}, "by_severity": {}, "corners_with_diagnostics": 0},
           "corners": [{"process": "tt", "temperature_c": 27.0, "status": cstatus,
                        "measurements": [{"name": "fosc", "value": freq, "unit": "Hz", "status": mstatus}]}],
           "environment": {"engine_version": engine,
                           "engine_build": {"binary_sha256": binary or ("b" * 64)},
                           "models_lib_sha256": models or ("m" * 64),
                           **({"remote": {"job_id": job}} if job else {})}}
    (rdir / f"report_{curve}_c{code:02X}.json").write_text(json.dumps(rep))


def run_compare(a_dir, b_dir, tmp_path, curves=CURVE, half_lsb=None, out_json=None, label_a="46", label_b="47"):
    args = argparse.Namespace(
        reports_a=a_dir, reports_b=b_dir, label_a=label_a, label_b=label_b, curves=curves,
        half_lsb_pct=ce.analyze.HALF_LSB_PCT if half_lsb is None else half_lsb,
        out_json=out_json)
    return ce.cmd_compare(args)


def run_attest(tmp_path, ab_bench=None, ab_prov=None, frozen_prov=None, tags=None,
               pin_key="engine_version", ab_reports=None, expect_engine=None, expect_models_sha=None):
    args = argparse.Namespace(
        ab_bench=ab_bench, ab_prov=ab_prov, frozen_prov=frozen_prov, tags=tags, pin_key=pin_key,
        ab_reports=ab_reports, expect_engine=expect_engine, expect_models_sha=expect_models_sha)
    return ce.cmd_attest(args)


# ----------------------------------------------------------------- compare ----

def test_hand_calculated_paired_deltas_and_half_lsb_count(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    write_report(a, CURVE, 0x00, 100.0)
    write_report(a, CURVE, 0x01, 200.0)
    write_report(b, CURVE, 0x00, 102.0, engine="47")   # delta +2.0 %
    write_report(b, CURVE, 0x01, 201.0, engine="47")   # delta +0.5 %
    out = tmp_path / "cmp.json"
    assert run_compare(a, b, tmp_path, out_json=out) == 0
    res = json.loads(out.read_text())
    d = res["curves"][0]["delta_pct"]
    assert res["curves"][0]["n_pairs"] == 2
    assert d["min"] == pytest.approx(0.5) and d["max"] == pytest.approx(2.0)
    assert d["median"] == pytest.approx(1.25) and d["mean"] == pytest.approx(1.25)
    assert d["abs_over_half_lsb_count"] == 2 and d["half_lsb_pct"] == pytest.approx(40.0 / 255.0)
    assert res["overall"]["n_pairs"] == 2
    rows = res["curves"][0]["pairs"]
    assert rows[0]["code_hex"] == "0x00" and rows[0]["delta_pct"] == pytest.approx(2.0)
    assert rows[0]["f_a_hz"] == 100.0 and rows[0]["f_b_hz"] == 102.0
    assert rows[0]["over_half_lsb"] is True
    # A raised threshold must re-count, not re-measure.
    out2 = tmp_path / "cmp2.json"
    assert run_compare(a, b, tmp_path, half_lsb=3.0, out_json=out2) == 0
    assert json.loads(out2.read_text())["overall"]["abs_over_half_lsb_count"] == 0
    # Strictly-exceeding count: |delta| == threshold is not over.
    out3 = tmp_path / "cmp3.json"
    assert run_compare(a, b, tmp_path, half_lsb=2.0, out_json=out3) == 0
    assert json.loads(out3.read_text())["overall"]["abs_over_half_lsb_count"] == 1
    stdout = capsys.readouterr().out
    assert "OVERALL" in stdout and CURVE in stdout


def test_negative_deltas_and_diagnostic_tally(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    write_report(a, CURVE, 0x10, 50e6, diag={"nonconvergence": 1})
    write_report(b, CURVE, 0x10, 49.95e6, engine="47", diag={"singular_matrix": 2})
    out = tmp_path / "cmp.json"
    assert run_compare(a, b, tmp_path, out_json=out) == 0
    res = json.loads(out.read_text())
    row = res["curves"][0]["pairs"][0]
    assert row["delta_pct"] == pytest.approx(100.0 * (49.95 / 50.0 - 1.0))
    assert res["curves"][0]["diagnostic_codes_a"] == {"nonconvergence": 1}
    assert res["curves"][0]["diagnostic_codes_b"] == {"singular_matrix": 2}
    assert res["curves"][0]["delta_pct"]["abs_over_half_lsb_count"] == 0


def test_unpaired_and_unusable_reports_are_reported_not_dropped(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    write_report(a, CURVE, 0x00, 100.0)
    write_report(a, CURVE, 0x01, 200.0)
    write_report(a, CURVE, 0x02, 300.0, status="error")          # unusable in A
    write_report(a, CURVE, 0x03, 400.0, mstatus="fail")          # unusable in A
    write_report(b, CURVE, 0x00, 101.0, engine="47")
    write_report(b, CURVE, 0x01, 201.0, engine="47")
    write_report(b, CURVE, 0x04, 500.0, engine="47")             # no counterpart in A
    rc = run_compare(a, b, tmp_path)
    assert rc == 1
    captured = capsys.readouterr()
    err, out = captured.err, captured.out
    assert "0x04 in --reports-b has no counterpart in --reports-a" in err
    assert "c02.json: report status 'error' != pass" in err
    assert "c03.json: fosc status 'fail' != pass" in err
    # The good pair is still compared.
    assert "n=2" in out


def test_baseline_codes_not_resampled_are_expected_not_problems(tmp_path, capsys):
    """The A/B design re-runs a sparse sample of a complete baseline set: A
    codes without a B counterpart are the normal state, reported in the JSON
    but never failing the run."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    for c in range(0, 8):
        write_report(a, CURVE, c, 100.0 + c)
    for c in (0x00, 0x04):
        write_report(b, CURVE, c, 100.0 + c, engine="47")
    out = tmp_path / "cmp.json"
    assert run_compare(a, b, tmp_path, out_json=out) == 0
    res = json.loads(out.read_text())
    cv = res["curves"][0]
    assert cv["n_pairs"] == 2
    assert cv["unsampled_a_codes"] == ["0x01", "0x02", "0x03", "0x05", "0x06", "0x07"]
    assert cv["unpaired_b_codes"] == []
    assert "a-codes not sampled: 6" in capsys.readouterr().out


def test_compare_detects_mixed_versions_within_a_set(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    write_report(a, CURVE, 0x00, 100.0, engine="46")
    write_report(a, CURVE, 0x01, 200.0, engine="47")             # mixed set
    write_report(b, CURVE, 0x00, 100.0, engine="47")
    write_report(b, CURVE, 0x01, 200.0, engine="47")
    assert run_compare(a, b, tmp_path, label_a="46", label_b="47") == 1
    assert "non-uniform engine_version" in capsys.readouterr().err


def test_compare_out_json_refuses_overwrite_and_requires_pairs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    write_report(a, CURVE, 0x00, 100.0)
    out = tmp_path / "cmp.json"
    out.write_text("keep me")
    assert run_compare(a, b, tmp_path, out_json=out) == 2
    assert out.read_text() == "keep me"
    # Only one side populated: no pairs -> exit 1 even without problems.
    (a / f"report_{CURVE}_c01.json").write_text("{not json")
    rc = run_compare(a, b, tmp_path)
    assert rc == 1


# ------------------------------------------------------------------ attest ----

def ext_fixture(tmp_path):
    p = tmp_path / "ext_fixture.spice"
    p.write_text("* FIXTURE extracted netlist stand-in\n"
                 ".subckt rcosc_top clk t0 t1 t2 t3 t4 t5 t6 t7 vdd vss\n.ends rcosc_top\n")
    return p


@pytest.fixture
def benches(tmp_path, no_exec):
    """(frozen bench/prov, pinned A/B bench/prov) over the same inputs."""
    ext = ext_fixture(tmp_path)
    frozen = tmp_path / "frozen"
    prov_f = prepare.generate(frozen, SCH, ext, CORNER)
    ab = tmp_path / "ab"
    prov_a = prepare.generate(ab, SCH, ext, CORNER, {"engine_version_expected": "47"})
    return frozen, prov_a, ab, tmp_path / "frozen" / "provenance.json", tmp_path / "ab" / "provenance.json"


@pytest.fixture
def no_exec(monkeypatch):
    import os
    import subprocess

    def boom(*a, **k):
        raise AssertionError("tests must not launch any process")
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, boom)
    monkeypatch.setattr(os, "system", boom)


def test_attest_pinned_bench_matches_frozen_mod_pin(benches, tmp_path, capsys):
    frozen_dir, prov_a, ab_dir, prov_f_path, prov_a_path = benches
    rc = run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path)
    assert rc == 0, capsys.readouterr().err
    out = capsys.readouterr().out
    assert f"attested {len(prov_a['requests'])} tag(s)" in out
    assert f"{len(prov_a['requests'])} carried the 'engine_version' key" in out


def test_attest_reports_an_edited_request_even_when_its_own_hash_is_fixed(benches, tmp_path, capsys):
    """A consistent-but-different bench (request edited AND provenance hash
    updated to match) must still fail the frozen comparison."""
    frozen_dir, prov_a, ab_dir, prov_f_path, prov_a_path = benches
    victim = prov_a["requests"][7]
    rf = ab_dir / victim["request"]
    req = json.loads(rf.read_text())
    req["options"]["timeout_s"] = 999
    raw = (json.dumps(req, indent=2) + "\n").encode()
    rf.write_bytes(raw)
    prov = json.loads(prov_a_path.read_text())
    prov["requests"][7]["sha256"]["request"] = hashlib.sha256(raw).hexdigest()
    prov_a_path.write_text(json.dumps(prov, indent=2) + "\n")
    rc = run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path)
    assert rc == 1
    err = capsys.readouterr().err
    assert victim["tag"] in err and "!= frozen" in err


def test_attest_unknown_and_missing_tags_fail(benches, tmp_path, capsys):
    frozen_dir, prov_a, ab_dir, prov_f_path, prov_a_path = benches
    some = prov_a["requests"][0]["tag"]
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=f"{some},no_such_tag") == 1
    err = capsys.readouterr().err
    assert "no_such_tag" in err
    # A frozen provenance missing the tag entirely is a hard problem too.
    prov_f = json.loads(prov_f_path.read_text())
    prov_f["requests"] = [e for e in prov_f["requests"] if e["tag"] != some]
    prov_f_path.write_text(json.dumps(prov_f, indent=2) + "\n")
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=some) == 1
    assert "not in the frozen provenance" in capsys.readouterr().err


def test_attest_report_audit_uniformity_and_job_ids(benches, tmp_path, capsys):
    frozen_dir, prov_a, ab_dir, prov_f_path, prov_a_path = benches
    r = tmp_path / "reports"
    r.mkdir()
    write_report(r, CURVE, 0x00, 1e6, engine="47", binary="c" * 64, models="f6" + "a" * 62, job="j-1")
    write_report(r, CURVE, 0x01, 1e6, engine="47", binary="c" * 64, models="f6" + "a" * 62, job="j-2")
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=prov_a["requests"][0]["tag"], ab_reports=r,
                      expect_engine="47", expect_models_sha="f6" + "a" * 62) == 0
    out = capsys.readouterr().out
    assert "engine_version=47" in out and "remote job ids distinct=True" in out
    # A stray ngspice-46 report breaks uniformity; a duplicated or missing
    # remote job id is a hard problem too.
    write_report(r, CURVE, 0x02, 1e6, engine="46", binary="c" * 64, models="f6" + "a" * 62, job="j-3")
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=prov_a["requests"][0]["tag"], ab_reports=r, expect_engine="47") == 1
    assert "non-uniform engine_version" in capsys.readouterr().err
    write_report(r, CURVE, 0x02, 1e6, engine="47", binary="c" * 64, models="f6" + "a" * 62, job="j-1")
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=prov_a["requests"][0]["tag"], ab_reports=r) == 1
    assert "duplicate remote job ids" in capsys.readouterr().err
    write_report(r, CURVE, 0x02, 1e6, engine="47", binary="c" * 64, models="f6" + "a" * 62, job=None)
    assert run_attest(tmp_path, ab_bench=ab_dir, ab_prov=prov_a_path, frozen_prov=prov_f_path,
                      tags=prov_a["requests"][0]["tag"], ab_reports=r) == 1
    assert "without environment.remote.job_id" in capsys.readouterr().err


def test_split_tag_and_unreadable_inputs(tmp_path, capsys):
    assert ce.split_tag("report_ext_tt_27C_3p3V_c0F") == (CURVE, 0x0F)
    assert ce.split_tag("report_sch_ff_85C_3p6V_cB3") == ("sch_ff_85C_3p6V", 0xB3)
    assert ce.split_tag("report_x_cZZ") is None
    assert ce.split_tag("other_ext_tt_27C_3p3V_c00") is None
    assert ce.split_tag("report_nocodes") is None
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / f"report_{CURVE}_c00.json").write_text("{not json")
    (bad / "not_a_report.json").write_text("{}")
    recs, probs = ce.load_set(bad, None)
    assert recs == {} and len(probs) == 1 and "unreadable" in probs[0]
    assert run_attest(tmp_path, ab_bench=tmp_path, ab_prov=tmp_path / "nope.json",
                      frozen_prov=tmp_path / "nope2.json") == 2
