"""Offline tests for sim/trim-dense (issue #98).  Every frequency curve and
report here is a SYNTHETIC FIXTURE built in this file; nothing is measured
evidence and no simulator or cloud operation is invoked (subprocess/os.system
are monkeypatched to fail inside the generation tests).

Run:  python3 -I -m pytest -p no:cacheprovider sim/trim-dense/test_harness.py
"""
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import prepare  # noqa: E402

SCH = prepare.REPO / "sim" / "pvt-postlayout" / "klt-pex" / "rcosc_top_schematic.spice"
CORNER = (("tt", 27.0, 3.3),)
NOM = 80 / 255


def linear(f0=36e6, k=NOM / 100):
    """FIXTURE: arithmetic-ramp frequency curve, mean step exactly 80 %/255."""
    return [f0 * (1 + k * c) for c in range(256)]


def entries(freqs):
    return [{"code": c, "freq_hz": f} for c, f in enumerate(freqs)]


# ------------------------------------------------------------ analysis ----

def test_hand_calculated_steps_and_signs():
    assert analyze.step_pct(100.0, 101.0) == pytest.approx(1.0)
    assert analyze.step_pct(100.0, 99.5) == pytest.approx(-0.5)
    assert analyze.step_pct(50e6, 50e6) == 0.0
    # Ratio, not difference of percentages: 40 -> 40.1256 MHz is +0.314 %.
    assert analyze.step_pct(40e6, 40.1256e6) == pytest.approx(0.314, abs=1e-9)
    assert analyze.NOMINAL_STEP_PCT == pytest.approx(0.3137254901960784)
    assert analyze.HALF_LSB_PCT == pytest.approx(0.1568627450980392)


def test_monotone_curve_tables_extrema_carries_and_resolution():
    f = analyze.normalize_curve(entries(linear()))
    rows = analyze.step_table(f)
    assert [r["code"] for r in rows] == list(range(256))
    assert rows[255]["step_to_next_pct"] is None
    assert rows[0]["step_to_next_pct"] == pytest.approx(100 * (f[1] / f[0] - 1))
    s = analyze.summarize(f)
    assert s["strictly_increasing"] and s["non_positive_transitions"] == []
    assert s["worst_negative_step"] is None
    # An arithmetic ramp has the largest ratio-step at code 0 and the smallest at 0xFE.
    assert s["worst_positive_step"]["from_hex"] == "0x00"
    assert s["min_step"]["from_hex"] == "0xFE"
    assert [t["carry"] for t in s["carry_transitions"]] == [
        "0x7F->0x80", "0xBF->0xC0", "0xDF->0xE0", "0xEF->0xF0"]
    assert s["span_pct"] == pytest.approx(80.0)
    rc = s["ratified_comparison"]
    assert rc["mean_step_pct"] == pytest.approx(80 / 255)
    assert rc["mean_step_over_nominal"] == pytest.approx(1.0)
    # step[0] = k*100 = nominal exactly; step[254] = nominal/(1+254/255*0.8)... within half-LSB.
    assert rc["steps_outside_half_lsb_count"] == 0
    assert rc["max_abs_deviation_at"] == "0xFE->0xFF"


def test_known_negative_carry_steps_are_reported():
    freqs = linear()
    for lo in (0x7F, 0xBF):              # break two carry transitions
        freqs[lo + 1] = freqs[lo] * 0.998
        for c in range(lo + 2, 256):     # keep the rest ordered above the dip
            freqs[c] = max(freqs[c], freqs[lo + 1] * 1.001 ** (c - lo))
    f = analyze.normalize_curve(entries(freqs))
    s = analyze.summarize(f)
    nonpos = {t["from_hex"] for t in s["non_positive_transitions"]}
    assert {"0x7F", "0xBF"} <= nonpos
    assert not s["strictly_increasing"]
    assert s["worst_negative_step"]["step_pct"] == pytest.approx(-0.2)
    by = {t["carry"]: t for t in s["carry_transitions"]}
    assert by["0x7F->0x80"]["step_pct"] == pytest.approx(-0.2)
    assert by["0xBF->0xC0"]["step_pct"] == pytest.approx(-0.2)
    assert by["0xDF->0xE0"]["step_pct"] > 0
    # Outside-half-LSB accounting: -0.2 % deviates from 0.3137 by 0.5137 > 0.1569.
    assert "0x7F->0x80" in s["ratified_comparison"]["steps_outside_half_lsb_codes"]


