#!/usr/bin/env python3
"""Verify this block's committed ``klt signoff`` records against the live tree.

Three independent checks, all PDK-free (``klt signoff --manifest`` grades
committed JSON envelopes; it never runs DRC/LVS/sim gates, so this needs no
PDK, xschem, or ngspice):

1.  Re-run ``klt signoff --manifest signoff/block-manifest.json --format
    json``. Exit 0 = block graded T1; exit 3 = graded below T1 (data, not
    failure -- this block has unmet items by design until it matures); any
    other exit is a real error and fails here.
2.  Compare the fresh per-item grades (id, title, status, reason) plus the
    block-level fields against the committed verdict of record,
    ``signoff/signoff-report.json``. Any drift fails: a manifest or evidence
    envelope that changed without re-grading and re-committing the report
    rots loudly instead of passing -- this is the anti-rot gate for the part
    the grader itself does not check.
3.  Re-hash the committed artifacts each citation pins and compare against
    the hashes recorded in the cited envelope AND in the manifest, so a
    citation whose artifact has since changed fails rather than rotting --
    the equivalent of upstream klayout-tools #2212, done repo-side until the
    pinned grader release carries it natively.

Run from anywhere inside the repository:

    python3 signoff/verify-report.py

CI runs exactly this command (``.github/workflows/signoff.yml``). Before
committing a refreshed report locally, run it too -- if the freshly graded
report is not what got committed, or an artifact drifted, it fails.

Environment note: the grader pin documented in ``signoff/README.md`` is
load-bearing for check 2. Two klt builds that bundle different
``design-evidence-tiers.md`` rulebooks legitimately grade different item
tables (the 11-item rulebook this report is committed under vs. the 10-item
one released klt 0.5.0 bundles), so this script does not try to paper over
a ``source_doc_content_hash``/item-table mismatch: it reports the drift and
exits nonzero. Install the pinned grader from signoff/README.md first.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "signoff" / "block-manifest.json"
COMMITTED_REPORT = REPO_ROOT / "signoff" / "signoff-report.json"

# Per-citation pin re-verification (check 3). Keyed by T1 item id:
#   (evidence envelope a manifest entry cites, committed artifact whose
#    sha256 must equal the manifest pin and the envelope's recorded
#    provenance.input.content_hash for that citation).
#
# The artifact mapping lives here -- not in the envelopes -- because the
# committed layout envelopes record the absolute path of the worktree they
# were generated in (`klt` echoes the path it was given), which does not
# resolve from any other checkout. That is also why these are exactly the
# citations block-manifest.json makes: adding a citation means adding a row
# here, and signoff/README.md's refresh contract says so.
PINNED_ARTIFACTS = {
    "2": (
        REPO_ROOT / "layout" / "reports" / "rcosc_top.extract.json",
        REPO_ROOT / "layout" / "cells" / "rcosc_top.gds",
    ),
    "3": (
        REPO_ROOT / "layout" / "reports" / "rcosc_top.drc.json",
        REPO_ROOT / "layout" / "cells" / "rcosc_top.gds",
    ),
    "8": (
        REPO_ROOT / "signoff" / "characterization-envelope.json",
        REPO_ROOT / "docs" / "chipalooza" / "challenge-5-proposal.md",
    ),
}

# The unpinned LVS citation's own freshness statement: the committed envelope
# records the sha256 of each netlist it compared, so the committed files can
# be re-hashed and compared against the record directly.
LVS_ENVELOPE = REPO_ROOT / "layout" / "reports" / "rcosc_top.lvs.json"
LVS_INPUTS = (
    (
        REPO_ROOT / "layout" / "reports" / "rcosc_top.extracted.spice",
        "layout_sha256",
    ),
    (
        REPO_ROOT / "layout" / "lvs_ref" / "rcosc_top.spice",
        "reference_sha256",
    ),
)

# T1 item 11's compound citation (klayout-tools issue #2025) -- the one
# manifest entry that is a *list* of evidence parts graded together. The
# ERC part is pinned exactly like items 2, 3 and 8 (manifest pin == the
# envelope's recorded provenance.input.content_hash == the current bytes
# of the GDS it ran against) and, because `klt signoff` reads the spec the
# envelope names to grade the item's supply-style/tie conditions, the
# spec hash the envelope records is checked against the spec's current
# bytes too: a spec edit without an erc re-run rots here the same way a
# GDS edit rots items 2/3. The LVS part is the same unpinned
# klt-0.4.0-era envelope item 4 cites -- the grader accepts it via its
# net_correspondence rows (VDD/VSS paired as pins), and its two netlists
# are already re-hashed against its own recorded digests by
# LVS_ENVELOPE/LVS_INPUTS above, so it needs no second row here.
ITEM11_ERC_ENVELOPE = REPO_ROOT / "layout" / "reports" / "rcosc_top.erc.json"
ITEM11_ERC_ARTIFACT = REPO_ROOT / "layout" / "cells" / "rcosc_top.gds"
ITEM11_ERC_SPEC = REPO_ROOT / "layout" / "erc-supply-spec.json"
ITEM11_LVS_FILE = "layout/reports/rcosc_top.lvs.json"

BLOCK_LEVEL_FIELDS = (
    "schema_version",
    "block",
    "kind",
    "tier",
    "t1_item_count",
    "t1_met_count",
    "source_doc",
    "source_doc_content_hash",
)
ITEM_FIELDS = ("tier", "id", "title", "status", "reason")


def find_klt() -> str:
    """Prefer the klt installed alongside this script's interpreter (CI's
    venv layout), then any klt on PATH. Absent both, there is nothing to
    verify with -- fail with the install command from signoff/README.md."""
    beside_interpreter = Path(sys.executable).parent / "klt"
    if beside_interpreter.is_file():
        return str(beside_interpreter)
    on_path = shutil.which("klt")
    if on_path:
        return on_path
    sys.exit(
        "no klt binary found (looked next to "
        f"{sys.executable} and on PATH) -- install the pinned grader per "
        "signoff/README.md, e.g.\n"
        "  python -m pip install "
        "'klayout-tools @ git+https://github.com/2AMLogic/klayout-tools"
        "@2b1e55e51bb803c082e8857da44687f3e37ebfc0'"
    )


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(problems: list[str]) -> None:
    for line in problems:
        print(f"FAIL: {line}", file=sys.stderr)
    sys.exit(f"{len(problems)} signoff verification problem(s) -- see above")


def fresh_signoff(manifest: Path) -> dict:
    """Run the grader and return its report. Exit 0 (T1) and exit 3 (below
    T1, unmet items exist) are both valid outcomes; anything else -- or a
    non-JSON payload -- is an error."""
    completed = subprocess.run(
        [
            find_klt(),
            "signoff",
            "--manifest",
            str(manifest),
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode not in (0, 3):
        print(completed.stdout[-2000:], file=sys.stderr)
        print(completed.stderr[-2000:], file=sys.stderr)
        sys.exit(f"klt signoff exited {completed.returncode} (expected 0 or 3)")
    try:
        return json.loads(completed.stdout)
    except ValueError:
        sys.exit("klt signoff stdout did not parse as JSON")


def grade_drift(fresh: dict, committed: dict) -> list[str]:
    """Block-level + per-item comparison of the fresh grade against the
    committed verdict of record. Returns a list of drift descriptions."""
    problems = []
    for field in BLOCK_LEVEL_FIELDS:
        if fresh.get(field) != committed.get(field):
            problems.append(
                f"block-level field {field!r} drifted: committed report has "
                f"{committed.get(field)!r}, fresh grade has {fresh.get(field)!r} "
                "(re-grade and commit a fresh signoff/signoff-report.json -- "
                "see signoff/README.md -- or restore the evidence/manifest)"
            )
    fresh_rows = [
        tuple(item.get(field) for field in ITEM_FIELDS) for item in fresh.get("items", [])
    ]
    committed_rows = [
        tuple(item.get(field) for field in ITEM_FIELDS)
        for item in committed.get("items", [])
    ]
    if fresh_rows != committed_rows:
        fresh_by_key = {(t[0], t[1]): t for t in fresh_rows}
        committed_by_key = {(t[0], t[1]): t for t in committed_rows}
        for key in sorted(
            set(fresh_by_key) | set(committed_by_key),
            key=lambda k: (str(k[0]), -1 if k[1] is None else k[1]),
        ):
            if fresh_by_key.get(key) != committed_by_key.get(key):
                problems.append(
                    f"item {key} drifted: committed report has "
                    f"{committed_by_key.get(key)}, fresh grade has "
                    f"{fresh_by_key.get(key)}"
                )
    return problems


def verify_pins(manifest: dict) -> list[str]:
    """Check every pinned citation: manifest pin == the cited envelope's
    recorded input hash == the sha256 of the artifact's current bytes. Also
    re-verify the unpinned LVS citation via the digests its own envelope
    records. Returns a list of rot/consistency problems."""
    problems = []
    evidence = manifest.get("evidence", {})
    for item, (envelope_path, artifact_path) in PINNED_ARTIFACTS.items():
        label = f"item {item} citation"
        entry = evidence.get(item)
        if not isinstance(entry, dict) or "content_hash" not in entry:
            problems.append(
                f"{label} is expected to carry a content_hash pin "
                "(see signoff/README.md's refresh contract)"
            )
            continue
        manifest_pin = entry["content_hash"].removeprefix("sha256:")
        envelope = json.loads(envelope_path.read_text())
        recorded = (
            (envelope.get("provenance") or {})
            .get("input", {})
            .get("content_hash", "")
        ).removeprefix("sha256:")
        actual = sha256_of(artifact_path)
        if manifest_pin != recorded:
            problems.append(
                f"{label}: manifest pin {manifest_pin[:16]}... does not match "
                f"the hash recorded in {envelope_path.name} "
                f"({recorded[:16] if recorded else 'absent'}...)"
            )
        if recorded != actual:
            problems.append(
                f"{label}: envelope {envelope_path.name} pins "
                f"{(recorded or 'no hash')[:16] if recorded else 'no hash'}... but "
                f"{artifact_path.name} currently hashes to {actual[:16]}... "
                f"({artifact_path.name} changed since the evidence was "
                "generated -- refresh the evidence, then re-pin and re-grade "
                "per signoff/README.md's refresh contract)"
            )
    lvs = json.loads(LVS_ENVELOPE.read_text())
    environment = lvs.get("environment") or {}
    for artifact_path, digest_field in LVS_INPUTS:
        recorded = environment.get(digest_field) or ""
        actual = sha256_of(artifact_path)
        if recorded != actual:
            problems.append(
                f"unpinned LVS citation: {LVS_ENVELOPE.name} records "
                f"{digest_field}={recorded[:16] if recorded else 'absent'}... but "
                f"{artifact_path.name} currently hashes to {actual[:16]}... "
                "(a netlist the committed LVS match compared has changed -- "
                "regenerate the layout evidence per layout/run_checks.sh and "
                "re-grade per signoff/README.md)"
            )
    problems += verify_power_delivery_citation(evidence)
    return problems


def _evidence_file(entry: Any) -> str | None:
    """The repo-relative path a manifest evidence entry (or list part)
    cites -- its ``file`` key as a dict, or the entry itself as a bare
    string; ``None`` for any other shape."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and isinstance(entry.get("file"), str):
        return entry["file"]
    return None


