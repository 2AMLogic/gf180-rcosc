"""Offline tests for pex_pvt_sweep.py's extracted report/record helpers
(issue #353): build_summary(), write_results(), write_guardrails_csv().

Pure text; no simulator/PDK. The committed `sim/pvt-postlayout/results/`
runs are read as fixtures and never written; everything is replayed into
tmp dirs. Not evidence."""

import csv
import json
import re
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


# --------------------------- offline guardrail calibration (issue #462)
#
# The guardrail's trim search is pvt_sweep's shared bisect_trim_code; these
# drive run_guardrail_passes end-to-end with a synthetic run_point (no
# simulator, no PDK) on both sides and hand-check the full calibration
# record -- code, f_hz, saturation and the two endpoint fields -- against
# linear curves. Not evidence; no ngspice, no network, nothing written
# under sim/*/results/.

class FakeRunPoint:
    """Stands in for pex.run_point: f_hz = fn(side, code); records calls."""

    def __init__(self, fn):
        self.fn, self.calls = fn, []

    def __call__(self, side, netlist_text, point, model_dir, build_dir,
                 log_dir, runid):
        self.calls.append((side, point))
        return pex.Result(
            side=side, point=point, f_hz=self.fn(side, point.code),
            period_s=None, status="ok", log_path="log", tstop_ns=1200,
        )


def _guardrails(monkeypatch, tmp_path, curves, target_hz):
    """run_guardrail_passes against synthetic per-side f(code) curves."""
    fake = FakeRunPoint(lambda side, code: curves[side](code))
    monkeypatch.setattr(pex, "run_point", fake)
    monkeypatch.setitem(base.SPEC, "f_target_hz", target_hz)
    routed = []
    real = base.bisect_trim_code

    def spy(target, f_at):
        routed.append(target)
        return real(target, f_at)

    monkeypatch.setattr(base, "bisect_trim_code", spy)
    guard = pex.run_guardrail_passes(
        sides=[("schematic", "sch-text"), ("extracted", "pex-text")],
        model_dir=tmp_path,
        build_dir=tmp_path,
        corner_dir=tmp_path,
        runid="TEST",
        jobs=2,
        seed={},
        baseline_dir=tmp_path,  # no results.csv -> no DR-0017 cell basis
        baseline_manifest={
            "calibration_spec_target": {
                p: {"code": 1, "saturated": False} for p in pex.PEX_PROCESSES
            }
        },
    )
    return guard, fake, routed


def _linear(code):  # 10 MHz .. 265 MHz, 1 MHz/code -- same shape as the
    return 10e6 + code * 1e6  # legacy-analysis calibration fixture


def test_guardrail_calibration_routes_through_the_shared_search(
    monkeypatch, tmp_path
):
    guard, fake, routed = _guardrails(
        monkeypatch, tmp_path,
        {"schematic": _linear, "extracted": _linear}, 48e6,
    )
    # every (side, process) calibration went through pvt_sweep's shared
    # search (2 sides x 3 processes), against the patched target
    assert routed == [48e6] * 6
    assert guard["calibration_target_hz"] == 48e6
    # each (side, point) is measured at most once (run_cached) and every
    # calibration point sits at 27 C / 3.3 V (the only other measured
    # point is the Row-4 guardrail cell, checked below)
    keys = [(side, pt.key) for side, pt in fake.calls]
    assert len(keys) == len(set(keys))
    cal_points = [
        pt for _side, pt in fake.calls
        if pt.code != pex.GUARDRAIL_CODE
        or pt.temp_c != pex.GUARDRAIL_TEMP_C
    ]
    assert cal_points
    assert all(
        pt.temp_c == base.REF_TEMP_C and pt.vdd_v == base.REF_VDD_V
        for pt in cal_points
    )
    # the guardrail cell (0x80/ff/85 C/3.6 V) was measured on both sides
    assert guard["cell"]["schematic_f_hz"] == _linear(0x80)
    assert guard["cell"]["extracted_f_hz"] == _linear(0x80)