def test_constant_frequencies_are_non_positive_not_monotone():
    s = analyze.summarize(analyze.normalize_curve(entries([48e6] * 256)))
    assert len(s["non_positive_transitions"]) == 255
    assert not s["strictly_increasing"]
    assert s["worst_positive_step"] is None and s["worst_negative_step"] is None
    assert s["span_pct"] == 0.0


def test_half_lsb_boundary_hand_check():
    f = [100.0] * 256
    for c in range(1, 256):              # every step exactly nominal + 0.2 pp -> outside
        f[c] = f[c - 1] * (1 + (NOM + 0.2) / 100)
    rc = analyze.summarize(f)["ratified_comparison"]
    assert rc["steps_outside_half_lsb_count"] == 255
    assert rc["max_abs_deviation_pct"] == pytest.approx(0.2)
    assert rc["max_abs_dnl_lsb"] == pytest.approx(0.2 / NOM)
    for c in range(1, 256):              # every step nominal + 0.1 pp -> inside
        f[c] = f[c - 1] * (1 + (NOM + 0.1) / 100)
    assert analyze.summarize(f)["ratified_comparison"]["steps_outside_half_lsb_count"] == 0


def test_shuffled_entries_are_normalized_by_code():
    import random
    es = entries(linear())
    random.Random(7).shuffle(es)
    assert analyze.normalize_curve(es) == analyze.normalize_curve(entries(linear()))


@pytest.mark.parametrize("mutate, kind, status", [
    (lambda es: es.pop(10), "missing", "INCOMPLETE"),
    (lambda es: es.append(dict(es[5])), "duplicate", "INVALID"),
    (lambda es: es[3].update(status="error", error="no convergence"), "failed", "INCOMPLETE"),
    (lambda es: es[3].update(freq_hz=math.nan), "non_finite", "INVALID"),
    (lambda es: es[3].update(freq_hz=math.inf), "non_finite", "INVALID"),
    (lambda es: es[3].update(freq_hz=None), "non_finite", "INVALID"),
    (lambda es: es[3].update(freq_hz="48e6"), "non_finite", "INVALID"),
    (lambda es: es[3].update(freq_hz=True), "non_finite", "INVALID"),
    (lambda es: es[3].update(freq_hz=0.0), "non_positive", "INVALID"),
    (lambda es: es[3].update(freq_hz=-1e6), "non_positive", "INVALID"),
    (lambda es: es[3].update(code=256), "bad_code", "INVALID"),
])
def test_invalid_entries_fail_validation(mutate, kind, status):
    es = entries(linear())
    mutate(es)
    with pytest.raises(analyze.CurveError) as ei:
        analyze.normalize_curve(es)
    kinds = {p["kind"] for p in ei.value.problems}
    assert kind in kinds
    assert analyze.curve_status(ei.value.problems) == status


def test_too_few_entries_lists_every_missing_code():
    with pytest.raises(analyze.CurveError) as ei:
        analyze.normalize_curve(entries(linear())[:200])
    assert [p["code"] for p in ei.value.problems] == list(range(200, 256))


# ----------------------------------------------------------- generation ----

@pytest.fixture
def no_exec(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("generation must not launch any process")
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, boom)
    monkeypatch.setattr(os, "system", boom)


def ext_fixture(tmp_path):
    p = tmp_path / "ext_fixture.spice"
    p.write_text("* FIXTURE extracted netlist stand-in\n"
                 ".subckt rcosc_top clk t0 t1 t2 t3 t4 t5 t6 t7 vdd vss\n.ends rcosc_top\n")
    return p


