#!/usr/bin/env python3
"""Verify that no tracked prose restates a klayout-tools/klayout pin value.

PDK-free and stdlib-only (no klt, ngspice, xschem): it reads the pin
declarations and scans tracked prose, the same shape as
``signoff/verify-doc-citations.py``. The repo declares its klt/klayout
runtimes in exactly four sites; prose that repeats a declared value has
drifted on every pin bump (issues #363 and #408), so this guard fails on
any version mention in klt context that the sidecar
``signoff/pin-restatements.json`` does not exempt.

The declarations are read at run time, never hardcoded:

-   geometry (the ``klt`` CLI + the Python runtime that runs
    ``build_cells.py``): ``KLT_VERSION_EXPECTED`` /
    ``KLAYOUT_VERSION_EXPECTED`` in ``layout/run_checks.sh``
-   ERC build: the inline ``"klayout-tools==<ver>"`` pin of the
    ``ERC_KLT`` line in ``layout/run_checks.sh``
-   grader: the ``pip install "klayout-tools==<ver>"`` line in
    ``.github/workflows/signoff.yml`` (that file is otherwise not scanned;
    its header comment is issue #358's, deliberately out of scope here)
-   netlist: ``KLT_NETLIST_VERSION_EXPECTED`` in
    ``design/regen-netlist.sh``

Scanned prose is every tracked ``*.md`` outside the Loom trees
(``.loom/``, ``.claude/``, ``.agents/``) and the append-only ``sim/``
evidence trees, plus the comments of the two pin-owning shell scripts
(their code lines, including the declarations themselves, are not prose).

A **version mention** is an ``X.Y.Z`` token with strict token boundaries
(so ``0.9.20`` is not a ``0.9.2`` mention, and ``v0.8.0`` is no mention at
all) in **klt context**: some line from the start of the enclosing
paragraph up through the token's own line mentions ``klt`` or
``klayout-tools`` (case-insensitive). Historical forms are not mentions:
``0.4.0-era`` / ``the 0.4.0 era``, ``0.5.0's``, ``post-0.4.0`` /
``pre-0.4.0``, and dev-build ids like ``0.5.0+g2b1e55e51bb8`` name a range
or a record, never the live pin (the same spirit as the citations guard's
``superseded``/``historical`` markers).

Every mention must be covered by a sidecar exemption (``file``,
``prefix``, ``marker`` or ``region``, each with a reason); otherwise it is
a finding. A mention whose value no declaration pins is reported as a
stale restatement. The sidecar is checked against the tree so it cannot
rot: an entry whose file, marker, heading or region no longer exists
fails.

Run from anywhere in the repository (CI:
``.github/workflows/doc-citations.yml``)::

    python3 -I signoff/verify-pin-restatements.py

Exit 0 = clean; exit 1 = findings, printed as ``file:line: message``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDECAR = REPO_ROOT / "signoff" / "pin-restatements.json"

# (pin name, declaring path, extraction regex). If a site moves or changes
# shape, the guard fails until it is repointed -- it never guesses.
DECL_SITES = (
    ("geometry-klt", "layout/run_checks.sh",
     re.compile(r'^KLT_VERSION_EXPECTED="([^"]+)"', re.M)),
    ("geometry-klayout", "layout/run_checks.sh",
     re.compile(r'^KLAYOUT_VERSION_EXPECTED="([^"]+)"', re.M)),
    ("erc", "layout/run_checks.sh",
     re.compile(r'^ERC_KLT=\([^\n]*"klayout-tools==([^"]+)"', re.M)),
    ("grader", ".github/workflows/signoff.yml",
     re.compile(r'pip install[^\n]*"klayout-tools==([^"]+)"')),
    ("netlist", "design/regen-netlist.sh",
     re.compile(r'^KLT_NETLIST_VERSION_EXPECTED="([^"]+)"', re.M)),
)

# The two scripts whose comments are scanned besides tracked *.md.
COMMENT_SHELLS = ("layout/run_checks.sh", "design/regen-netlist.sh")

EXCLUDED_PREFIXES = (".loom/", ".claude/", ".agents/", ".git/")
EVIDENCE_RE = re.compile(r"^sim/[^/]+/(results|corners|batch-attempts)/")

VERSION_RE = re.compile(r"(?<![\w.])(\d+\.\d+\.\d+)(?!\w|\.\d)")
KLT_RE = re.compile(r"klt|klayout[-_]tools", re.I)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")


def _historical_form(text: str, start: int, end: int) -> bool:
    """Era names, genitives, post/pre comparisons, dev-build ids."""
    if text[end:end + 2] in ("'s", "+g"):
        return True
    if text[end:end + 4] in (" era", "-era"):
        return True
    return text[max(0, start - 5):start].endswith(("post-", "pre-"))


def read_declarations(root: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """pin name -> (value, declaring path); plus findings for broken sites."""
    decls: dict[str, tuple[str, str]] = {}
    findings: list[str] = []
    for name, rel, rx in DECL_SITES:
        p = root / rel
        if not p.is_file():
            findings.append(f"signoff/verify-pin-restatements.py: {rel}: declaration site of the {name} pin is missing")
            continue
        m = rx.search(p.read_text(encoding="utf-8"))
        if not m:
            findings.append(f"signoff/verify-pin-restatements.py: {rel}: cannot read the {name} pin (declaration pattern moved?)")
            continue
        decls[name] = (m.group(1), rel)
    return decls, findings


def tracked_prose(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.split()
    keep = [p for p in out
            if not p.startswith(EXCLUDED_PREFIXES) and not EVIDENCE_RE.match(p)]
    for rel in COMMENT_SHELLS:
        if rel not in keep:
            keep.append(rel)
    return sorted(keep)


def shell_comment_lines(text: str) -> list[tuple[int, str]]:
    return [(i, line.lstrip()[1:])
            for i, line in enumerate(text.splitlines(), 1)
            if line.lstrip().startswith("#")]


class CarveOut:
    """Exemptions from signoff/pin-restatements.json, rot-checked."""

    def __init__(self, root: Path, scanned: list[str], findings: list[str]):
        self.files: set[str] = set()
        self.prefixes: list[str] = []
        self.markers: dict[str, list[str]] = {}
        self.regions: dict[str, list[tuple[int, int]]] = {}
        side_path = root / "signoff" / "pin-restatements.json"
        if not side_path.is_file():
            findings.append("signoff/pin-restatements.json: sidecar is missing")
            return
        try:
            side = json.loads(side_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            findings.append(f"signoff/pin-restatements.json: cannot parse sidecar: {exc}")
            return
        scanned_set = set(scanned)
        for ent in side.get("exemptions", []):
            if not isinstance(ent, dict):
                findings.append("signoff/pin-restatements.json: exemption is not an object")
                continue
            kind = ent.get("kind")
            path = ent.get("path", "")
            reason = ent.get("reason", "")
            if not reason:
                findings.append(f"signoff/pin-restatements.json: {kind} exemption for {path}: no reason given")
            if kind == "file":
                if path in scanned_set:
                    self.files.add(path)
                else:
                    findings.append(f"signoff/pin-restatements.json: file exemption {path}: not a scanned file")
            elif kind == "prefix":
                if any(s.startswith(path) for s in scanned_set):
                    self.prefixes.append(path)
                else:
                    findings.append(f"signoff/pin-restatements.json: prefix exemption {path}: no scanned file under it")
            elif kind == "marker":
                marker = ent.get("marker", "")
                text = self._raw(root, path)
                if text is not None and marker in text:
                    self.markers.setdefault(path, []).append(marker)
                else:
                    findings.append(f"signoff/pin-restatements.json: marker exemption {path}: marker {marker!r} not found (stale entry?)")
            elif kind == "region":
                start, end = ent.get("start", ""), ent.get("end", "")
                span = self._region(root, path, start, end)
                if span:
                    self.regions.setdefault(path, []).append(span)
                else:
                    findings.append(f"signoff/pin-restatements.json: region exemption {path}: start {start!r} / end {end!r} not found in order (stale entry?)")
            else:
                findings.append(f"signoff/pin-restatements.json: unknown exemption kind {kind!r} for {path}")

    @staticmethod
    def _raw(root: Path, rel: str) -> str | None:
        p = root / rel
        return p.read_text(encoding="utf-8") if p.is_file() else None

    @classmethod
    def _region(cls, root: Path, rel: str, start: str, end: str) -> tuple[int, int] | None:
        text = cls._raw(root, rel)
        if text is None:
            return None
        a = b = -1
        for i, line in enumerate(text.splitlines(), 1):
            if a < 0 and start in line:
                a = i
            if a > 0 and end in line and i >= a:
                b = i
                break
        return (a, b) if a > 0 and b > 0 else None

    def covers(self, rel: str, lineno: int, line_text: str) -> bool:
        if rel in self.files:
            return True
        if any(rel.startswith(p) for p in self.prefixes):
            return True
        if any(m in line_text for m in self.markers.get(rel, ())):
            return True
        return any(a <= lineno <= b for a, b in self.regions.get(rel, ()))


def scan(root: Path) -> tuple[list[str], int, int]:
    """Returns (findings, mentions checked, prose files scanned)."""
    decls, findings = read_declarations(root)
    by_value: dict[str, tuple[str, str]] = {}
    for name, (value, rel) in decls.items():
        label, sites = by_value.setdefault(value, ([], []))
        label.append(name)
        if rel not in sites:
            sites.append(rel)
    by_value = {v: ("/".join(n), " and ".join(r)) for v, (n, r) in by_value.items()}
    prose = tracked_prose(root)
    carve = CarveOut(root, prose, findings)
    hits = 0
    for rel in prose:
        p = root / rel
        if not p.is_file():
            continue
        raw = p.read_text(encoding="utf-8")
        is_md = rel.endswith(".md")
        entries = ([(i, line) for i, line in enumerate(raw.splitlines(), 1)]
                   if is_md else shell_comment_lines(raw))
        para_klt = False
        for i, line in entries:
            if is_md and (not line.strip() or HEADING_RE.match(line)):
                para_klt = False
            elif not is_md and not line.strip():
                para_klt = False
            in_ctx = para_klt or bool(KLT_RE.search(line))
            for m in VERSION_RE.finditer(line):
                if _historical_form(line, m.start(), m.end()):
                    continue
                if not in_ctx:
                    continue
                hits += 1
                if carve.covers(rel, i, line):
                    continue
                value = m.group(1)
                if value in by_value:
                    label, drel = by_value[value]
                    findings.append(
                        f"{rel}:{i}: restates the {label} pin ({value}, declared in {drel}); "
                        f"point at the declaration instead of the value, or exempt the line "
                        f"in signoff/pin-restatements.json with a reason"
                    )
                else:
                    findings.append(
                        f"{rel}:{i}: names version {value} in klt context, but no declaration "
                        f"pins it (stale restatement?); see signoff/pin-restatements.json"
                    )
            if KLT_RE.search(line):
                para_klt = True
    return findings, hits, len(prose)


def find_findings(root: Path = REPO_ROOT) -> list[str]:
    return scan(root)[0]


def main(root: Path = REPO_ROOT) -> int:
    findings, hits, nfiles = scan(root)
    if findings:
        findings = list(dict.fromkeys(findings))
        print("\n".join(findings), file=sys.stderr)
        print(f"FAIL: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print(f"OK: {hits} klt-context version mention(s) in {nfiles} prose files, all exempt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