@pytest.mark.parametrize(
    "target,code,f,sat",
    [
        (9e6, 0x00, 10e6, True),      # below range
        (10e6, 0x00, 10e6, True),     # endpoint equality clamps
        (265e6, 0xFF, 265e6, True),   # endpoint equality clamps
        (266e6, 0xFF, 265e6, True),   # above range
        (48e6, 38, 48e6, False),      # exact hit
        (100.5e6, 90, 100e6, False),  # tie resolves to the lower code
        (100.6e6, 91, 101e6, False),  # nearer to the upper code
    ],
)
def test_guardrail_calibration_record_is_hand_computed(
    monkeypatch, tmp_path, target, code, f, sat
):
    guard, _fake, _routed = _guardrails(
        monkeypatch, tmp_path,
        {"schematic": _linear, "extracted": _linear}, target,
    )
    # the full record, including both endpoint fields, on both sides and
    # at every process -- hand-computed, not replayed from the code
    for side in ("schematic", "extracted"):
        for p in pex.PEX_PROCESSES:
            assert guard["calibration"][p][side] == {
                "code": code, "f_hz": f, "saturated": sat,
                "f_code0x00_hz": 10e6, "f_code0xff_hz": 265e6,
            }


def test_guardrail_calibration_tracks_each_sides_own_curve(
    monkeypatch, tmp_path
):
    # extracted side 1% slower than schematic: each record reports its own
    # side's f and realized endpoint range (48 MHz lands on code 38 for
    # both; f(38) = 0.99 * 48 MHz = 47.52 MHz on the extracted side)
    guard, _fake, _routed = _guardrails(
        monkeypatch, tmp_path,
        {"schematic": _linear,
         "extracted": lambda c: _linear(c) * 0.99},
        48e6,
    )
    sch = guard["calibration"]["tt"]["schematic"]
    ext = guard["calibration"]["tt"]["extracted"]
    assert (sch["code"], sch["f_hz"], sch["saturated"]) == (38, 48e6, False)
    assert ext["code"] == 38 and ext["saturated"] is False
    assert ext["f_hz"] == pytest.approx(47.52e6)
    assert ext["f_code0x00_hz"] == pytest.approx(9.9e6)
    assert ext["f_code0xff_hz"] == pytest.approx(262.35e6)


# --------------------------- exact rcosc_top header lookup (issue #480)
#
# The block extractor and the extracted-header reorder used to accept any
# subcircuit whose name *started* with `rcosc_top`, so a sibling like
# `rcosc_top_probe` declared ahead of the real top hijacked both lookups
# (equal pin sets let the wrong selection pass the reorder's set
# validation). One shared exact-name lookup (find_rcosc_top_header) now
# serves both callers; these regressions pin its selection rules and prove
# the rewrite is output-preserving on the committed testbench + every
# committed extracted netlist -- harness text byte-identical to the old
# prefix scans replayed verbatim below as the differential oracle.

PROBE_FIRST_DECK = """\
.subckt rcosc_top_probe b a
Rprobe b a 1k
.ends
.subckt rcosc_top b a
Rtop b a 2k
.ends
"""

PROBE_ONLY_DECK = """\
.subckt rcosc_top_probe b a
Rprobe b a 1k
.ends
"""


def test_block_extractor_selects_the_exact_top_over_a_prefixed_sibling():
    pins, block, all_lines = pex.extract_rcosc_top_block(PROBE_FIRST_DECK)
    assert pins == ["b", "a"]
    assert block == [".subckt rcosc_top b a", "Rtop b a 2k", ".ends"]
    assert len(all_lines) == 6


def test_reorder_rewrites_only_the_exact_top_header():
    reordered = pex.reorder_extracted_header(PROBE_FIRST_DECK, ["a", "b"])
    assert reordered == (
        ".subckt rcosc_top_probe b a\n"
        "Rprobe b a 1k\n"
        ".ends\n"
        ".SUBCKT rcosc_top a b\n"
        "Rtop b a 2k\n"
        ".ends\n"
    )


def test_prefixed_sibling_alone_reports_a_missing_top():
    with pytest.raises(SystemExit) as ei:
        pex.extract_rcosc_top_block(PROBE_ONLY_DECK)
    assert str(ei.value) == "ERROR: no '.subckt rcosc_top ...' header found"
    with pytest.raises(SystemExit) as ei:
        pex.reorder_extracted_header(PROBE_ONLY_DECK, ["b", "a"])
    assert str(ei.value) == (
        "ERROR: extracted netlist has no '.SUBCKT rcosc_top ...' header"
    )