def test_generation_default_grid_coverage_and_batch_only(tmp_path, no_exec):
    ext = ext_fixture(tmp_path)
    out = tmp_path / "bench"
    prov = prepare.generate(out, SCH, ext)
    assert len(prov["requests"]) == 2 * 3 * 256
    groups = {}
    for e in prov["requests"]:
        groups.setdefault((e["variant"], e["corner"]), []).append(e["code"])
    assert set(groups) == {(v, c) for v in ("sch", "ext")
                           for c in ("tt_27C_3p3V", "ss_m40C_3p0V", "ff_85C_3p6V")}
    for codes in groups.values():
        assert sorted(codes) == list(range(256))     # exactly 256 unique codes
    assert len({e["tag"] for e in prov["requests"]}) == len(prov["requests"])
    for e in prov["requests"][::97]:
        req = json.loads((out / e["request"]).read_text())
        assert req["backend"] == "batch"
        assert len(req["corners"]["process"]) == 1 and len(req["corners"]["temperature_c"]) == 1
        assert req["netlist_source"] == ("schematic" if e["variant"] == "sch" else "extracted")
        assert req["corners"]["temperature_c"] == [e["temperature_c"]]
        vmid = f"{e['vdd_v'] / 2:.4f}"
        assert all(f"v(clk)={vmid}" in m["spice"] for m in req["measurements"] if m["name"] in ("ta", "tb"))
        assert hashlib.sha256((out / e["request"]).read_bytes()).hexdigest() == e["sha256"]["request"]
        tb = (out / e["netlist"]).read_text()
        for i in range(8):
            want = e["vdd_v"] * ((e["code"] >> i) & 1)
            assert f"VT{i} t{i} 0 DC {want:g}\n" in tb
        assert ".options reltol=0.001 abstol=1e-12 vntol=1e-06" in tb
    s = prov["corners"]
    assert [(c["process"], c["temperature_c"], c["vdd_v"]) for c in s] == [
        ("tt", 27.0, 3.3), ("ss", -40.0, 3.0), ("ff", 85.0, 3.6)]
    assert "NOT EVIDENCE" in prov["evidence"]


def test_generation_records_hashes_solver_and_manifest_template(tmp_path):
    ext = ext_fixture(tmp_path)
    out = tmp_path / "bench"
    prov = prepare.generate(out, SCH, ext, CORNER, {"reltol": 1e-4, "engine_version_expected": "46"})
    assert prov["inputs"]["sch"]["sha256"] == hashlib.sha256(SCH.read_bytes()).hexdigest()
    assert prov["inputs"]["ext"]["sha256"] == hashlib.sha256(ext.read_bytes()).hexdigest()
    assert prov["settings"]["reltol"] == 1e-4 and prov["settings"]["engine_version_expected"] == "46"
    assert "reltol=0.0001" in (out / prov["requests"][0]["netlist"]).read_text()
    tmpl = json.loads((out / "manifest.template.json").read_text())
    assert tmpl["_template"] is True and tmpl["solver"]["reltol"] == 1e-4
    for k in prepare.MANIFEST_REQUIRED:
        if k not in ("backend", "engine"):
            assert tmpl[k] is None
    assert tmpl["backend"] == "batch"
    assert prov["execution"]["local_grid_fallback"].startswith("forbidden")


def test_generation_rejects_bad_inputs(tmp_path):
    bad = tmp_path / "bad.spice"
    bad.write_text(".subckt rcosc_top vdd vss clk t0 t1 t2 t3 t4 t5 t6 t7\n.ends\n")
    with pytest.raises(prepare.PrepareError, match="pins"):
        prepare.generate(tmp_path / "a", bad, None, CORNER)
    bad.write_text("* nothing\n")
    with pytest.raises(prepare.PrepareError, match="no `.subckt rcosc_top`"):
        prepare.generate(tmp_path / "b", bad, None, CORNER)
    with pytest.raises(prepare.PrepareError, match="at least one"):
        prepare.generate(tmp_path / "c", None, None, CORNER)
    with pytest.raises(prepare.PrepareError, match="unreadable"):
        prepare.generate(tmp_path / "d", tmp_path / "missing.spice", None, CORNER)
    with pytest.raises(prepare.PrepareError, match="supply"):
        prepare.generate(tmp_path / "e", SCH, None, (("tt", 27.0, 3.1),))
    with pytest.raises(prepare.PrepareError, match="temperature"):
        prepare.generate(tmp_path / "f", SCH, None, (("tt", 30.0, 3.3),))
    with pytest.raises(prepare.PrepareError, match="unknown process"):
        prepare.generate(tmp_path / "g", SCH, None, (("xx", 27.0, 3.3),))
    with pytest.raises(prepare.PrepareError, match="duplicate"):
        prepare.generate(tmp_path / "h", SCH, None, CORNER * 2)
    with pytest.raises(prepare.PrepareError, match="positive"):
        prepare.generate(tmp_path / "i", SCH, None, CORNER, {"reltol": 0})
    full = tmp_path / "full"
    full.mkdir()
    (full / "x").write_text("x")
    with pytest.raises(prepare.PrepareError, match="not empty"):
        prepare.generate(full, SCH, None, CORNER)


