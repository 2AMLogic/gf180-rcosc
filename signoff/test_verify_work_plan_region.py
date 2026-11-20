#!/usr/bin/env python3
"""Tests for signoff/verify-work-plan-region.py (the plan-region guard).

Stdlib ``unittest`` only, so the CI job that runs the guard needs no pip
install. Fixtures are throwaway directories holding a ``WORK_PLAN.md``;
nothing under the real repository is written.

The two principal fixtures are built from the shapes of the two commits the
issue names: ``9f03c31d`` (PR #445, canonical renderer output — must pass)
and ``97c84f9c`` (PR #446, a ``_Generated:`` line plus six ``*(held)*``
suffixes inside the markers — must fail).

Run (CI: ``.github/workflows/doc-citations.yml``)::

    python3 -I signoff/test_verify_work_plan_region.py

``pytest`` collects it too.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "verify_work_plan_region", HERE / "verify-work-plan-region.py"
)
vwpr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vwpr)

# Shape of 9f03c31d (PR #445): what render_plan_body() actually emits — no
# _Generated line, suffixes only from the allowed set.
CLEAN_PLAN = """\
# Work Plan

This roadmap is generated from the current GitHub label state by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption

## Important

`loom:important`; taken before unlabelled work.

- **#70**: Item 7: produce a grader-readable klt pex report for the current rcosc_top layout
- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5
- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) and comparator-H hot/low-V delay collapse (ff)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns for DR-0019 statistical rows 2, 4 and 5 *(curated)*
- **#337**: Measure running Iq at per-die calibrated codes for w3r65 and w2.5r75 before row 4 adoption *(curated)*

## Epics

- **#5**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Very important | 1 |
| Important | 3 |
| Curated | 2 |
| Active epics | 1 |
<!-- guide:plan-body:end -->

(Region ends above; hand-maintained notes live below.)
"""

# Shape of 97c84f9c (PR #446): same plan plus a _Generated line directly
# inside the start marker and *(held)* suffixes — bare on the Important and
# Epics bullets, stacked after *(curated)* on the Proposed bullets.
ANNOTATED_PLAN = CLEAN_PLAN.replace(
    "<!-- guide:plan-body:start -->\n## Operator Attention",
    "<!-- guide:plan-body:start -->\n"
    "_Generated: 2026-11-20T06:21:08Z (snapshot; compare against live labels)_\n"
    "## Operator Attention",
).replace(
    "- **#70**: Item 7: produce a grader-readable klt pex report "
    "for the current rcosc_top layout\n",
    "- **#70**: Item 7: produce a grader-readable klt pex report "
    "for the current rcosc_top layout *(held)*\n",
).replace(
    "- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns "
    "for DR-0019 statistical rows 2, 4 and 5\n",
    "- **#202**: T1 item 6 (Monte Carlo): klt yield campaigns "
    "for DR-0019 statistical rows 2, 4 and 5 *(held)*\n",
).replace(
    "- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) "
    "and comparator-H hot/low-V delay collapse (ff)\n",
    "- **#317**: Rows 4/5: trim-bank switch supply dependence (ss) "
    "and comparator-H hot/low-V delay collapse (ff) *(held)*\n",
).replace(
    "rows 2, 4 and 5 *(curated)*\n",
    "rows 2, 4 and 5 *(curated)* *(held)*\n",
).replace(
    "w3r65 and w2.5r75 before row 4 adoption *(curated)*\n",
    "w3r65 and w2.5r75 before row 4 adoption *(curated)* *(held)*\n",
).replace(
    "- **#5**: Track the gap to T1 sim-validated / bronze "
    "(klayout-tools design-evidence tiers)\n",
    "- **#5**: Track the gap to T1 sim-validated / bronze "
    "(klayout-tools design-evidence tiers) *(held)*\n",
)

MINIMAL_PLAN = """\
# Work Plan

<!-- guide:plan-body:start -->
## Ready

