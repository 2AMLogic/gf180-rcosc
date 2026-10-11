"""Offline regression for the legacy sweep drivers' --jobs default (issue #139).

All four drivers (pvt_sweep, delay_probe, iq_sweep, pex_pvt_sweep) must default
--jobs to the shared constant pvt_sweep.DEFAULT_JOBS (<= 2) so an unattended
run cannot saturate a shared host. The test only captures each driver's
argparse parser (parse_args is intercepted before any work happens); no
simulation, PDK or ngspice is used and nothing is written.

Run:  python3 -I -m pytest -p no:cacheprovider sim/legacy-analysis/test_jobs_defaults.py
"""
import argparse
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
MAX_DEFAULT_JOBS = 2


class _Captured(Exception):
    def __init__(self, parser):
        self.parser = parser


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _module_loader import load_module  # noqa: E402


def _load(name, path):
    return load_module(name, path, reuse=False)


@pytest.fixture(scope="module")
def base():
    return _load("pvt_sweep", SIM / "pvt" / "pvt_sweep.py")


DRIVERS = [
    ("pvt_sweep", "pvt/pvt_sweep.py"),
    ("delay_probe", "pvt/delay_probe.py"),
    ("iq_sweep", "iq/iq_sweep.py"),
    ("pex_pvt_sweep", "pvt-postlayout/pex_pvt_sweep.py"),
]


def test_shared_constant_is_small(base):
    assert 1 <= base.DEFAULT_JOBS <= MAX_DEFAULT_JOBS


@pytest.mark.parametrize("name,rel", DRIVERS)
def test_driver_jobs_default(name, rel, base, monkeypatch):
    mod = base if name == "pvt_sweep" else _load(name, SIM / rel)

    def fake_parse_args(self, *a, **k):
        raise _Captured(self)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", fake_parse_args)
    with pytest.raises(_Captured) as ei:
        mod.main()
    parser = ei.value.parser
    action = next(a for a in parser._actions if "--jobs" in a.option_strings)
    assert action.default <= MAX_DEFAULT_JOBS
    assert action.default == base.DEFAULT_JOBS
    assert "default 6" not in (action.help or "")
