import datetime
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_common as ec  # noqa: E402


def test_banner_literal_is_frozen():
    assert ec.SYNTHETIC_BANNER == "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"
    assert ec.banner(True) == ec.SYNTHETIC_BANNER
    assert ec.banner(False) == ec.MEASURED_BANNER


def test_sha256(tmp_path):
    p = tmp_path / "f"
    p.write_bytes(b"abc")
    want = hashlib.sha256(b"abc").hexdigest()
    assert ec.sha256_bytes(b"abc") == ec.sha256_text("abc") == ec.sha256_file(p) == want


def test_is_synthetic():
    assert ec.is_synthetic(True, [])
    assert ec.is_synthetic(False, [{}, {"synthetic": True}])
    assert not ec.is_synthetic(False, [{}, {"synthetic": False}])


def test_new_run_dir_guard(tmp_path):
    out = ec.new_run_dir(tmp_path / "a" / "run")
    assert out.is_dir()
    with pytest.raises(SystemExit, match="refusing to overwrite existing run"):
        ec.new_run_dir(out)
    with pytest.raises(ValueError, match="refusing to overwrite existing run"):
        ec.require_absent(out, ValueError)


def test_run_prologue(tmp_path):
    metas = [{}, {"synthetic": True}]
    out, synthetic, b = ec.run_prologue(tmp_path / "r", False, metas)
    assert out.is_dir() and synthetic is True and b == ec.SYNTHETIC_BANNER
    out2, synthetic2, b2 = ec.run_prologue(tmp_path / "s", False, [])
    assert out2.is_dir() and synthetic2 is False and b2 == ec.MEASURED_BANNER
    with pytest.raises(SystemExit, match="refusing to overwrite existing run"):
        ec.run_prologue(out, False, [])


def test_dash():
    assert ec.dash(None) == "-"
    assert ec.dash(None, "%d") == "-"
    assert ec.dash(1.234) == "1.234"
    assert ec.dash(1.234, "%.2f") == "1.23"
    assert ec.dash(7, "%d") == "7"


def test_write_results_csv(tmp_path):
    p = tmp_path / "results.csv"
    rows = [{"a": 1.23456789, "b": "x", "c": 2},
            {"a": 0.000123456789, "b": None, "c": None}]
    ec.write_results_csv(p, rows, ["a", "b", "c"])
    assert p.read_bytes() == b"a,b,c\r\n1.23457,x,2\r\n0.000123457,,\r\n"


def test_write_results_csv_fmt_is_per_call_site(tmp_path):
    rows = [{"a": 1.23456789}]
    p4 = tmp_path / "g4.csv"
    ec.write_results_csv(p4, rows, ["a"], fmt=".4g")
    assert p4.read_bytes() == b"a\r\n1.235\r\n"   # the .4g sites' rendering
    p6 = tmp_path / "g6.csv"
    ec.write_results_csv(p6, rows, ["a"], fmt=".6g")
    assert p6.read_bytes() == b"a\r\n1.23457\r\n"  # the .6g sites' rendering


def test_write_results_csv_flat_and_extrasaction(tmp_path):
    p = tmp_path / "results.csv"
    ec.write_results_csv(p, [{"a": 1.0, "z": "dropped"}], ["a"], flat=lambda r: {"a": r["a"] / 4})
    assert p.read_bytes() == b"a\r\n0.25\r\n"
    with pytest.raises(ValueError, match="dict contains fields not in fieldnames"):
        ec.write_results_csv(tmp_path / "r2.csv", [{"a": 1.0, "z": 2}], ["a"])
    (tmp_path / "r3.csv").unlink(missing_ok=True)
    ec.write_results_csv(tmp_path / "r3.csv", [{"a": 1.0, "z": 2}], ["a"], extrasaction="ignore")
    assert (tmp_path / "r3.csv").read_bytes() == b"a\r\n1\r\n"


def test_run_header_order_and_optional_keys():
    doc = ec.run_header("L", True, params={"w": 1}, note="n", metas=[{"r": 1}])
    assert list(doc) == ["label", "synthetic", "utc", "params", "note", "reports"]
    assert doc["label"] == "L" and doc["synthetic"] is True
    assert doc["params"] == {"w": 1} and doc["note"] == "n" and doc["reports"] == [{"r": 1}]
    datetime.datetime.fromisoformat(doc["utc"])  # parseable stamp, now()
    # keys not passed are omitted, not emitted empty (loadsweep has no "note")
    assert list(ec.run_header("L", False)) == ["label", "synthetic", "utc"]
    assert list(ec.run_header("L", False, note="")) == ["label", "synthetic", "utc", "note"]