- **#1**: A title *(curated)*
<!-- guide:plan-body:end -->
"""


class PlanDir:
    def __init__(self, plan_text: str | None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        if plan_text is not None:
            (self.root / "WORK_PLAN.md").write_text(plan_text, encoding="utf-8")

    def close(self):
        self._tmp.cleanup()


def line_of(text: str, needle: str) -> int:
    return text[: text.index(needle)].count("\n") + 1


class WorkPlanRegionGuardTest(unittest.TestCase):
    def make(self, plan_text: str | None) -> Path:
        d = PlanDir(plan_text)
        self.addCleanup(d.close)
        return d.root

    def test_clean_tree_shape_passes(self):
        # Blob shape of 9f03c31d (PR #445).
        root = self.make(CLEAN_PLAN)
        self.assertEqual(vwpr.find_findings(root), [])
        self.assertEqual(vwpr.main(root), 0)

    def test_annotated_tree_shape_fails(self):
        # Blob shape of 97c84f9c (PR #446): the _Generated line plus the six
        # *(held)* suffixes, exactly as that commit wrote them.
        root = self.make(ANNOTATED_PLAN)
        findings = vwpr.find_findings(root)
        self.assertEqual(vwpr.main(root), 1)
        gen_line = line_of(ANNOTATED_PLAN, "_Generated:")
        self.assertTrue(
            any(f.startswith(f"WORK_PLAN.md:{gen_line}:") and "_Generated:" in f
                for f in findings),
            findings,
        )
        held = [f for f in findings if "'*(held)*'" in f]
        self.assertEqual(len(held), 6, findings)
        expected_held_lines = [
            line_of(ANNOTATED_PLAN, needle) for needle in (
                "layout *(held)*",
                "rows 2, 4 and 5 *(held)*",
                "delay collapse (ff) *(held)*",
                "rows 2, 4 and 5 *(curated)* *(held)*",
                "row 4 adoption *(curated)* *(held)*",
                "design-evidence tiers) *(held)*",
            )
        ]
        for n in expected_held_lines:
            self.assertTrue(
                any(f.startswith(f"WORK_PLAN.md:{n}:") for f in held),
                f"no *(held)* finding on line {n}: {held}",
            )
        # A stacked line is reported once (per suffix), not twice.
        stacked = f"WORK_PLAN.md:{line_of(ANNOTATED_PLAN, '*(curated)* *(held)*')}:"
        self.assertEqual(
            sum(1 for f in findings if f.startswith(stacked)), 1, findings
        )

    def test_generated_line_flagged_with_line_number(self):
        plan = MINIMAL_PLAN.replace(
            "## Ready\n", "_Generated: 2026-11-20T06:21:08Z (snapshot)_\n## Ready\n"
        )
        root = self.make(plan)
        findings = vwpr.find_findings(root)
        self.assertEqual(len(findings), 1, findings)
        self.assertTrue(findings[0].startswith("WORK_PLAN.md:4:"), findings)

    def test_allowed_suffixes_pass(self):
        body = "".join(
            f"- **#1**: A title *({tag})*\n" for tag in ("curated", "architect", "hermit")
        )
        plan = MINIMAL_PLAN.replace("- **#1**: A title *(curated)*\n", body)
        root = self.make(plan)
        self.assertEqual(vwpr.find_findings(root), [])

    def test_disallowed_suffixes_fail(self):
        for tag in ("held", "blocked", "wip", ""):
            with self.subTest(tag=tag):
                plan = MINIMAL_PLAN.replace(
                    "*(curated)*", f"*({tag})*" if tag else "*()*"
                )
                root = self.make(plan)
                findings = vwpr.find_findings(root)
                self.assertEqual(len(findings), 1, findings)
                self.assertIn(f"'*({tag})*'", findings[0])

    def test_stacked_suffix_caught_per_suffix(self):
        plan = MINIMAL_PLAN.replace(
            "*(curated)*", "*(curated)* *(held)*"
        )
        root = self.make(plan)
        findings = vwpr.find_findings(root)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("'*(held)*'", findings[0])

    def test_missing_markers_fail(self):
        for which, plan in (
            ("both", "# Work Plan\n\nNothing generated here.\n"),
            ("start", MINIMAL_PLAN.replace("<!-- guide:plan-body:start -->\n", "")),
            ("end", MINIMAL_PLAN.replace("<!-- guide:plan-body:end -->\n", "")),
        ):
            with self.subTest(which=which):
                root = self.make(plan)
                findings = vwpr.find_findings(root)
                self.assertEqual(vwpr.main(root), 1)
                self.assertTrue(
                    any("missing <!-- guide:plan-body:" in f for f in findings),
                    findings,
                )

    def test_duplicated_marker_fails(self):
        marker_line = "<!-- guide:plan-body:start -->\n"
        plan = MINIMAL_PLAN + MINIMAL_PLAN[MINIMAL_PLAN.index(marker_line):]
        root = self.make(plan)
        findings = vwpr.find_findings(root)
        self.assertEqual(vwpr.main(root), 1)
        self.assertTrue(
            any("duplicate <!-- guide:plan-body:start -->" in f for f in findings),
            findings,
        )

    def test_out_of_order_markers_fail(self):
        plan = (
            "# Work Plan\n\n"
            "<!-- guide:plan-body:end -->\n"
            "- **#1**: A title *(curated)*\n"
            "<!-- guide:plan-body:start -->\n"
        )
        root = self.make(plan)
        findings = vwpr.find_findings(root)
        self.assertEqual(vwpr.main(root), 1)
        self.assertTrue(
            any("out of order" in f for f in findings), findings
        )

    def test_annotations_outside_region_ignored(self):
        plan = MINIMAL_PLAN.replace(
            "<!-- guide:plan-body:end -->\n",
            "<!-- guide:plan-body:end -->\n\n"
            "_Generated: 2099-01-01T00:00:00Z (notes area)_\n"
            "- A hand note kept deliberately *(held)*\n",
        )
        root = self.make(plan)
        self.assertEqual(vwpr.find_findings(root), [])

    def test_empty_region_passes(self):
        plan = (
            "# Work Plan\n\n"
            "<!-- guide:plan-body:start --><!-- guide:plan-body:end -->\n"
        )
        root = self.make(plan)
        self.assertEqual(vwpr.find_findings(root), [])

    def test_missing_file_fails(self):
        root = self.make(None)
        findings = vwpr.find_findings(root)
        self.assertEqual(vwpr.main(root), 1)
        self.assertTrue(any("file not found" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
