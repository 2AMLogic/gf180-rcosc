#!/usr/bin/env python3
"""Offline effective bit-weight fit and sizing proposal for the trim ladder (issue #460).

Input : the committed dense-campaign reports (`sim/trim-dense/results/
20261106T1115Z-campaign/reports/report_<variant>_<corner>_cXX.json`, issue #87).
No simulator is launched and nothing outside --out is written.

Model (per variant x corner curve, f[c] in Hz, T[c] = 1/f[c]):
    T(c) = intercept + sum_b bit_b(c) * beta_b        beta_b < 0
  fitted by exact least squares on the 256 codes (9 parameters).  beta_b is
  the period change when trim bit b closes.  A ladder whose effective weights
  are binary-exact has beta_b = -W * 2^b with one unit period step
  W = sum|beta_b| / 255, so the weight ratio
    rho_b = |beta_b| / (W * 2^b)
  is 1.000 for a binary-exact bank.  rho_b > 1 means bit b removes more period
  than its binary share.

  Physical decomposition: closing bit b replaces the drawn segment r_b with the
  bypass switch's transient on-resistance Ron_b, so
    beta_b = -K_b * (r_b - Ron_b),   Ron_b ~= k / W_switch_b
  with K_b = dT/dR for bit b (the Elmore-style gain grows as more ladder node
  capacitance sits below the shorted segment, so K_b is NOT one number).  The
  8-point regression of beta_b on (-r_b, 1/W_b) is reported but is
  ill-conditioned (the drawn switch widths nearly follow the binary segment
  weights, so the two regressors are near-collinear; fitted "Ron" can come out
  negative) and is not used further.  The carry defects, the rho_b gradient
  (low bits heavy, bit 7 light) and their corner drift are, however, direct
  measurements.

Sizing proposal (for one compensation corner, default tt):
    r_b' = r_b * (W' * 2^b) / |beta_b|        (ratio rule)
  re-sizes each drawn segment by the inverse of its measured weight error, so
  the effective weights become binary-exact at the compensation corner to the
  extent that beta_b scales with the drawn r_b (the switch Ron share breaks
  exact proportionality; the screen re-fits and one Newton round corrects).
  The unit period step W' = (T_lo - T_hi)/255 sets the span; the base resistor
  RFIX' places T(0x00) via the Ron-free two-point model
    B = sum|beta_b| / sum r_b,   T_fix = T(0x00) - B * R_drawn(0x00)
  whose Ron uncertainty mostly cancels in R(0x00).  Residual ratios at the
  other corners (the same ratio scaling applied to their beta) predict the
  carry steps there through the linear model.

Output: <out>/fit.json (raw fits + proposals) and <out>/fit.md (tables).  The
output is analysis of already-committed evidence, not new measured evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

N_CODES = 256
# Drawn ladder geometry from sim/cmph-fix/rcosc_top_p3_cmphfix.spice (P3, DR-0023).
# X$91 = RFIX, X$92..X$99 = trim segments bit 0..7; switch = nfet+pfet pair, W in um.
RFIX_LEN_UM = 12.03860
SEG_LEN_UM = [0.52360, 1.04790, 2.09510, 4.19020, 8.38040, 16.76080, 33.52160, 67.04250]
SW_W_UM = [24.0, 16.0, 12.0, 8.0, 6.0, 5.0, 4.0, 3.0]
R_PER_UM = 500.0     # ppolyf_u_1k body, r_width=2u, 1 kohm/sq (DR-0023)
R_HEAD = 85.0        # per-resistor model head (DR-0023)
CURVES = ("ext_tt_27C_3p3V", "ext_ss_m40C_3p0V", "ext_ff_85C_3p6V")
COMP_DEFAULT = "ext_tt_27C_3p3V"
F_RATIFIED = 67.2 / 28.8          # 2.3333: ratified +/-40 % ends
NOMINAL_STEP_PCT = 80.0 / 255.0   # DR-0003 Row 2 (analyze.py convention)
HALF_LSB_PCT = 40.0 / 255.0


def drawn_r(len_um: float) -> float:
    return R_PER_UM * len_um + R_HEAD


def solve_ls(rows: list[list[float]], y: list[float]) -> list[float]:
    k = len(rows[0])
    A = [[sum(r[i] * r[j] for r in rows) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * y[c] for c, r in enumerate(rows)) for i in range(k)]
    for i in range(k):
        piv = max(range(i, k), key=lambda x: abs(A[x][i]))
        A[i], A[piv] = A[piv], A[i]
        b[i], b[piv] = b[piv], b[i]
        for r_ in range(i + 1, k):
            fac = A[r_][i] / A[i][i]
            for c_ in range(i, k):
                A[r_][c_] -= fac * A[i][c_]
            b[r_] -= fac * b[i]
    x = [0.0] * k
    for i in reversed(range(k)):
        x[i] = (b[i] - sum(A[i][j] * x[j] for j in range(i + 1, k))) / A[i][i]
    return x


def load_curve(reports: Path, tag: str) -> list[float] | None:
    f: dict[int, float] = {}
    for p in reports.glob(f"report_{tag}_c*.json"):
        code = int(p.stem.split("_c")[1], 16)
        r = json.loads(p.read_text())
        for m in r.get("measurements", []):
            if m["name"] == "fosc":
                f[code] = m["worst_case"]["value"]
    if sorted(f) != list(range(N_CODES)):
        return None
    if any(not (v > 0) for v in f.values()):
        return None
    return [f[c] for c in range(N_CODES)]


def fit_curve(f: list[float]) -> dict:
    T = [1.0 / v for v in f]
    rows = [[1.0] + [(c >> b) & 1 for b in range(8)] for c in range(N_CODES)]
    x = solve_ls(rows, T)
    beta = x[1:]
    resid = [T[c] - sum(x[i] * rows[c][i] for i in range(9)) for c in range(N_CODES)]
    span = -sum(beta)
    W = span / 255.0
    rho = [abs(beta[b]) / (W * (2 ** b)) for b in range(8)]
    # Ron decomposition: beta_b = -B*(r_b - k/W_b) -> regress beta on (-r_b, 1/W_b)
    r_drawn = [drawn_r(L) for L in SEG_LEN_UM]
    rows2 = [[-r_drawn[b], 1.0 / SW_W_UM[b]] for b in range(8)]
    sol = solve_ls(rows2, beta)
    B, Bk = sol
    ron = [Bk / SW_W_UM[b] / B for b in range(8)] if B else [float("nan")] * 8
    ron_resid = [beta[b] - (-sol[0] * r_drawn[b] - sol[1] / SW_W_UM[b]) for b in range(8)]
    steps = [100.0 * (f[c + 1] / f[c] - 1.0) for c in range(255)]
    # measured carry steps (period and frequency)
    carries = {}
    for lo, hi in ((0x7F, 0x80), (0xBF, 0xC0), (0xDF, 0xE0), (0xEF, 0xF0)):
        carries[f"0x{lo:02X}->0x{hi:02X}"] = {
            "step_pct": 100.0 * (f[hi] / f[lo] - 1.0),
            "dT_s": T[hi] - T[lo],
        }
    return {
        "f00_hz": f[0], "f255_hz": f[255],
        "intercept_s": x[0],
        "beta_s": beta,
        "W_s": W,
        "rho": rho,
        "max_abs_resid_s": max(abs(r) for r in resid),
        "B_s_per_ohm": B,
        "ron_eff_ohm": ron,
        "ron_fit_max_abs_resid_s": max(abs(r) for r in ron_resid),
        "mean_step_pct": 100.0 * (f[255] / f[0] - 1.0) / 255.0,
        "worst_pos_step_pct": max(steps),
        "worst_neg_step_pct": min(steps),
        "nonpositive_steps": sum(1 for s in steps if s <= 0),
        "carries": carries,
    }


def predict_steps(beta: list[float], comp_beta: list[float], W_target: float) -> dict:
    """Predict a re-sized curve at the corner whose fit is `beta`, given that the
    drawn re-sizing made the compensation corner's `comp_beta` binary-exact with
    unit step W_target.  Scaling law: each bit's drawn segment was multiplied by
    |target_b| / |comp_beta_b| (Ron-neglecting ratio rule), so at this corner
    the same ratio applies to beta."""
    out = {}
    new_beta = []
    for b in range(8):
        scale = (W_target * (2 ** b)) / abs(comp_beta[b])
        new_beta.append(beta[b] * scale)
    W_new = -sum(new_beta) / 255.0
    # carry period steps in units of W: carry_b = (sum_{k<b}|beta_k| - |beta_b|)/W
    for b in range(1, 8):
        lo, hi = (1 << b) - 1, 1 << b
        dT = -abs(new_beta[b]) + sum(abs(new_beta[k]) for k in range(b))
        out[f"carry{b}_dT_over_W"] = dT / W_new
    out["W_s"] = W_new
    return out


def sizing(comp: dict, f_lo_hz: float, f_hi_hz: float) -> dict:
    """Drawn lengths that make the compensation corner binary-exact with ends at
    (f_lo, f_hi): ratio rule r_b' = r_b * (W'*2^b)/|beta_b|; RFIX' from the
    Ron-free two-point model T(0x00) = T_fix + B * R_drawn(0x00)."""
    T_lo, T_hi = 1.0 / f_lo_hz, 1.0 / f_hi_hz
    W = (T_lo - T_hi) / 255.0
    r_drawn = [drawn_r(L) for L in SEG_LEN_UM]
    r_new = [r_drawn[b] * (W * (2 ** b)) / abs(comp["beta_s"][b]) for b in range(8)]
    B = sum(abs(b_) for b_ in comp["beta_s"]) / sum(r_drawn)
    T_fix = comp["intercept_s"] - B * (drawn_r(RFIX_LEN_UM) + sum(r_drawn))
    R_lo = (T_lo - T_fix) / B
    rfix_new = R_lo - sum(r_new)
    return {
        "f_lo_hz": f_lo_hz, "f_hi_hz": f_hi_hz, "W_s": W,
        "T_fix_s": T_fix, "B_s_per_ohm": B,
        "seg_len_um": [(r - R_HEAD) / R_PER_UM for r in r_new],
        "seg_r_ohm": r_new,
        "rfix_len_um": (rfix_new - R_HEAD) / R_PER_UM if rfix_new > R_HEAD else None,
        "rfix_r_ohm": rfix_new,
        "span_r_ohm": sum(r_new),
        "min_seg_r_ohm": min(r_new),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--campaign", type=Path,
                    default=REPO / "sim/trim-dense/results/20261106T1115Z-campaign")
    ap.add_argument("--reports", type=Path, default=None,
                    help="override the reports directory (default <campaign>/reports)")
    ap.add_argument("--comp-corner", default=COMP_DEFAULT, help="compensation curve tag")
    ap.add_argument("--out", required=True, type=Path, help="NEW output directory")
    args = ap.parse_args()

    reports = args.reports or (args.campaign / "reports")
    out = args.out
    if out.exists() and any(out.iterdir()):
        print(f"error: {out} exists and is not empty", file=sys.stderr)
        return 1
    out.mkdir(parents=True)

    fits = {}
    for tag in CURVES:
        f = load_curve(reports, tag)
        if f is None:
            print(f"error: curve {tag} incomplete in {reports}", file=sys.stderr)
            return 1
        fits[tag] = fit_curve(f)

    comp = fits[args.comp_corner]
    # Sizing family: (name, f_lo, f_hi) at the compensation corner, tt.
    # Balanced placement keeps 48 MHz reachable at the two bounding corners with
    # equal margins (end corner factors ss/tt and ff/tt measured by the campaign).
    k_hi = fits["ext_ss_m40C_3p0V"]["f255_hz"] / comp["f255_hz"]   # ss/tt at 0xFF
    k_lo = fits["ext_ff_85C_3p6V"]["f00_hz"] / comp["f00_hz"]      # ff/tt at 0x00
    proposals = {}
    for name, F in (("F1.85", 1.85), ("F1.95", 1.95), ("F2.50", 2.50)):
        if name == "F2.50":   # range-true: cover the ratified ends with headroom
            f_lo, f_hi = 27.5e6, 68.75e6
        else:                 # balanced: k_hi*F*x - 48 = 48 - k_lo*x
            x = 96.0e6 / (k_hi * F + k_lo)
            f_lo, f_hi = x, F * x
        prop = sizing(comp, f_lo, f_hi)
        if prop["rfix_len_um"] is None:
            print(f"error: sizing {name} needs a negative RFIX", file=sys.stderr)
            return 1
        prop["end_margin_hz"] = {"ss_top": k_hi * f_hi - 48e6, "ff_bottom": 48e6 - k_lo * f_lo}
        # predicted residual carry ratios at the two other corners
        for tag in CURVES:
            if tag != args.comp_corner:
                prop[f"predict_{tag}"] = predict_steps(fits[tag]["beta_s"], comp["beta_s"], prop["W_s"])
        proposals[name] = prop

    doc = {
        "kind": "row2-trimsize offline bit-weight fit",
        "evidence": "analysis of the committed #87 dense campaign; no simulation run",
        "issue": 460,
        "campaign": str(args.campaign.relative_to(REPO)) if args.campaign.is_relative_to(REPO) else str(args.campaign),
        "curves": fits,
        "comp_corner": args.comp_corner,
        "proposals": proposals,
        "drawn": {
            "rfix_len_um": RFIX_LEN_UM, "seg_len_um": SEG_LEN_UM, "sw_w_um": SW_W_UM,
            "r_per_um": R_PER_UM, "r_head_ohm": R_HEAD,
            "seg_r_ohm": [drawn_r(L) for L in SEG_LEN_UM],
            "rfix_r_ohm": drawn_r(RFIX_LEN_UM),
        },
        "ratified": {"f_ratio": F_RATIFIED, "nominal_step_pct": NOMINAL_STEP_PCT,
                     "half_lsb_pct": HALF_LSB_PCT},
    }
    (out / "fit.json").write_text(json.dumps(doc, indent=2) + "\n")

    lines = [
        "# Row-2 trim-bank effective bit-weight fit (offline, committed #87 campaign)",
        "",
        f"- compensation corner: `{args.comp_corner}`",
        f"- ratified: mean step {NOMINAL_STEP_PCT:.4f} %/code, half-LSB {HALF_LSB_PCT:.4f} %, "
        f"ends ratio {F_RATIFIED:.4f} (28.8-67.2 MHz)",
        "",
        "## Per-curve fit (T = intercept + sum bit_b * beta_b)",
        "",
        "| curve | f(0x00) MHz | f(0xFF) MHz | mean step % | worst+ % | worst- % | nonpos | max resid %T |",
        "|---|---|---|---|---|---|---|---",
    ]
    for tag, ft in fits.items():
        lines.append(
            f"| {tag} | {ft['f00_hz']/1e6:.3f} | {ft['f255_hz']/1e6:.3f} | {ft['mean_step_pct']:.4f} "
            f"| {ft['worst_pos_step_pct']:.3f} | {ft['worst_neg_step_pct']:.3f} | {ft['nonpositive_steps']} "
            f"| {100*ft['max_abs_resid_s']/(1/ft['f255_hz']):.2f} |")
    lines += ["", "## Weight ratios rho_b (1.000 = binary-exact)", "",
              "| curve | " + " | ".join(f"b{b}" for b in range(8)) + " | B s/ohm | Ron b0..b7 ohm |",
              "|---" * 10 + "|"]
    for tag, ft in fits.items():
        lines.append(f"| {tag} | " + " | ".join(f"{r:.3f}" for r in ft["rho"]) +
                     f" | {ft['B_s_per_ohm']:.3e} | " + ",".join(f"{r:.0f}" for r in ft["ron_eff_ohm"]) + " |")
    lines += ["", "## Measured DR-0021 carries (% f-step / ns T-step)", ""]
    for tag, ft in fits.items():
        c = ft["carries"]
        lines.append("| " + tag + " | " + " | ".join(
            f"{k}: {v['step_pct']:+.2f}%/{v['dT_s']*1e9:+.2f}ns" for k, v in c.items()) + " |")
    lines += ["", "## Sizing proposals (drawn lengths, um; r_width 2u unchanged)", "",
              "| name | RFIX | r0..r7 | f_lo/f_hi MHz (tt) | ss top margin MHz | ff bottom margin MHz |",
              "|---|---|---|---|---|---|"]
    for name, p in proposals.items():
        lines.append(
            f"| {name} | {p['rfix_len_um']:.3f} | " +
            ",".join(f"{L:.3f}" for L in p["seg_len_um"]) +
            f" | {p['f_lo_hz']/1e6:.2f}/{p['f_hi_hz']/1e6:.2f} "
            f"| {p['end_margin_hz']['ss_top']/1e6:+.2f} | {p['end_margin_hz']['ff_bottom']/1e6:+.2f} |")
    lines += ["", "Predicted residual carries at the non-compensation corners "
                  "(period step / W; negative = monotone f-increase): see fit.json `proposals.*.predict_*`.",
              ""]
    (out / "fit.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
