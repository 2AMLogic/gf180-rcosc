"""Offline tests for sim/_module_loader.py (synthetic temp modules only)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _module_loader import load_module  # noqa: E402


def _write(tmp_path, name, body):
    p = tmp_path / f"{name}.py"
    p.write_text(body)
    return p


@pytest.fixture(autouse=True)
def _clean():
    before = set(sys.modules)
    yield
    for k in set(sys.modules) - before:
        if k.startswith("ml_test_"):
            del sys.modules[k]


def test_success_with_dataclass_registered_during_exec(tmp_path):
    p = _write(tmp_path, "a", (
        "import sys, dataclasses\n"
        "SEEN = __name__ in sys.modules\n"
        "@dataclasses.dataclass\n"
        "class P:\n    x: int = 3\n"
        "V = P().x\n"))
    m = load_module("ml_test_a", p, reuse=False)
    assert m.SEEN and m.V == 3
    assert sys.modules["ml_test_a"] is m


def test_distinct_names_distinct_modules(tmp_path):
    p = _write(tmp_path, "a", "V = 1\n")
    m1 = load_module("ml_test_n1", p, reuse=False)
    m2 = load_module("ml_test_n2", p, reuse=False)
    assert m1 is not m2 and m1.__name__ == "ml_test_n1" and m2.__name__ == "ml_test_n2"


def test_reuse_returns_cached(tmp_path):
    p = _write(tmp_path, "a", "V = 1\n")
    m1 = load_module("ml_test_r", p, reuse=True)
    assert load_module("ml_test_r", p, reuse=True) is m1


def test_fresh_replaces_cached(tmp_path):
    p = _write(tmp_path, "a", "V = 1\n")
    m1 = load_module("ml_test_f", p, reuse=False)
    m2 = load_module("ml_test_f", p, reuse=False)
    assert m1 is not m2 and sys.modules["ml_test_f"] is m2


def test_failure_without_prior_removes_partial(tmp_path):
    p = _write(tmp_path, "bad", "X = 1\nraise ValueError('boom')\n")
    with pytest.raises(ValueError, match="boom"):
        load_module("ml_test_bad", p, reuse=False)
    assert "ml_test_bad" not in sys.modules


def test_failure_with_prior_restores_it(tmp_path):
    good = _write(tmp_path, "good", "V = 1\n")
    prior = load_module("ml_test_bad2", good, reuse=False)
    bad = _write(tmp_path, "bad", "raise RuntimeError('nope')\n")
    with pytest.raises(RuntimeError, match="nope"):
        load_module("ml_test_bad2", bad, reuse=False)
    assert sys.modules["ml_test_bad2"] is prior


def test_missing_file_propagates_and_cleans(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_module("ml_test_missing", tmp_path / "nope.py", reuse=False)
    assert "ml_test_missing" not in sys.modules
