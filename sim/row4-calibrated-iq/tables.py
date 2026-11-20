#!/usr/bin/env python3
"""Tabulate the calibrated-code running-Iq campaign (sim/row4-calibrated-iq, issue #337).

  python3 -I sim/row4-calibrated-iq/tables.py --cand PHASE1_DIR --ctrl PHASE2_DIR --out RUNDIR

PHASE1_DIR holds the phase-1 batch-set outputs (per-member report.json under phase1/<stem>/);
PHASE2_DIR the phase-2 deck-set outputs (per-unit meas.csv under <dreq stem>/<uNNN>/meas.csv).
Writes tables.md (per-die matched comparison) and summary.md (distributions, worst dice, band
comparison) into --out.  Print-only; appends nothing to prior runs.
"""
import glob
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POINTS = [("n40_30", -40.0, 3.0), ("n40_33", -40.0, 3.3), ("n40_36", -40.0, 3.6),
          ("27_30", 27.0, 3.0), ("27_33", 27.0, 3.3), ("27_36", 27.0, 3.6),
          ("85_30", 85.0, 3.0), ("85_33", 85.0, 3.3), ("85_36", 85.0, 3.6)]
LABS = [p[0] for p in POINTS]
LIMIT_UA = 500.0
DR44_BAND = (-4.57, 0.18)  # % , DR-0044's fixed-code l07-vs-L1u band (the relative no-regression reference)
NAMES = {"w3r65": "w3r65 (3x W, X$91 65 %)", "w2.5r75": "w2.5r75 (2.5x W, X$91 75 %)"}


def load_phase1(phase1_dir: Path):
    """{name: {proc: [(sample_index, code, {lab: (f_hz, iq_a)}, seed)]}} from the batch-set member reports."""
    out = {}
    for rep in sorted(glob.glob(str(phase1_dir / "phase1" / "*" / "report.json"))):
        stem = Path(rep).parent.name  # request_w3r65_tt
        _, name, proc = stem.split("_")
        r = json.load(open(rep))
        dice = {}
        for c in r["corners"]:
            if c.get("status") != "pass" or c.get("monte_carlo") is None:
                continue
            m = {x["name"]: x.get("value") for x in c["measurements"]}
            if m.get("code_sel") is None:
                continue
            pts = {}
            for lab in LABS:
                f, iq = m.get(f"f_{lab}_hz"), m.get(f"iq_{lab}_a")
                if f is None or iq is None:
                    pts = None
                    break
                pts[lab] = (f, iq)
            if pts is None:
                continue
            dice[int(c["monte_carlo"]["sample_index"])] = (
                int(m["code_sel"]), pts, c["monte_carlo"]["seed"],
                m.get("e_cal_pct"), m.get("hold_gap_hz"))
        out.setdefault(name, {})[proc] = dice
    return out


def load_phase2(phase2_dir: Path):
    """{(name, proc): {sample_index: {lab: (f_hz, iq_a)}}} from the deck-set unit outputs."""
    out = {}
    for csv in sorted(glob.glob(str(phase2_dir / "dreq_*" / "u*" / "meas.csv"))):
        unit_dir = Path(csv).parent
        stem = unit_dir.parent.name  # dreq_w3r65_tt_00
        _, name, proc, _k = stem.split("_")
        idx = int(unit_dir.name[1:])
        # wrdata writes two columns per vector (scale, value); the values are the odd columns
        nums = []
        for tok in Path(csv).read_text().split():
            try:
                nums.append(float(tok))
            except ValueError:
                pass
        ys = nums[1::2]
        if len(ys) < 2 * len(LABS):
            continue
        pts = {}
        for i, lab in enumerate(LABS):
            pts[lab] = (ys[i], ys[len(LABS) + i] * 1e6)
        out.setdefault((name, proc), {})[idx] = pts
    return out


