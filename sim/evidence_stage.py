"""Stage a campaign's raw outputs in git-ignored scratch, then store them.

Issue #196. A campaign driver (``sim/pvt``, ``sim/iq``, ``sim/pvt-postlayout``,
``sim/recentre``) no longer writes its raw logs, CSVs and decks under
``sim/<bench>/corners|results/<runid>/``. It writes them into the scratch tree
``sim/build/evidence/<bench>/<runid>/{corners,results}/`` (``sim/build/`` is
git-ignored) and calls :meth:`Stage.finish`, which puts every file through
``klt artifact put`` under the logical name
``sim/<bench>/{corners,results}/<runid>/<relative path>`` and commits only

* ``manifests/artifacts/<bench>-<runid>.manifest.json``, and
* ``sim/<bench>/results/<runid>/summary.md`` -- the run's Markdown summary
  (the one the driver staged as ``results/<runid>/summary.md``) with a "Stored
  evidence" table of name, size and sha256 per object.

Fail closed: :func:`open_stage` runs :func:`harness.evidence_store.preflight`
before any simulation time is spent (broker unset, ``klt`` missing or too old,
broker unreachable or refusing -> :class:`StoreError`), and
:meth:`Stage.finish` installs nothing under ``manifests/`` or ``sim/`` unless
every put succeeded and matches the local bytes. A failure leaves the staged
files in scratch so the run is not lost; there is no fallback that commits
bytes. See ``sim/README.md``, "Stored evidence".

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sim"))

from harness import evidence_store as store_mod  # noqa: E402

StoreError = store_mod.StoreError
STAGE_ROOT = REPO_ROOT / "sim" / "build" / "evidence"
SUMMARY = "summary.md"
#: Exit status a driver returns when the run finished but could not be stored.
EXIT_NOT_STORED = 10


class Stage:
    """Scratch tree of one run: ``corners`` and ``results`` mirror the
    committed ``sim/<bench>/`` layout so logical names stay unchanged."""

    def __init__(self, bench: str, runid: str, repo_root: Path = REPO_ROOT,
                 stage_root: Path | None = None, summary_name: str = SUMMARY):
        self.bench, self.runid, self.repo_root = bench, runid, repo_root
        self.summary_name = summary_name
        self.root = (stage_root or repo_root / "sim" / "build" / "evidence") / bench / runid
        self.corners = self.root / "corners"
        self.results = self.root / "results"

    @property
    def manifest(self) -> Path:
        return store_mod.manifest_path(self.repo_root, self.bench, self.runid)

    @property
    def summary_path(self) -> Path:
        return self.repo_root / "sim" / self.bench / "results" / self.runid / self.summary_name

    def create(self) -> None:
        """Make the scratch dirs; refuse a run id that already has evidence
        anywhere (append-only): a manifest, committed dirs, or earlier scratch."""
        taken = [self.manifest, self.summary_path.parent,
                 self.repo_root / "sim" / self.bench / "corners" / self.runid]
        for p in taken:
            if p.exists() and (p.is_file() or any(p.iterdir())):
                raise StoreError(f"{p.relative_to(self.repo_root)} already exists; "
                                 "evidence is append-only (run id collision?)")
        if self.root.exists() and any(self.root.iterdir()):
            raise StoreError(f"{self.root.relative_to(self.repo_root)} already holds "
                             "staged evidence (run id collision?)")
        self.corners.mkdir(parents=True, exist_ok=True)
        self.results.mkdir(parents=True, exist_ok=True)

    def finish(self, *, put=None) -> Path:
        """Store the staged tree; commit only the manifest and the summary.
        Raises :class:`StoreError` (nothing installed) on any failure."""
        summary = self.results / self.runid / self.summary_name
        try:
            summary_text = summary.read_text(encoding="utf-8")
        except OSError as exc:
            raise StoreError(f"no staged {self.summary_name} to commit: {exc}") from None
        files = store_mod.stage_files(self.root, f"sim/{self.bench}", exclude=[summary])
        return store_mod.store_files(
            files, repo_root=self.repo_root, bench=self.bench, rid=self.runid,
            summary_text=summary_text, summary_path=self.summary_path, put=put)


def open_stage(bench: str, runid: str, **kw) -> Stage:
    """Preflight the store, then create the scratch tree for ``runid``."""
    stage = Stage(bench, runid, **kw)
    store_mod.manifest_path(stage.repo_root, bench, runid)  # validates the ids
    store_mod.preflight(stage.repo_root)
    stage.create()
    return stage


def finish_or_report(stage: Stage) -> int:
    """Store ``stage``; print the outcome. 0 stored, 10 not stored."""
    try:
        manifest = stage.finish()
    except StoreError as exc:
        print(f"EVIDENCE NOT STORED -- nothing committed (fail closed): {exc}\n"
              f"staged bytes are kept in {stage.root.relative_to(stage.repo_root)}",
              file=sys.stderr)
        return EXIT_NOT_STORED
    rel = manifest.relative_to(stage.repo_root)
    print(f"stored evidence: commit {rel} and "
          f"{stage.summary_path.relative_to(stage.repo_root)}; then "
          f"`klt artifact verify {rel}`", flush=True)
    return 0
