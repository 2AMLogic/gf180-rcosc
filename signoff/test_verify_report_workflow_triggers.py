#!/usr/bin/env python3
"""Synthetic tests for the workflow-trigger checks in
signoff/verify-report.py's ``verify_workflow_concurrency`` (issue #429).

Stdlib ``unittest`` only; the seven required-check workflows are written
into a temp tree the module's ``REPO_ROOT`` is pointed at, so no klt, PDK,
network, or committed evidence is read or written.

Run (CI: ``.github/workflows/offline-suites.yml``)::

    python3 -I signoff/test_verify_report_workflow_triggers.py

Policy under test: each of the seven required-check workflows keeps the
pull_request and merge_group triggers (merge_group is what makes each
required context report on the merge queue's trial-merge commit); a
merge_group mention that is only a comment or lives outside the ``on:``
block does not count; sim-append-only's missing push trigger is not a
problem (only signoff.yml is push-checked).
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("verify_report", HERE / "verify-report.py")
vr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vr)


def workflow_yaml(
    triggers=("pull_request", "merge_group", "push"),
    *,
    concurrency=False,
    extra_on_lines=(),
    extra_top_level="",
):
    lines = ["name: ci", "on:"]
    for t in triggers:
        lines.append(f"  {t}:")
        if t == "push":
            lines.append("    branches: [main]")
    lines.extend(extra_on_lines)
    lines.append("")
    lines.append("permissions: {}")
    if concurrency:
        lines.extend(
            [
                "concurrency:",
                "  group: signoff-${{ github.ref }}",
                "  cancel-in-progress: false",
            ]
        )
    lines.extend(["jobs:", "  build:", "    steps:", "      - run: echo hi"])
    if extra_top_level:
        lines.append(extra_top_level)
    return "\n".join(lines) + "\n"


class WorkflowTriggerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._saved = vr.REPO_ROOT
        self.addCleanup(setattr, vr, "REPO_ROOT", self._saved)
        vr.REPO_ROOT = Path(self._tmp.name).resolve()

    def write(self, name, text):
        rel = f".github/workflows/{name}.yml"
        path = vr.REPO_ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return rel

    def write_all_like_main(self):
        """The seven workflows as they are on main: six with all three
        triggers, sim-append-only without push; signoff with concurrency."""
        for name in vr.REQUIRED_CHECK_WORKFLOWS:
            if name == "sim-append-only":
                self.write(name, workflow_yaml(triggers=("pull_request", "merge_group")))
            elif name == "signoff":
                self.write(name, workflow_yaml(concurrency=True))
            else:
                self.write(name, workflow_yaml())

    def problems(self):
        return vr.verify_workflow_concurrency()

    def test_main_shaped_tree_yields_no_problems(self):
        self.write_all_like_main()
        self.assertEqual(self.problems(), [])

    def test_removed_merge_group_reports_per_workflow(self):
        for name in vr.REQUIRED_CHECK_WORKFLOWS:
            with self.subTest(workflow=name):
                self.write_all_like_main()
                rel = self.write(
                    name,
                    workflow_yaml(
                        triggers=("pull_request", "push"),
                        concurrency=(name == "signoff"),
                    ),
                )
                problems = self.problems()
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(rel, problems[0])
                self.assertIn("merge_group", problems[0])

    def test_merge_group_only_in_comment_does_not_count(self):
        self.write_all_like_main()
        self.write(
            "signoff",
            workflow_yaml(
                triggers=("pull_request", "push"),
                concurrency=True,
                extra_on_lines=("  # merge_group: removed",),
            ),
        )
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("merge_group", problems[0])

    def test_merge_group_only_outside_on_block_does_not_count(self):
        self.write_all_like_main()
        self.write(
            "signoff",
            workflow_yaml(
                triggers=("pull_request", "push"),
                concurrency=True,
                extra_top_level=(
                    "jobs:\n"
                    "  build:\n"
                    "    if: github.event_name == 'merge_group'\n"
                    "    steps:\n"
                    "      - run: echo hi"
                ),
            ),
        )
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("merge_group", problems[0])

    def test_sim_append_only_without_push_is_not_a_problem(self):
        self.write_all_like_main()
        self.write(
            "sim-append-only",
            workflow_yaml(triggers=("pull_request", "merge_group")),
        )
        self.assertEqual(self.problems(), [])

    def test_missing_workflow_file_reports_problem(self):
        self.write_all_like_main()
        (vr.REPO_ROOT / ".github/workflows/offline-suites.yml").unlink()
        problems = self.problems()
        self.assertEqual(
            problems, [".github/workflows/offline-suites.yml is missing"]
        )

    def test_signoff_concurrency_checks_survive_the_refactor(self):
        self.write_all_like_main()
        self.write(
            "signoff",
            workflow_yaml(
                triggers=("pull_request", "merge_group"),
                concurrency=False,
            ),
        )
        text = self.problems()
        joined = "\n".join(text)
        self.assertIn("push-to-main", joined)
        self.assertIn("cancel-in-progress", joined)
        self.assertNotIn("merge_group", joined)


if __name__ == "__main__":
    unittest.main()
