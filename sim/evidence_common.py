"""Shared evidence-integrity helpers for the simulation drivers (#260).

Standard library only.  One definition of the three things every ``sim/``
driver that writes a run directory used to spell out for itself:

* sha256 helpers (``sha256_bytes`` / ``sha256_text`` / ``sha256_file``);
* the evidence banners.  ``SYNTHETIC_BANNER`` is part of the repo's
  evidence-integrity contract and is asserted by tests and present in
  committed ``results/``; its value must never change;
* the append-only new-run guard (``require_absent`` / ``new_run_dir``).

Same placement and import convention as ``git_provenance`` (#216).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SYNTHETIC_BANNER = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"
MEASURED_BANNER = ("Analysis of simulator output; evidence status is set by the "
                   "originating campaign record")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode())


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def banner(synthetic: bool) -> str:
    return SYNTHETIC_BANNER if synthetic else MEASURED_BANNER


def is_synthetic(synthetic: bool, metas) -> bool:
    """True when the caller says so or any input report is itself synthetic."""
    return bool(synthetic or any(m.get("synthetic") for m in metas))


def require_absent(out, exc=SystemExit) -> Path:
    """Refuse (raise ``exc``) when ``out`` already exists: results are append-only."""
    out = Path(out)
    if out.exists():
        raise exc(f"refusing to overwrite existing run {out}")
    return out


def new_run_dir(out, exc=SystemExit) -> Path:
    """``require_absent`` then create ``out`` (with parents) and return it."""
    out = require_absent(out, exc)
    out.mkdir(parents=True)
    return out
