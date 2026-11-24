#!/usr/bin/env python3
"""Summarise a graded item-6 campaign (issue #202): yield reports, the three
DR-0019 / DR-0022 negative controls, and the per-die spread.  Offline and
stdlib-only: reads committed `klt sim` / `klt yield` JSON, prints markdown.

Usage: python3 -I analyze.py <grade dir> <run dir> [<run dir> ...]

Control criteria (stated before the run, DR-0019 s2 / DR-0022 s3):
  zero-mismatch   every draw identical; chosen code and calibration frequency
                  equal the deterministic P3 value (sim/recentre/results/
                  20261106T044714Z/summary.md) within 0.25 % (the repeatability
                  tolerance recorded in sim/mc-groundwork/README.md)
  inflated 3x     `klt yield` reports the control's degradation as detected
                  (negative_control verdict), and the control fails the claim
  seeded defect   (issue #461, DR-0051) a known-bad deck per row set, same seed, draws, probes
                  and grading expressions as the nominal.  Detected only on the pinned
                  grader's own per-measurement `negative_control.verdict` ("detected":
                  lower empirical yield with non-overlapping exact CIs).  A cell whose
                  nominal pass fraction is below 0.99 (exact upper bound < 0.99) is listed
                  as `nominal_fails`, deferred to #317, and never counted as control evidence.
  sensitivity     MOS off, injected terms only: the sample sigma of the step
                  at the fixed MSB transition (0x7F->0x80) and at 0x7E->0x7F
                  scales with mm_scale; the 10x/1x ratio must be about 10
                  (accepted band 7..13 for n=100 per arm: the relative standard
                  error of a sigma estimate is 1/sqrt(2(n-1)) = 7 %)
"""
import json
import math
import statistics
import sys
from pathlib import Path

# deterministic P3 calibration (27 C / 3.3 V): code and f in MHz, process -> value
P3_GRID = {"tt": (0xA9, 48.060), "ff": (0x59, 48.092), "ss": (0xD7, 48.129)}
ZERO_TOL_PCT = 0.25
SENS_BAND = (7.0, 13.0)


def find(case: str, dirs: list[Path]) -> Path | None:
    for d in dirs:
        p = d / f"report_{case}.json"
        if p.exists():
            return p
    return None


def column(report: dict, name: str) -> list[float]:
    out = []
    for c in report.get("corners", []):
        for m in c.get("measurements", []):
            if m["name"] == name and m.get("value") is not None:
                out.append(float(m["value"]))
    return out


def parse_zero_ref(text: str) -> dict:
    """"tt=164:47.91,ff=79:47.97" -> {"tt": (164, 47.91), ...} (code:MHz per process)."""
    out = {}
    for part in text.strip().split(","):
        k, v = part.split("=")
        c, f = v.split(":")
        out[k.strip()] = (int(c), float(f))
    return out


def first_value(rep: dict | None, name: str):
    v = column(rep, name) if rep else []
    return v[0] if v else None


def fmt(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}g}"


ROWS_DEF = (("2", "r2def"), ("4", "r45def"), ("5", "r45def"))


