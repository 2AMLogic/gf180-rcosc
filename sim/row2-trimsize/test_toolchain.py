"""Offline tests for the row2-trimsize toolchain (issue #460).  Every curve
here is a SYNTHETIC FIXTURE built in this file; nothing is measured evidence
and no simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/row2-trimsize/test_toolchain.py
"""
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit_weights as fw  # noqa: E402
import variant  # noqa: E402

SRC = fw.REPO / "sim" / "cmph-fix" / "rcosc_top_p3_cmphfix.spice"
NAME = "s30.87078-0.18093-0.45059-0.97650-2.08666-4.29269-8.85515-19.14635-44.82498"

BENCH_DIR_CLIS = [
    ("gen_screen.py", ["--sizing", "s30.8-0.18-0.36-0.72-1.44-2.88-5.76-11.52-23.04"]),
    ("gen_full.py", ["--sizing", "ctrl"]),
]


def _run_cli(script: str, out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(HERE / script), "--out", str(out), *extra],
        capture_output=True, text=True, timeout=30)


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def ladder_lines(text: str) -> dict[str, str]:
    return {m.group(1): m.group(0) for m in
            (variant.LINE.match(l) for l in text.split("\n")) if m}


def test_ctrl_identity() -> None:
    text = SRC.read_text()
    assert variant.build(text, "ctrl") == text


def test_sizing_edits_exactly_the_nine_ladder_lengths() -> None:
    text = SRC.read_text()
    out = variant.build(text, NAME)
    before, after = ladder_lines(text), ladder_lines(out)
    assert sorted(before) == sorted(after) == [f"X${i}" for i in range(91, 100)]
    lengths = [float(v) for v in NAME[1:].split("-")]
    for i, inst in enumerate(f"X${91 + i}" for i in range(9)):
        assert re.search(rf"r_length={lengths[i]:.5f}U ", after[inst]), inst
        assert before[inst] != after[inst]
    # nothing outside the nine ladder lines moves
    n_changed = sum(1 for a, b in zip(text.split("\n"), out.split("\n")) if a != b)
    assert n_changed == 9


def test_rejects_unknown_and_nonpositive_names() -> None:
    text = SRC.read_text()
    with pytest.raises(ValueError):
        variant.build(text, "w3r65")            # row-4 name, not a sizing
    with pytest.raises(ValueError):
        variant.build(text, "s1-0-1-1-1-1-1-1-1")  # zero-length segment


def test_w2_applies_the_row45_switch_doubling_on_top() -> None:
    text = SRC.read_text()
    plain = variant.build(text, NAME)
    doubled = variant.build(text, NAME + "w2")
    assert doubled != plain
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "variant317", fw.REPO / "sim" / "row45-rerun" / "variant.py")
    v317 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v317)
    assert doubled == v317.double_bank_switches(plain, 2.0)
    assert variant.sw_mult(NAME) == 1.0
    assert variant.sw_mult(NAME + "w2") == 2.0


def test_solve_ls_recovers_an_exact_system() -> None:
    rows = [[1.0, 0.0, 2.0], [1.0, 1.0, 3.0], [1.0, 2.0, 5.0], [1.0, 0.5, 2.5]]
    x = [0.25, -1.5, 0.75]
    y = [sum(r[i] * x[i] for i in range(3)) for r in rows]
    assert fw.solve_ls(rows, y) == pytest.approx(x)


def test_fit_curve_on_a_binary_exact_synthetic() -> None:
    # T(c) = 20 ns + (2^-b weights): a binary-exact bank has rho_b == 1 and
    # every adjacent step positive.
    W = 20.0  # ps, unit period step
    beta = [-W * (2 ** b) for b in range(8)]
    f = [1.0 / (20000.0 + sum(((c >> b) & 1) * beta[b] for b in range(8)))
         for c in range(256)]
    ft = fw.fit_curve(f)
    assert ft["rho"] == pytest.approx([1.0] * 8)
    assert ft["nonpositive_steps"] == 0
    assert all(v["step_pct"] > 0 for v in ft["carries"].values())
    # a period-linear bit-weight deficit at the carry reproduces DR-0021's sign
    beta[7] *= 0.80
    f2 = [1.0 / (20000.0 + sum(((c >> b) & 1) * beta[b] for b in range(8)))
          for c in range(256)]
    ft2 = fw.fit_curve(f2)
    assert ft2["carries"]["0x7F->0x80"]["step_pct"] < 0
    # rho is normalised to the bank's own W = sum|beta|/255, so shrinking
    # bit 7 by 0.80 also shrinks W: rho_7 = 0.8*2^7*255/(sum - 0.2*2^7*W)
    rho7 = 0.8 * 255 / (255 - 0.2 * 128)
    assert ft2["rho"][7] == pytest.approx(rho7, rel=1e-6)


