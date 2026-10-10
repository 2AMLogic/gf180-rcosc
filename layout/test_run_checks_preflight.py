"""Offline tests of layout/run_checks.sh's toolchain-pin preflight (issue #115).

The preflight must validate both the `klt` CLI *and* the Python runtime that
runs build_cells.py (which draws the committed GDS in-process) against the
geometry pins klayout-tools 0.4.0 / klayout 0.30.12, and must do so before
any netlist / GDS / LVS-reference / report mutation.

Everything here is SYNTHETIC: run_checks.sh is copied into a temporary
repo skeleton whose `design/regen-netlist.sh` is a sentinel stub (it records
that it ran and exits with a distinctive code), and `klt`, `python3` and `uv`
are fake commands on a controlled PATH. The fake `python3` is the real
interpreter run with `-S` (no site-packages) and a PYTHONPATH holding fake
`klayout` / `klayout_tools` packages plus `*.dist-info` metadata at the
versions under test, so the script's real importlib.metadata check is what
gets exercised. No PDK, no KLayout, no evidence regeneration; nothing under
the real layout/ is written.

    python3 -I -m pytest -p no:cacheprovider layout/test_run_checks_preflight.py
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RUN_CHECKS = Path(__file__).resolve().parent / "run_checks.sh"
PIN_KLT = "0.4.0"
PIN_KLAYOUT = "0.30.12"
REGEN_SENTINEL_RC = 42  # the stub regen-netlist.sh exits with this


def _write_exec(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_site(root: Path, klt_version: str | None, klayout_version: str | None) -> Path:
    """A fake site dir: importable modules plus dist-info at the given versions.

    A version of None omits that package entirely (modules and metadata).
    """
    root.mkdir(parents=True, exist_ok=True)
    if klayout_version is not None:
        (root / "klayout").mkdir()
        (root / "klayout" / "__init__.py").write_text("")
        (root / "klayout" / "db.py").write_text("")
        di = root / f"klayout-{klayout_version}.dist-info"
        di.mkdir()
        (di / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: klayout\nVersion: {klayout_version}\n"
        )
    if klt_version is not None:
        (root / "klayout_tools").mkdir()
        (root / "klayout_tools" / "__init__.py").write_text("")
        (root / "klayout_tools" / "gen.py").write_text("")
        di = root / f"klayout_tools-{klt_version}.dist-info"
        di.mkdir()
        (di / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: klayout-tools\nVersion: {klt_version}\n"
        )
    return root


class Env:
    """A temporary repo skeleton plus a fake-command PATH."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.repo = tmp / "repo"
        self.layout = self.repo / "layout"
        self.layout.mkdir(parents=True)
        (self.repo / "design").mkdir()
        shutil.copy2(RUN_CHECKS, self.layout / "run_checks.sh")
        self.regen_marker = tmp / "regen-ran"
        _write_exec(
            self.repo / "design" / "regen-netlist.sh",
            f"#!/bin/sh\ntouch '{self.regen_marker}'\nexit {REGEN_SENTINEL_RC}\n",
        )
        self.bin = tmp / "bin"
        self.bin.mkdir()
        self.uv_log = tmp / "uv-args"

    def klt(self, version: str) -> None:
        _write_exec(self.bin / "klt", f"#!/bin/sh\necho 'klt {version}'\n")

    def python3(self, site: Path | None) -> None:
        pp = f"PYTHONPATH='{site}' " if site is not None else ""
        _write_exec(
            self.bin / "python3",
            f"#!/bin/sh\n{pp}exec '{sys.executable}' -S \"$@\"\n",
        )

    def uv_with_site(self, site: Path) -> None:
        """Fake uv whose resolved environment is `site` regardless of request."""
        _write_exec(
            self.bin / "uv",
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$@\" > '{self.uv_log}'\n"
            'while [ "$#" -gt 0 ] && [ "$1" != python3 ]; do shift; done\n'
            "shift\n"
            f"PYTHONPATH='{site}' exec '{sys.executable}' -S \"$@\"\n",
        )

    def uv_resolving_requested(self) -> None:
        """Fake uv that honours `--with name==ver` pins (and resolves an
        unpinned `--with name` to a newer 9.9.9) by building a site to match."""
        _write_exec(
            self.bin / "uv",
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$@\" > '{self.uv_log}'\n"
            f"'{sys.executable}' -I -c '\n"
            "import sys, pathlib\n"
            "args = sys.argv[2:]\n"
            "site = pathlib.Path(sys.argv[1])\n"
            "site.mkdir(parents=True, exist_ok=True)\n"
            "mods = {\"klayout\": (\"klayout\", \"db\"), \"klayout-tools\": (\"klayout_tools\", \"gen\")}\n"
            "for i, a in enumerate(args):\n"
            "    if a != \"--with\":\n"
            "        continue\n"
            "    name, _, ver = args[i + 1].partition(\"==\")\n"
            "    ver = ver or \"9.9.9\"\n"
            "    pkg, sub = mods[name]\n"
            "    (site / pkg).mkdir(exist_ok=True)\n"
            "    (site / pkg / \"__init__.py\").write_text(\"\")\n"
            "    (site / pkg / (sub + \".py\")).write_text(\"\")\n"
            "    di = site / (name.replace(\"-\", \"_\") + \"-\" + ver + \".dist-info\")\n"
            "    di.mkdir(exist_ok=True)\n"
            "    (di / \"METADATA\").write_text(\"Metadata-Version: 2.1\\nName: \" + name + \"\\nVersion: \" + ver + \"\\n\")\n"
            f"' '{self.tmp / 'uv-site'}' \"$@\" || exit 99\n"
            'while [ "$#" -gt 0 ] && [ "$1" != python3 ]; do shift; done\n'
            "shift\n"
            f"PYTHONPATH='{self.tmp / 'uv-site'}' exec '{sys.executable}' -S \"$@\"\n",
        )

    def run(self) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.tmp),
            "LC_ALL": "C",
        }
        return subprocess.run(
            ["bash", str(self.layout / "run_checks.sh")],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def assert_no_mutation(self, proc: subprocess.CompletedProcess[str]) -> None:
        assert not self.regen_marker.exists(), "netlist regeneration ran before preflight failed"
        assert not (self.layout / "reports").exists(), "reports/ created before preflight passed"
        assert sorted(p.name for p in self.layout.iterdir()) == ["run_checks.sh"], (
            "preflight wrote into layout/"
        )
        assert "regenerating design/netlist" not in proc.stdout

    def assert_reached_regen(self, proc: subprocess.CompletedProcess[str]) -> None:
        assert proc.returncode == REGEN_SENTINEL_RC, proc.stdout + proc.stderr
        assert self.regen_marker.exists()


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def _uv_args(env: Env) -> list[str]:
    return env.uv_log.read_text().splitlines()


# --- passing configurations -------------------------------------------------


def test_pinned_cli_and_pinned_python3_pass(env: Env, tmp_path: Path) -> None:
    env.klt(PIN_KLT)
    env.python3(_make_site(tmp_path / "site", PIN_KLT, PIN_KLAYOUT))
    env.uv_with_site(tmp_path / "nonexistent")  # must not be consulted
    proc = env.run()
    env.assert_reached_regen(proc)
    assert "builder runtime: klayout-tools 0.4.0, klayout 0.30.12" in proc.stdout
    assert not env.uv_log.exists(), "uv fallback used although python3 was pinned"


def test_import_failure_falls_back_to_exact_uv_pins_and_passes(env: Env) -> None:
    env.klt(PIN_KLT)
    env.python3(None)  # cannot import klayout / klayout_tools
    env.uv_resolving_requested()
    proc = env.run()
    env.assert_reached_regen(proc)
    assert "falling back to pinned uv run" in proc.stdout
    args = _uv_args(env)
    assert f"klayout-tools=={PIN_KLT}" in args
    assert f"klayout=={PIN_KLAYOUT}" in args
    assert "builder runtime: klayout-tools 0.4.0, klayout 0.30.12" in proc.stdout


# --- failing configurations: must stop before any mutation -------------------


def test_pinned_cli_with_mismatched_python3_fails_before_mutation(
    env: Env, tmp_path: Path
) -> None:
    env.klt(PIN_KLT)
    env.python3(_make_site(tmp_path / "site", "0.5.0", PIN_KLAYOUT))
    env.uv_with_site(_make_site(tmp_path / "uvsite", PIN_KLT, PIN_KLAYOUT))
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "klayout-tools 0.5.0 != pinned 0.4.0" in proc.stderr
    assert "builder Python runtime (python3 on PATH" in proc.stderr
    assert not env.uv_log.exists(), "mismatch must fail, not silently switch to uv"
    env.assert_no_mutation(proc)


def test_mismatched_klayout_alone_fails(env: Env, tmp_path: Path) -> None:
    env.klt(PIN_KLT)
    env.python3(_make_site(tmp_path / "site", PIN_KLT, "0.30.13"))
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "klayout 0.30.13 != pinned 0.30.12" in proc.stderr
    env.assert_no_mutation(proc)


def test_fallback_resolving_wrong_versions_fails(env: Env, tmp_path: Path) -> None:
    """The resolved uv runtime is validated, not trusted because it was pinned."""
    env.klt(PIN_KLT)
    env.python3(None)
    env.uv_with_site(_make_site(tmp_path / "uvsite", "0.5.0", "0.30.13"))
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "uv run fallback" in proc.stderr
    assert "klayout-tools 0.5.0 != pinned 0.4.0" in proc.stderr
    assert "klayout 0.30.13 != pinned 0.30.12" in proc.stderr
    env.assert_no_mutation(proc)


def test_fallback_import_failure_fails(env: Env, tmp_path: Path) -> None:
    """Metadata present but modules not importable in the resolved runtime."""
    site = tmp_path / "uvsite"
    site.mkdir()
    for name, ver in (("klayout", PIN_KLAYOUT), ("klayout_tools", PIN_KLT)):
        di = site / f"{name}-{ver}.dist-info"
        di.mkdir()
        (di / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name.replace('_', '-')}\nVersion: {ver}\n"
        )
    env.klt(PIN_KLT)
    env.python3(None)
    env.uv_with_site(site)
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "cannot import klayout.db / klayout_tools.gen" in proc.stderr
    env.assert_no_mutation(proc)


