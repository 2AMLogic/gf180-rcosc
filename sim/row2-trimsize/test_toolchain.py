"""Offline tests for the row2-trimsize toolchain (issue #460).  Every curve
here is a SYNTHETIC FIXTURE built in this file; nothing is measured evidence
and no simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/row2-trimsize/test_toolchain.py
"""
import errno
import hashlib
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
import run_set  # noqa: E402
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


def _write_bench(bench: Path, tree: dict[tuple[str, str], list[str]]) -> dict[str, dict]:
    """Build a synthetic <bench>/<variant>/<corner>/{tb_<stem>.spice, request_<stem>.json}
    tree with repeated basenames across variants and corners."""
    meta: dict[str, dict] = {}
    idx = 0
    for (var, corner), stems in tree.items():
        d = bench / var / corner
        d.mkdir(parents=True, exist_ok=True)
        for stem in stems:
            idx += 1
            tb_name = f"tb_{stem}.spice"
            tb_path = d / tb_name
            tb_bytes = f"* synthetic fixture {var}/{corner}/{stem}\n.end\n".encode()
            tb_path.write_bytes(tb_bytes)
            req_path = d / f"request_{stem}.json"
            req_path.write_text(json.dumps({
                "netlist": tb_name,
                "engine": "ngspice",
                "backend": "batch",
                "corners": {"process": [{"name": corner}], "temperature_c": [27.0]},
            }, indent=2) + "\n")
            tag = f"{var}_{corner}_{stem}"
            meta[tag] = {
                "tag": tag,
                "variant": var,
                "corner": corner,
                "stem": stem,
                "req_path": req_path,
                "tb_path": tb_path,
                "netlist_sha256": hashlib.sha256(tb_bytes).hexdigest(),
                "fosc_hz": 40_000_000.0 + idx * 125_000.0,
            }
    return meta