def verify_power_delivery_citation(evidence: dict[str, Any]) -> list[str]:
    """Verify T1 item 11's compound citation (a list of evidence parts),
    whose ERC half is hash-pinned and whose LVS half is the same envelope
    item 4's own LVS_ENVELOPE/LVS_INPUTS block already re-verifies.

    Checks, all against current bytes:
    - the manifest entry is the compound list shape, with one part citing
      the ERC report and one part citing the LVS report;
    - the ERC part's manifest pin == the ERC envelope's recorded
      ``provenance.input.content_hash`` == the GDS's sha256 (mirroring
      the items 2/3 loop above for the pinned part of the compound);
    - the ERC envelope's recorded ``provenance.spec.content_hash`` == the
      supply spec's sha256, so a spec edit without an erc re-run fails
      here instead of silently grading against stale declarations.
    """
    label = "item 11 citation"
    problems: list[str] = []
    entry = evidence.get("11")
    if not isinstance(entry, list) or not entry:
        problems.append(
            f"{label} is expected to be the compound list entry "
            "(erc + lvs, see signoff/README.md and "
            "klayout-tools docs/cli/signoff.md)"
        )
        return problems
    by_file = {_evidence_file(part): part for part in entry}
    erc_part = by_file.get(str(ITEM11_ERC_ENVELOPE.relative_to(REPO_ROOT)))
    if not isinstance(erc_part, dict) or "content_hash" not in erc_part:
        problems.append(
            f"{label}: no ERC part carrying a content_hash pin for "
            f"{ITEM11_ERC_ENVELOPE.relative_to(REPO_ROOT)} "
            "(it is the pinned half of the compound entry)"
        )
        return problems
    if not any(_evidence_file(part) == ITEM11_LVS_FILE for part in entry):
        problems.append(
            f"{label}: no part cites {ITEM11_LVS_FILE} (the LVS half of "
            "the compound entry)"
        )
    manifest_pin = erc_part["content_hash"].removeprefix("sha256:")
    envelope = json.loads(ITEM11_ERC_ENVELOPE.read_text())
    provenance = envelope.get("provenance") or {}
    recorded_input = (
        (provenance.get("input") or {}).get("content_hash", "")
    ).removeprefix("sha256:")
    actual = sha256_of(ITEM11_ERC_ARTIFACT)
    if manifest_pin != recorded_input:
        problems.append(
            f"{label}: manifest pin {manifest_pin[:16]}... does not match "
            f"the hash recorded in {ITEM11_ERC_ENVELOPE.name} "
            f"({recorded_input[:16] if recorded_input else 'absent'}...)"
        )
    if recorded_input != actual:
        problems.append(
            f"{label}: envelope {ITEM11_ERC_ENVELOPE.name} pins "
            f"{(recorded_input or 'no hash')[:16] if recorded_input else 'no hash'}... but "
            f"{ITEM11_ERC_ARTIFACT.name} currently hashes to {actual[:16]}... "
            f"({ITEM11_ERC_ARTIFACT.name} changed since the evidence was "
            "generated -- refresh the evidence, then re-pin and re-grade "
            "per signoff/README.md's refresh contract)"
        )
    recorded_spec = (
        (provenance.get("spec") or {}).get("content_hash", "")
    ).removeprefix("sha256:")
    actual_spec = sha256_of(ITEM11_ERC_SPEC)
    if recorded_spec != actual_spec:
        problems.append(
            f"{label}: envelope {ITEM11_ERC_ENVELOPE.name} records "
            f"spec hash {recorded_spec[:16] if recorded_spec else 'absent'}... but "
            f"{ITEM11_ERC_SPEC.name} currently hashes to "
            f"{actual_spec[:16]}... ({ITEM11_ERC_SPEC.name} changed since the "
            "erc evidence was generated -- re-run the erc evidence per the "
            "command in its own _comment, then re-grade per "
            "signoff/README.md's refresh contract)"
        )
    return problems


def main() -> None:
    if not MANIFEST.is_file():
        sys.exit(f"missing {MANIFEST.relative_to(REPO_ROOT)}")
    if not COMMITTED_REPORT.is_file():
        sys.exit(
            "missing signoff/signoff-report.json (the committed verdict of "
            "record) -- generate it with the command in signoff/README.md and "
            "commit it alongside the manifest"
        )
    manifest = json.loads(MANIFEST.read_text())
    committed = json.loads(COMMITTED_REPORT.read_text())

    fresh = fresh_signoff(MANIFEST)

    problems = []
    problems += grade_drift(fresh, committed)
    problems += verify_pins(manifest)
    if problems:
        fail(problems)

    t1_met = fresh["t1_met_count"]
    t1_total = fresh["t1_item_count"]
    tier = fresh["tier"] or f"below T1 ({t1_met}/{t1_total} T1 items met)"
    print(f"OK: fresh klt signoff grade == committed signoff/signoff-report.json")
    print(f"OK: every pinned citation's content_hash matches the current artifact bytes")
    print(f"OK: klt pin {fresh['source_doc_content_hash']} rulebook, {t1_total} T1 items -> {tier}")


if __name__ == "__main__":
    main()
