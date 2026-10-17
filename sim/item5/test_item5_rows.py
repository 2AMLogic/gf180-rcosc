"""Offline checks for the T1 item-5 request set (issue #185).

Synthetic-free but evidence-free: parses the committed requests and ROWS.md,
and asserts the map is complete. Runs no simulator and needs no PDK.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = HERE / "ROWS.md"
REQS = HERE / "requests"
GEN = HERE / "gen_requests.py"

# Row table lines look like "| 4 | ... |".
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")
PATH_RE = re.compile(r"`((?:\.\./startup/|requests/)[A-Za-z0-9_./*<>-]+\.json)`")


def table_rows():
    return [l for l in ROWS.read_text().splitlines() if ROW_RE.match(l)]


def test_every_ratified_row_appears_exactly_once():
    nums = [int(ROW_RE.match(l).group(1)) for l in table_rows()]
    assert sorted(nums) == list(range(1, 11))


def test_row_6_is_a_declared_gap_citing_dr_0004():
    (row6,) = [l for l in table_rows() if ROW_RE.match(l).group(1) == "6"]
    assert "DR-0004" in row6 and "declared gap" in row6


def test_statistical_rows_declare_the_monte_carlo_remainder():
    for n in ("2", "4", "5"):
        (row,) = [l for l in table_rows() if ROW_RE.match(l).group(1) == n]
        assert "Monte Carlo remainder" in row and "DR-0019" in row, n


def test_every_row_is_mapped_or_a_declared_gap():
    for l in table_rows():
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        assert cells[2] != "none" or "declared gap" in cells[4], l


def test_cited_requests_exist():
    cited = set()
    for l in table_rows():
        cited.update(PATH_RE.findall(l))
    assert cited
    for p in cited:
        if "*" in p:
            assert list((HERE / p).parent.glob(Path(p).name)), p
        else:
            assert (HERE / p).is_file(), p


def test_requests_parse_and_reference_existing_netlists():
    files = sorted(REQS.glob("request_*.json"))
    assert len(files) == 15
    for f in files:
        req = json.loads(f.read_text())
        assert (REQS / req["netlist"]).is_file(), f
        assert len(req["corners"]["process"]) == 7
        assert req["corners"]["temperature_c"] == [-40.0, 27.0, 85.0]
        assert {m["name"] for m in req["measurements"]} >= {"fosc", "iq_run_ua"}
        assert "limits" not in json.dumps(req)


def test_regeneration_is_byte_identical(tmp_path):
    subprocess.run([sys.executable, "-I", str(GEN), "--out", str(tmp_path)], check=True)
    fresh = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    committed = {p.name: p.read_bytes() for p in REQS.iterdir()}
    assert fresh == committed
