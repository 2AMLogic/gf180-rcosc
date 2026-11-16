"""Offline tests for pex_pvt_sweep.py's extracted report/record helpers
(issue #353): build_summary(), write_results(), write_guardrails_csv().

Pure text; no simulator/PDK. The committed `sim/pvt-postlayout/results/`
runs are read as fixtures and never written; everything is replayed into
tmp dirs. Not evidence."""

import csv
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sim" / "pvt-postlayout"))
import pex_pvt_sweep as pex  # noqa: E402  (its own shim imports sim/pvt + sim/)

import pvt_sweep as base  # noqa: E402

RUN_NO_GUARD = "20260921T164434Z"
RUN_GUARDRAILS = "20260923T152954Z"

# The only committed pex runs predate #65 (commit 555cf5e7), which added the
# `pdk_revision` manifest fields and changed pdk_provenance.display()'s PDK
# line format. Evidence is append-only, so those runs can never be
# regenerated: the replay synthesizes the post-#65 fields display() requires
# and the byte comparison excludes the single evolved PDK line. Every other
# line -- including both `--guardrails` sections -- must reproduce exactly.


def _run(runid):
    d = REPO_ROOT / "sim" / "pvt-postlayout" / "results" / runid
    assert (d / "manifest.json").is_file(), f"committed evidence missing: {d}"
    assert (d / "summary.md").is_file() and (d / "results.csv").is_file()
    return d


def _replay(runid):
    """Rebuild the exact helper inputs a committed run had, from that run's
    own committed manifest.json + results.csv (plus the post-#65 fields
    display() needs -- see the module note above)."""
    d = _run(runid)
    manifest = json.loads((d / "manifest.json").read_text())
    manifest.setdefault("pdk_revision", "0" * 40)
    manifest.setdefault("pdk_revision_source", "pre-#65 evidence replay")
    with (d / "results.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    code = manifest["trim_code"]
    points = [
        base.Point(p, t, v, code)
        for p in pex.PEX_PROCESSES
        for t in base.TEMPS_C
        for v in base.VDDS_V
    ]
    return d, manifest, rows, points


def _summary(d, manifest, rows, points, failures=None):
    return pex.build_summary(
        runid=d.name,
        manifest=manifest,
        rows=rows,
        points=points,
        guard=manifest.get("guardrails"),
        failures=failures or [],
        host_variance_pct=manifest[
            "schematic_rerun_vs_published_baseline_max_delta_pct"
        ],
        baseline_id=manifest["schematic_baseline_runid"],
        code=manifest["trim_code"],
        elapsed=manifest["wall_clock_s"],
        jobs=manifest["jobs"],
    )


@pytest.mark.parametrize("runid", [RUN_NO_GUARD, RUN_GUARDRAILS])
def test_build_summary_reproduces_committed_run(runid):
    d, manifest, rows, points = _replay(runid)
    rebuilt = _summary(d, manifest, rows, points) + "\n"
    committed = (d / "summary.md").read_text()
    # Exclude the one line whose format #65 evolved after the run (see the
    # module note); everything else must be byte-identical.
    strip_pdk = lambda text: [l for l in text.splitlines() if not l.startswith("| PDK | ")]  # noqa: E731
    committed_lines, rebuilt_lines = strip_pdk(committed), strip_pdk(rebuilt)
    assert len(committed_lines) == len(committed.splitlines()) - 1
    assert committed_lines == rebuilt_lines


def test_write_results_reproduces_committed_csv(tmp_path):
    d, _manifest, rows, _points = _replay(RUN_GUARDRAILS)
    out = pex.write_results(rows, tmp_path)
    assert out.read_bytes() == (d / "results.csv").read_bytes()


def test_write_guardrails_csv_reproduces_committed_csv(tmp_path):
    d, manifest, _rows, _points = _replay(RUN_GUARDRAILS)
    out = pex.write_guardrails_csv(manifest["guardrails"], tmp_path)
    assert out is not None
    assert out.read_bytes() == (d / "guardrails.csv").read_bytes()


def test_write_guardrails_csv_is_a_noop_without_guard(tmp_path):
    assert pex.write_guardrails_csv(None, tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_result_rows_delta_and_status_fields():
    pt = base.Point("tt", 27.0, 3.3, 0xC0)

    def res(side, f_hz, status="ok"):
        return pex.Result(
            side=side,
            point=pt,
            f_hz=f_hz,
            period_s=None,
            status=status,
            log_path="log",
            tstop_ns=1200,
        )

    results = {
        ("schematic", pt): res("schematic", 48.0e6),
        ("extracted", pt): res("extracted", 48.48e6),
    }
    row = pex.result_rows(results, [pt])[0]
    assert row["delta_pct"] == "1.0000"
    assert row["trim_hex"] == "0xC0"
    assert row["schematic_f_hz"] == "4.800000e+07"

    results[("schematic", pt)] = res("schematic", None, status="no_damage")
    row = pex.result_rows(results, [pt])[0]
    assert row["schematic_f_hz"] == "" and row["delta_pct"] == ""
    assert row["schematic_status"] == "no_damage"


def test_build_summary_reports_failed_runs():
    d, manifest, rows, points = _replay(RUN_NO_GUARD)
    manifest = dict(manifest)
    pt = base.Point("tt", 27.0, 3.3, manifest["trim_code"])
    manifest["failed_runs"] = [f"schematic_{pt.key}"]
    failures = [
        pex.Result(
            side="schematic",
            point=pt,
            f_hz=None,
            period_s=None,
            status="no_damage",
            log_path="log",
            tstop_ns=1200,
        )
    ]
    text = _summary(d, manifest, rows, points, failures=failures)
    assert "| failed runs | 1 |" in text
    assert "## Failed runs" in text
    assert f"- `schematic_{pt.key}`: no_damage" in text
