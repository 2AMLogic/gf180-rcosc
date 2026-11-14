"""Shared evidence-integrity helpers for the simulation drivers (#260).

Standard library only.  One definition of the three things every ``sim/``
driver that writes a run directory used to spell out for itself:

* sha256 helpers (``sha256_bytes`` / ``sha256_text`` / ``sha256_file``);
* the evidence banners.  ``SYNTHETIC_BANNER`` is part of the repo's
  evidence-integrity contract and is asserted by tests and present in
  committed ``results/``; its value must never change;
* the append-only new-run guard (``require_absent`` / ``new_run_dir``);
* the run-writer boilerplate: the ``results.csv`` DictWriter block
  (``write_results_csv``), the dash-or-format summary formatter (``dash``),
  the ``new_run_dir`` / ``is_synthetic`` / ``banner`` prologue
  (``run_prologue``) and the common ``results.json`` header keys
  (``run_header``).  Float precision and ``extrasaction`` stay per-call-site
  parameters on purpose: collapsing them would silently reformat
  regenerated evidence.

Same placement and import convention as ``git_provenance`` (#216).
"""
from __future__ import annotations

import csv
import datetime
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


def run_prologue(out, synthetic, metas):
    """``new_run_dir`` + ``is_synthetic`` + ``banner`` in one step.

    Returns ``(out, synthetic, banner)`` in the shape every run-writer used
    to spell out line by line.
    """
    out = new_run_dir(out)
    synthetic = is_synthetic(synthetic, metas)
    return out, synthetic, banner(synthetic)


def dash(x, f="%.4g"):
    """Dash-or-format summary cell: ``"-"`` for a missing value, else ``f % x``."""
    return "-" if x is None else f % x


def write_results_csv(out, rows, fieldnames, *, flat=None, fmt=".6g", extrasaction="raise"):
    """One ``results.csv`` DictWriter block: header, then rows with floats via ``fmt``.

    ``flat`` maps each row to the dict actually written (flatten / derive);
    identity when omitted.  ``fmt`` and ``extrasaction`` are per-call-site on
    purpose -- ``.4g`` and ``.6g`` sites coexist and must not collapse.
    """
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction=extrasaction)
        w.writeheader()
        for r in rows:
            d = flat(r) if flat is not None else r
            w.writerow({k: (f"{v:{fmt}}" if isinstance(v, float) else v) for k, v in d.items()})


def run_header(label, synthetic, *, params=None, note=None, metas=None):
    """The common ``results.json`` header keys, in emission order.

    Callers merge their own keys on top (``{**run_header(...), ...}``), which
    keeps every key in its original position.  ``params`` / ``note`` /
    ``metas`` keys are emitted only when passed, so drivers whose doc omits
    them (e.g. loadsweep has no ``note``) stay byte-identical.
    """
    doc = {"label": label, "synthetic": synthetic,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if params is not None:
        doc["params"] = params
    if note is not None:
        doc["note"] = note
    if metas is not None:
        doc["reports"] = metas
    return doc