def _install_fake_klt(monkeypatch: pytest.MonkeyPatch, meta: dict[str, dict]) -> list[dict]:
    """Install a recording fake `klt sim --batch-set` on subprocess.run.

    Models klayout-tools==0.9.0's basename staging (#7180): if one batch-set
    invocation receives multiple requests whose netlists share a basename, the
    staged netlist collides, so any straddling batch produces mismatched member
    reports just as the 0.9.0 client did.
    """
    by_req = {m["req_path"].resolve(): m for m in meta.values()}
    calls: list[dict] = []

    def fake_run(cmd, *args, **kwargs):
        cmd = list(cmd)
        sim_i = cmd.index("sim")
        assert cmd[sim_i + 1] == "--batch-set"
        mif_i = cmd.index("--max-in-flight")
        out_i = cmd.index("-o")
        req_paths = [Path(s) for s in cmd[sim_i + 2:mif_i]]
        gdir = Path(cmd[out_i + 1])
        calls.append({
            "klt": cmd[:sim_i],
            "requests": req_paths,
            "gdir": gdir,
            "cmd": cmd,
        })
        # Stage netlists by basename (reproduces 0.9.0's #7180 cross-wiring when basenames collide).
        staged_tb: dict[str, dict] = {}
        for rp in req_paths:
            m = by_req[rp.resolve()]
            staged_tb[m["tb_path"].name] = m
        env_reqs = []
        for rp in req_paths:
            req_m = by_req[rp.resolve()]
            sim_m = staged_tb[req_m["tb_path"].name]
            rpath = gdir / rp.stem / "report.json"
            rpath.parent.mkdir(parents=True, exist_ok=True)
            req_doc = json.loads(rp.read_text())
            req_with_wait = {
                **req_doc,
                "batch": {**(req_doc.get("batch") or {}), "capacity_wait_s": float(run_set.CAPACITY_WAIT_S)},
            }
            rec_sha = hashlib.sha256(
                json.dumps(req_with_wait, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            (gdir / rp.stem / "batch-receipt.json").write_text(json.dumps({
                "job_id": f"klt-sim-fake-{req_m['tag']}",
                "request_sha256": rec_sha,
                "state": "done",
            }, indent=2, sort_keys=True) + "\n")
            rep = {
                "synthetic": True,
                "status": "pass",
                "measured_tag": sim_m["tag"],
                "measurements": [{"name": "fosc", "worst_case": {"value": sim_m["fosc_hz"]}}],
                "environment": {"netlist_sha256": sim_m["netlist_sha256"]},
            }
            rpath.write_text(json.dumps(rep) + "\n")
            env_reqs.append({"request": str(rp), "state": "done", "report": str(rpath)})
        stdout = "batch-set progress line\n" + json.dumps({"requests": env_reqs}) + "\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(run_set.subprocess, "run", fake_run)
    return calls


def _run_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["run_set.py", *args])
    return run_set.main()


def test_run_set_chunks_per_variant_and_corner_and_keeps_ledger_tags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bench = tmp_path / "bench"
    meta = _write_bench(bench, {
        ("A", "ff"): ["c00", "c01", "c02"],
        ("A", "tt"): ["c00", "c01", "c02"],
        ("B", "tt"): ["c00", "c01", "c02"],
    })
    calls = _install_fake_klt(monkeypatch, meta)

    # --group 2 on 3 requests per (variant, corner) must leave a 1-member partial
    # chunk in each directory ([2, 1, 2, 1, 2, 1]) rather than straddling dirs.
    out = tmp_path / "out_g2"
    rc = _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out), "--group", "2")
    assert rc == 0
    assert [len(c["requests"]) for c in calls] == [2, 1, 2, 1, 2, 1]
    for c in calls:
        assert c["klt"] == run_set.DEFAULT_KLT
        assert "--wait-for-capacity" in c["cmd"]
        parents = {(p.parent.parent.name, p.parent.name) for p in c["requests"]}
        assert len(parents) == 1
        var, corner = next(iter(parents))
        assert c["gdir"] == out / "jobs" / var / corner
        assert len({p.name for p in c["requests"]}) == len(c["requests"])

    ledger_rows = [json.loads(line) for line in (out / "ledger.jsonl").read_text().splitlines()]
    assert [r["tag"] for r in ledger_rows] == sorted(meta)
    for row in ledger_rows:
        m = meta[row["tag"]]
        assert row["report"] == f"reports/report_{m['tag']}.json"
        assert Path(row["report_rel"]) == out / "jobs" / m["variant"] / m["corner"] / f"request_{m['stem']}" / "report.json"
        assert (out / "jobs" / m["variant"] / m["corner"] / f"request_{m['stem']}" / "report.json").is_file()
        copied = json.loads((out / row["report"]).read_text())
        assert copied["measured_tag"] == m["tag"]
        assert copied["environment"]["netlist_sha256"] == m["netlist_sha256"]
        assert copied["measurements"][0]["worst_case"]["value"] == m["fosc_hz"]

    # Default --group (64) also keeps each (variant, corner) in its own batch ([3, 3, 3]).
    calls.clear()
    out_def = tmp_path / "out_default"
    assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_def)) == 0
    assert [len(c["requests"]) for c in calls] == [3, 3, 3]
    assert [(c["gdir"].parent.name, c["gdir"].name) for c in calls] == [("A", "ff"), ("A", "tt"), ("B", "tt")]


