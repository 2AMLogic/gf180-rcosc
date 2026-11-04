"""Offline tests for sim/git_provenance.py (throwaway repos in tmp_path)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_provenance as gp  # noqa: E402


def _repo(tmp_path):
    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    g("init", "-q")
    (tmp_path / "f").write_text("x")
    g("add", "f")
    g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c")
    return tmp_path


def test_head_and_clean(tmp_path):
    r = _repo(tmp_path)
    assert len(gp.head_sha(r)) == 40
    assert gp.is_dirty(r) is False


def test_dirty_and_path_scope(tmp_path):
    r = _repo(tmp_path)
    (r / "g").write_text("y")
    assert gp.is_dirty(r) is True
    assert gp.is_dirty(r, "f") is False


def test_not_a_repo_is_unknown_and_dirty(tmp_path):
    assert gp.head_sha(tmp_path) == gp.UNKNOWN
    assert gp.is_dirty(tmp_path) is True


def test_missing_git_and_timeout(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(subprocess, "run", boom)
    assert gp.head_sha(tmp_path) == gp.UNKNOWN
    assert gp.is_dirty(tmp_path) is True

    def slow(*a, **k):
        raise subprocess.TimeoutExpired("git", 1)
    monkeypatch.setattr(subprocess, "run", slow)
    assert gp.head_sha(tmp_path) == gp.UNKNOWN


def test_non_sha_output_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "HEAD\n", ""))
    assert gp.head_sha(tmp_path) == gp.UNKNOWN
