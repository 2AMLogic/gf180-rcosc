"""Shared git-revision provenance for the simulation campaign manifests (#216).

Standard library only, read-only (spawns ``git rev-parse`` / ``git status``).
One implementation for every sim driver that records the repository revision
in an evidence manifest (``git_sha`` / ``git_head`` / ``git_revision`` and the
dirty-tree flag).

Single failure convention (never an empty string, never ``None``):

``head_sha()``  returns the 40-hex HEAD commit, or exactly ``UNKNOWN``
                (``"unknown"``) when git is missing, times out, exits nonzero
                or prints something that is not a 40-hex sha.
``is_dirty()``  returns ``True`` when the tree has uncommitted changes *or*
                the state could not be determined: a tree that cannot be
                proven clean is never recorded as clean.

Git is invoked as ``git <args>`` with ``cwd=repo`` (not ``git -C``) so offline
test guards that inspect ``cmd[1]`` keep working.
"""
from __future__ import annotations

import re
import subprocess

UNKNOWN = "unknown"
TIMEOUT_S = 60
_HEX40 = re.compile(r"[0-9a-f]{40}")


def _git(repo, *args):
    """Return stdout of ``git *args`` in ``repo``, or ``None`` on any failure."""
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           cwd=str(repo), timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def head_sha(repo) -> str:
    """40-hex HEAD of ``repo``, or ``UNKNOWN`` if it cannot be determined."""
    out = _git(repo, "rev-parse", "HEAD")
    sha = (out or "").strip()
    return sha if _HEX40.fullmatch(sha) else UNKNOWN


def is_dirty(repo, *paths) -> bool:
    """True if ``repo`` (optionally limited to ``paths``) has uncommitted
    changes, or if that cannot be determined."""
    args = ["status", "--porcelain"]
    if paths:
        args += ["--", *map(str, paths)]
    out = _git(repo, *args)
    return True if out is None else bool(out.strip())
