#!/usr/bin/env python3
"""Fail when a tracked ``test_*.py`` is not run by any CI workflow.

PDK-free and stdlib-only. Every ``git ls-files`` path whose basename matches
``test_*.py`` (outside ``.loom/`` and ``.claude/``) must appear, as its full
repo-relative path, in the non-comment text of some
``.github/workflows/*.yml`` / ``*.yaml`` file. YAML comments (whole-line and
trailing `` #``) are stripped first, so a mention in a header comment does not
count as running the test. A path match must be bounded: ``x/sim/a/test_b.py``
is not satisfied by a reference to ``sim/a/test_b.py``, and vice versa.

This is a reference check, not proof the step passes; it exists so a new test
file cannot land without being wired into CI (issue #134).

Run from anywhere in the repository (CI: ``.github/workflows/doc-citations.yml``)::

    python3 signoff/verify-test-coverage.py

Exit 0 = every tracked test file is referenced; exit 1 = orphans, listed one
per line.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_PREFIXES = (".loom/", ".claude/", ".git/")
TEST_NAME_RE = re.compile(r"^test_[^/]*\.py$")
# A YAML comment starts at '#' at line start or after whitespace. Workflow
# run lines in this repo do not put '#' inside quoted strings; if one ever
# does, the effect is a false orphan (fail closed), never a false pass.
COMMENT_RE = re.compile(r"(^|\s)#.*$")
PATH_CHARS = r"A-Za-z0-9_./-"


def _git_ls_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def tracked_tests(root: Path) -> list[str]:
    return sorted(
        p for p in _git_ls_files(root)
        if not p.startswith(EXCLUDED_PREFIXES)
        and TEST_NAME_RE.match(PurePosixPath(p).name)
    )


def workflow_text(root: Path) -> str:
    wf_dir = root / ".github" / "workflows"
    chunks = []
    for wf in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        for line in wf.read_text(encoding="utf-8").splitlines():
            chunks.append(COMMENT_RE.sub("", line))
    return "\n".join(chunks)


def find_orphans(root: Path) -> list[str]:
    text = workflow_text(root)
    orphans = []
    for path in tracked_tests(root):
        pat = rf"(?<![{PATH_CHARS}])(?:\./)?{re.escape(path)}(?![{PATH_CHARS}])"
        if not re.search(pat, text):
            orphans.append(path)
    return orphans


def main(root: Path = REPO_ROOT) -> int:
    orphans = find_orphans(root)
    if orphans:
        print("Tracked test files not referenced by any .github/workflows/*.yml "
              "(outside comments):")
        for p in orphans:
            print(f"  {p}")
        print("Add each to a workflow's pytest invocation (see issue #134).")
        return 1
    print(f"OK: all {len(tracked_tests(root))} tracked test_*.py files are run by a workflow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
