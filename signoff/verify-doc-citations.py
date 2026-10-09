#!/usr/bin/env python3
"""Verify that docs cite committed ``sim/<bench>/results/<ts>/`` dirs correctly.

PDK-free and stdlib-only (no klt, ngspice, xschem): it reads tracked
markdown and walks ``sim/``. Two checks:

1.  Existence (every tracked ``*.md`` outside the evidence trees): every
    cited ``sim/<bench>/{results,corners}/<ts>`` -- full, relative
    (``../../sim/...``), shortened (``pvt/results/<ts>``) or a bare
    ``<ts>`` resolved against the nearest preceding bench mention in the
    same paragraph -- names a directory that exists.
2.  Currency (only the ``strict_docs`` in ``signoff/citations.json``): a
    cite must name the bench's ``current`` run or one of its ``probes``.
    A cite of any other (older) dir passes only when its line carries a
    marker -- ``superseded``, ``historical``, or ``(was ...)`` -- or it
    sits under a heading containing ``Historical``. Nothing else loosens it.

The sidecar itself is checked: ``current``/``probes`` must exist, and a
newer campaign dir (one holding ``manifest.json`` or ``summary.md``) than
``current`` that is not a listed probe fails, so the sidecar cannot rot.

Run from anywhere in the repository (CI: ``.github/workflows/doc-citations.yml``)::

    python3 signoff/verify-doc-citations.py

Exit 0 = clean; exit 1 = findings, printed as ``file:line: message``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIM = REPO_ROOT / "sim"
SIDECAR = REPO_ROOT / "signoff" / "citations.json"

TS = r"\d{8}T\d{6}Z"
TS_RE = re.compile(rf"(?<![0-9A-Za-z]){TS}(?![0-9A-Za-z])")
# `<bench>/results|corners/<ts>`, optionally preceded by `sim/` (or ../..).
FULL_RE = re.compile(rf"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+)/(results|corners)/({TS})(?![0-9A-Za-z])")
BENCH_MENTION_RE = re.compile(r"(?:sim/)?([A-Za-z0-9_-]+)/(?:results|corners)\b|sim/([A-Za-z0-9_-]+)/")
MARKER_RE = re.compile(r"superseded|historical|\(was\b", re.I)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")

EXCLUDED_PREFIXES = (".loom/", ".claude/", ".git/")


def tracked_markdown() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.split()
    keep = []
    for p in out:
        if p.startswith(EXCLUDED_PREFIXES):
            continue
        if re.match(r"sim/[^/]+/(results|corners|batch-attempts)/", p):
            continue  # append-only evidence trees are not docs
        keep.append(p)
    return keep


def benches() -> set[str]:
    return {p.name for p in SIM.iterdir() if p.is_dir()}


def check_sidecar(side: dict, errors: list[str]) -> None:
    for bench, ent in side["benches"].items():
        base = SIM / bench / "results"
        for ts in [ent["current"], *ent.get("probes", [])]:
            if not (base / ts).is_dir():
                errors.append(f"signoff/citations.json: {bench}: {ts} is not a dir under sim/{bench}/results/")
        if not base.is_dir():
            continue
        allowed = {ent["current"], *ent.get("probes", [])}
        for d in sorted(base.iterdir()):
            is_campaign = (d / "manifest.json").exists() or (d / "summary.md").exists()
            if d.is_dir() and is_campaign and d.name > ent["current"] and d.name not in allowed:
                errors.append(
                    f"signoff/citations.json: {bench}: sim/{bench}/results/{d.name} is newer than "
                    f"current {ent['current']} and not a listed probe; update the sidecar"
                )


def scan(rel: str, side: dict, known: set[str], strict: bool, errors: list[str]) -> int:
    lines = (REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()
    n = 0
    heading_historical = False
    heading_level = 0
    bench_ctx: str | None = None  # nearest preceding bench mention in paragraph
    for i, line in enumerate(lines, 1):
        m = HEADING_RE.match(line)
        if m:
            level = len(line.lstrip()) - len(line.lstrip().lstrip("#"))
            if "historical" in m.group(1).lower():
                heading_historical, heading_level = True, level
            elif heading_historical and level <= heading_level:
                heading_historical = False
        if not line.strip():
            bench_ctx = None

        # Walk the line left to right so bare timestamps see the nearest
        # preceding bench mention (on this line, else earlier in paragraph).
        events: list[tuple[int, str, str, str | None]] = []
        covered: list[tuple[int, int]] = []
        for fm in FULL_RE.finditer(line):
            if fm.group(1) in known:
                events.append((fm.start(), "cite", fm.group(1), fm.group(3)))
                covered.append((fm.start(), fm.end()))
        for bm in BENCH_MENTION_RE.finditer(line):
            b = bm.group(1) or bm.group(2)
            if b in known:
                events.append((bm.start(), "ctx", b, None))
        for tm in TS_RE.finditer(line):
            if not any(a <= tm.start() < b for a, b in covered):
                events.append((tm.start(), "bare", "", tm.group(0)))
        events.sort(key=lambda e: (e[0], e[1] != "ctx"))

        ctx_events = [(pos, b) for pos, k, b, _ in events if k == "ctx"]
        for pos, kind, bench, ts in events:
            if kind == "ctx":
                bench_ctx = bench
                continue
            if kind == "bare":
                # nearest preceding bench mention on the line, else the first
                # following one on the line, else the paragraph's last one.
                before = [b for p, b in ctx_events if p < pos]
                after = [b for p, b in ctx_events if p > pos]
                bench = before[-1] if before else (after[0] if after else (bench_ctx or ""))
                if not bench or not (
                    (SIM / bench / "results" / ts).is_dir() or (SIM / bench / "corners" / ts).is_dir()
                ):
                    # context bench lacks it: accept a unique owner elsewhere
                    cands = [b for b in sorted(known) if (SIM / b / "results" / ts).is_dir()]
                    if len(cands) == 1:
                        bench = cands[0]
                    elif not cands:
                        errors.append(f"{rel}:{i}: bare timestamp {ts} matches no sim run")
                        continue
                    elif not bench:
                        errors.append(f"{rel}:{i}: bare timestamp {ts} is ambiguous without a bench; cite sim/<bench>/results/{ts}")
                        continue
            n += 1
            if not ((SIM / bench / "results" / ts).is_dir() or (SIM / bench / "corners" / ts).is_dir()):
                errors.append(f"{rel}:{i}: cited dir sim/{bench}/{{results,corners}}/{ts} does not exist")
                continue
            if not strict:
                continue
            ent = side["benches"].get(bench)
            if ent is None:
                errors.append(f"{rel}:{i}: bench '{bench}' has no entry in signoff/citations.json")
                continue
            if ts == ent["current"] or ts in ent.get("probes", []):
                continue
            if MARKER_RE.search(line) or heading_historical:
                continue
            errors.append(
                f"{rel}:{i}: cites sim/{bench}/.../{ts}, not the current run {ent['current']} "
                f"(or a listed probe), and the line has no superseded/historical/(was ...) marker"
            )
    return n


def main() -> int:
    side = json.loads(SIDECAR.read_text(encoding="utf-8"))
    known = benches()
    errors: list[str] = []
    check_sidecar(side, errors)
    strict_docs = set(side["strict_docs"])
    for rel in side["strict_docs"]:
        if not (REPO_ROOT / rel).is_file():
            errors.append(f"signoff/citations.json: strict doc {rel} does not exist")
    total = 0
    for rel in tracked_markdown():
        total += scan(rel, side, known, rel in strict_docs, errors)
    if errors:
        errors = list(dict.fromkeys(errors))
        print("\n".join(errors), file=sys.stderr)
        print(f"FAIL: {len(errors)} finding(s)", file=sys.stderr)
        return 1
    print(f"OK: {total} run-dir citation(s) checked across {len(tracked_markdown())} docs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
