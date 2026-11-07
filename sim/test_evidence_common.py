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