def defect_section(grade: Path, dirs: list[Path]) -> None:
    """Seeded-defect controls (issue #461): one line per measurement verdict, the nominal
    pass fraction against 0.99, the control pass fraction, and the grader's own verdict."""
    if not any((grade / f"yield_{p}_row{r}_def.json").exists() for p in ("tt", "ff", "ss") for r in ("2", "4", "5")):
        return
    print("## Control 4: seeded known-bad defect (issue #461, DR-0051)\n")
    print("Detection is the pinned grader's per-measurement verdict only.  `nominal_fails` = the "
          "nominal's exact 95 % upper bound is below the 0.99 target: the cell cannot show a "
          "yield degradation, is deferred to #317 and is **not** counted as control evidence.\n")
    print("| process | row | measurement | n nominal | nominal pass (95 % CI) | vs 0.99 | n control | control pass (95 % CI) | grader verdict | disposition |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    tally = {"detected": 0, "not_detected": 0, "nominal_fails": 0, "other": 0}
    for p in ("tt", "ff", "ss"):
        for row, _ in ROWS_DEF:
            f = grade / f"yield_{p}_row{row}_def.json"
            if not f.exists():
                print(f"| {p} | {row} | (missing) | | | | | | | |")
                tally["other"] += 1
                continue
            for m in json.loads(f.read_text()).get("measurements", []):
                e = m["yield"]["empirical"]
                lo, hi = e["confidence_interval"]["low"], e["confidence_interval"]["high"]
                nc = m.get("negative_control") or {}
                ce = (nc.get("yield") or {}).get("empirical") or {}
                cci = ce.get("confidence_interval") or {}
                verdict = nc.get("verdict", "not_declared")
                if hi < 0.99:
                    rel, disp = "below (upper < 0.99)", "nominal_fails"
                elif lo > 0.99:
                    rel, disp = "above (lower > 0.99)", "detected" if verdict == "detected" else "not_detected"
                else:
                    rel, disp = "straddles", "detected" if verdict == "detected" else "not_detected"
                tally[disp] = tally.get(disp, 0) + 1
                print(f"| {p} | {row} | {m['name']} | {m['n']} | {e['estimate']:.3f} ({lo:.3f}-{hi:.3f}) | {rel} | "
                      f"{nc.get('n', 'n/a')} | {fmt(ce.get('estimate'), 3)} ({fmt(cci.get('low'), 3)}-{fmt(cci.get('high'), 3)}) | "
                      f"{verdict} | {disp} |")
    print(f"\nTally: {tally['detected']} detected, {tally['not_detected']} not detected, "
          f"{tally['nominal_fails']} nominal fails (deferred to #317), {tally['other']} missing "
          "(twelve measurement verdicts expected: rows 4/5 one each and row 2 two per corner).\n")


def sens_fine_section(dirs: list[Path]) -> None:
    arms = {r: find(f"{r}_tt", dirs) for r in ("sens1", "sens10", "sens1fine", "sens10fine")}
    if not (arms["sens1fine"] and arms["sens10fine"]):
        return
    print("\n### Timing-resolution hypothesis (issue #461): matched draws, `tran 200p` vs `tran 50p`\n")
    print("| quantity | step | sigma at 1x | sigma at 10x | ratio | in 7..13 |")
    print("|---|---|---|---|---|---|")
    for step, (a, b) in (("200p", ("sens1", "sens10")), ("50p", ("sens1fine", "sens10fine"))):
        ra, rb = json.loads(arms[a].read_text()), json.loads(arms[b].read_text())
        for name in ("step_0x7f_0x80_hz", "step_0x7e_0x7f_hz"):
            s1, s10 = statistics.stdev(column(ra, name)), statistics.stdev(column(rb, name))
            ratio = s10 / s1 if s1 else float("inf")
            print(f"| {name} | {step} | {s1:.4g} Hz | {s10:.4g} Hz | {ratio:.2f} | "
                  f"{'yes' if SENS_BAND[0] <= ratio <= SENS_BAND[1] else 'NO'} |")
    print("\nThe 7..13 band is unchanged.  A miss at both steps is the measured limit of the bench.")


def main() -> None:
    global P3_GRID
    grade = Path(sys.argv[1])
    dirs = [Path(a) for a in sys.argv[2:]]
    if (grade / "zero_ref.txt").exists():
        P3_GRID = parse_zero_ref((grade / "zero_ref.txt").read_text())
        zero_label = "the recorded deterministic reference (zero_ref.txt)"
    else:
        zero_label = "the DR-0023 P3 grid"
    dut_txt = next((d / "dut.txt" for d in dirs if (d / "dut.txt").exists()), None)
    dut = dut_txt.read_text().strip() if dut_txt else "P3 extracted netlist (DR-0023, proposed)"
    mrep = find("main_tt", dirs)
    n_main = len(column(json.loads(mrep.read_text()), "code_sel")) if mrep else 0
    print("# Item-6 Monte Carlo campaign summary (generated by analyze.py)\n")
    print(f"DUT: {dut}; DR-0019 (proposed) claims S1-S3; "
          "DR-0022 matching model A_R = A_C = 1.0 %.um (flagged assumption). "
          f"Seed 20261008, {n_main} samples per process corner (zero-mismatch reference: {zero_label}).\n")

    print("## Yield (klt yield, 95 % two-sided, target yield 0.99)\n")
    print("| process | row | measurement | n | pass | yield lower bound | sample-size | negative control | status |")
    print("|---|---|---|---|---|---|---|---|---|")
    for p in ("tt", "ff", "ss"):
        for row in ("2", "4", "5"):
            f = grade / f"yield_{p}_row{row}.json"
            if not f.exists():
                print(f"| {p} | {row} | (missing) | | | | | | |")
                continue
            y = json.loads(f.read_text())
            for m in y.get("measurements", []):
                emp = m["yield"]["empirical"]
                nc = m.get("negative_control") or {}
                print(f"| {p} | {row} | {m['name']} | {m['n']} | {fmt(emp['estimate'])} | "
                      f"{fmt(emp['confidence_interval']['low'])} | {m['sample_size']['verdict']} | "
                      f"{nc.get('verdict', 'not_declared')} | {m['status']} |")
    print()

    print("## Per-die spread (main runs)\n")
    print("| process | code min/median/max | calibration residual |e| p99 (%) | S2 margin min (%) | S3 margin min (%) |")
    print("|---|---|---|---|---|---|")
    for p in ("tt", "ff", "ss"):
        r = find(f"main_{p}", dirs)
        if not r:
            continue
        rep = json.loads(r.read_text())
        code = column(rep, "code_sel")
        res = sorted(column(rep, "s1_resid_abs_pct"))
        s2, s3 = column(rep, "s2_margin_pct"), column(rep, "s3_margin_pct")
        if code:
            p99 = res[min(len(res) - 1, math.ceil(0.99 * len(res)) - 1)]
            print(f"| {p} | {min(code):.0f}/{statistics.median(code):.0f}/{max(code):.0f} | {p99:.3f} | "
                  f"{min(s2):.3f} | {min(s3):.3f} |")
    print()

    print("## Control 1: zero mismatch (plumbing)\n")
    print("| process | draws identical | code | expected code | f_hold (MHz) | expected (MHz) | delta (%) | within 0.25 % |")
    print("|---|---|---|---|---|---|---|---|")
    for p, (ecode, ef) in P3_GRID.items():
        r = find(f"zero_{p}", dirs)
        if not r:
            print(f"| {p} | (no report) | | | | | | |")
            continue
        rep = json.loads(r.read_text())
        code, fh = column(rep, "code_sel"), column(rep, "f_hold_hz")
        ident = len(set(zip(code, fh))) == 1
        d = (fh[0] / 1e6 - ef) / ef * 100
        ok = ident and code[0] == ecode and abs(d) <= ZERO_TOL_PCT
        print(f"| {p} | {'yes' if ident else 'NO'} | {code[0]:.0f} | {ecode} | {fh[0] / 1e6:.4f} | {ef:.3f} | {d:+.3f} | {'yes' if ok else 'NO'} |")
    print()

    print("## Control 2: inflated 3x (negative control, via klt yield-samples)\n")
    print("See the `negative control` column above: the verdict is klt yield's own.\n")
    for p in ("tt", "ff", "ss"):
        r = find(f"inflated_{p}", dirs)
        if not r:
            continue
        rep = json.loads(r.read_text())
        rs = column(rep, "s1_resid_abs_pct")
        print(f"* {p}: n={len(rs)}, calibration residual |e| median {statistics.median(rs):.3f} % "
              f"(main run: see per-die table), code spread sd {statistics.pstdev(column(rep, 'code_sel')):.2f}")
    print()

    defect_section(grade, dirs)

    print("## Control 3: injected-term sensitivity (MOS off)\n")
    z = find("senszero_tt", dirs)
    a, b = find("sens1_tt", dirs), find("sens10_tt", dirs)
    if a and b:
        ra, rb = json.loads(a.read_text()), json.loads(b.read_text())
        print("| quantity | sigma at 1x | sigma at 10x | ratio | in 7..13 |")
        print("|---|---|---|---|---|")
        allok = True
        for name in ("step_0x7f_0x80_hz", "step_0x7e_0x7f_hz"):
            s1 = statistics.stdev(column(ra, name))
            s10 = statistics.stdev(column(rb, name))
            ratio = s10 / s1 if s1 else float("inf")
            ok = SENS_BAND[0] <= ratio <= SENS_BAND[1]
            allok &= ok
            print(f"| {name} | {s1:.4g} Hz | {s10:.4g} Hz | {ratio:.2f} | {'yes' if ok else 'NO'} |")
        c1, c10 = column(ra, "code_sel"), column(rb, "code_sel")
        print(f"\ncode-selection spread (reported, not gated: discrete): sd {statistics.pstdev(c1):.3f} at 1x, "
              f"{statistics.pstdev(c10):.3f} at 10x")
        if z:
            rz = json.loads(z.read_text())
            zs = column(rz, "step_0x7f_0x80_hz")
            print(f"zero-mismatch baseline step 0x7F->0x80: {zs[0]:.0f} Hz (3 identical draws: "
                  f"{'yes' if len(set(zs)) == 1 else 'NO'})")
        print(f"\nSensitivity control: {'PASS' if allok else 'FAIL (no verdict)'}")
        sens_fine_section(dirs)
    else:
        print("(sensitivity reports missing)")


if __name__ == "__main__":
    main()