def test_sizing_from_floors_low_segments_and_keeps_ratio_rule() -> None:
    # minimal fit.json: one compensation curve with beta twice the drawn share
    # for bit 0 (rho_0 = 2) and binary-exact elsewhere.
    r_drawn = [fw.drawn_r(L) for L in fw.SEG_LEN_UM]
    beta = [-2000.0 * (2 ** b) for b in range(8)]
    beta[0] = -2 * 2000.0
    doc = {"drawn": {"seg_r_ohm": r_drawn, "r_head_ohm": fw.R_HEAD,
                     "r_per_um": fw.R_PER_UM},
           "curves": {"c": {"beta_s": beta}},
           "proposals": {"P": {"W_s": 2000.0, "rfix_len_um": 30.0,
                               "seg_len_um": [1.0] * 8}}}
    import gen_screen
    p = Path("fit.json")
    p.write_text(json.dumps(doc))
    try:
        name = gen_screen.sizing_from(p, "P", "c")
    finally:
        p.unlink()
    vals = [float(v) for v in name[1:].split("-")]
    assert len(vals) == 9
    # name = s<RFIX>-<r0>-...-<r7>: RFIX passes through, bit 0 halved, rest unchanged
    assert vals[0] == 30.0
    assert vals[1] == pytest.approx((r_drawn[0] / 2 - fw.R_HEAD) / fw.R_PER_UM, abs=2e-5)
    for b in range(1, 8):
        assert vals[1 + b] == pytest.approx(fw.SEG_LEN_UM[b], abs=2e-5)
    # a sub-floor ratio rule result is floored at L_MIN_UM
    doc["curves"]["c"]["beta_s"][0] = -8 * 2000.0
    p.write_text(json.dumps(doc))
    try:
        assert float(gen_screen.sizing_from(p, "P", "c").split("-")[1]) == gen_screen.L_MIN_UM
    finally:
        p.unlink()


@pytest.mark.parametrize("writer,contender,extra,precreated", [
    ("gen_full", "gen_full.py", ["--sizing", NAME], False),
    ("gen_screen", "gen_screen.py", ["--sizing", NAME, "--corner", "ss:-40:3.0"], True),
    ("gen_screen", "../trim-dense/prepare.py", ["--extracted-netlist", str(SRC)], False),
])
def test_only_one_generator_can_write_a_bench(tmp_path, monkeypatch, writer, contender,
                                              extra, precreated) -> None:
    out = tmp_path / "bench"
    if precreated:
        out.mkdir()
    generator = importlib.import_module(writer)
    sizing = "ctrl" if writer == "gen_full" else NAME
    monkeypatch.setattr(sys, "argv", [writer, "--out", str(out), "--sizing", sizing])

    # Run a second process after the first claimed the bench but just before
    # its first corner directory exists. The two runs use disjoint requests.
    mkdir = Path.mkdir
    attempts = []

    def mkdir_with_contender(path, *args, **kwargs):
        if path == out / "ctrl" / "tt_27C_3p3V" and not attempts:
            attempts.append(_run_cli(contender, out, *extra))
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir_with_contender)
    assert generator.main() == 0
    [loser] = attempts
    assert loser.returncode == 1, loser
    assert "not empty" in loser.stderr
    requests = json.loads((out / "provenance.json").read_text())["requests"]
    assert sorted(entry["request"] for entry in requests) == sorted(
        path.relative_to(out).as_posix() for path in out.rglob("request_*.json"))


def test_failed_generation_releases_an_empty_bench(tmp_path) -> None:
    out = tmp_path / "bench"
    failed = _run_cli("gen_screen.py", out, "--sizing", NAME, "--corner", "unknown:27:3.3")
    assert failed.returncode != 0 and "unknown process" in failed.stderr
    assert list(out.iterdir()) == []
    retry = _run_cli("gen_screen.py", out, "--sizing", NAME)
    assert retry.returncode == 0, retry.stderr


@pytest.mark.parametrize("script,extra", BENCH_DIR_CLIS)
def test_cli_accepts_a_precreated_empty_bench_dir(tmp_path, script, extra) -> None:
    # the advertised "NEW (or empty)" --out: a mktemp -d destination (issue #500)
    fresh, empty = tmp_path / "fresh", tmp_path / "empty"
    empty.mkdir()
    for out in (fresh, empty):
        r = _run_cli(script, out, *extra)
        assert r.returncode == 0, r.stderr
    assert _tree(fresh) == _tree(empty)


@pytest.mark.parametrize("script,extra", BENCH_DIR_CLIS)
def test_cli_refuses_an_occupied_bench_dir_and_preserves_its_sentinel(
        tmp_path, script, extra) -> None:
    out = tmp_path / "occupied"
    out.mkdir()
    (out / "sentinel").write_bytes(b"bench-data-do-not-touch")
    r = _run_cli(script, out, *extra)
    assert r.returncode != 0
    assert "not empty" in r.stderr
    assert [p.name for p in out.iterdir()] == ["sentinel"]
    assert (out / "sentinel").read_bytes() == b"bench-data-do-not-touch"
