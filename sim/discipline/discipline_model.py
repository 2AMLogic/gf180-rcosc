#!/usr/bin/env python3
"""Behavioural SOF discipline-loop model against the committed freq-vs-code data (issue #79).

Pure stdlib (no numpy). Reads only committed CSVs; runs no analogue simulation.
Writes a NEW results/<runid>/ directory and refuses to overwrite one.

    python3 -I sim/discipline/discipline_model.py [--runid ID]

Plant and assumptions are documented in sim/discipline/README.md.
"""
import argparse, csv, datetime, hashlib, json, math, os, platform, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCH_CSV = "sim/pvt/results/20260923T030125Z/results.csv"
EXT_CSV = "sim/pvt-postlayout/results/20260923T152954Z/results.csv"
GRD_CSV = "sim/pvt-postlayout/results/20260923T152954Z/guardrails.csv"
F_TARGET = 48.0e6
FRAME_S = 1e-3          # USB full-speed SOF interval
N_NOM = 48000           # nominal counts per frame
BAND = 0.25             # percent, the reserved discipline row
HALF_LSB = 0.157        # percent, ratified half-LSB
SEED = 20261009
TS = (-40.0, 27.0, 85.0)
VS = (3.0, 3.3, 3.6)


def rows(rel):
    with open(os.path.join(ROOT, rel), newline="") as f:
        return list(csv.DictReader(f))


