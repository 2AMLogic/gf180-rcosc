#!/usr/bin/env python3
"""Tests for signoff/verify-decision-record-index.py (the index guard).

Stdlib ``unittest`` only, so the CI job that runs the guard needs no pip
install. Fixtures are throwaway directories holding a ``spec/README.md``
and a ``spec/decision-records/`` tree; nothing under the real repository
is written.

The principal fixture mirrors the drift issue #469 measured on ``main`` at
``e50243db`` (47 records, 28 index rows): a small records tree with a
complete index passes, and each documented failure mode — a record lacking
its row while a prose link survives, a duplicated row, a row pointing at
the wrong file, two record files sharing a number, rows out of numeric
order — fails naming the offending ID or path.

Run (CI: ``.github/workflows/doc-citations.yml``)::

    python3 -I signoff/test_verify_decision_record_index.py

``pytest`` collects it too.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "verify_decision_record_index", HERE / "verify-decision-record-index.py"
)
vdri = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vdri)

README_HEAD = """\
# spec

Prose. See [`decision-records/TEMPLATE.md`](decision-records/TEMPLATE.md)
and a prose link to [0002](decision-records/0002-b-second.md) that is not a
table row and must not satisfy the index.

## Decision records

| Record | Title | Status |
|---|---|
"""


def _write_repo(records: dict[str, str], rows: list[str]) -> Path:
    """Build a throwaway repo: records map filename -> H1, rows are table lines."""
    root = Path(tempfile.mkdtemp(prefix="drix-test-"))
    (root / "spec" / "decision-records").mkdir(parents=True)
    (root / "spec" / "decision-records" / "TEMPLATE.md").write_text(
        "# Template\n\n- **Status**: proposed\n", encoding="utf-8"
    )
    for name, title in records.items():
        (root / "spec" / "decision-records" / name).write_text(
            f"# {title}\n\n- **Status**: proposed\n", encoding="utf-8"
        )
    (root / "spec" / "README.md").write_text(
        README_HEAD + "\n".join(rows) + "\n", encoding="utf-8"
    )
    return root


# A complete, ordered index over three records (0001, 0002, 0003) plus the
# unnumbered TEMPLATE.md — the shape main will have after the backfill.
COMPLETE_RECORDS = {
    "0001-a-first.md": "0001: first",
    "0002-b-second.md": "0002: second",
    "0003-c-third.md": "0003: third",
}
COMPLETE_ROWS = [
    "| [0001](decision-records/0001-a-first.md) | first | Proposed |",
    "| [0002](decision-records/0002-b-second.md) | second | Proposed |",
    "| [0003](decision-records/0003-c-third.md) | third | Proposed |",
]


class CompleteIndex(unittest.TestCase):
    def test_complete_table_with_template_passes(self) -> None:
        root = _write_repo(COMPLETE_RECORDS, COMPLETE_ROWS)
        self.assertEqual(vdri.find_findings(root), [])


class MissingRow(unittest.TestCase):
    def test_record_without_row_fails_even_with_prose_link(self) -> None:
        rows = [COMPLETE_ROWS[0], COMPLETE_ROWS[2]]  # 0002's row removed
        root = _write_repo(COMPLETE_RECORDS, rows)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("spec/decision-records/0002-b-second.md", findings[0])
        self.assertIn("no index row", findings[0])


class DuplicateRow(unittest.TestCase):
    def test_duplicated_row_fails_naming_id_and_lines(self) -> None:
        rows = COMPLETE_ROWS[:2] + [COMPLETE_ROWS[1], COMPLETE_ROWS[2]]
        root = _write_repo(COMPLETE_RECORDS, rows)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("duplicate index row for 0002", findings[0])


class WrongTarget(unittest.TestCase):
    def test_row_pointing_at_wrong_file_fails(self) -> None:
        rows = [
            COMPLETE_ROWS[0],
            "| [0002](decision-records/0002-wrong-name.md) | second | Proposed |",
            COMPLETE_ROWS[2],
        ]
        root = _write_repo(COMPLETE_RECORDS, rows)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("0002", findings[0])
        self.assertIn("expected decision-records/0002-b-second.md", findings[0])

    def test_row_pointing_at_nonexistent_number_fails(self) -> None:
        rows = COMPLETE_ROWS + [
            "| [0009](decision-records/0009-x-missing.md) | ghost | Proposed |",
        ]
        root = _write_repo(COMPLETE_RECORDS, rows)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("no spec/decision-records/0009-*.md exists", findings[0])


class NumberCollision(unittest.TestCase):
    def test_two_files_sharing_a_number_fail(self) -> None:
        records = dict(COMPLETE_RECORDS)
        records["0003-d-also-third.md"] = "0003: the other third"
        root = _write_repo(records, COMPLETE_ROWS)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("share number 0003", findings[0])
        self.assertIn("0003-c-third.md", findings[0])
        self.assertIn("0003-d-also-third.md", findings[0])


class NumericOrder(unittest.TestCase):
    def test_out_of_order_rows_fail(self) -> None:
        rows = [COMPLETE_ROWS[1], COMPLETE_ROWS[0], COMPLETE_ROWS[2]]
        root = _write_repo(COMPLETE_RECORDS, rows)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("out of numeric order at 0001 (after 0002)", findings[0])


class MissingInputs(unittest.TestCase):
    def test_missing_readme_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="drix-test-"))
        (root / "spec" / "decision-records").mkdir(parents=True)
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("spec/README.md", findings[0])
        self.assertIn("file not found", findings[0])

    def test_missing_records_dir_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="drix-test-"))
        (root / "spec").mkdir(parents=True)
        (root / "spec" / "README.md").write_text(
            README_HEAD + COMPLETE_ROWS[0] + "\n", encoding="utf-8"
        )
        findings = vdri.find_findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("spec/decision-records", findings[0])
        self.assertIn("directory not found", findings[0])


if __name__ == "__main__":
    unittest.main()