def test_run_set_variant_filter_resume_skip_and_single_corner_salvage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bench = tmp_path / "bench"
    meta = _write_bench(bench, {
        ("A", "ff"): ["c00", "c01", "c02"],
        ("A", "tt"): ["c00", "c01", "c02"],
        ("B", "tt"): ["c00", "c01", "c02"],
    })
    calls = _install_fake_klt(monkeypatch, meta)
    out = tmp_path / "out"

    # Existing tagged report must trigger resume skip (neither salvaged over nor resubmitted).
    existing_doc = {"synthetic": True, "status": "pass", "measured_tag": "preexisting_A_ff_c00"}
    (out / "reports").mkdir(parents=True)
    (out / "reports" / "report_A_ff_c00.json").write_text(json.dumps(existing_doc) + "\n")
    stale_job = out / "jobs" / "A" / "ff" / "request_c00" / "report.json"
    stale_job.parent.mkdir(parents=True)
    stale_job.write_text(json.dumps({"synthetic": True, "status": "pass", "measured_tag": "should_not_overwrite"}) + "\n")

    # Interrupted finished member for ONE corner only (A/ff/c01); A/tt/c01 has no job report.
    salvaged_doc = {
        "synthetic": True,
        "status": "pass",
        "measured_tag": "salvaged_A_ff_c01",
        "measurements": [{"name": "fosc", "worst_case": {"value": meta["A_ff_c01"]["fosc_hz"]}}],
    }
    ff_c01_job = out / "jobs" / "A" / "ff" / "request_c01" / "report.json"
    ff_c01_job.parent.mkdir(parents=True)
    ff_c01_job.write_text(json.dumps(salvaged_doc) + "\n")

    rc = _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out), "--variant", "A", "--group", "2")
    assert rc == 0

    # A/ff had only c02 left to submit ([1]); A/tt had all 3 eligible ([2, 1]); B/tt excluded.
    assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
        ["A/ff/request_c02.json"],
        ["A/tt/request_c00.json", "A/tt/request_c01.json"],
        ["A/tt/request_c02.json"],
    ]
    assert json.loads((out / "reports" / "report_A_ff_c00.json").read_text())["measured_tag"] == "preexisting_A_ff_c00"
    assert json.loads((out / "reports" / "report_A_ff_c01.json").read_text())["measured_tag"] == "salvaged_A_ff_c01"
    assert json.loads((out / "reports" / "report_A_tt_c01.json").read_text())["measured_tag"] == "A_tt_c01"
    assert not any((out / "reports").glob("report_B_*.json"))
    ledger_tags = [json.loads(line)["tag"] for line in (out / "ledger.jsonl").read_text().splitlines()]
    assert ledger_tags == ["A_ff_c02", "A_tt_c00", "A_tt_c01", "A_tt_c02"]


