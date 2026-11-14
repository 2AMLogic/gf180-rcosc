"""Offline tests for sim/startup-settled (issue #346).

The regen/trim-pattern checks run the real `gen_requests.py`; the manifest
check feeds `settled_report.py` a SYNTHETIC report + SYNTHETIC waveform
fixture built in this file. Nothing here is measured evidence and no
simulator, klt, or cloud operation is invoked (the klt --version lookup is
stubbed).  Run:
  python3 -I -m pytest -p no:cacheprovider sim/startup-settled/test_startup_settled.py
"""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
REPO = SIM.parent
GEN = HERE / "gen_requests.py"
REPORT = HERE / "settled_report.py"
EXTRACTION = REPO / "sim" / "row45-rerun" / "results" / "20261112T200335Z-extract-l07" / "rcosc_top_p3_cmphfix.spice"

sys.path.insert(0, str(SIM))
from _module_loader import load_module  # noqa: E402

GENERATED = ["rcosc_top_p3.spice", "tb_v30.spice", "tb_v33.spice", "tb_v36.spice",
             "request_v30.json", "request_v33.json", "request_v36.json"]


# ------------------------------------------------------------ fixtures -----

def _oscillator_waveform(path, vdd):
    """SYNTHETIC 20 us run: 1 us 0->VDD ramp then a steady 48 MHz clock."""
    p, amp, tstop, step = 1.0 / 48e6, vdd, 20e-6, 200e-12
    pts, t = [], 0.0
    half = p / 2
    while t <= tstop + step:
        vdd_t = vdd * min(t / 1e-6, 1.0)
        phase = t % p
        if phase < step:
            clk = amp * phase / step
        elif phase < half:
            clk = amp
        elif phase < half + step:
            clk = amp * (1 - (phase - half) / step)
        else:
            clk = 0.0
        pts.append([t, clk, vdd_t])
        t += step
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"variables": [{"name": n} for n in ("time", "v(clk)", "v(vdd)")],
                                "points": pts}))
    return path


def _synthetic_report(path, vdd, corner):
    path.parent.mkdir(parents=True, exist_ok=True)
    wf = Path("unused") / corner / "waveform.raw.json"  # only parent name + name are read back
    path.write_text(json.dumps({
        "status": "pass", "corner_count": 1,
        "environment": {"remote": {"job_id": f"klt-sim-synthetic-v{vdd:g}", "provider": "aws-batch-fleet",
                                   "runner_klt_version": "0.0.0-synthetic", "client_klt_version": "0.0.0-synthetic"}},
        "corners": [{"process": corner.split("_")[0], "temperature_c": 27.0, "status": "pass",
                     "measurements": [], "artifacts": {"waveform": str(wf)}}],
    }))
    return path


@pytest.fixture
def report_mod(monkeypatch, tmp_path):
    """settled_report with HERE pointed at a temp home and klt stubbed."""
    mod = load_module("settled_report_t", REPORT, reuse=False)
    monkeypatch.setattr(mod, "HERE", tmp_path)
    monkeypatch.setattr(mod, "subprocess",
                        types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout="klt 0.0.0-synthetic")))
    return mod


def _run_report(mod, tmp_path, reports, runid, dut, code):
    argv = [REPORT.name] + [str(r) for r in reports] + [
        "--vdd", "3.0", "3.3", "3.6",
        "--artifacts-root", str(tmp_path / "artifacts"), str(tmp_path / "artifacts"), str(tmp_path / "artifacts"),
        "--dut", str(dut), "--code", code, "--runid", runid]
    old = sys.argv
    sys.argv = argv
    try:
        mod.main()
    finally:
        sys.argv = old
    return tmp_path / "results" / runid


# -------------------------------------------------- gen_requests.py --------

def test_regeneration_with_defaults_is_byte_identical(tmp_path):
    """No flags -> the committed 0xA9 requests/testbenches reproduce exactly."""
    subprocess.run([sys.executable, "-I", str(GEN), "--out", str(tmp_path)], check=True)
    for name in GENERATED:
        assert (tmp_path / name).read_bytes() == (HERE / name).read_bytes(), name


