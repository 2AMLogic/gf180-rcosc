#!/usr/bin/env python3
"""Fail when the spec/README.md decision-record index drifts from spec/decision-records/.

The index table under ``## Decision records`` is where a *partial*
supersession is annotated — the superseded record's own Status field is
append-only and stays untouched — so a record missing from the table is
missing from the story the index tells: a reader checking whether a ratified
row still stands gets a stale answer. The same table is where a number
collision shows up before it lands (the README carries the ``0015 -> 0016``
renumber note; PRs #465/#468 both proposed a DR-0049).

This guard fails on (issue #469):

- a numbered ``spec/decision-records/NNNN-*.md`` with no matching table row;
- a table row whose ID is duplicated, or whose link points to a nonexistent
  file, to a file of a different number, or to the wrong filename for its
  number;
- two record files sharing an ``NNNN`` (the collision shape above: either
  PR can renumber before landing, but both cannot keep it);
- index rows out of numeric order.

``TEMPLATE.md`` and other non-``NNNN-*.md`` files are not numbered records,
and links in prose are not table rows (only lines opening with
``| [NNNN](...)`` are); neither is checked. Title and Status cells are free
text — checking their wording would re-adjudicate records, which the issue
puts out of scope.

PDK-free and stdlib-only. Run from anywhere in the repository (CI:
``.github/workflows/doc-citations.yml``)::

    python3 -I signoff/verify-decision-record-index.py

Exit 0 = index and directory agree; exit 1 = findings, one per line, each
naming the offending ID or path.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = Path("spec/README.md")
RECORDS_DIR = Path("spec/decision-records")
RECORD_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")
# An index-table row: the line opens the table cell with the four-digit ID
# linked to its record file. Prose links never sit at a line start after
# ``| ``, so they cannot match.
ROW_RE = re.compile(r"^\|\s*\[(\d{4})\]\(([^)\s]+)\)")


def _records_by_number(records_dir: Path) -> dict[str, list[str]]:
    """Map each NNNN to the record filenames carrying it (TEMPLATE.md etc. excluded)."""
    by_number: dict[str, list[str]] = {}
    for path in sorted(records_dir.glob("*.md")):
        match = RECORD_FILE_RE.match(path.name)
        if match:
            by_number.setdefault(match.group(1), []).append(path.name)
    return by_number


def _index_rows(readme: Path) -> list[tuple[int, str, str]]:
    """Collect (line number, NNNN, link target) for every index-table row."""
    rows: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(
        readme.read_text(encoding="utf-8").splitlines(), 1
    ):
        match = ROW_RE.match(line)
        if match:
            rows.append((lineno, match.group(1), match.group(2)))
    return rows


def find_findings(root: Path) -> list[str]:
    readme = root / README
    if not readme.is_file():
        return [f"{README}: file not found; the decision-record index "
                "cannot be checked"]
    records_dir = root / RECORDS_DIR
    if not records_dir.is_dir():
        return [f"{RECORDS_DIR}: directory not found; the decision-record "
                "index cannot be checked"]

    findings: list[str] = []
    by_number = _records_by_number(records_dir)
    rows = _index_rows(readme)

    # Two record files sharing an NNNN: the pre-landing collision the old
    # doc-citations check could not see (every *cited* path existed).
    for number, names in sorted(by_number.items()):
        if len(names) > 1:
            findings.append(
                f"{RECORDS_DIR}: {len(names)} record files share number "
                f"{number}: "
                + ", ".join(f"{RECORDS_DIR}/{name}" for name in names)
            )

    # Duplicate rows, and rows whose link does not name the record file
    # carrying their ID.
    row_lines: dict[str, int] = {}
    for lineno, number, target in rows:
        if number in row_lines:
            findings.append(
                f"{README}:{lineno}: duplicate index row for {number} "
                f"(first at line {row_lines[number]})"
            )
            continue
        row_lines[number] = lineno
        names = by_number.get(number)
        if not names:
            findings.append(
                f"{README}:{lineno}: index row {number} links to {target}, "
                f"but no {RECORDS_DIR}/{number}-*.md exists"
            )
        elif len(names) == 1 and target != f"decision-records/{names[0]}":
            findings.append(
                f"{README}:{lineno}: index row {number} links to {target}, "
                f"expected decision-records/{names[0]}"
            )

    # Every numbered record must have its row.
    for number, names in sorted(by_number.items()):
        if number not in row_lines:
            findings.append(
                f"{README}: record {RECORDS_DIR}/{names[0]} has no index row"
            )

    # Numeric order: strictly increasing, ignoring the duplicates already
    # reported above.
    order = [number for _, number, _ in rows]
    for earlier, later in zip(order, order[1:]):
        if later < earlier:
            findings.append(
                f"{README}: index rows out of numeric order at {later} "
                f"(after {earlier})"
            )

    return findings


def main() -> int:
    findings = find_findings(REPO_ROOT)
    for finding in findings:
        print(finding)
    if findings:
        print(
            f"{README}: decision-record index and {RECORDS_DIR}/ disagree "
            f"({len(findings)} finding{'s' if len(findings) != 1 else ''})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
