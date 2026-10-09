"""Offline tests for sim/trim-transition (issue #103).  Every waveform here is a
SYNTHETIC FIXTURE built in this file; nothing is measured evidence and no
simulator or cloud operation is invoked.

Run:  python3 -I -m pytest -p no:cacheprovider sim/trim-transition/test_harness.py
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


prepare = _load("tt_prepare", "prepare.py")
analyze = _load("tt_analyze", "analyze.py")
NS = 1e-9
VDD = 3.3


# ---------------------------------------------------------------- prepare --

@pytest.fixture
def no_sim(monkeypatch):
    def guard(cmd, *a, **k):
        raise AssertionError(f"offline test must not run subprocesses: {cmd}")
    monkeypatch.setattr(subprocess, "run", guard)


def test_bank_weighting_is_binary_in_the_schematic(no_sim):
    """The carry choice rests on this: stage i resistor length = 2^i x stage 0."""
    text = prepare.wf.dut_block()
    ln = {int(m.group(1)): float(m.group(2))
          for m in re.finditer(r"^XR(\d) c\d \w+ vss ppolyf_u_1k r_width=2u r_length=([\d.]+)u", text, re.M)}
    assert sorted(ln) == list(range(8))
    for i in range(1, 8):
        assert ln[i] / ln[0] == pytest.approx(2 ** i, rel=2e-3)
    for i in range(8):  # switch i is gated by t<i> and shunts exactly stage i
        assert re.search(rf"^XSW{i} c\d t{i} \w+ vss nfet_03v3", text, re.M)


def test_positions_bits_flipped():
    flips = {n: len(prepare.bits_changed(lo, hi)) for n, lo, hi in prepare.POSITIONS}
    assert flips == {"noncarry_A2_A3": 1, "carry_3F_40": 7, "carry_7F_80": 8, "carry_BF_C0": 7}
    for _, lo, hi in prepare.POSITIONS:
        assert hi == lo + 1


def test_skew_orders():
    a, b = 0x7F, 0x80
    assert set(prepare.bit_delays("none", a, b).values()) == {0.0}
    lsb = prepare.bit_delays("lsb_first", a, b)
    msb = prepare.bit_delays("msb_first", a, b)
    assert lsb[0] < lsb[6] < lsb[7] and msb[7] < msb[6] < msb[0]
    assert max(lsb.values()) == 7.0 and max(msb.values()) == 7.0


def test_generate_requests_offline(tmp_path, no_sim):
    prov = prepare.generate(tmp_path)
    reqs = prov["requests"]
    assert len(reqs) == 9
    pts = set()
    for r in reqs:
        req = json.loads((tmp_path / r["request"]).read_text())
        for proc in req["corners"]["process"]:
            fets, res, mim = prepare.PROCESS_CORNERS[proc["name"]]
            assert proc["sections"] == [fets, res, mim, "cap_mim"]
            pts.add((proc["name"], r["vdd_v"], r["skew"]))
        assert req["corners"]["temperature_c"] == [27.0]
        assert req["analysis"]["kind"] == "tran"
        assert req["options"]["waveforms"] and req["options"]["save_mode"] == "netlist"
        tb = (tmp_path / req["netlist"]).read_text()
        assert ".save v(clk) v(vdd)" in tb and "XXDUT vdd 0 clk t0 t1 t2 t3 t4 t5 t6 t7 rcosc_top" in tb
        sched = json.loads((tmp_path / r["schedule"]).read_text())
        evs = [c for c in sched["changes"] if c["kind"] == "event"]
        assert len(evs) == 4 * 2 * 4  # positions x directions x phases
        for a, b in zip(sched["changes"], sched["changes"][1:]):
            assert b["t_start_ns"] > a["t_end_ns"] + 100
        assert sched["tstop_ns"] > sched["changes"][-1]["t_end_ns"] + 500
    assert len(pts) == 27  # 3 process x 3 supply x 3 skew


def test_pwl_matches_schedule(tmp_path, no_sim):
    prepare.generate(tmp_path)
    tb = (tmp_path / "tb_v33_msb_first.spice").read_text()
    sched = json.loads((tmp_path / "schedule_v33_msb_first.json").read_text())
    # rebuild each trim line's waveform from the netlist and compare to the schedule
    lines = tb.splitlines()
    for i in range(8):
        k = next(j for j, l in enumerate(lines) if l.startswith(f"VT{i} "))
        txt = lines[k]
        while k + 1 < len(lines) and lines[k + 1].startswith("+"):
            k += 1
            txt += " " + lines[k][1:]
        if "DC 0" in txt:
            pts = []
        else:
            nums = re.findall(r"([\d.]+)n ([\d.]+)", txt)
            pts = [(float(a), float(b)) for a, b in nums]
        times = [t for t, _ in pts]
        assert times == sorted(times) and len(set(times)) == len(times)
        # level after each change equals the schedule's code bit
        code = sched["init_code"]
        want = []
        for c in sched["changes"]:
            b = c["bits"].get(str(i))
            if b:
                want.append((b["start_ns"], b["level_to"] * VDD))
                code = c["to"]
        for ts, lvl in want:
            after = [v for t, v in pts if abs(t - (ts + sched["edge_ns"])) < 1e-3]
            assert after and after[0] == pytest.approx(lvl)
        assert code == sched["changes"][-1]["to"]


def test_probe_option(tmp_path, no_sim):
    prov = prepare.generate(tmp_path, probe="tt:3.3:none")
    assert len(prov["requests"]) == 1
    req = json.loads((tmp_path / "request_probe.json").read_text())
    assert [p["name"] for p in req["corners"]["process"]] == ["tt"]
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "x", probe="zz:3.3:none")
    with pytest.raises(prepare.PrepareError):
        prepare.generate(tmp_path / "y", probe="nonsense")


def test_committed_requests_are_current(tmp_path, no_sim):
    """The generated files checked into this directory equal a fresh generation."""
    prepare.generate(tmp_path)
    for f in sorted(tmp_path.iterdir()):
        assert (HERE / f.name).read_text() == f.read_text(), f.name


# ---------------------------------------------------------------- analyze --

def clock(periods, high=8 * NS, edge=1 * NS, t0=100 * NS, amp=None, highs=None):
    """Trapezoid clock; rising 50 % crossing i at t0+sum(periods[:i]).  `highs`
    overrides the high time per cycle, `amp` the amplitude per cycle."""
    r, x = [], t0
    for q in periods:
        r.append(x)
        x += q
    r.append(x)
    pts = [(0.0, 0.0)]
    for i, ri in enumerate(r):
        h = (highs or {}).get(i, high)
        a = (amp or {}).get(i, VDD)
        pts += [(ri - edge / 2, 0.0), (ri + edge / 2, a), (ri + h - edge / 2, a), (ri + h + edge / 2, 0.0)]
    pts.sort()
    t = [p[0] for p in pts]
    c = [p[1] for p in pts]
    return t, c, [VDD] * len(t), r


def make_sched(events, tstop_ns):
    ch = [{"kind": "event", "block": "blk", "dir": "up", "phase": 0, "from": 1, "to": 2, "bits_changed": 1,
           "t_start_ns": ts, "t_end_ns": ts + 1} for ts in events]
    return {"vdd_v": VDD, "skew": "none", "tstop_ns": tstop_ns, "changes": ch}


def seq(n_before, n_after, p_old=20 * NS, p_new=21 * NS, transient=()):
    return [p_old] * n_before + list(transient) + [p_new] * n_after


def run(periods, events=(600.0,), tstop=None, **kw):
    t, c, v, r = clock(periods, **kw)
    tstop = tstop or r[-1] / NS
    sched = make_sched(events, tstop)
    return analyze.analyse_corner(t, c, v, sched), r


def test_clean_step_passes():
    # change at 600 ns = in the cycle starting at r[25] (100 + 25*20)
    rows, _ = run(seq(25, 55), events=[605.0], tstop=1500)
    (row,) = rows
    assert row["status"] == "OK" and row["verdict"] == "PASS", row
    assert row["p_old_s"] == pytest.approx(20 * NS) and row["p_new_s"] == pytest.approx(21 * NS)
    assert row["p_min_s"] == pytest.approx(20 * NS) and row["p_max_s"] == pytest.approx(21 * NS)
    assert row["settle_cycles"] == 0 and not row["runt"]  # change cycle already at the new period and not row["missing_edge"]
    assert row["excursion_pct"] == pytest.approx(0.0, abs=1e-9)
    assert 0 < row["phase_in_cycle"] < 1


def test_excursion_and_flag():
    rows, _ = run(seq(25, 55, transient=[18 * NS, 22.5 * NS]), events=[605.0], tstop=1500)
    row = rows[0]
    assert row["verdict"] == "FLAG" and not row["runt"]
    assert row["p_min_s"] == pytest.approx(18 * NS)
    assert row["excursion_pct"] == pytest.approx((20 - 18) / 20 * 100)
    assert row["settle_cycles"] == 2


def test_slow_settling_is_flagged_by_cycle_count():
    tr = [21 * NS + 0.5 * NS * 0.6 ** k for k in range(12)]
    rows, _ = run(seq(25, 55, transient=tr), events=[605.0], tstop=1500)
    assert rows[0]["verdict"] == "FLAG" and rows[0]["settle_cycles"] > 3


def test_never_settles_is_violation():
    per = [20 * NS] * 25 + [21 * NS + (0.5 * NS if k % 2 else -0.5 * NS) for k in range(40)]
    rows, _ = run(per, events=[605.0], tstop=1400)
    assert rows[0]["settle_cycles"] is None and rows[0]["verdict"] == "VIOLATION"


def test_runt_high_pulse_is_violation():
    # cycle 25 (the change cycle) has a 1.5 ns high pulse (period kept)
    rows, _ = run(seq(25, 55), events=[605.0], tstop=1500, highs={25: 1.5 * NS})
    assert rows[0]["runt"] and rows[0]["verdict"] == "VIOLATION"
    assert any("high" in s for s in rows[0]["runt_reasons"])


def test_runt_low_pulse_is_violation():
    rows, _ = run(seq(25, 55), events=[605.0], tstop=1500, highs={25: 18.8 * NS})
    assert rows[0]["runt"] and any("low" in s for s in rows[0]["runt_reasons"])


def test_incomplete_swing_is_runt():
    rows, _ = run(seq(25, 55), events=[605.0], tstop=1500, amp={25: 0.6 * VDD})
    assert rows[0]["runt"] and rows[0]["verdict"] == "VIOLATION"
    assert any("peaks" in s for s in rows[0]["runt_reasons"])


def test_missing_edge_is_violation():
    rows, _ = run(seq(25, 55, transient=[41 * NS]), events=[605.0], tstop=1500)
    assert rows[0]["missing_edge"] and rows[0]["verdict"] == "VIOLATION"


def test_skewed_change_straddling_an_edge_extends_the_window():
    # t_start just before r[25], t_end after it: window covers up to the cycle holding t_end
    t, c, v, r = clock(seq(25, 55))
    ts = r[25] / NS - 2.0
    sched = make_sched([ts], 1500)
    sched["changes"][0]["t_end_ns"] = ts + 8
    row = analyze.analyse_corner(t, c, v, sched)[0]
    assert row["window_cycles"] == 3 and row["status"] == "OK"
    sched["changes"][0]["t_end_ns"] = ts + 45
    row = analyze.analyse_corner(t, c, v, sched)[0]
    assert row["window_cycles"] == 5


def test_two_events_use_neighbouring_change_as_steady_bounds():
    per = [20 * NS] * 25 + [21 * NS] * 35 + [20 * NS] * 30
    t, c, v, r = clock(per)
    s = make_sched([605.0, 1325.0], r[-1] / NS)
    rows = analyze.analyse_corner(t, c, v, s)
    assert [x["verdict"] for x in rows] == ["PASS", "PASS"]
    assert rows[1]["p_old_s"] == pytest.approx(21 * NS) and rows[1]["p_new_s"] == pytest.approx(20 * NS)


def test_run_level_failures():
    per = seq(25, 55)
    t, c, v, r = clock(per)
    # steady old window overlaps the previous change
    s = make_sched([300.0, 420.0], r[-1] / NS)
    rows = analyze.analyse_corner(t, c, v, s)
    assert rows[1]["status"].startswith("FAIL") and "previous change" in rows[1]["status"]
    # event too early
    rows = analyze.analyse_corner(t, c, v, make_sched([150.0], r[-1] / NS))
    assert "too early" in rows[0]["status"]
    # run shorter than the schedule
    with pytest.raises(analyze.AnalysisError, match="run ends"):
        analyze.analyse_corner(t, c, v, make_sched([605.0], 5000))
    # rail off
    with pytest.raises(analyze.AnalysisError, match="rail"):
        analyze.analyse_corner(t, c, [2.5] * len(t), make_sched([605.0], 1500))
    # event too close to the end of the data for a new-code steady window
    rows = analyze.analyse_corner(t, c, v, make_sched([r[-12] / NS], r[-1] / NS))
    assert rows[0]["status"].startswith("FAIL")


def test_aggregate_orders_worst_verdict():
    rows = [{"process": "tt", "vdd_v": 3.3, "skew": "none", "block": "b", "dir": "up", "status": "OK",
             "verdict": v, "p_min_s": 1e-8, "p_max_s": 2e-8, "p_old_s": 1.5e-8, "p_new_s": 1.5e-8,
             "excursion_pct": 1.0, "runt": False, "missing_edge": False, "settle_cycles": 1,
             "phase_in_cycle": 0.3} for v in ("PASS", "FLAG")]
    (a,) = analyze.aggregate(rows)
    assert a["verdict"] == "FLAG" and a["events"] == 2


# ---------------------------------------------------------------- reports --

def write_wf(tmp, name, tcv):
    t, c, v = tcv[:3]
    d = tmp / name
    d.mkdir()
    (d / "waveform.raw.json").write_text(json.dumps({
        "variables": [{"name": "time"}, {"name": "v(clk)"}, {"name": "v(vdd)"}],
        "points": [[a, b, e] for a, b, e in zip(t, c, v)]}))
    return str(d / "waveform.raw.json")


def bench(tmp, tag="v33_none", events=(605.0,), tstop=1500):
    (tmp / f"schedule_{tag}.json").write_text(json.dumps(make_sched(events, tstop) | {"tag": tag}))


def write_report(tmp, corners, **extra):
    p = tmp / "report.json"
    p.write_text(json.dumps({"schema_version": 3, "status": "pass", "corner_count": len(corners),
                             "synthetic": True, "corners": corners, **extra}))
    return p


def corner(proc, wf=None, status="pass"):
    return {"process": proc, "temperature_c": 27.0, "status": status,
            "artifacts": {"waveform": wf} if wf else {}}


def test_report_rows_and_failures(tmp_path):
    bench(tmp_path)
    good = write_wf(tmp_path, "g", clock(seq(25, 55))[:3])
    short = write_wf(tmp_path, "s", clock(seq(5, 5))[:3])
    rep = write_report(tmp_path, [corner("tt", good), corner("ss", short), corner("ff", None),
                                  corner("tt", good, status="error")])
    rows, meta = analyze.analyse_report("v33_none", rep, tmp_path)
    assert [r["verdict"] for r in rows] == ["PASS", "FAIL", "FAIL", "FAIL"]
    assert "run ends" in rows[1]["status"] and "no waveform" in rows[2]["status"]
    assert "klt corner status" in rows[3]["status"]
    assert rows[0]["process"] == "tt" and rows[0]["skew"] == "none" and meta["synthetic"]
    out = tmp_path / "run"
    doc = analyze.write_run(out, rows, [meta], analyze.Params(), synthetic=False)
    assert doc["synthetic"] and not doc["no_violation"] and doc["verdict_counts"]["FAIL"] == 3
    assert "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE" in (out / "summary.md").read_text()
    assert (out / "results.csv").read_text().count("FAIL") >= 3
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        analyze.write_run(out, rows, [meta], analyze.Params(), synthetic=True)


def test_missing_inputs_fail_explicitly(tmp_path):
    bench(tmp_path)
    rows, _ = analyze.analyse_report("v33_none", tmp_path / "nope.json", tmp_path)
    assert rows[0]["status"].startswith("FAIL: report unreadable")
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    assert analyze.analyse_report("v33_none", bad, tmp_path)[0][0]["status"].startswith("FAIL: report is not valid JSON")
    assert analyze.analyse_report("v33_none", write_report(tmp_path, []), tmp_path)[0][0]["status"] == "FAIL: report has no corners"
    assert "schedule unreadable" in analyze.analyse_report("v99_x", bad, tmp_path)[0][0]["status"]
    good = write_wf(tmp_path, "g", clock(seq(25, 55))[:3])
    rep = write_report(tmp_path, [corner("tt", good)], corner_count=9)
    assert any("corner_count" in r["status"] for r in analyze.analyse_report("v33_none", rep, tmp_path)[0])


def test_artifacts_root_override(tmp_path):
    bench(tmp_path)
    write_wf(tmp_path, "tt_27", clock(seq(25, 55))[:3])
    rep = write_report(tmp_path, [corner("tt", "/elsewhere/tt_27/waveform.raw.json")])
    rows, _ = analyze.analyse_report("v33_none", rep, tmp_path, artifacts_root=tmp_path)
    assert rows[0]["verdict"] == "PASS"


def test_cli_exit_codes(tmp_path):
    bench(tmp_path)
    good = write_wf(tmp_path, "g", clock(seq(25, 55))[:3])
    bad = write_wf(tmp_path, "b", clock(seq(25, 55), highs={25: 1.5 * NS})[:3])
    base = [sys.executable, "-I", str(HERE / "analyze.py"), "--bench-dir", str(tmp_path), "--synthetic"]
    rep = write_report(tmp_path, [corner("tt", good)])
    r = subprocess.run(base + [f"v33_none={rep}", "--outdir", str(tmp_path / "o1")], capture_output=True, text=True)
    assert r.returncode == 0 and "SYNTHETIC" in r.stdout
    rep2 = tmp_path / "rep2.json"
    rep2.write_text(json.dumps({"corner_count": 1, "corners": [corner("tt", bad)]}))
    r = subprocess.run(base + [f"v33_none={rep2}", "--outdir", str(tmp_path / "o2")], capture_output=True, text=True)
    assert r.returncode == 1