def test_mixed_case_top_directive_is_matched_exactly():
    deck = (
        ".SUBCKT RCOSC_TOP_PROBE b a\n"
        "Rprobe b a 1k\n"
        ".ENDS\n"
        ".Subckt Rcosc_Top b a\n"
        "Rtop b a 2k\n"
        ".Ends\n"
    )
    pins, block, _ = pex.extract_rcosc_top_block(deck)
    assert pins == ["b", "a"]
    assert block[0] == ".Subckt Rcosc_Top b a"
    reordered_lines = pex.reorder_extracted_header(deck, ["a", "b"]).splitlines()
    assert reordered_lines[0] == ".SUBCKT RCOSC_TOP_PROBE b a"
    assert reordered_lines[3] == ".SUBCKT Rcosc_Top a b"


def test_committed_testbench_selects_the_expected_11_pin_top():
    schem = pex.PVT_TB.read_text()
    pins, block, _ = pex.extract_rcosc_top_block(schem)
    assert pins == ["vdd", "vss", "clk"] + [f"t{i}" for i in range(8)]
    assert block[0].split()[:2] == [".subckt", "rcosc_top"]


def _legacy_extract(text):
    """The pre-#480 prefix-scan block extractor, verbatim."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^\.subckt\s+(\S+)\s+(.*)$", line.strip(), re.IGNORECASE) \
                and line.strip().lower().startswith(".subckt rcosc_top"):
            start = i
            break
    if start is None:
        raise SystemExit("ERROR: no '.subckt rcosc_top ...' header found")
    pins = re.match(
        r"^\.subckt\s+(\S+)\s+(.*)$", lines[start].strip(), re.IGNORECASE
    ).group(2).split()
    end = None
    for j in range(start + 1, len(lines)):
        if re.match(r"^\.ends\b.*$", lines[j].strip(), re.IGNORECASE):
            end = j
            break
    if end is None:
        raise SystemExit("ERROR: no matching '.ends' found for '.subckt rcosc_top'")
    return pins, lines[start : end + 1], lines


def _legacy_reorder(extracted_text, pin_order):
    """The pre-#480 prefix-scan header reorder, verbatim."""
    lines = extracted_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith(".subckt rcosc_top"):
            m = re.match(r"^\.subckt\s+(\S+)\s+(.*)$", stripped, re.IGNORECASE)
            name = m.group(1)
            found_pins = m.group(2).split()
            if sorted(found_pins) != sorted(pin_order):
                raise SystemExit(
                    "ERROR: extracted netlist pin set "
                    f"{sorted(found_pins)} != schematic pin set {sorted(pin_order)}"
                )
            lines[i] = f".SUBCKT {name} " + " ".join(pin_order)
            return "\n".join(lines) + "\n"
    raise SystemExit("ERROR: extracted netlist has no '.SUBCKT rcosc_top ...' header")


def _driver_harness(extract, reorder, schem, extracted):
    """The driver's extracted-side substitution: extract the schematic top
    block, reorder the extracted header to its pin order, swap the block."""
    pins, block, _ = extract(schem)
    return schem.replace("\n".join(block), reorder(extracted, pins).rstrip("\n"), 1)


def test_committed_harness_text_is_byte_identical_to_the_prefix_scans():
    schem = pex.PVT_TB.read_text()
    pex_netlists = sorted(
        (REPO_ROOT / "sim" / "pvt-postlayout" / "results").glob(
            "**/rcosc_top.pex.spice"
        )
    )
    assert pex_netlists
    for pex_netlist in pex_netlists:
        extracted = pex_netlist.read_text()
        new = _driver_harness(
            pex.extract_rcosc_top_block, pex.reorder_extracted_header,
            schem, extracted,
        )
        old = _driver_harness(_legacy_extract, _legacy_reorder, schem, extracted)
        assert new == old, pex_netlist


def test_recentre_harness_is_byte_identical_to_the_prefix_scans(monkeypatch):
    # sim/recentre/pexlib.py's harness() reaches the same two functions;
    # its output on the committed PEX source must not change either.
    sys.path.insert(0, str(REPO_ROOT / "sim" / "recentre"))
    import pexlib  # noqa: E402  (recentre path; pulls in pex via its own shim)

    cards = pexlib.load_cards()
    new = pexlib.harness(list(cards))
    monkeypatch.setattr(pex, "extract_rcosc_top_block", _legacy_extract)
    monkeypatch.setattr(pex, "reorder_extracted_header", _legacy_reorder)
    old = pexlib.harness(list(cards))
    assert new == old
