"""Offline tests for gen_bench.py --inject-mismatch (issue #186). Pure text;
no simulator/PDK. Not evidence."""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_bench as gb  # noqa: E402

COVERED = re.compile(r"\b(ppolyf_u_1k|cap_mim_1f0fF)\b")


def _covered_cards(text):
    return [l for l in text.splitlines() if l[:1] in "xX" and COVERED.search(l)]


def test_default_benches_unchanged():
    assert gb.bench(0) == (HERE / "tb_trimsel_nomm.spice").read_text()
    assert gb.bench(1) == (HERE / "tb_trimsel_mm.spice").read_text()
    assert gb.fixed_code_bench() == (HERE / "tb_fixedcode.spice").read_text()


def test_injected_benches_have_no_bare_m1_and_full_manifest():
    dut, manifest = gb.inject(gb.DUT_TEXT)
    for text in (gb.bench(1, dut), gb.bench(0, dut), gb.fixed_code_bench(dut)):
        cards = _covered_cards(text)
        assert cards
        assert not [c for c in cards if re.search(r"\bm=1\b", c)]
    assert {m["instance"].lower() for m in manifest} == {
        c.split()[0].lower() for c in _covered_cards(gb.DUT_TEXT)}


def test_cli_flag_writes_tagged_files_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(gb, "here", tmp_path)
    gb.write_set("_inj", True)
    for stem in ("tb_trimsel_nomm", "tb_trimsel_mm", "tb_fixedcode"):
        assert (tmp_path / f"{stem}_inj.spice").exists()
        assert json.loads((tmp_path / f"{stem}_inj.spice.mismatch.json").read_text())
    req = json.loads((tmp_path / "request_smoke_mm_inj.json").read_text())
    assert req["netlist"] == "tb_trimsel_mm_inj.spice"


def test_default_run_leaves_committed_files_identical():
    r = subprocess.run(["git", "diff", "--exit-code", "--", str(HERE)], capture_output=True)
    before = r.returncode
    subprocess.run([sys.executable, "-I", str(HERE / "gen_bench.py")], check=True)
    r = subprocess.run(["git", "diff", "--exit-code", "--", str(HERE)], capture_output=True)
    assert r.returncode == before
