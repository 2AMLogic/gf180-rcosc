#!/usr/bin/env python3
"""SOF reference-loss and reacquisition extension of the discipline-loop model (issue #128).

Behavioural simulation only.  Pure stdlib.  Imports (never edits) discipline_model.py, reads the
same committed plant CSVs, runs no analogue simulation, and writes a NEW results/<runid>/
directory (append-only; refuses to overwrite).

    python3 -I sim/discipline/outage_model.py [--runid ID]

Candidate policy "freeze_reacquire" (an engineering assumption for sensitivity analysis, not a
hardware design decision and not a sourced reference guarantee):

  * Observation i is the oscillator count between SOF_i and SOF_{i+1}.  SOF_0 is assumed present
    (identical to the existing no-loss model).  ``lost[i]`` True means SOF_{i+1} did not arrive.
  * Observation i is VALID iff both of its bounding SOFs arrived: not lost[i] and not lost[i-1].
    A valid observation spans exactly one nominal frame and updates the controller exactly as in
    the no-loss model.
  * An invalid observation is never delivered.  The trim code AND all controller state (integrator,
    fractional residue, averaging accumulator) are frozen.  The first arrival after an outage only
    establishes a baseline; the next one gives a fresh one-frame interval.  A count that spans
    several frames is never presented as one nominal 48 000-count frame.
  * No "locked" flag exists in this model: status words are derived afterwards from the TRUE
    frequency, never from the controller's previous state.

mode="naive_nominal" is a CONTRAST FIXTURE ONLY: it delivers the multi-frame span count to the
controller as if it were a single frame.  It is not a candidate policy and is not swept.
"""
import argparse, csv, datetime, hashlib, importlib.util, json, math, os, platform, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_base():
    spec = importlib.util.spec_from_file_location("discipline_model_base", os.path.join(HERE, "discipline_model.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


dm = _load_base()

HOLD = 256           # frames the band must be held to call a quantity "recovered"
TAIL = 6000          # frames simulated after the outage ends
WARM = dm.WARM if hasattr(dm, "WARM") else 8000
OUTAGES = (1, 16, 256)     # lost SOFs (engineering assumptions, not sourced guarantees)
MODES = ("freeze_reacquire", "naive_nominal")


# ---------------------------------------------------------------- engine
def outage_schedule(n_frames, start, length):
    """lost[i] True for i in [start, start+length)."""
    return [start <= i < start + length for i in range(n_frames)]


def valid_schedule(lost):
    """valid[i] = both bounding SOFs present = not lost[i] and not lost[i-1] (SOF_0 present)."""
    return [(not lost[i]) and not (i > 0 and lost[i - 1]) for i in range(len(lost))]


def run_loop_outage(pl, policy, c0, profile, jitter_ns, rng, lost=None, mode="freeze_reacquire", trace_state=False):
    """Same plant/counter/jitter timing as dm.run_loop, plus a reference-availability schedule.

    Returns dict: errs (true error % per frame), codes, obs (observed count error delivered to
    the controller at frame i, or None), valid, ref_state ('tracking'|'holdover'|'reacquiring'),
    ctl (final controller), states (per-frame vars(ctl) snapshots after the frame's update, only
    if trace_state).  With lost all-False or None, errs/codes equal dm.run_loop exactly.
    """
    if mode not in MODES:
        raise ValueError(mode)
    n = len(profile)
    lost = lost if lost is not None else [False] * n
    if len(lost) != n:
        raise ValueError("lost schedule length must match the profile")
    valid = valid_schedule(lost)
    ctl = policy(c0); code = c0
    errs, codes, obs, ref_state, states = [], [], [], [], []
    jprev = rng.uniform(-jitter_ns, jitter_ns) * 1e-9 if jitter_ns else 0.0
    phase = 0.0
    span = 0            # counts accumulated since the last delivered observation (naive mode)
    span_frames = 0
    for i, (T, V) in enumerate(profile):
        f = pl.f(code, T, V)
        jk = rng.uniform(-jitter_ns, jitter_ns) * 1e-9 if jitter_ns else 0.0   # drawn every frame
        interval = dm.FRAME_S + jk - jprev; jprev = jk
        phase += f * interval
        cnt = math.floor(phase); phase -= cnt          # free-running counter keeps counting
        errs.append((f / dm.F_TARGET - 1) * 100); codes.append(code)
        span += cnt; span_frames += 1
        o = None
        if valid[i]:
            o = cnt - dm.N_NOM
            ref_state.append("tracking")
            span = 0; span_frames = 0
        elif lost[i]:
            ref_state.append("holdover")
        else:
            ref_state.append("reacquiring")     # SOF back, interval not yet fresh (baseline only)
            if mode == "naive_nominal":
                o = span - dm.N_NOM             # WRONG by construction: multi-frame count as one frame
                span = 0; span_frames = 0
        obs.append(o)
        if o is not None:
            code = ctl.update(o)
        if trace_state:
            states.append(dict(vars(ctl)))
    return {"errs": errs, "codes": codes, "obs": obs, "valid": valid, "ref_state": ref_state,
            "ctl": ctl, "states": states}


# ---------------------------------------------------------------- reachability / status
def reach(pl, T, V):
    """Static reachability at (T, V): can any single code be inside the band (inst), and can a
    code dither bracket the target closely enough that a window mean can be inside it (avg)."""
    e = [(pl.f(c, T, V) / dm.F_TARGET - 1) * 100 for c in range(256)]
    return {"inst": min(abs(x) for x in e) <= dm.BAND,
            "avg": min(e) <= dm.BAND and max(e) >= -dm.BAND}


def recovery(errs, end_idx, kind):
    """Frames after end_idx until the quantity stays in band for HOLD frames; None if never.
    kind 'inst' = per-frame error, 'avg16' = 16-frame moving mean (separate readings)."""
    if kind == "inst":
        return dm.lock_frame(errs[end_idx:], dm.BAND, HOLD)
    ma = dm.movavg(errs, 16)           # ma[j] is the mean of errs[j .. j+15]; align to the window end
    start = max(0, end_idx - 15)
    r = dm.lock_frame(ma[start:], dm.BAND, HOLD)
    if r is None:
        return None
    return max(0, start + r + 15 - end_idx)


def status(rec, reachable):
    if rec is not None:
        return "recovered"
    return "controller_not_recovered" if reachable else "plant_unreachable"


def analyze(pl, run, base, s, L, final_cond):
    """Metrics for one outage run against its no-loss baseline run of the same profile."""
    e = s + L                                   # first frame whose closing SOF arrives again
    errs, codes = run["errs"], run["codes"]
    hold_end = min(e + 1, len(errs) - 1)        # code is frozen through frame e+1
    hz = errs[s:hold_end + 1]
    rc = reach(pl, *final_cond)
    out = {
        "true_err_at_outage_start": errs[s], "true_err_at_holdover_end": errs[hold_end],
        "true_drift_during_holdover": errs[hold_end] - errs[s],
        "true_absmax_during_holdover": max(abs(x) for x in hz),
        "frozen_code": codes[s],
        "observed_during_outage": "none",       # no observation exists; not reported as an error
        "last_valid_count_err_before": next((run["obs"][i] for i in range(s - 1, -1, -1) if run["obs"][i] is not None), None),
        "first_valid_count_err_after": next((run["obs"][i] for i in range(e, len(errs)) if run["obs"][i] is not None and run["valid"][i]), None),
        "update_resume_frames_after_outage_end": next((i - e for i in range(e, len(errs)) if run["valid"][i]), None),
        "max_excursion_pct": max(abs(x) for x in errs[s:]),
        "baseline_max_excursion_pct": max(abs(x) for x in base["errs"][s:]),
        "rail_contact": any(c in (0, 255) for c in codes[s:]),
        "baseline_rail_contact": any(c in (0, 255) for c in base["codes"][s:]),
        "final_code": codes[-1], "final_err_pct": errs[-1],
        "reachable_inst": rc["inst"], "reachable_avg16": rc["avg"],
    }
    for kind in ("inst", "avg16"):
        rec = recovery(errs, e, kind); brec = recovery(base["errs"], e, kind)
        out[f"reacq_{kind}_frames"] = rec
        out[f"status_{kind}"] = status(rec, rc["inst" if kind == "inst" else "avg"])
        out[f"baseline_reacq_{kind}_frames"] = brec
        out[f"baseline_status_{kind}"] = status(brec, rc["inst" if kind == "inst" else "avg"])
    return out


# ---------------------------------------------------------------- scenarios
def make_profile(case, n_after_start):
    """Return (profile, outage_start).  Conditions follow the existing experiments."""
    if case == "constant_27C_3p3V":
        pre = [(27.0, 3.3)] * WARM
        s = len(pre)
        total = s + n_after_start
        return pre + [(27.0, 3.3)] * (total - s), s
    if case.startswith("ramp_"):
        rate = 1.0 if case == "ramp_1C_per_s" else 20.0
        n_ramp = int(125.0 / rate * 1000)
        s = WARM + n_ramp // 2                  # outage starts mid-ramp
        total = s + n_after_start
        prof = [(-40.0, 3.3)] * WARM + [(min(85.0, -40.0 + rate * i / 1000.0), 3.3) for i in range(total - WARM)]
        return prof, s
    if case.startswith("vdd_step_"):
        T = 27.0 if case.endswith("+27C") else -40.0
        s = WARM - 1                            # outage begins one frame before the 3.3 -> 3.0 V step
        total = s + n_after_start
        return [(T, 3.3)] * WARM + [(T, 3.0)] * (total - WARM), s
    raise KeyError(case)


CASES = ("constant_27C_3p3V", "ramp_1C_per_s", "ramp_20C_per_s", "vdd_step_+27C", "vdd_step_-40C")


def scenario_runs(pl, policy, case, jitter, seed, lengths=OUTAGES):
    """Yield (L, analysis) for each outage length; baseline computed once per case."""
    rows = []
    # the profile must be long enough for the longest outage plus the tail; same profile for all L
    prof, s = make_profile(case, max(lengths) + TAIL)
    base = run_loop_outage(pl, policy, 128, prof, jitter, random.Random(seed))
    for L in lengths:
        n = s + L + TAIL
        p = prof[:n]
        b = {k: base[k][:n] for k in ("errs", "codes", "obs", "valid")}
        r = run_loop_outage(pl, policy, 128, p, jitter, random.Random(seed), outage_schedule(n, s, L))
        rows.append((L, analyze(pl, r, b, s, L, p[-1])))
    return rows, s


# ---------------------------------------------------------------- regression vs committed results
def regression_vs_committed(plants, policies):
    """No-loss cold-start steady state vs the committed results.csv (jitter 0).  Read-only."""
    path = os.path.join(dm.ROOT, "sim/discipline/results/20261009T010000Z/results.csv")
    ref = {(r["plant"], r["policy"]): r for r in csv.DictReader(open(path))
           if r["exp"] == "cold_start_27C_3p3V" and float(r["jitter_ns"]) == 0.0}
    worst = 0.0; n = 0
    for pl in plants:
        for P in policies:
            r = run_loop_outage(pl, P, 128, [(27.0, 3.3)] * 8000, 0.0, random.Random(dm.SEED))
            st = dm.stats(r["errs"][-2000:])
            h = ref[(f"{pl.name}/{pl.side}", P.name)]
            for k, kk in (("min", "ss_min"), ("max", "ss_max"), ("absmax", "ss_absmax")):
                worst = max(worst, abs(st[k] - float(h[kk]))); n += 1
    return {"compared_values": n, "max_abs_diff_pct": worst, "committed_precision_pct": 5e-5}


# ---------------------------------------------------------------- main
def fmt(v):
    if v is None: return "none"
    if isinstance(v, float): return f"{v:.4f}"
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runid", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    a = ap.parse_args()
    outdir = os.path.join(HERE, "results", a.runid)
    if os.path.exists(outdir):
        sys.exit(f"refusing to overwrite {outdir} (results/ is append-only)")
    plants, checks, curve = dm.build()
    os.makedirs(outdir)
    reg = regression_vs_committed(plants, dm.POLICIES)
    assert reg["max_abs_diff_pct"] <= 1e-4, reg
    rows = []
    for pl in plants:
        pn = f"{pl.name}/{pl.side}"
        for P in dm.POLICIES:
            for case in CASES:
                res, s = scenario_runs(pl, P, case, 0.0, dm.SEED)
                for L, an in res:
                    rows.append({"case": case, "plant": pn, "policy": P.name, "jitter_ns": 0.0,
                                 "outage_start_frame": s, "lost_sofs": L, **an})
    cols = list(rows[0].keys())
    with open(os.path.join(outdir, "outage_results.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r[k]) for k in cols])
    man = {"runid": a.runid, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "git_head": subprocess.run(["git", "-C", dm.ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           "python": platform.python_version(), "seed": dm.SEED, "kind": "behavioural simulation, no analogue sim",
           "inputs_sha256": {p: dm.sha(p) for p in (dm.SCH_CSV, dm.EXT_CSV, dm.GRD_CSV,
                                                    "sim/discipline/discipline_model.py",
                                                    "sim/discipline/outage_model.py",
                                                    "sim/discipline/results/20261009T010000Z/results.csv")},
           "controller_policy": {"name": "freeze_reacquire",
                                 "rule": "invalid observations are not delivered; trim code and all controller state frozen; "
                                         "first SOF after an outage is a baseline only; updates resume at the next one-frame observation",
                                 "valid_observation": "not lost[i] and not lost[i-1]; lost[i] means SOF_{i+1} absent",
                                 "status": "assumption for sensitivity analysis, not a hardware decision"},
           "outage_schedules": {"cases": list(CASES), "lost_sofs": list(OUTAGES), "start": {
               "constant_27C_3p3V": "frame 8000 after cold-start warm-up", "ramp_*": "mid-ramp",
               "vdd_step_*": "one frame before the 3.3 -> 3.0 V step"},
               "tail_frames_after_outage": TAIL, "warm_frames": WARM, "durations_are_assumptions": True,
               "jitter_ns_cases": [0.0]},
           "recovery_definition": {"band_pct": dm.BAND, "hold_frames": HOLD,
                                   "inst": "per-frame true error in band", "avg16": "16-frame mean of true error in band",
                                   "note": "both readings reported; neither is selected as the spec interpretation"},
           "no_loss_regression_vs_committed_20261009T010000Z": reg,
           "limitations": [
               "plant is the interpolated 24-code model of DR-0021 (sub-16-code structure and mismatch absent)",
               "temperature/supply factor assumed code-independent (bounded 0.95-1.24 % in DR-0021)",
               "outage lengths 1/16/256 ms and the freeze policy are engineering assumptions, not sourced USB figures",
               "ideal counter and reference apart from SOF jitter; no jitter is applied in the sweep (jitter 0 only)",
               "oscillator free-runs on the frozen code; no claim that runtime discipline exists in hardware"]}
    json.dump(man, open(os.path.join(outdir, "manifest.json"), "w"), indent=2)
    write_summary(outdir, a.runid, rows, man)
    print("wrote", outdir)


def write_summary(outdir, runid, rows, man):
    L = [f"# SOF reference-loss model run {runid}\n",
         "BEHAVIOURAL SIMULATION ONLY (issue #128). Extends the DR-0021 candidate discipline loop with a "
         "reference-availability schedule and the `freeze_reacquire` policy. Nothing here is a hardware, USB-"
         "compliance, or ratified-spec claim; the reserved runtime-disciplined row is unchanged. Plant = the "
         "interpolated 24-code model of DR-0021 (see its uncertainty; sub-16-code structure absent). Outage lengths "
         "(1 / 16 / 256 lost SOFs) and the freeze behaviour are engineering assumptions.\n",
         "Policy: lost SOF -> observation not delivered, trim code and controller state frozen; the first SOF back "
         "is a baseline only; updates resume at the next one-frame interval. No 'locked' flag is carried across an "
         "outage. True frequency during the outage is reported separately from observed count error (none exists "
         "while the reference is absent). Per-frame (`inst`) and 16-frame-mean (`avg16`) readings are separate; "
         "neither is chosen as the spec interpretation. Status: `recovered`; `plant_unreachable` (no code / dither "
         "can reach the band at the final condition); `controller_not_recovered` (reachable, but the loop did not "
         f"hold the band for {HOLD} frames). Each row also carries the no-loss baseline of the same profile.\n",
         f"No-loss regression against committed 20261009T010000Z cold-start values: {man['no_loss_regression_vs_committed_20261009T010000Z']}\n"]
    for case in CASES:
        L.append(f"\n## {case}\n")
        L.append("Aggregated over the 10 plants; `worst` = maximum. Frames = ms.\n")
        L.append("| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for n in OUTAGES:
            for P in dm.POLICIES:
                rs = [r for r in rows if r["case"] == case and r["lost_sofs"] == n and r["policy"] == P.name]
                def cnt(k, v): return sum(1 for r in rs if r[k] == v)
                def worst(k):
                    xs = [r[k] for r in rs]
                    return "never" if any(x is None for x in xs) else str(max(xs))
                L.append(f"| {n} | {P.name} | {max(abs(r['true_drift_during_holdover']) for r in rs):.3f} | "
                         f"{max(r['true_absmax_during_holdover'] for r in rs):.3f} | "
                         f"{max(r['max_excursion_pct'] for r in rs):.3f} ({max(r['baseline_max_excursion_pct'] for r in rs):.3f}) | "
                         f"{sum(r['rail_contact'] for r in rs)} ({sum(r['baseline_rail_contact'] for r in rs)}) of {len(rs)} | "
                         f"{rs[0]['update_resume_frames_after_outage_end']} | "
                         f"{cnt('status_avg16','recovered')} / {cnt('status_avg16','plant_unreachable')} / {cnt('status_avg16','controller_not_recovered')} ({cnt('baseline_status_avg16','recovered')}) | "
                         f"{worst('reacq_avg16_frames')} | "
                         f"{cnt('status_inst','recovered')} / {cnt('status_inst','plant_unreachable')} / {cnt('status_inst','controller_not_recovered')} | "
                         f"{worst('reacq_inst_frames')} |")
    L.append("\nPer plant x policy x outage detail: `outage_results.csv`. Inputs, schedules, policy and limitations: `manifest.json`.\n")
    open(os.path.join(outdir, "summary.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