def pct(a, b):
    return (a - b) / b * 100.0 if b else None


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    cand_dir = Path(a[a.index("--cand") + 1])
    ctrl_dir = Path(a[a.index("--ctrl") + 1])
    out = Path(a[a.index("--out") + 1])
    out.mkdir(parents=True, exist_ok=True)
    p1 = load_phase1(cand_dir)
    p2 = load_phase2(ctrl_dir)

    L = [f"# calibrated-code running-Iq campaign tables ({out.name})\n",
         "Candidate die i and control die i carry the same mismatch realization (same derived seed, folded-literal"
         " injection); the control is the DR-0044 L=1 um control at the candidate die's held code.\n"]
    S = ["# campaign summary\n"]
    for name in sorted(p1):
        for proc in sorted(p1[name]):
            dice = p1[name][proc]
            ctrl = p2.get((name, proc), {})
            matched = sorted(set(dice) & set(ctrl))
            L.append(f"\n## {NAMES.get(name, name)} - {proc} ({len(dice)} candidate dice, {len(ctrl)} control decks,"
                     f" {len(matched)} matched pairs)\n")
            codes = [dice[i][0] for i in sorted(dice)]
            if codes:
                L.append(f"\nCalibration codes (27 C / 3.3 V nearest-48 MHz, DR-0032 rule): min {min(codes)},"
                         f" median {sorted(codes)[len(codes) // 2]}, max {max(codes)},"
                         f" distinct {len(set(codes))} ({', '.join(f'0x{c:02X}x{codes.count(c)}' for c in sorted(set(codes)))}).\n")
                L.append(f"At 0xFF: {sum(1 for c in codes if c == 255)} of {len(codes)} dice.\n")
            S.append(f"\n## {NAMES.get(name, name)} - {proc}\n")
            S.append(f"\n| grid point | cand Iq med (uA) | p90 | max | ctrl med | ctrl max | delta med % | delta p90 % | delta max % | delta min % | >=500uA cand | ctrl | worst die (idx, code) |\n"
                     "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
            worst_all = None
            band = {"within": 0, "above": 0, "below": 0}
            deltas_all = []
            for lab, t, v in POINTS:
                cd = [dice[i][1][lab][1] * 1e6 for i in matched]
                kd = [ctrl[i][lab][1] for i in matched]
                dl = [pct(c, k) for c, k in zip(cd, kd)]
                if not dl:
                    continue
                imax = max(range(len(dl)), key=lambda i: dl[i])
                wi = matched[imax]
                row_max = (dl[imax], wi, dice[wi][0], cd[imax], kd[imax])
                if worst_all is None or dl[imax] > worst_all[1][0]:
                    worst_all = (lab, row_max, t, v)
                deltas_all += dl
                for d in dl:
                    band["within" if DR44_BAND[0] <= d <= DR44_BAND[1] else ("above" if d > DR44_BAND[1] else "below")] += 1
                S.append(f"| {lab} ({t:g} C, {v:.1f} V) | {st.median(cd):.1f} | {sorted(cd)[int(0.9 * len(cd))]:.1f} | {max(cd):.1f} |"
                         f" {st.median(kd):.1f} | {max(kd):.1f} | {st.median(dl):+.2f} | {sorted(dl)[int(0.9 * len(dl))]:+.2f} |"
                         f" {max(dl):+.2f} | {min(dl):+.2f} | {sum(1 for c in cd if c >= LIMIT_UA)} |"
                         f" {sum(1 for c in kd if c >= LIMIT_UA)} | u{wi:03d}, 0x{dice[wi][0]:02X} |\n")
            if deltas_all:
                S.append(f"\nAll matched deltas: n={len(deltas_all)}, median {st.median(deltas_all):+.2f} %,"
                         f" p90 {sorted(deltas_all)[int(0.9 * len(deltas_all))]:+.2f} %, min {min(deltas_all):+.2f} %,"
                         f" max {max(deltas_all):+.2f} %.  Against the DR-0044 fixed-code band"
                         f" ({DR44_BAND[0]:+.2f}..{DR44_BAND[1]:+.2f} %): {band['within']} within,"
                         f" {band['above']} above, {band['below']} below.\n")
                if worst_all:
                    lab, (d, wi, code, c_mu, k_mu), t, v = worst_all
                    S.append(f"Worst single cell: u{wi:03d} ({proc}), code 0x{code:02X}, {lab} ({t:g} C, {v:.1f} V):"
                             f" {c_mu:.1f} uA vs control {k_mu:.1f} uA = {d:+.2f} %.\n")
            # per-die table (top offenders by worst-cell delta)
            per_die = []
            for i in matched:
                ds = [pct(dice[i][1][lab][1] * 1e6, ctrl[i][lab][1]) for lab in LABS]
                per_die.append((max(ds), i, dice[i][0], ds))
            per_die.sort(reverse=True)
            L.append("\nWorst die by max-point delta (top 12):\n")
            L.append("| die | code | max delta % | " + " | ".join(LABS) + " |\n|---|---|---|" + "---|" * len(LABS) + "\n")
            for dmax, i, code, ds in per_die[:12]:
                L.append(f"| u{i:03d} | 0x{code:02X} | {dmax:+.2f} | " + " | ".join(f"{d:+.2f}" for d in ds) + " |\n")
    (out / "summary.md").write_text("".join(S))
    (out / "tables.md").write_text("".join(L))
    print("".join(S))


if __name__ == "__main__":
    main()