def sha(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()


# ---------------------------------------------------------------- plant
class Plant:
    """f(code, T, V) = F27(code) * g(T, V).

    F27: ln-f interpolation of the committed tt/27C/3.3V curve (24 codes), mapped to the
    corner by a 2-point affine fit in ln f; g: bilinear in (T, V) from the committed
    fixed-code (0xA3) grid, normalised to its 27C/3.3V point.
    """

    def __init__(self, name, side, a, b, gtab, anchors):
        self.name, self.side, self.a, self.b, self.g, self.anchors = name, side, a, b, gtab, anchors
        self.F = [self._f27(c) for c in range(256)]

    def _f27(self, c):
        if self.side == "sch":
            return math.exp(self.a + self.b * LNTT(c))
        sh = SHAPE(c)
        return math.exp(self.a + self.b * sh + getattr(self, "k", 0.0) * sh * (1 - sh))

    def gain(self, T, V):
        T = min(max(T, TS[0]), TS[-1]); V = min(max(V, VS[0]), VS[-1])
        i = 0 if T < TS[1] else 1
        j = 0 if V < VS[1] else 1
        tt = (T - TS[i]) / (TS[i + 1] - TS[i]); vv = (V - VS[j]) / (VS[j + 1] - VS[j])
        g = self.g
        return ((1 - tt) * (1 - vv) * g[(TS[i], VS[j])] + tt * (1 - vv) * g[(TS[i + 1], VS[j])]
                + (1 - tt) * vv * g[(TS[i], VS[j + 1])] + tt * vv * g[(TS[i + 1], VS[j + 1])])

    def f(self, c, T, V):
        return self.F[c] * self.gain(T, V)


def build():
    sch = rows(SCH_CSV)
    curve = sorted((int(r["trim_code"]), float(r["f_hz"])) for r in sch if r["pass"] == "trim_curve")
    cs = [c for c, _ in curve]; ln = [math.log(f) for _, f in curve]

    def lntt(c):
        if c <= cs[0]: return ln[0]
        for k in range(1, len(cs)):
            if c <= cs[k]:
                return ln[k - 1] + (ln[k] - ln[k - 1]) * (c - cs[k - 1]) / (cs[k] - cs[k - 1])
        return ln[-1]
    global LNTT, SHAPE
    LNTT = lntt
    s0, s1 = lntt(0), lntt(255)
    SHAPE = lambda c: (lntt(c) - s0) / (s1 - s0)

    def sel(p, passname, T, V, rowsrc=sch):
        for r in rowsrc:
            if r["pass"] == passname and r["process"] == p and float(r["temp_c"]) == T and float(r["vdd_v"]) == V:
                return r
        raise KeyError((p, passname, T, V))

    plants, checks = [], []
    for p in ("tt", "ff", "ss", "fs", "sf", "rc_f", "rc_s"):
        f128 = float(sel(p, "pretrim", 27, 3.3)["f_hz"])
        f163 = float(sel(p, "posttrim_spec", 27, 3.3)["f_hz"])
        b = (math.log(f163) - math.log(f128)) / (lntt(163) - lntt(128))
        a = math.log(f128) - b * lntt(128)
        g = {(T, V): float(sel(p, "posttrim_spec", T, V)["f_hz"]) / f163 for T in TS for V in VS}
        g128 = {(T, V): float(sel(p, "pretrim", T, V)["f_hz"]) / f128 for T in TS for V in VS}
        gdiff = max(abs(g[k] / g128[k] - 1) for k in g) * 100
        pl = Plant(p, "sch", a, b, g, {"f128": f128, "f163": f163})
        rcal = sel(p, "posttrim_ratif", 27, 3.3)
        ccal = int(rcal["trim_code"])
        checks.append({"plant": f"{p}/sch", "check": "model f at measured per-corner cal code vs measured",
                       "model_mhz": pl.F[ccal] / 1e6, "measured_mhz": float(rcal["f_hz"]) / 1e6,
                       "err_pct": (pl.F[ccal] / float(rcal["f_hz"]) - 1) * 100,
                       "g_code_dependence_max_pct": gdiff})
        pl.cal_code = ccal
        plants.append(pl)
    # extracted (post-layout) plants: tt, ff, ss
    ext = rows(EXT_CSV); grd = rows(GRD_CSV)
    for p in ("tt", "ff", "ss"):
        cal = [r for r in grd if r["kind"] == "calibration" and r["side"] == "extracted" and r["process"] == p][0]
        f0, f255 = float(cal["f_code0x00_hz"]), float(cal["f_code0xff_hz"])
        b = math.log(f255 / f0); a = math.log(f0)   # ln F = a + b*SHAPE(c)
        k = 0.0   # a 3-point (cal-anchored) fit was tried and rejected: it worsened the independent 0xA3 check (ss: -6.2 % vs +1.2 %)
        er = {(float(r["temp_c"]), float(r["vdd_v"])): float(r["extracted_f_hz"]) for r in ext if r["process"] == p}
        g = {k: er[k] / er[(27.0, 3.3)] for k in er}
        pl = Plant(p, "ext", a, b, g, {"f0": f0, "f255": f255}) if False else None
        Plant.k = 0.0
        pl = Plant.__new__(Plant)
        pl.k = k
        Plant.__init__(pl, p, "ext", a, b, g, {"f0": f0, "f255": f255})
        pl.cal_code = int(cal["code"])
        ccal = pl.cal_code
        checks.append({"plant": f"{p}/ext", "check": "model f at measured per-corner cal code (independent check) vs measured",
                       "model_mhz": pl.F[ccal] / 1e6, "measured_mhz": float(cal["f_hz"]) / 1e6,
                       "err_pct": (pl.F[ccal] / float(cal["f_hz"]) - 1) * 100, "g_code_dependence_max_pct": ""})
        checks.append({"plant": f"{p}/ext", "check": "model f at 0xA3 27C/3.3V vs measured extracted f(0xA3) (independent check)",
                       "model_mhz": pl.F[163] / 1e6, "measured_mhz": er[(27.0, 3.3)] / 1e6,
                       "err_pct": (pl.F[163] / er[(27.0, 3.3)] - 1) * 100, "g_code_dependence_max_pct": ""})
        plants.append(pl)
    return plants, checks, curve


# ---------------------------------------------------------------- trim math
def trim_math(pl):
    """Static, no loop: realized steps, best code per (T,V), headroom."""
    steps = [(pl.F[c + 1] / pl.F[c] - 1) * 100 for c in range(255)]
    out = {"plant": f"{pl.name}/{pl.side}",
           "min_step_pct": min(steps), "max_step_pct": max(steps),
           "n_negative_steps": sum(1 for s in steps if s < 0),
           "worst_negative_step_pct": min(steps),
           "mean_step_pct": (pl.F[255] / pl.F[0]) ** (1 / 255) * 100 - 100,
           "f0_mhz": pl.F[0] / 1e6, "f255_mhz": pl.F[255] / 1e6, "grid": []}
    for T in TS:
        for V in VS:
            fs = [pl.f(c, T, V) for c in range(256)]
            errs = [(f / F_TARGET - 1) * 100 for f in fs]
            cbest = min(range(256), key=lambda c: abs(errs[c]))
            ups = [errs[c] for c in range(255)]
            # smallest code at which f >= target ("first crossing from below") and its neighbour error
            cross = sum(1 for c in range(255) if (errs[c] < 0) != (errs[c + 1] < 0))
            loc_step = ((fs[min(cbest + 1, 255)] / fs[max(cbest - 1, 0)]) ** 0.5 - 1) * 100 if 0 < cbest < 255 else float("nan")
            out["grid"].append({"T": T, "V": V, "best_code": cbest, "best_err_pct": errs[cbest],
                                "saturated": cbest in (0, 255) and abs(errs[cbest]) > 1e-9 and (errs[255] < 0 or errs[0] > 0),
                                "local_step_pct": loc_step, "crossings": cross, "f255_err_pct": errs[255], "f0_err_pct": errs[0]})
    return out


# ---------------------------------------------------------------- controllers
class BangBang:
    name = "bangbang"
    def __init__(s, c0): s.c = c0
    def update(s, e):
        s.c = min(255, max(0, s.c + (-1 if e > 0 else 1 if e < 0 else 0))); return s.c

class Deadband:
    name = "deadband"
    D = round(HALF_LSB / 100 * N_NOM)
    def __init__(s, c0): s.c = c0
    def update(s, e):
        if e > s.D: s.c -= 1
        elif e < -s.D: s.c += 1
        s.c = min(255, max(0, s.c)); return s.c

class AvgStep:
    name = "avg32"
    M = 32; D = round(HALF_LSB / 100 * N_NOM)
    def __init__(s, c0): s.c = c0; s.acc = 0; s.n = 0
    def update(s, e):
        s.acc += e; s.n += 1
        if s.n == s.M:
            m = s.acc / s.M; s.acc = 0; s.n = 0
            if m > s.D: s.c -= 1
            elif m < -s.D: s.c += 1
            s.c = min(255, max(0, s.c))
        return s.c

class FracDither:
    """Integrator with 4 fractional code bits, first-order sigma-delta onto the 8-bit code."""
    name = "fracdither"
    KI = 0.8        # codes per percent error per frame (loop gain = KI * local slope, slope<=~1 %/code)
    FRAC = 16
    def __init__(s, c0): s.I = float(c0); s.r = 0.0; s.c = c0
    def update(s, e):
        s.I -= s.KI * (e / N_NOM * 100)
        s.I = min(255.0, max(0.0, s.I))                 # clamp = anti-windup at the rails
        iq = round(s.I * s.FRAC) / s.FRAC
        v = iq + s.r; c = math.floor(v); s.r = v - c
        s.c = min(255, max(0, c)); return s.c

POLICIES = (BangBang, Deadband, AvgStep, FracDither)


# ---------------------------------------------------------------- loop sim
def run_loop(pl, policy, c0, profile, jitter_ns, rng, trace=False):
    """profile: list of (T, V) per frame. Returns per-frame true error % (list), codes."""
    ctl = policy(c0); code = c0
    errs, codes = [], []
    jprev = rng.uniform(-jitter_ns, jitter_ns) * 1e-9 if jitter_ns else 0.0
    phase = 0.0
    for T, V in profile:
        f = pl.f(code, T, V)
        jk = rng.uniform(-jitter_ns, jitter_ns) * 1e-9 if jitter_ns else 0.0
        interval = FRAME_S + jk - jprev; jprev = jk
        phase += f * interval
        n = math.floor(phase); phase -= n                 # integer counter; carry the fraction
        errs.append((f / F_TARGET - 1) * 100); codes.append(code)
        code = ctl.update(n - N_NOM)
    return errs, codes


def lock_frame(x, band, hold):
    """first index i s.t. |x[j]|<=band for all j in [i, i+hold); None if never."""
    run = 0
    for i, v in enumerate(x):
        run = run + 1 if abs(v) <= band else 0
        if run >= hold: return i - hold + 1
    return None


def movavg(x, w):
    out, s = [], 0.0
    for i, v in enumerate(x):
        s += v
        if i >= w: s -= x[i - w]
        if i >= w - 1: out.append(s / w)
    return out


def stats(x):
    return {"min": min(x), "max": max(x), "pp": max(x) - min(x), "absmax": max(abs(min(x)), abs(max(x))),
            "frac_in_band": sum(1 for v in x if abs(v) <= BAND) / len(x)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runid", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    a = ap.parse_args()
    outdir = os.path.join(HERE, "results", a.runid)
    if os.path.exists(outdir):
        sys.exit(f"refusing to overwrite {outdir} (results/ is append-only)")
    plants, checks, curve = build()
    os.makedirs(outdir)
    csvrows = []

    tm = [trim_math(p) for p in plants]
    with open(os.path.join(outdir, "trim_math.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["plant", "T_c", "V", "best_code", "best_err_pct", "saturated", "local_step_pct", "target_crossings",
                    "f255_err_pct", "f0_err_pct"])
        for t in tm:
            for g in t["grid"]:
                w.writerow([t["plant"], g["T"], g["V"], g["best_code"], f"{g['best_err_pct']:.4f}", g["saturated"],
                            f"{g['local_step_pct']:.4f}", g["crossings"], f"{g['f255_err_pct']:.3f}", f"{g['f0_err_pct']:.3f}"])
    with open(os.path.join(outdir, "plant_checks.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(checks[0].keys())); w.writeheader(); w.writerows(checks)

    res = []
    def record(**k): res.append(k)
    WARM = 8000
    for pl in plants:
        pn = f"{pl.name}/{pl.side}"
        for jit in (0.0, 500.0):
            for P in POLICIES:
                rng = random.Random(SEED)
                # E2: cold start at 0x80, 27C/3.3V
                prof = [(27.0, 3.3)] * WARM
                e, c = run_loop(pl, P, 128, prof, jit, rng)
                ss = e[-2000:]; sc = c[-2000:]
                st = stats(ss); st16 = stats(movavg(ss, 16)); st64 = stats(movavg(ss, 64))
                record(exp="cold_start_27C_3p3V", plant=pn, policy=P.name, jitter_ns=jit,
                       lock_inst_frames=lock_frame(e, BAND, 256), lock_avg16_frames=lock_frame(movavg(e, 16), BAND, 256),
                       ss_min=st["min"], ss_max=st["max"], ss_pp=st["pp"], ss_absmax=st["absmax"],
                       ss_frac_in_band=st["frac_in_band"], ss_avg16_absmax=st16["absmax"], ss_avg64_absmax=st64["absmax"],
                       ss_code_min=min(sc), ss_code_max=max(sc), extra="")
                # E3: temperature ramps, start locked at -40C
                for rate, label in ((1.0, "ramp_1C_per_s"), (20.0, "ramp_20C_per_s")):
                    n_ramp = int(125.0 / rate * 1000)
                    prof = [(-40.0, 3.3)] * WARM + [(-40.0 + 125.0 * i / n_ramp, 3.3) for i in range(n_ramp + 1)]
                    rng = random.Random(SEED)
                    e, c = run_loop(pl, P, 128, prof, jit, rng)
                    r = e[WARM:]; rc = c[WARM:]
                    st = stats(r); a16 = stats(movavg(r, 16)); a64 = stats(movavg(r, 64))
                    rail = sum(1 for x in rc if x in (0, 255)) / len(rc)
                    record(exp=label, plant=pn, policy=P.name, jitter_ns=jit, lock_inst_frames="", lock_avg16_frames="",
                           ss_min=st["min"], ss_max=st["max"], ss_pp=st["pp"], ss_absmax=st["absmax"],
                           ss_frac_in_band=st["frac_in_band"], ss_avg16_absmax=a16["absmax"], ss_avg64_absmax=a64["absmax"],
                           ss_code_min=min(rc), ss_code_max=max(rc), extra=f"rail_frac={rail:.4f}")
                # E4: supply steps 3.3 -> 3.0 -> 3.6 -> 3.3 at 27C and at -40C
                for T in (27.0, -40.0):
                    seq = [3.3, 3.0, 3.6, 3.3]
                    prof = [(T, 3.3)] * WARM
                    for V in seq: prof += [(T, V)] * 1500
                    rng = random.Random(SEED)
                    e, c = run_loop(pl, P, 128, prof, jit, rng)
                    e = e[WARM:]; c = c[WARM:]
                    relock = []
                    for k in (1, 2, 3):
                        seg = e[k * 1500:(k + 1) * 1500]
                        relock.append(lock_frame(movavg(seg, 16), BAND, 128))
                    last = e[-500:]
                    st = stats(last); a16 = stats(movavg(last, 16))
                    record(exp=f"vdd_steps_{T:+.0f}C", plant=pn, policy=P.name, jitter_ns=jit,
                           lock_inst_frames="", lock_avg16_frames="|".join(str(x) for x in relock),
                           ss_min=st["min"], ss_max=st["max"], ss_pp=st["pp"], ss_absmax=st["absmax"],
                           ss_frac_in_band=st["frac_in_band"], ss_avg16_absmax=a16["absmax"], ss_avg64_absmax="",
                           ss_code_min=min(c[-500:]), ss_code_max=max(c[-500:]), extra="relock_avg16 after 3.0|3.6|3.3 V")
    cols = list(res[0].keys())
    with open(os.path.join(outdir, "results.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in res:
            w.writerow([f"{v:.4f}" if isinstance(v, float) else ("none" if v is None else v) for v in (r[k] for k in cols)])
    # one committed trace: ss/ext cold start with each policy (first 400 frames)
    ss_ext = [p for p in plants if p.name == "ss" and p.side == "ext"][0]
    with open(os.path.join(outdir, "trace_ss_ext_cold_start.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["frame"] + [f"{P.name}_{k}" for P in POLICIES for k in ("code", "err_pct")])
        cols_t = []
        for P in POLICIES:
            e, c = run_loop(ss_ext, P, 128, [(27.0, 3.3)] * 400, 0.0, random.Random(SEED))
            cols_t.append((c, e))
        for i in range(400):
            w.writerow([i] + [x for c, e in cols_t for x in (c[i], f"{e[i]:.4f}")])

    try:
        sha_git = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        sha_git = ""
    man = {"runid": a.runid, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "git_head": sha_git, "python": platform.python_version(), "seed": SEED,
           "inputs_sha256": {p: sha(p) for p in (SCH_CSV, EXT_CSV, GRD_CSV)},
           "params": {"frame_s": FRAME_S, "n_nom": N_NOM, "band_pct": BAND, "half_lsb_pct": HALF_LSB,
                      "deadband_counts": Deadband.D, "avg_frames": AvgStep.M, "fracdither_ki": FracDither.KI,
                      "fracdither_frac_bits": 4, "jitter_ns_cases": [0.0, 500.0], "warm_frames": WARM},
           "no_analogue_sim": True}
    json.dump(man, open(os.path.join(outdir, "manifest.json"), "w"), indent=2)
    write_summary(outdir, a.runid, tm, checks, res, man)
    print("wrote", outdir)


def _n(v):
    return 'none' if v is None else v


def write_summary(outdir, runid, tm, checks, res, man):
    L = []
    L.append(f"# Discipline-loop model run {runid}\n")
    L.append("Generated by `discipline_model.py`; plant = committed runs "
             f"`{SCH_CSV}` (schematic, post-#60, DR-0017) and `{EXT_CSV}` + `guardrails.csv` (post-layout, DR-0018). No analogue simulation. Interpretation: `sim/discipline/README.md` and DR-0021.\n")
    L.append("## Plant model validation\n")
    L.append("| plant | check | model MHz | measured MHz | err % | max g(code) dependence % |\n|---|---|---|---|---|---|")
    for c in checks:
        gd = f"{c['g_code_dependence_max_pct']:.2f}" if c["g_code_dependence_max_pct"] != "" else ""
        L.append(f"| {c['plant']} | {c['check']} | {c['model_mhz']:.3f} | {c['measured_mhz']:.3f} | {c['err_pct']:+.2f} | {gd} |")
    L.append("\n## Static trim math (no loop)\n")
    L.append("Realized per-code step (interpolated committed curve; ratified nominal 0.314 %/code), and the best achievable single-code error to 48 MHz over the 9 T/V points.\n")
    L.append("| plant | mean step %/code | max step | min step | negative steps | f(0x00) MHz | f(0xFF) MHz | best-code |err| range over 9 T/V % | saturated T/V points | max target crossings (>1 = non-monotone) |\n|---|---|---|---|---|---|---|---|---|---|")
    for t in tm:
        be = [abs(g["best_err_pct"]) for g in t["grid"]]
        sat = [f"{g['T']:+.0f}C/{g['V']}V" for g in t["grid"] if g["saturated"]]
        L.append(f"| {t['plant']} | {t['mean_step_pct']:.3f} | {t['max_step_pct']:.3f} | {t['min_step_pct']:.3f} | {t['n_negative_steps']} | {t['f0_mhz']:.2f} | {t['f255_mhz']:.2f} | {min(be):.3f}..{max(be):.3f} | {', '.join(sat) or 'none'} | {max(g['crossings'] for g in t['grid'])} |")
    L.append("\nPer-point detail: `trim_math.csv`.\n")
    def sel(exp, jit, plants=None):
        return [r for r in res if r["exp"] == exp and r["jitter_ns"] == jit and (plants is None or r["plant"] in plants)]
    L.append("## Steady state, cold start from 0x80 at 27 C / 3.3 V (last 2000 of 8000 frames)\n")
    L.append("`inst` = per-frame true frequency error; `avg16` = 16-frame moving average (16 ms). Band = +/-0.25 %. Lock = first frame after which the quantity stays in band for 256 frames (`none` = never). Jitter = uniform +/-J on each SOF arrival (an assumed parameter).\n")
    for jit in (0.0, 500.0):
        L.append(f"\n### SOF jitter +/-{jit:.0f} ns\n")
        L.append("| plant | policy | lock inst | lock avg16 | inst min..max % | inst frac in band | avg16 absmax % | avg64 absmax % | codes used |\n|---|---|---|---|---|---|---|---|---|")
        for r in sel("cold_start_27C_3p3V", jit):
            L.append(f"| {r['plant']} | {r['policy']} | {_n(r['lock_inst_frames'])} | {_n(r['lock_avg16_frames'])} | {r['ss_min']:+.3f}..{r['ss_max']:+.3f} | {r['ss_frac_in_band']:.3f} | {r['ss_avg16_absmax']:.3f} | {r['ss_avg64_absmax']:.3f} | 0x{r['ss_code_min']:02X}..0x{r['ss_code_max']:02X} |")
    for exp, title in (("ramp_1C_per_s", "Temperature ramp -40 -> +85 C at 1 C/s (125 000 frames), 3.3 V, locked at -40 C first"),
                       ("ramp_20C_per_s", "Temperature ramp -40 -> +85 C at 20 C/s (6 250 frames), 3.3 V")):
        L.append(f"\n## {title}\n")
        for jit in (0.0, 500.0):
            L.append(f"\n### SOF jitter +/-{jit:.0f} ns\n")
            L.append("| plant | policy | inst min..max % | inst frac in band | avg16 absmax % | avg64 absmax % | extra |\n|---|---|---|---|---|---|---|")
            for r in sel(exp, jit):
                L.append(f"| {r['plant']} | {r['policy']} | {r['ss_min']:+.3f}..{r['ss_max']:+.3f} | {r['ss_frac_in_band']:.3f} | {r['ss_avg16_absmax']:.3f} | {r['ss_avg64_absmax']:.3f} | {r['extra']} |")
    for T in ("+27", "-40"):
        exp = f"vdd_steps_{T}C"
        L.append(f"\n## Supply steps 3.3 -> 3.0 -> 3.6 -> 3.3 V at {T} C (1500 frames each after an 8000-frame warm-up at 3.3 V; last 500 frames of final segment reported)\n")
        L.append("Re-lock (avg16 in band for 128 frames) in frames after each step, 3.0|3.6|3.3 V.\n")
        for jit in (0.0,):
            L.append("| plant | policy | re-lock frames | final-segment inst min..max % | avg16 absmax % |\n|---|---|---|---|---|")
            for r in sel(exp, jit):
                L.append(f"| {r['plant']} | {r['policy']} | {str(r['lock_avg16_frames']).replace('None','none')} | {r['ss_min']:+.3f}..{r['ss_max']:+.3f} | {r['ss_avg16_absmax']:.3f} |")
    open(os.path.join(outdir, "summary.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