# -------------------------------------------------------- report flow ------

def write_report(rdir, entry, freq, synthetic=True, remote=None, status="pass", cstatus="pass",
                 process=None, temp=None, mstatus="pass", engine="46", sha=None):
    c = {"process": process or entry["process"], "temperature_c": entry["temperature_c"] if temp is None else temp,
         "status": cstatus,
         "measurements": [{"name": "fosc", "value": freq, "unit": "Hz", "status": mstatus}]}
    rep = {"schema_version": 3, "status": status, "corner_count": 1, "corners": [c],
           "environment": {"engine_version": engine, **({"remote": remote} if remote else {}),
                           **({"netlist_sha256": sha} if sha else {})}}
    if synthetic:
        rep["synthetic"] = True
    (rdir / f"report_{entry['tag']}.json").write_text(json.dumps(rep))


@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    d = tmp_path_factory.mktemp("b")
    ext = d / "ext_fixture.spice"
    ext.write_text(ext_fixture(d).read_text())
    out = d / "bench"
    prov = prepare.generate(out, SCH, ext, CORNER)
    return out, prov


def fill(bench, tmp_path, rdir, freqs_by_variant=None, **kw):
    out, prov = bench
    for e in prov["requests"]:
        f = (freqs_by_variant or {}).get(e["variant"], linear())[e["code"]]
        write_report(rdir, e, f, **kw)


def test_synthetic_campaign_ok_is_labelled_fixture(tmp_path, bench):
    out, prov = bench
    r = tmp_path / "r"
    r.mkdir()
    fill(bench, tmp_path, r)
    res = analyze.analyse_campaign(out, r)
    assert res["synthetic"] and res["banner"] == analyze.SYN_BANNER
    assert res["all_curves_valid"] and len(res["curves"]) == 2
    c = res["curves"][0]
    assert c["status"] == "OK" and len(c["table"]) == 256
    analyze.write_run(tmp_path / "res", res)
    assert analyze.SYN_BANNER in (tmp_path / "res" / "summary.md").read_text()
    assert analyze.SYN_BANNER in (tmp_path / "res" / "steps.csv").read_text()
    with pytest.raises(FileExistsError):
        analyze.write_run(tmp_path / "res", res)


def test_report_level_failures_are_incomplete_not_passing(tmp_path, bench):
    out, prov = bench
    r = tmp_path / "r"
    r.mkdir()
    fill(bench, tmp_path, r)
    ents = [e for e in prov["requests"] if e["variant"] == "sch"]
    (r / f"report_{ents[4]['tag']}.json").unlink()                             # missing
    write_report(r, ents[5], 1.0, status="error")                              # refused/errored report
    write_report(r, ents[6], None, cstatus="error")                            # corner error
    write_report(r, ents[7], 1.0, mstatus="fail")                              # failed measurement
    write_report(r, ents[8], 1.0, process="ss")                                # wrong corner
    write_report(r, ents[9], 1.0, sha="0" * 64)                                # wrong testbench hash
    (r / f"report_{ents[10]['tag']}.json").write_text("{not json")             # unreadable
    write_report(r, ents[11], math.nan)                                        # non-finite
    res = analyze.analyse_campaign(out, r)
    sch = next(c for c in res["curves"] if c["variant"] == "sch")
    assert sch["status"] == "INVALID" and "table" not in sch and "summary" not in sch
    kinds = {}
    for p in sch["problems"]:
        kinds.setdefault(p["kind"], []).append(p["code"])
    assert kinds["missing"] == [4]
    assert kinds["failed"] == [5, 6, 7, 8, 9, 10]
    assert kinds["non_finite"] == [11] or 11 in kinds["non_finite"]
    assert not res["all_curves_valid"]
    ext = next(c for c in res["curves"] if c["variant"] == "ext")
    assert ext["status"] == "OK"                                               # failures stay local to one curve