def test_run_set_ambiguous_legacy_job_path_and_defensive_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Case 1: multi-corner variant A with a legacy variant-only jobs/A/request_c00/report.json.
    bench = tmp_path / "bench"
    meta = _write_bench(bench, {
        ("A", "ff"): ["c00"],
        ("A", "tt"): ["c00"],
        ("B", "tt"): ["c00"],
    })
    calls = _install_fake_klt(monkeypatch, meta)
    out = tmp_path / "out_legacy_multi"
    legacy = out / "jobs" / "A" / "request_c00" / "report.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"synthetic": True, "status": "pass", "measured_tag": "ambiguous_legacy"}) + "\n")

    assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out), "--variant", "A") == 0
    assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
        ["A/ff/request_c00.json"],
        ["A/tt/request_c00.json"],
    ]
    assert json.loads((out / "reports" / "report_A_ff_c00.json").read_text())["measured_tag"] == "A_ff_c00"
    assert json.loads((out / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"

    # Case 2: single-corner variant A with --variant A; a legacy variant-only report could come
    # from a straddling (A, B) batch, so unverified, mismatched, or non-unique netlist_sha256 stays pending.
    bench_single = tmp_path / "bench_single"
    meta_single = _write_bench(bench_single, {("A", "tt"): ["c00"], ("B", "tt"): ["c00"]})
    calls_single = _install_fake_klt(monkeypatch, meta_single)
    for label, legacy_doc in (
        ("unverified", {"synthetic": True, "status": "pass", "measured_tag": "legacy_no_sha"}),
        ("crosswired", {"synthetic": True, "status": "pass", "measured_tag": "B_tt_c00",
                        "environment": {"netlist_sha256": meta_single["B_tt_c00"]["netlist_sha256"]}}),
    ):
        out_s = tmp_path / f"out_{label}"
        leg = out_s / "jobs" / "A" / "request_c00" / "report.json"
        leg.parent.mkdir(parents=True)
        leg.write_text(json.dumps(legacy_doc) + "\n")
        calls_single.clear()
        assert _run_main(monkeypatch, "--bench-dir", str(bench_single), "--out-dir", str(out_s), "--variant", "A") == 0
        assert len(calls_single) == 1
        assert not (out_s / "reports" / "report_B_tt_c00.json").exists()
        assert json.loads((out_s / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"

    # Shared netlist bytes across A/tt and B/tt (e.g. .include-only benches) remain ambiguous
    # without netlist.path even when --variant A selects only one variant.
    shared_bytes = b"* shared wrapper tb\n.include \"dut.spice\"\n.end\n"
    shared_sha = hashlib.sha256(shared_bytes).hexdigest()
    meta_single["A_tt_c00"]["tb_path"].write_bytes(shared_bytes)
    meta_single["B_tt_c00"]["tb_path"].write_bytes(shared_bytes)
    meta_single["A_tt_c00"]["netlist_sha256"] = shared_sha
    meta_single["B_tt_c00"]["netlist_sha256"] = shared_sha
    out_shared = tmp_path / "out_shared_sha"
    leg_sh = out_shared / "jobs" / "A" / "request_c00" / "report.json"
    leg_sh.parent.mkdir(parents=True)
    leg_sh.write_text(json.dumps({
        "synthetic": True,
        "status": "pass",
        "measured_tag": "ambiguous_shared_sha",
        "environment": {"netlist_sha256": shared_sha},
    }) + "\n")
    calls_single.clear()
    assert _run_main(monkeypatch, "--bench-dir", str(bench_single), "--out-dir", str(out_shared), "--variant", "A") == 0
    assert len(calls_single) == 1
    assert json.loads((out_shared / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"

    # A straddling batch filed A/ff under B with a suffixed stem. A second
    # report's SHA identifies A/tt but its netlist path contradicts that SHA.
    calls = _install_fake_klt(monkeypatch, meta)
    out_verified = tmp_path / "out_verified_legacy"
    leg_v = out_verified / "jobs" / "B" / "request_c00-57" / "report.json"
    leg_v.parent.mkdir(parents=True)
    leg_v.write_text(json.dumps({
        "synthetic": True,
        "status": "pass",
        "measured_tag": "verified_legacy_A_ff_c00",
        "environment": {"netlist_sha256": meta["A_ff_c00"]["netlist_sha256"]},
    }) + "\n")
    conflicting = out_verified / "jobs" / "B" / "request_c00" / "report.json"
    conflicting.parent.mkdir(parents=True)
    conflicting.write_text(json.dumps({
        "status": "pass",
        "environment": {"netlist_sha256": meta["A_tt_c00"]["netlist_sha256"]},
        "netlist": {"path": str(meta["B_tt_c00"]["tb_path"])},
    }))
    assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_verified), "--variant", "A") == 0
    assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
        ["A/tt/request_c00.json"],
    ]
    assert json.loads((out_verified / "reports" / "report_A_ff_c00.json").read_text())["measured_tag"] == "verified_legacy_A_ff_c00"
    assert json.loads((out_verified / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"

    # Defensive guard on run_group() and klt 0.9.0 / #7180 documentation check.
    mixed = [
        ("A_ff_c00", "A", meta["A_ff_c00"]["req_path"]),
        ("A_tt_c00", "A", meta["A_tt_c00"]["req_path"]),
    ]
    with pytest.raises(ValueError, match="single"):
        run_set.run_group(run_set.DEFAULT_KLT, mixed, tmp_path / "out_err", 8)
    same_dir_colliding = tmp_path / "bench_collide" / "A" / "tt"
    (same_dir_colliding / "s1").mkdir(parents=True)
    (same_dir_colliding / "s2").mkdir(parents=True)
    (same_dir_colliding / "s1" / "tb.spice").write_text("* s1\n.end\n")
    (same_dir_colliding / "s2" / "tb.spice").write_text("* s2\n.end\n")
    r_s1 = same_dir_colliding / "request_s1.json"
    r_s2 = same_dir_colliding / "request_s2.json"
    r_s1.write_text(json.dumps({"netlist": "s1/tb.spice"}) + "\n")
    r_s2.write_text(json.dumps({"netlist": "s2/tb.spice"}) + "\n")
    with pytest.raises(ValueError, match="sharing basename"):
        run_set.run_group(
            run_set.DEFAULT_KLT,
            [("A_tt_s1", "A", r_s1), ("A_tt_s2", "A", r_s2)],
            tmp_path / "out_err2",
            8,
        )
    assert "klayout-tools==0.9.0" in run_set.DEFAULT_KLT
    assert "klayout-tools==0.9.0" in (run_set.__doc__ or "")
    assert "2AMLogic/klayout-tools#7180" in (run_set.__doc__ or "")


def test_interrupted_legacy_report_copy_can_be_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bench = tmp_path / "bench"
    meta = _write_bench(bench, {("A", "tt"): ["c00"]})
    reqs = run_set.find_requests(bench, None)
    out = tmp_path / "out"
    jobs = out / "jobs"
    src = jobs / "B" / "request_c00-57" / "report.json"
    src.parent.mkdir(parents=True)
    src.write_text(json.dumps({
        "status": "pass",
        "environment": {"netlist_sha256": meta["A_tt_c00"]["netlist_sha256"]},
    }))
    dst = out / "reports" / "report_A_tt_c00.json"
    write_bytes = Path.write_bytes

    def partial_write(path: Path, data: bytes) -> int:
        write_bytes(path, data[:1])
        raise OSError("interrupted copy")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", partial_write)
        with pytest.raises(OSError, match="interrupted copy"):
            run_set.salvage(jobs, out, reqs, bench)
    assert not dst.exists()
    assert run_set.salvage(jobs, out, reqs, bench) == 1
    assert dst.read_bytes() == src.read_bytes()


def test_partial_fresh_report_write_is_signalled_and_recovered_on_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A fresh submission whose tagged-report copy dies after the first byte
    # must not publish the tagged filename, must record copy_error, and must
    # exit 2; the rerun then recovers the intact job report through
    # salvage() without resubmitting the member (issue #498).
    bench = tmp_path / "bench"
    meta = _write_bench(bench, {("A", "tt"): ["c00"]})
    calls = _install_fake_klt(monkeypatch, meta)
    out = tmp_path / "out"
    dst = out / "reports" / "report_A_tt_c00.json"
    src = out / "jobs" / "A" / "tt" / "request_c00" / "report.json"
    reports_dir = out / "reports"
    write_bytes, write_text = Path.write_bytes, Path.write_text
    fired: list[Path] = []

    def _in_reports(path: Path) -> bool:
        return reports_dir.resolve() in path.resolve().parents

    def partial_bytes(path: Path, data: bytes) -> int:
        if not _in_reports(path):
            return write_bytes(path, data)
        fired.append(path)
        write_bytes(path, data[:1])
        raise OSError(errno.ENOSPC, "No space left on device")

    def partial_text(path: Path, text: str, **kwargs) -> int:
        if not _in_reports(path):
            return write_text(path, text, **kwargs)
        fired.append(path)
        write_text(path, text[:1])
        raise OSError(errno.ENOSPC, "No space left on device")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", partial_bytes)
        patch.setattr(Path, "write_text", partial_text)
        capsys.readouterr()
        rc1 = _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out))
    out1 = capsys.readouterr().out
    assert len(calls) == 1
    assert len(fired) == 1
    assert rc1 == 2
    assert "0/1 reports written" in out1
    assert "1 requests still without a report" in out1
    assert not dst.exists()
    job_bytes = src.read_bytes()
    assert json.loads(job_bytes)["measured_tag"] == "A_tt_c00"
    rows = [json.loads(line) for line in (out / "ledger.jsonl").read_text().splitlines()]
    assert [r["tag"] for r in rows] == ["A_tt_c00"]
    assert "copy_error" in rows[0]
    assert "report" not in rows[0]

    capsys.readouterr()
    rc2 = _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out))
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert "salvaged 1 finished member reports" in out2
    assert "1 requests, 1 already reported, 0 to run" in out2
    assert dst.read_bytes() == job_bytes
    assert len(calls) == 1
    rows = [json.loads(line) for line in (out / "ledger.jsonl").read_text().splitlines()]
    assert len(rows) == 1


def test_salvage_recovers_committed_screen_reports_with_090_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    screen = fw.REPO / "sim" / "row2-trimsize" / "results" / "20261122T0550Z-screen"
    ctrl_req = screen / "bench" / "ctrl" / "tt_27C_3p3V" / "request_c00.json"
    ctrl_job = screen / "jobs" / "ctrl" / "request_c00"
    raw_req_sha = hashlib.sha256(ctrl_req.read_bytes()).hexdigest()
    receipt_sha = json.loads((ctrl_job / "batch-receipt.json").read_text())["request_sha256"]
    assert raw_req_sha.startswith("6dcb73e2")
    assert receipt_sha.startswith("46c6059e")
    assert raw_req_sha != receipt_sha

    # Replay committed screen jobs read-only into an empty temp output directory.
    out_all = tmp_path / "out_screen"
    reqs = run_set.find_requests(screen / "bench", None)
    n_salv = run_set.salvage(screen / "jobs", out_all, reqs, screen / "bench")
    assert n_salv == len(reqs) == 342
    for tag, _, _ in reqs:
        name = f"report_{tag}.json"
        assert (out_all / "reports" / name).read_bytes() == (screen / "reports" / name).read_bytes(), tag

    # Also exercise run_set.py --dry-run with the committed ctrl c00 report + receipt.
    out_ctrl = tmp_path / "out_ctrl_dry"
    dst_job = out_ctrl / "jobs" / "ctrl" / "request_c00"
    dst_job.mkdir(parents=True)
    (dst_job / "report.json").write_text((ctrl_job / "report.json").read_text())
    (dst_job / "batch-receipt.json").write_text((ctrl_job / "batch-receipt.json").read_text())
    capsys.readouterr()
    assert _run_main(
        monkeypatch,
        "--bench-dir", str(screen / "bench"),
        "--out-dir", str(out_ctrl),
        "--variant", "ctrl",
        "--dry-run",
    ) == 0
    stdout = capsys.readouterr().out
    assert "salvaged 1 finished member reports" in stdout
    assert "57 requests, 1 already reported, 56 to run" in stdout
    assert (out_ctrl / "reports" / "report_ctrl_tt_27C_3p3V_c00.json").read_text() == (
        ctrl_job / "report.json"
    ).read_text()


def test_salvage_shared_netlist_path_requires_unique_request_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_sim = tmp_path / "repo"
    (repo_sim / ".git").mkdir(parents=True)
    bench = repo_sim / "bench"
    bench.mkdir(parents=True)
    common_tb = bench / "common.spice"
    common_bytes = b"* shared netlist across process corners\n.end\n"
    common_tb.write_bytes(common_bytes)
    common_sha = hashlib.sha256(common_bytes).hexdigest()

    meta: dict[str, dict] = {}
    for idx, (var, corner, proc, temp_c) in enumerate((
        ("A", "ff", "ff", 85.0),
        ("A", "tt", "tt", 27.0),
        ("B", "tt", "tt", 27.0),
    ), 1):
        d = bench / var / corner
        d.mkdir(parents=True, exist_ok=True)
        req_path = d / "request_c00.json"
        req_path.write_text(json.dumps({
            "netlist": "../../common.spice",
            "engine": "ngspice",
            "backend": "batch",
            "corners": {"process": [{"name": proc}], "temperature_c": [temp_c]},
        }, indent=2) + "\n")
        tag = f"{var}_{corner}_c00"
        meta[tag] = {
            "tag": tag,
            "variant": var,
            "corner": corner,
            "stem": "c00",
            "req_path": req_path,
            "tb_path": common_tb,
            "netlist_sha256": common_sha,
            "fosc_hz": 45_000_000.0 + idx * 100_000.0,
        }

    for mode, net_path_str in (
        ("abs", str(common_tb.resolve())),
        ("rel", common_tb.relative_to(repo_sim).as_posix()),
    ):
        shared_report = {
            "synthetic": True,
            "status": "pass",
            "measured_tag": "ambiguous_shared_path",
            "netlist": {"path": net_path_str, "scope": "repo"},
            "environment": {"netlist_sha256": common_sha},
        }
        # Full bench --dry-run (no receipt): both A/ff and A/tt stay pending.
        out_all = tmp_path / f"out_all_{mode}"
        leg_all = out_all / "jobs" / "A" / "request_c00" / "report.json"
        leg_all.parent.mkdir(parents=True)
        leg_all.write_text(json.dumps(shared_report) + "\n")
        capsys.readouterr()
        assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_all), "--dry-run") == 0
        out_txt = capsys.readouterr().out
        assert "salvaged" not in out_txt
        assert "3 requests, 0 already reported, 3 to run" in out_txt
        assert not (out_all / "reports").exists()

        # Under --variant A (--dry-run and full execution): both A corners still stay pending.
        out_var = tmp_path / f"out_var_{mode}"
        leg_var = out_var / "jobs" / "A" / "request_c00" / "report.json"
        leg_var.parent.mkdir(parents=True)
        leg_var.write_text(json.dumps(shared_report) + "\n")
        capsys.readouterr()
        assert _run_main(
            monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_var), "--variant", "A", "--dry-run"
        ) == 0
        out_var_txt = capsys.readouterr().out
        assert "salvaged" not in out_var_txt
        assert "2 requests, 0 already reported, 2 to run" in out_var_txt
        assert not (out_var / "reports").exists()

        calls = _install_fake_klt(monkeypatch, meta)
        assert _run_main(
            monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_var), "--variant", "A"
        ) == 0
        assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
            ["A/ff/request_c00.json"],
            ["A/tt/request_c00.json"],
        ]
        assert json.loads((out_var / "reports" / "report_A_ff_c00.json").read_text())["measured_tag"] == "A_ff_c00"
        assert json.loads((out_var / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"

    # Under --variant B (single corner in B, sharing ../../common.spice with A/tt and A/ff):
    # still ambiguous across the bench without a uniquely matching receipt.
    out_b = tmp_path / "out_var_b"
    leg_b = out_b / "jobs" / "B" / "request_c00" / "report.json"
    leg_b.parent.mkdir(parents=True)
    leg_b.write_text(json.dumps({
        "synthetic": True,
        "status": "pass",
        "measured_tag": "ambiguous_B",
        "netlist": {"path": common_tb.relative_to(repo_sim).as_posix(), "scope": "repo"},
        "environment": {"netlist_sha256": common_sha},
    }) + "\n")
    calls = _install_fake_klt(monkeypatch, meta)
    assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_b), "--variant", "B") == 0
    assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
        ["B/tt/request_c00.json"],
    ]
    assert json.loads((out_b / "reports" / "report_B_tt_c00.json").read_text())["measured_tag"] == "B_tt_c00"

    # When a 0.9.0 receipt uniquely identifies A/ff/request_c00.json across the entire bench,
    # ONLY A_ff_c00 is salvaged and A/tt/request_c00.json remains pending for submission.
    out_uniq = tmp_path / "out_unique_receipt"
    leg_uniq = out_uniq / "jobs" / "A" / "request_c00"
    leg_uniq.mkdir(parents=True)
    (leg_uniq / "report.json").write_text(json.dumps({
        "synthetic": True,
        "status": "pass",
        "measured_tag": "salvaged_shared_tb_A_ff",
        "netlist": {"path": common_tb.relative_to(repo_sim).as_posix(), "scope": "repo"},
        "environment": {"netlist_sha256": common_sha},
    }) + "\n")
    ff_doc = json.loads(meta["A_ff_c00"]["req_path"].read_text())
    ff_with_wait = {**ff_doc, "batch": {"capacity_wait_s": float(run_set.CAPACITY_WAIT_S)}}
    ff_rec_sha = hashlib.sha256(
        json.dumps(ff_with_wait, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    (leg_uniq / "batch-receipt.json").write_text(json.dumps({
        "job_id": "klt-sim-ff-only",
        "request_sha256": ff_rec_sha,
        "state": "done",
    }) + "\n")
    # Also verify a mismatched receipt on a per-corner job dir leaves A_tt_c00 pending.
    bad_corner_dir = out_uniq / "jobs" / "A" / "tt" / "request_c00"
    bad_corner_dir.mkdir(parents=True)
    (bad_corner_dir / "report.json").write_text(json.dumps({
        "synthetic": True,
        "status": "pass",
        "measured_tag": "stale_corner_report",
        "environment": {"netlist_sha256": common_sha},
    }) + "\n")
    (bad_corner_dir / "batch-receipt.json").write_text(json.dumps({
        "job_id": "klt-sim-wrong-req",
        "request_sha256": ff_rec_sha,
        "state": "done",
    }) + "\n")
    calls = _install_fake_klt(monkeypatch, meta)
    assert _run_main(monkeypatch, "--bench-dir", str(bench), "--out-dir", str(out_uniq), "--variant", "A") == 0
    assert [[p.relative_to(bench).as_posix() for p in c["requests"]] for c in calls] == [
        ["A/tt/request_c00.json"],
    ]
    assert json.loads((out_uniq / "reports" / "report_A_ff_c00.json").read_text())["measured_tag"] == "salvaged_shared_tb_A_ff"
    assert json.loads((out_uniq / "reports" / "report_A_tt_c00.json").read_text())["measured_tag"] == "A_tt_c00"
