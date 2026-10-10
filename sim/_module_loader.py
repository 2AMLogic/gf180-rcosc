"""Shared path-based module loader for the offline request generators.

Standard library only. Policy is explicit: ``reuse=True`` returns an existing
``sys.modules[name]`` entry untouched; ``reuse=False`` always builds and
executes a fresh module, replacing any prior entry on success.

The new module is registered in ``sys.modules`` *before* execution so
decorators (e.g. ``dataclasses``) and imports that consult ``sys.modules``
see it. If execution raises, the prior entry is restored (or the partial
entry removed when none existed) and the original exception propagates.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MISSING = object()


def load_module(name: str, path, *, reuse: bool):
    """Load the file at ``path`` as module ``name`` under the given policy."""
    if reuse and name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create import spec for {name!r} from {path}")
    mod = importlib.util.module_from_spec(spec)
    prior = sys.modules.get(name, _MISSING)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        if prior is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return mod
