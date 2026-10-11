#!/usr/bin/env python3
"""Synthetic tests for ``grade_drift`` in signoff/verify-report.py (issue #163).

Stdlib ``unittest`` only; inputs are in-memory dicts. No klt, PDK, network, or
committed evidence is read or written.

Run (CI: ``.github/workflows/offline-suites.yml``)::

    python3 -I signoff/test_verify_report_drift.py

Policy under test: item row order is ignored; repeated ``(tier, id)`` keys are
rejected in both the fresh and the committed report.
"""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("verify_report", HERE / "verify-report.py")
vr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vr)


def item(id_, status="met", reason="ok", tier="T1"):
    return {"tier": tier, "id": id_, "title": f"item {id_}", "status": status, "reason": reason}


def report(items, commit="abc123"):
    return {"build": {"git_commit": commit}, "items": items}


def base():
    return report([item(1), item(2), item(3, status="unmet", reason="no evidence")])


class GradeDriftTests(unittest.TestCase):
    def drift(self, fresh, committed):
        return vr.grade_drift(fresh, committed)

    def test_unchanged_unique_report_has_no_drift(self):
        self.assertEqual(self.drift(base(), base()), [])

    def test_extra_identical_row_in_fresh_rejected(self):
        fresh = base()
        fresh["items"].append(copy.deepcopy(fresh["items"][0]))
        problems = self.drift(fresh, base())
        self.assertEqual(len(problems), 1)
        self.assertIn("fresh grade", problems[0])
        self.assertIn("duplicate item key", problems[0])
        self.assertIn("'T1', 1", problems[0])

    def test_extra_identical_row_in_committed_rejected(self):
        committed = base()
        committed["items"].append(copy.deepcopy(committed["items"][1]))
        problems = self.drift(base(), committed)
        self.assertEqual(len(problems), 1)
        self.assertIn("committed report", problems[0])
        self.assertIn("duplicate item key", problems[0])

    def test_conflicting_duplicate_rejected_whichever_row_is_last(self):
        for order in ((item(2), item(2, status="unmet")), (item(2, status="unmet"), item(2))):
            for side in ("fresh", "committed"):
                a, b = base(), base()
                target = a if side == "fresh" else b
                target["items"] = [item(1), *order, item(3, status="unmet", reason="no evidence")]
                problems = self.drift(a, b)
                label = "fresh grade" if side == "fresh" else "committed report"
                self.assertTrue(
                    any(label in p and "duplicate item key" in p for p in problems),
                    (side, order, problems),
                )

    def test_missing_item_detected(self):
        fresh = base()
        del fresh["items"][1]
        problems = self.drift(fresh, base())
        self.assertEqual(len(problems), 1)
        self.assertIn("drifted", problems[0])

    def test_extra_unique_item_detected(self):
        fresh = base()
        fresh["items"].append(item(4))
        problems = self.drift(fresh, base())
        self.assertEqual(len(problems), 1)
        self.assertIn("('T1', 4)", problems[0])

    def test_changed_status_and_reason_detected(self):
        fresh = base()
        fresh["items"][0]["status"] = "unmet"
        self.assertEqual(len(self.drift(fresh, base())), 1)
        fresh = base()
        fresh["items"][2]["reason"] = "different"
        self.assertEqual(len(self.drift(fresh, base())), 1)

    def test_changed_grader_build_detected(self):
        fresh = base()
        fresh["build"]["git_commit"] = "def456"
        problems = self.drift(fresh, base())
        self.assertEqual(len(problems), 1)
        self.assertIn("grading build drifted", problems[0])

    def test_reordering_unique_rows_is_not_drift(self):
        fresh = base()
        fresh["items"].reverse()
        self.assertEqual(self.drift(fresh, base()), [])


if __name__ == "__main__":
    unittest.main()
