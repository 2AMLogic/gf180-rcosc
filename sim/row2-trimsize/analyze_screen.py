#!/usr/bin/env python3
"""Sparse-curve analyzer for the row-2 screen (issue #460).  Offline.

Reads the reports written by run_set.py (<reports-dir>/report_<variant>_
<corner>_cXX.json), extracts fosc per screened code and reports, per variant:
the measured endpoints, the bit-weight fit (same model as fit_weights.py on
the sparse code set), the weight ratios rho_b, every measured adjacent-code
step (the screened code set contains all carry codes +/- 1), the DR-0021
carry steps, and a monotonicity count over measured adjacent pairs.  The
full-curve statistics for finalists come from sim/trim-dense/analyze.py, not
here.  Fixture-free: a variant with any missing/failed code is reported
INCOMPLETE and excluded from rankings.

    python3 -I sim/row2-trimsize/analyze_screen.py --reports R --bench B --out D
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from fit_weights import solve_ls  # noqa: E402

NOMINAL_STEP_PCT = 80.0 / 255.0
HALF_LSB_PCT = 40.0 / 255.0
CARRIES = ((0x7F, 0x80), (0xBF, 0xC0), (0xDF, 0xE0), (0xEF, 0xF0))


def main() -> int:
    ap = argparse.ArgumentParser(description="row-2 screen analyzer (offline)")
    ap.add_argument("--reports", required=True, type=Path)
    ap.add_argument("--bench", required=True, type=Path,
                    help="bench dir (for the screened code list and sizing names)")
    ap.add_argument("--out", required=True, type=Path, help="NEW output directory")
    args = ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        print(f"error: {args.out} exists and is not empty", file=sys.stderr)
        return 1

    prov = json.loads((args.bench / "provenance.json").read_text())
    codes = sorted(prov["codes"])
    variants = prov["variants"]
    corner = prov["corner"]["tag"]
    want_sha = {e["tag"]: e["sha256"]["netlist"] for e in prov["requests"]}

    doc = {"kind": "row2-trimsize screen analysis", "issue": 460,
           "bench": str(args.bench), "reports_dir": str(args.reports),
           "corner": corner, "codes": codes, "variants": {}}
    lines = ["# row2-trimsize screen analysis (sparse, %s)" % corner, "",
             "| variant | f(lo) MHz | f(hi) MHz | mean-step* % | worst step % | nonpos (measured pairs) | rho b0..b7 | carries % |",
             "|---|---|---|---|---|---|---|---"]
    for name in variants:
        f = {}
        incomplete = []
        for c in codes:
            p = args.reports / f"report_{name}_{corner}_c{c:02X}.json"
            if not p.is_file():
                incomplete.append(f"0x{c:02X}:missing")
                continue
            r = json.loads(p.read_text())
            if r.get("status") != "pass":
                incomplete.append(f"0x{c:02X}:{r.get('status')}")
                continue
            # batch-set cross-wiring guard (klayout-tools#7180): a member report
            # whose netlist sha does not match its own request's netlist is a
            # measurement of a DIFFERENT testbench - never silently accepted.
            got = (r.get("environment") or {}).get("netlist_sha256")
            if got != want_sha[f"{name}_{corner}_c{c:02X}"]:
                incomplete.append(f"0x{c:02X}:netlist_sha_mismatch")
                continue
            for m in r.get("measurements", []):
                if m["name"] == "fosc":
                    f[c] = m["worst_case"]["value"]
        v = {"codes_measured": len(f), "incomplete": incomplete, "f": {str(k): x for k, x in f.items()}}
        if len(f) >= 12 and not incomplete:
            meas = sorted(f)
            lo, hi = meas[0], meas[-1]
            steps = [(c, 100.0 * (f[c + 1] / f[c] - 1.0)) for c in meas if c + 1 in f]
            mean_step = 100.0 * (f[hi] / f[lo] - 1.0) / (hi - lo)
            T = {c: 1.0 / x for c, x in f.items()}
            rows = [[1.0] + [(c >> b) & 1 for b in range(8)] for c in meas]
            x = solve_ls(rows, [T[c] for c in meas])
            beta = x[1:]
            W = -sum(beta) / 255.0
            rho = [abs(beta[b]) / (W * (2 ** b)) for b in range(8)]
            carr = {f"0x{a:02X}->0x{b_:02X}": round(100.0 * (f[b_] / f[a] - 1.0), 3)
                    for a, b_ in CARRIES if a in f and b_ in f}
            v |= {"f_lo": f[lo], "f_hi": f[hi], "lo_code": lo, "hi_code": hi,
                  "mean_step_pct": mean_step,
                  "worst_step_pct": max(s for _, s in steps),
                  "worst_neg_step_pct": min(s for _, s in steps),
                  "nonpos_pairs": [hex(c) for c, s in steps if s <= 0.0],
                  "beta_s": beta, "W_s": W, "rho": rho, "carries_pct": carr}
        doc["variants"][name] = v
        if "rho" in v:
            lines.append(
                f"| {name} | {v['f_lo']/1e6:.3f} | {v['f_hi']/1e6:.3f} | {v['mean_step_pct']:.4f} "
                f"| {v['worst_step_pct']:+.3f}/{v['worst_neg_step_pct']:+.3f} | {len(v['nonpos_pairs'])} "
                f"| " + ",".join(f"{r:.3f}" for r in v["rho"]) +
                " | " + " ".join(f"{k}:{vv:+.2f}" for k, vv in v["carries_pct"].items()) + " |")
        else:
            lines.append(f"| {name} | INCOMPLETE ({'; '.join(incomplete[:4])}) | | | | | | |")
    lines += ["", f"*mean-step = 100*(f(hi code)/f(lo code)-1)/(hi-lo) over the measured span "
                  f"(analyze.py endpoint convention, nominal {NOMINAL_STEP_PCT:.4f} %/code, "
                  f"half-LSB {HALF_LSB_PCT:.4f} %).", ""]
    args.out.mkdir(parents=True)
    (args.out / "screen.json").write_text(json.dumps(doc, indent=2) + "\n")
    (args.out / "screen.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