def test_fallback_missing_packages_fails(env: Env, tmp_path: Path) -> None:
    env.klt(PIN_KLT)
    env.python3(None)
    env.uv_with_site(tmp_path / "empty")
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "klayout-tools not installed != pinned 0.4.0" in proc.stderr
    env.assert_no_mutation(proc)


def test_mismatched_cli_fails_before_mutation(env: Env, tmp_path: Path) -> None:
    env.klt("0.5.0")
    env.python3(_make_site(tmp_path / "site", PIN_KLT, PIN_KLAYOUT))
    proc = env.run()
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "klt 0.5.0 != pinned 0.4.0" in proc.stderr
    env.assert_no_mutation(proc)


def test_missing_cli_fails_with_message(env: Env, tmp_path: Path) -> None:
    env.python3(_make_site(tmp_path / "site", PIN_KLT, PIN_KLAYOUT))
    proc = env.run()  # no fake klt on PATH
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "klt unresolved != pinned 0.4.0" in proc.stderr
    env.assert_no_mutation(proc)


@pytest.mark.skipif(os.name != "posix", reason="shell fakes need POSIX sh")
def test_uv_fallback_command_shape(env: Env) -> None:
    """The fallback asks uv for the exact pins and nothing unpinned."""
    env.klt(PIN_KLT)
    env.python3(None)
    env.uv_resolving_requested()
    env.run()
    args = _uv_args(env)
    withs = [args[i + 1] for i, a in enumerate(args) if a == "--with"]
    assert sorted(withs) == sorted([f"klayout-tools=={PIN_KLT}", f"klayout=={PIN_KLAYOUT}"])
    assert args[0] == "run" and "--no-project" in args