def test_code_flag_drives_the_trim_pattern(tmp_path):
    """--code 0xA4 ramps trim bits 2, 5, 7 and holds the rest at DC 0 (#346)."""
    subprocess.run([sys.executable, "-I", str(GEN), "--out", str(tmp_path), "--code", "0xA4",
                    "--dut", str(EXTRACTION)], check=True)
    tb = (tmp_path / "tb_v33.spice").read_text()
    assert "trim 0xA4" in tb
    ramp = {f"VT{i}" for i in range(8) if f"VT{i} t{i} 0 PWL" in tb}
    dc = {f"VT{i}" for i in range(8) if f"VT{i} t{i} 0 DC 0" in tb}
    assert ramp == {"VT2", "VT5", "VT7"} and dc == {"VT0", "VT1", "VT3", "VT4", "VT6"}
    # the copied DUT is the committed extraction, byte for byte
    assert (tmp_path / "rcosc_top_p3.spice").read_bytes() == EXTRACTION.read_bytes()
    # the committed 0xA9 default ramps bits 0, 3, 5, 7 instead
    tb9 = (HERE / "tb_v33.spice").read_text()
    assert {f"VT{i}" for i in range(8) if f"VT{i} t{i} 0 PWL" in tb9} == {"VT0", "VT3", "VT5", "VT7"}


# ------------------------------------------------ settled_report.py --------

def test_manifest_records_actual_provenance(report_mod, tmp_path):
    """manifest.json dut/dut_sha256/trim_code match the caller's inputs (#346)."""
    reports = []
    for k, v in enumerate((30, 33, 36)):
        _oscillator_waveform(tmp_path / "artifacts" / f"tt_27C_v{k}" / "waveform.raw.json", v / 10)
        reports.append(_synthetic_report(tmp_path / f"report_v{v}.json", v, corner=f"tt_27C_v{k}"))
    dut = tmp_path / "dut.spice"
    dut.write_text("* synthetic DUT for the provenance test\n.end\n")
    out = _run_report(report_mod, tmp_path, reports, "TEST01", dut, "0xA4")
    m = json.load(open(out / "manifest.json"))
    assert m["dut"] == str(dut)
    assert m["dut_sha256"] == hashlib.sha256(dut.read_bytes()).hexdigest()
    assert m["trim_code"] == "0xA4"
    summary = (out / "summary.md").read_text()
    assert str(dut) in summary and "trim code 0xA4" in summary


def test_report_refuses_to_overwrite_runid(report_mod, tmp_path):
    reports = [_synthetic_report(tmp_path / f"report_v{v}.json", v, corner="tt_27C") for v in (30, 33, 36)]
    for k, v in enumerate((30, 33, 36)):
        _oscillator_waveform(tmp_path / "artifacts" / f"tt_27C" / "waveform.raw.json", v / 10)
    _run_report(report_mod, tmp_path, reports, "TEST02", HERE / "rcosc_top_p3.spice", "0xA9")
    with pytest.raises(SystemExit):
        _run_report(report_mod, tmp_path, reports, "TEST02", HERE / "rcosc_top_p3.spice", "0xA9")


def test_verdict_surfaces_nonstart_and_overbound_as_fail():
    """NON-START / out-of-band points are FAIL verdicts, never dropped (#346)."""
    mod = load_module("settled_report_verdict_t", REPORT, reuse=False)
    sr = mod.sr
    started = {"status": "STARTED", f"t_settle_{sr.PRIMARY}_ns": 9000}
    assert mod.verdict(started) == "pass"
    assert mod.verdict({**started, f"t_settle_{sr.PRIMARY}_ns": sr.SPEC_US * 1e3 + 1}) == "FAIL: > 10 us"
    assert mod.verdict({**started, f"t_settle_{sr.PRIMARY}_ns": None}) == "FAIL: not within band at end of run"
    assert mod.verdict({"status": "NON-START"}) == "FAIL: NON-START"
