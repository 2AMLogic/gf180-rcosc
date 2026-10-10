#!/usr/bin/env python3
"""Tests for signoff/verify-test-coverage.py (the orphaned-test guard).

Stdlib ``unittest`` only, so the CI job that runs the guard needs no pip
install. Fixtures are throwaway git repositories in temporary directories;
nothing under the real repository is written.

Run (CI: ``.github/workflows/doc-citations.yml``)::

    python3 -I signoff/test_verify_test_coverage.py

``pytest`` collects it too.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "verify_test_coverage", HERE / "verify-test-coverage.py"
)
vtc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vtc)

WORKFLOW = """\
name: demo
# sim/bench/test_commented.py is only mentioned in a comment
jobs:
  j:
    steps:
      - run: python3 -I -m pytest -p no:cacheprovider sim/bench/test_a.py  # sim/bench/test_trailing.py
      - run: |
          python3 -I -m pytest sim/bench/test_b.py
"""


class FixtureRepo:
    def __init__(self, files: dict[str, str]):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        for rel, text in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)

    def close(self):
        self._tmp.cleanup()


class OrphanGuardTest(unittest.TestCase):
    def make(self, extra: dict[str, str]) -> Path:
        files = {
            ".github/workflows/demo.yml": WORKFLOW,
            "sim/bench/test_a.py": "",
            "sim/bench/test_b.py": "",
        }
        files.update(extra)
        repo = FixtureRepo(files)
        self.addCleanup(repo.close)
        return repo.root

    def test_all_referenced_passes(self):
        root = self.make({})
        self.assertEqual(vtc.find_orphans(root), [])
        self.assertEqual(vtc.main(root), 0)

    def test_unreferenced_test_file_fails(self):
        root = self.make({"sim/bench/test_orphan.py": ""})
        self.assertEqual(vtc.find_orphans(root), ["sim/bench/test_orphan.py"])
        self.assertEqual(vtc.main(root), 1)

    def test_comment_mentions_do_not_count(self):
        root = self.make({
            "sim/bench/test_commented.py": "",
            "sim/bench/test_trailing.py": "",
        })
        self.assertEqual(
            vtc.find_orphans(root),
            ["sim/bench/test_commented.py", "sim/bench/test_trailing.py"],
        )

    def test_path_prefix_does_not_count(self):
        # sim/bench/test_a.py is referenced; x/sim/bench/test_a.py is not.
        root = self.make({"x/sim/bench/test_a.py": ""})
        self.assertEqual(vtc.find_orphans(root), ["x/sim/bench/test_a.py"])

    def test_untracked_test_file_ignored(self):
        root = self.make({})
        (root / "sim/bench/test_untracked.py").write_text("")
        self.assertEqual(vtc.find_orphans(root), [])

    def test_real_repository_has_no_orphans(self):
        self.assertEqual(vtc.find_orphans(vtc.REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