def test_incomplete_only_when_all_problems_are_missing_or_failed(tmp_path, bench):
    out, prov = bench
    r = tmp_path / "r"
    r.mkdir()
    fill(bench, tmp_path, r)
    e = next(e for e in prov["requests"] if e["variant"] == "sch")
    (r / f"report_{e['tag']}.json").unlink()
    res = analyze.analyse_campaign(out, r)
    assert next(c for c in res["curves"] if c["variant"] == "sch")["status"] == "INCOMPLETE"


def test_non_synthetic_requires_provenance_and_batch(tmp_path, bench):
    out, prov = bench
    r = tmp_path / "r"
    r.mkdir()
    fill(bench, tmp_path, r, synthetic=False, remote="job-1")
    res = analyze.analyse_campaign(out, r)                                     # no manifest
    assert not res["synthetic"] and not res["all_curves_valid"]
    assert res["banner"] == analyze.NOPROV_BANNER
    assert any("no --manifest" in e for e in res["run_errors"])
    # unfilled template
    tmpl = out / "manifest.template.json"
    res = analyze.analyse_campaign(out, r, tmpl)
    assert any("unfilled template" in e for e in res["run_errors"])
    assert any("'git_sha' missing" in e for e in res["run_errors"])
    # filled manifest passes
    man = tmp_path / "man.json"
    m = json.loads(tmpl.read_text())
    m = {k: v for k, v in m.items() if not k.startswith("_")}
    m |= {"git_sha": "a" * 40, "git_dirty": False, "klt_version": "0.0.0-fixture", "engine_version": "46",
          "pdk": "gf180mcuC", "pdk_revision": "unknown", "pdk_revision_reason": "fixture",
          "executed_utc": "2000-01-01T00:00:00+00:00",
          "provenance_sha256": hashlib.sha256((out / "provenance.json").read_bytes()).hexdigest()}
    man.write_text(json.dumps(m))
    res = analyze.analyse_campaign(out, r, man)
    assert res["run_errors"] == [] and res["all_curves_valid"] and not res["synthetic"]
    assert "SYNTHETIC" not in res["banner"]
    # wrong provenance hash, solver drift, mixed engines
    m2 = m | {"provenance_sha256": "0" * 64, "solver": m["solver"] | {"reltol": 1e-4}}
    man.write_text(json.dumps(m2))
    errs = analyze.analyse_campaign(out, r, man)["run_errors"]
    assert any("provenance_sha256" in e for e in errs) and any("solver.reltol" in e for e in errs)
    man.write_text(json.dumps(m | {"engine_version": "42"}))
    assert any("engine_version" in e for e in analyze.analyse_campaign(out, r, man)["run_errors"])
    # local (non-remote) report in a non-synthetic run fails that curve
    fill(bench, tmp_path, r, synthetic=False, remote=None)
    man.write_text(json.dumps(m))
    res = analyze.analyse_campaign(out, r, man)
    assert not res["all_curves_valid"]
    assert any("batch fleet" in p["detail"] for c in res["curves"] for p in c["problems"])


def test_cli_synthetic_end_to_end(tmp_path, bench):
    out, prov = bench
    r = tmp_path / "r"
    r.mkdir()
    fill(bench, tmp_path, r, synthetic=False, remote="job-1")
    cmd = [sys.executable, "-I", str(HERE / "analyze.py"), "--bench-dir", str(out), "--reports-dir", str(r),
           "--outdir", str(tmp_path / "o")]
    p = subprocess.run(cmd, capture_output=True, text=True)       # non-synthetic, no manifest
    assert p.returncode == 1 and analyze.NOPROV_BANNER in p.stdout
    sr = tmp_path / "sr"
    sr.mkdir()
    fill(bench, tmp_path, sr)
    p = subprocess.run(cmd[:6] + [str(sr), "--outdir", str(tmp_path / "o2")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert analyze.SYN_BANNER in p.stdout
    assert (tmp_path / "o2" / "results.json").exists()


def test_cli_prepare_end_to_end(tmp_path):
    ext = ext_fixture(tmp_path)
    cmd = [sys.executable, "-I", str(HERE / "prepare.py"), "--schematic-netlist", str(SCH),
           "--extracted-netlist", str(ext), "--out", str(tmp_path / "o"), "--corner", "tt:27:3.3",
           "--reltol", "0.0003"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "512 request(s)" in p.stdout and "NOT submitted" in p.stdout
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode != 0 and "not empty" in p.stderr


def test_no_measured_artifacts_in_tree():
    assert not (HERE / "results").exists()
