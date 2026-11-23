"""Offline regression tests for the row-8 comparator-H screen reports."""
import json

import pytest

import row8_table as table


def write_iq_report(directory, iq):
    directory.mkdir()
    corner = {
        "process": "ff", "temperature_c": 85, "status": "pass",
        "measurements": [{"name": "iq_run", "value": iq}],
    }
    (directory / "report.json").write_text(json.dumps({"corners": [corner]}))


@pytest.mark.parametrize("held_code", [0x4F, 0xFF])
def test_held_and_full_scale_requests_keep_independent_cells(tmp_path, held_code):
    cell = ("ff", 85, 3.6)
    write_iq_report(tmp_path / "request_iq_cFF_v36", 750e-6)
    held, full_scale = table.iq_cells(tmp_path)
    assert held == {}
    assert full_scale[cell] == (0xFF, None, 750, "pass")

    write_iq_report(tmp_path / f"request_iq_ff_c{held_code:02X}_v36", 475e-6)
    held, full_scale = table.iq_cells(tmp_path)
    assert held[cell] == (held_code, None, 475, "pass")
    assert full_scale[cell] == (0xFF, None, 750, "pass")


def test_unrecognized_request_names_leave_cells_missing(tmp_path):
    variant = tmp_path / "control"
    for bench, name in (("iq", "request_iq_retry"), ("delay", "request_dly_retry_v30"),
                        ("startup", "request_v33_retry")):
        report_dir = variant / bench / name
        report_dir.mkdir(parents=True)
        (report_dir / "report.json").write_text("uncollected")

    assert table.iq_cells(variant / "iq") == ({}, {})
    assert table.delay_cells(variant / "delay") == {}
    assert table.startup_cells(tmp_path, "control") == {}
