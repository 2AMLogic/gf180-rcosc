"""Shared PDK-revision provenance for the simulation campaign manifests (#65).

Standard library only, side-effect free (reads the filesystem, writes nothing).
One implementation used by ``sim/pvt/pvt_sweep.py``,
``sim/pvt-postlayout/pex_pvt_sweep.py`` and ``sim/iq/iq_sweep.py``.

Manifest schema (the keys :func:`manifest_fields` returns; merge into the
manifest dict):

``pdk``                    family name, e.g. ``"gf180mcuC"``
``pdk_revision``           40-hex open_pdks commit, or exactly ``"unknown"``
``pdk_revision_source``    present when resolved: where the value came from
                           (``"SOURCES"`` or ``"volare-version-dir"``; both
                           are recorded as ``"SOURCES+volare-version-dir"``
                           when they agree)
``pdk_revision_reason``    present when ``"unknown"``: non-empty explanation
``model_dir``              ngspice model dir relative to the PDK root, or
                           omitted when it cannot be expressed portably

No absolute path (``pdk_root``, home directories) is ever emitted. Revision
detection never guesses: no mtime, no repository state, no partial match.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

UNKNOWN = "unknown"
_HEX40 = re.compile(r"[0-9a-f]{40}")
_SOURCES_LINE = re.compile(r"^open_pdks\s+([0-9a-f]{40})\s*$")


def _from_sources(variant_dir: Path):
    """Return (revision, None) or (None, reason) from <variant>/SOURCES."""
    f = variant_dir / "SOURCES"
    if not f.is_file():
        return None, "no SOURCES metadata file in the PDK variant directory"
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"SOURCES metadata unreadable ({type(exc).__name__})"
    revs = {m.group(1) for line in text.splitlines()
            if (m := _SOURCES_LINE.match(line))}
    if len(revs) == 1:
        return revs.pop(), None
    if not revs:
        return None, "SOURCES metadata has no 'open_pdks <40-hex>' record (malformed)"
    return None, "SOURCES metadata names several different open_pdks commits"


def _from_volare_dir(resolved_variant: Path):
    """Return the <hash> of a ``.../versions/<hash>/<variant>`` path, or None."""
    parent = resolved_variant.parent
    if parent.parent.name == "versions" and _HEX40.fullmatch(parent.name):
        return parent.name
    return None


def resolve_pdk_revision(pdk_root, pdk: str) -> dict:
    """Resolve the PDK revision for ``<pdk_root>/<pdk>``.

    Returns ``{"pdk_revision": <40-hex>, "pdk_revision_source": ...}`` or
    ``{"pdk_revision": "unknown", "pdk_revision_reason": ...}``.
    """
    def unknown(reason):
        return {"pdk_revision": UNKNOWN, "pdk_revision_reason": reason}

    variant = Path(pdk_root) / pdk
    try:
        resolved = variant.resolve(strict=True)
    except (OSError, RuntimeError):
        return unknown("PDK variant directory missing, broken symlink or symlink loop")
    if not resolved.is_dir():
        return unknown("PDK variant path is not a directory")

    meta, meta_reason = _from_sources(resolved)
    vdir = _from_volare_dir(resolved)
    if meta and vdir and meta != vdir:
        return unknown("SOURCES metadata and volare version directory disagree")
    if meta and vdir:
        return {"pdk_revision": meta,
                "pdk_revision_source": "SOURCES+volare-version-dir"}
    if meta:
        return {"pdk_revision": meta, "pdk_revision_source": "SOURCES"}
    if vdir:
        return {"pdk_revision": vdir, "pdk_revision_source": "volare-version-dir"}
    return unknown(f"{meta_reason}; install path is not a volare versions/<hash> directory")


def portable_relpath(path, pdk_root):
    """``path`` relative to ``pdk_root`` as a POSIX string, or None.

    None when the path is not under the root or the result is absolute or
    contains ``..``. Symlinks are not resolved, so the lexical layout is kept.
    """
    try:
        rel = PurePosixPath(Path(path).relative_to(Path(pdk_root)).as_posix())
    except ValueError:
        return None
    if rel.is_absolute() or ".." in rel.parts or str(rel) in ("", "."):
        return None
    return str(rel)


def manifest_fields(pdk_root, pdk: str, model_dir=None) -> dict:
    """The PDK block every campaign manifest carries (see module docstring)."""
    out = {"pdk": pdk}
    out.update(resolve_pdk_revision(pdk_root, pdk))
    if model_dir is not None:
        rel = portable_relpath(model_dir, pdk_root)
        if rel is not None:
            out["model_dir"] = rel
    return out


def display(fields: dict) -> str:
    """Human-readable one-liner for generated READMEs/summaries (no paths)."""
    rev = fields["pdk_revision"]
    if rev == UNKNOWN:
        return f"{fields['pdk']} (revision unknown: {fields['pdk_revision_reason']})"
    return f"{fields['pdk']} (open_pdks `{rev}`, from {fields['pdk_revision_source']})"
