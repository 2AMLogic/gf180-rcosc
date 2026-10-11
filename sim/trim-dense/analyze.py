#!/usr/bin/env python3
"""Dense trim-code report analyzer (issue #98, offline subset of #87).

Input : `klt sim --format json` reports, one per request written by
        sim/trim-dense/prepare.py, named `report_<tag>.json` in --reports-dir
        (tag = `<variant>_<corner>_cXX`, listed in the bench's provenance.json).
Output: results.json / steps.csv / summary.md in a NEW directory (never
        overwritten).  Fixture runs (--synthetic, or reports carrying
        `"synthetic": true`) are labelled "SYNTHETIC FIXTURE - NOT MEASURED
        EVIDENCE".

Definitions (per variant x corner curve; f[c] in Hz for trim code c):
  signed adjacent step   step[c] = 100 * (f[c+1] / f[c] - 1)   [%], c = 0..254
  worst positive step    largest step among steps > 0 (null if none)
  worst negative step    most negative step among steps < 0 (null if none)
  non-positive transition  every c with step[c] <= 0 (a constant frequency is
                         NOT monotone-increasing; it is listed)
  carry transitions      0x7F->0x80, 0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0
  ratified resolution    nominal LSB = 80 % / 255 = 0.313725 %/code,
                         half-LSB = 40 % / 255 = 0.156863 % (DR-0003, Row 2).
                         For each step: deviation = step - nominal [percentage
                         points]; dnl = step / nominal - 1 [LSB].  A step is
                         "outside half-LSB" when |deviation| > half-LSB, i.e. it
                         lies outside (0.156863, 0.470588) %.  Also reported:
                         mean step = 100*(f[255]/f[0]-1)/255 (the same
                         arithmetic convention as the 80 %/255 span).
  The comparison is descriptive.  Whether it satisfies the ratified rows is the
  campaign's (#87) decision, never this offline harness's.

Validation: a curve needs exactly one entry for each code 0..255 (unordered
input is normalized by code).  Missing, duplicate, failed/errored,
non-finite, non-positive or non-numeric entries make the curve INCOMPLETE
(missing/failed) or INVALID (everything else); no value is imputed.

Provenance: a non-synthetic run requires --manifest, an execution manifest
filled from prepare.py's manifest.template.json (git/tool/PDK revision,
solver, backend, provenance hash) and every report must carry
environment.remote (batch).  Any gap fails the run explicitly.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

N_CODES = 256
SYN_BANNER = "SYNTHETIC FIXTURE - NOT MEASURED EVIDENCE"
NOPROV_BANNER = "PROVENANCE INCOMPLETE - NOT USABLE AS EVIDENCE"
NOMINAL_STEP_PCT = 80.0 / 255.0        # DR-0003 Row 2: 0.313725 %/code
HALF_LSB_PCT = 40.0 / 255.0            # 0.156863 %
CARRIES = ((0x7F, 0x80), (0xBF, 0xC0), (0xDF, 0xE0), (0xEF, 0xF0))
OK_STATUS = {"pass"}
BAD_REPORT_STATUS = {"refused", "rejected", "submit_failed", "error", "errored", "fail", "failed"}
MANIFEST_REQUIRED = ("git_sha", "git_dirty", "klt_version", "engine", "engine_version", "pdk",
                     "pdk_revision", "backend", "executed_utc", "provenance_sha256")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class CurveError(Exception):
    """Carries a list of {kind, code, detail} problems."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("; ".join(f"{p['kind']}[{p['code']}]: {p['detail']}" for p in problems[:5]))


def step_pct(f_lo: float, f_hi: float) -> float:
    return 100.0 * (f_hi / f_lo - 1.0)


def normalize_curve(entries) -> list[float]:
    """entries: iterable of {"code": int, "freq_hz": number, optional "status"}.
    Returns f[0..255] ordered by code or raises CurveError listing every problem."""
    problems = []
    seen: dict[int, float] = {}

    def bad(kind, code, detail):
        problems.append({"kind": kind, "code": code, "detail": detail})
        seen.setdefault(code, math.nan)

    for e in entries:
        code = e.get("code") if isinstance(e, dict) else None
        if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < N_CODES:
            problems.append({"kind": "bad_code", "code": code, "detail": f"code {code!r} is not an int in 0..255"})
            continue
        if code in seen:
            bad("duplicate", code, "more than one entry for this code")
            continue
        status = e.get("status", "pass")
        f = e.get("freq_hz")
        if status not in OK_STATUS:
            bad("failed", code, f"entry status {status!r}" + (f": {e['error']}" if e.get("error") else ""))
        elif isinstance(f, bool) or not isinstance(f, (int, float)):
            bad("non_finite", code, f"frequency {f!r} is not a number")
        elif not math.isfinite(f):
            bad("non_finite", code, f"frequency {f!r} is not finite")
        elif f <= 0:
            bad("non_positive", code, f"frequency {f!r} is not positive")
        else:
            seen[code] = float(f)
    for c in range(N_CODES):
        if c not in seen:
            problems.append({"kind": "missing", "code": c, "detail": "no entry for this code"})
    if problems:
        raise CurveError(problems)
    return [seen[c] for c in range(N_CODES)]


def curve_status(problems) -> str:
    kinds = {p["kind"] for p in problems}
    return "INCOMPLETE" if kinds <= {"missing", "failed"} else "INVALID"


def step_table(freqs) -> list[dict]:
    rows = []
    for c in range(N_CODES):
        rows.append({"code": c, "code_hex": f"0x{c:02X}", "freq_hz": freqs[c],
                     "step_to_next_pct": step_pct(freqs[c], freqs[c + 1]) if c + 1 < N_CODES else None})
    return rows


def _tr(freqs, c) -> dict:
    return {"from_code": c, "to_code": c + 1, "from_hex": f"0x{c:02X}", "to_hex": f"0x{c + 1:02X}",
            "f_from_hz": freqs[c], "f_to_hz": freqs[c + 1], "step_pct": step_pct(freqs[c], freqs[c + 1])}


def summarize(freqs) -> dict:
    steps = [step_pct(freqs[c], freqs[c + 1]) for c in range(N_CODES - 1)]
    pos = [c for c, s in enumerate(steps) if s > 0]
    neg = [c for c, s in enumerate(steps) if s < 0]
    nonpos = [c for c, s in enumerate(steps) if s <= 0]
    wp = max(pos, key=lambda c: steps[c]) if pos else None
    wn = min(neg, key=lambda c: steps[c]) if neg else None
    dev = [s - NOMINAL_STEP_PCT for s in steps]
    outside = [c for c, d in enumerate(dev) if abs(d) > HALF_LSB_PCT]
    span = step_pct(freqs[0], freqs[-1])
    mean = span / (N_CODES - 1)
    imax = max(range(N_CODES - 1), key=lambda c: abs(dev[c]))
    return {
        "formula": "step[c] = 100*(f[c+1]/f[c]-1) [%]",
        "f_first_hz": freqs[0], "f_last_hz": freqs[-1], "span_pct": span,
        "worst_positive_step": _tr(freqs, wp) if wp is not None else None,
        "worst_negative_step": _tr(freqs, wn) if wn is not None else None,
        "min_step": _tr(freqs, min(range(N_CODES - 1), key=lambda c: steps[c])),
        "max_step": _tr(freqs, max(range(N_CODES - 1), key=lambda c: steps[c])),
        "non_positive_transitions": [_tr(freqs, c) for c in nonpos],
        "strictly_increasing": not nonpos,
        "carry_transitions": [_tr(freqs, a) | {"carry": f"0x{a:02X}->0x{b:02X}"} for a, b in CARRIES],
        "ratified_comparison": {
            "basis": "DR-0003 Row 2: 80 %/255 codes; descriptive only, verdict belongs to #87",
            "nominal_step_pct": NOMINAL_STEP_PCT, "half_lsb_pct": HALF_LSB_PCT,
            "mean_step_pct": mean, "mean_step_over_nominal": mean / NOMINAL_STEP_PCT,
            "steps_outside_half_lsb_count": len(outside),
            "steps_outside_half_lsb_codes": [f"0x{c:02X}->0x{c + 1:02X}" for c in outside],
            "max_abs_deviation_pct": abs(dev[imax]), "max_abs_dnl_lsb": abs(dev[imax]) / NOMINAL_STEP_PCT,
            "max_abs_deviation_at": f"0x{imax:02X}->0x{imax + 1:02X}",
        },
    }


# ---------------------------------------------------------------- reports --

def entry_from_report(entry: dict, report_path: Path, allow_nonremote: bool) -> tuple[dict, dict]:
    """One request tag -> ({code, freq_hz, status, error}, meta)."""
    code = entry["code"]
    out = {"code": code, "freq_hz": None, "status": "pass"}
    meta = {"tag": entry["tag"], "synthetic": False, "engine_version": None, "remote": None}

    def fail(msg):
        out["status"] = "failed"
        out["error"] = msg
        return out, meta
    try:
        d = json.loads(Path(report_path).read_text())
    except OSError as e:
        return fail(f"report unreadable: {e}")
    except ValueError as e:
        return fail(f"report is not valid JSON: {e}")
    if not isinstance(d, dict):
        return fail("report is not a JSON object")
    env = d.get("environment") or {}
    meta |= {"synthetic": bool(d.get("synthetic")), "engine_version": env.get("engine_version"),
             "remote": env.get("remote"), "klt_version": (d.get("provenance") or {}).get("klt_version")}
    if str(d.get("status")).lower() in BAD_REPORT_STATUS or d.get("refused"):
        return fail(f"report status {d.get('status')!r} {d.get('error') or d.get('message') or ''}".rstrip())
    corners = d.get("corners")
    if not isinstance(corners, list) or len(corners) != 1 or d.get("corner_count") not in (None, 1):
        return fail("expected exactly 1 corner in report")
    c = corners[0]
    if c.get("process") != entry["process"] or c.get("temperature_c") != entry["temperature_c"]:
        return fail(f"corner {c.get('process')}/{c.get('temperature_c')} does not match request "
                    f"{entry['process']}/{entry['temperature_c']}")
    if c.get("status") != "pass":
        return fail(f"klt corner status {c.get('status')!r}" + (f": {c.get('error')}" if c.get("error") else ""))
    sha = env.get("netlist_sha256")
    if sha is not None and sha != entry["sha256"]["netlist"]:
        return fail("report netlist_sha256 does not match the generated testbench")
    if not meta["synthetic"] and not env.get("remote") and not allow_nonremote:
        return fail("report was not executed on the batch fleet (environment.remote missing); no local fallback")
    ms = [m for m in (c.get("measurements") or []) if isinstance(m, dict) and m.get("name") == "fosc"]
    if len(ms) != 1:
        return fail(f"expected exactly one fosc measurement, found {len(ms)}")
    m = ms[0]
    if m.get("status") not in OK_STATUS:
        return fail(f"fosc measurement status {m.get('status')!r}")
    out["freq_hz"] = m.get("value")
    return out, meta


def check_manifest(path, prov_path: Path, prov: dict) -> list[str]:
    errs = []
    if path is None:
        return ["no --manifest: git/tool/PDK revision provenance missing for a non-synthetic run"]
    try:
        m = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return [f"manifest unreadable: {e}"]
    if not isinstance(m, dict):
        return ["manifest is not a JSON object"]
    if m.get("_template"):
        errs.append("manifest is still the unfilled template (remove `_template` after filling)")
    for k in MANIFEST_REQUIRED:
        if m.get(k) in (None, ""):
            errs.append(f"manifest field {k!r} missing/null")
    if m.get("git_sha") and not HEX40.match(str(m["git_sha"])):
        errs.append("git_sha is not a 40-hex commit")
    if "git_dirty" in m and not isinstance(m["git_dirty"], bool):
        errs.append("git_dirty must be a boolean")
    pr = m.get("pdk_revision")
    if pr and pr != "unknown" and not HEX40.match(str(pr)):
        errs.append("pdk_revision must be a 40-hex open_pdks commit or 'unknown'")
    if pr == "unknown" and not m.get("pdk_revision_reason"):
        errs.append("pdk_revision 'unknown' requires pdk_revision_reason")
    if m.get("backend") not in (None, "batch"):
        errs.append(f"backend {m.get('backend')!r} is not 'batch'")
    want = hashlib.sha256(Path(prov_path).read_bytes()).hexdigest()
    if m.get("provenance_sha256") not in (None, "", want):
        errs.append("provenance_sha256 does not match the bench provenance.json")
    solver = m.get("solver")
    if not isinstance(solver, dict):
        errs.append("manifest field 'solver' missing")
    else:
        for k in ("reltol", "abstol", "vntol", "tstep", "tstop"):
            if solver.get(k) != prov["settings"].get(k):
                errs.append(f"manifest solver.{k}={solver.get(k)!r} != generated {prov['settings'].get(k)!r}")
    exp = prov["settings"].get("engine_version_expected", "unspecified")
    if exp != "unspecified" and m.get("engine_version") not in (None, exp):
        errs.append(f"manifest engine_version {m.get('engine_version')!r} != expected {exp!r}")
    return errs


def analyse_campaign(bench_dir: Path, reports_dir: Path, manifest=None, synthetic: bool = False) -> dict:
    bench_dir, reports_dir = Path(bench_dir), Path(reports_dir)
    prov_path = bench_dir / "provenance.json"
    prov = json.loads(prov_path.read_text())
    groups: dict[tuple, list] = {}
    metas = []
    for e in prov["requests"]:
        groups.setdefault((e["variant"], e["corner"]), []).append(e)
    # classify synthetic first so remote checks and the manifest rule apply uniformly
    probe = {}
    for e in prov["requests"]:
        rp = reports_dir / f"report_{e['tag']}.json"
        probe[e["tag"]] = rp
    is_syn = synthetic
    for rp in probe.values():
        try:
            if json.loads(rp.read_text()).get("synthetic"):
                is_syn = True
        except (OSError, ValueError, AttributeError):
            pass
    curves = []
    for (variant, corner), ents in groups.items():
        entries, extras = [], []
        for e in sorted(ents, key=lambda x: x["code"]):
            rp = probe[e["tag"]]
            if not rp.exists():
                continue                      # absent -> reported as `missing` by normalize_curve
            ent, meta = entry_from_report(e, rp, allow_nonremote=is_syn)
            if not is_syn and meta["synthetic"]:
                ent = {"code": e["code"], "freq_hz": None, "status": "failed",
                       "error": "synthetic report inside a non-synthetic run"}
            entries.append(ent)
            metas.append(meta)
        # reports for extra files that name the same tag cannot exist (one file per tag);
        # duplicates are exercised through normalize_curve directly.
        c0 = ents[0]
        rec = {"variant": variant, "corner": corner, "process": c0["process"],
               "temperature_c": c0["temperature_c"], "vdd_v": c0["vdd_v"], "n_requests": len(ents)}
        try:
            f = normalize_curve(entries)
            rec |= {"status": "OK", "table": step_table(f), "summary": summarize(f)}
        except CurveError as ce:
            rec |= {"status": curve_status(ce.problems), "problems": ce.problems}
        curves.append(rec)
    engines = sorted({str(m["engine_version"]) for m in metas if m["engine_version"] is not None})
    run_errors = []
    if not is_syn:
        run_errors += check_manifest(manifest, prov_path, prov)
        if len(engines) > 1:
            run_errors.append(f"mixed simulator versions across reports: {engines}")
        if manifest is not None:
            try:
                me = json.loads(Path(manifest).read_text()).get("engine_version")
            except (OSError, ValueError, AttributeError):
                me = None
            if me and engines and engines != [str(me)]:
                run_errors.append(f"report engine_version {engines} != manifest engine_version {me!r}")
    all_ok = all(c["status"] == "OK" for c in curves) and not run_errors
    return {
        "banner": SYN_BANNER if is_syn else (NOPROV_BANNER if run_errors else "MEASURED CAMPAIGN DATA (analysis only; verdict belongs to #87)"),
        "synthetic": is_syn, "all_curves_valid": all_ok, "run_errors": run_errors,
        "engine_versions_in_reports": engines,
        "bench_provenance_sha256": hashlib.sha256(prov_path.read_bytes()).hexdigest(),
        "bench_inputs": prov.get("inputs"), "settings": prov.get("settings"),
        "curves": curves,
    }


# ----------------------------------------------------------------- output --

def _fmt_tr(t) -> str:
    return "none" if t is None else f"{t['from_hex']}->{t['to_hex']} {t['step_pct']:+.5f} %"


def write_run(out: Path, res: dict) -> None:
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"results directory exists and is not empty: {out} (append-only)")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2) + "\n")
    with open(out / "steps.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["banner", "variant", "corner", "code", "code_hex", "freq_hz", "step_to_next_pct"])
        for c in res["curves"]:
            for r in c.get("table", []):
                w.writerow([res["banner"], c["variant"], c["corner"], r["code"], r["code_hex"],
                            repr(r["freq_hz"]), "" if r["step_to_next_pct"] is None else repr(r["step_to_next_pct"])])
    L = [f"# Dense trim-code step analysis", "", f"**{res['banner']}**", ""]
    for e in res["run_errors"]:
        L.append(f"- RUN ERROR: {e}")
    if res["run_errors"]:
        L.append("")
    L += [f"Nominal step {NOMINAL_STEP_PCT:.6f} %/code, half-LSB {HALF_LSB_PCT:.6f} % (80 %/255; DR-0003). "
          "Step = 100*(f[c+1]/f[c]-1). Comparison is descriptive; verdict belongs to #87.", ""]
    for c in res["curves"]:
        L += [f"## {c['variant']} / {c['corner']}: {c['status']}", ""]
        if c["status"] != "OK":
            for p in c["problems"][:50]:
                L.append(f"- {p['kind']} code {p['code']}: {p['detail']}")
            if len(c["problems"]) > 50:
                L.append(f"- ... {len(c['problems']) - 50} more")
            L.append("")
            continue
        s = c["summary"]
        rc = s["ratified_comparison"]
        L += [f"- f[0x00] = {s['f_first_hz'] / 1e6:.6f} MHz, f[0xFF] = {s['f_last_hz'] / 1e6:.6f} MHz, span {s['span_pct']:+.4f} %",
              f"- worst positive step: {_fmt_tr(s['worst_positive_step'])}",
              f"- worst negative step: {_fmt_tr(s['worst_negative_step'])}",
              f"- smallest / largest signed step: {_fmt_tr(s['min_step'])} / {_fmt_tr(s['max_step'])}",
              f"- non-positive transitions: {len(s['non_positive_transitions'])}"]
        for t in s["non_positive_transitions"]:
            L.append(f"  - {_fmt_tr(t)}")
        L.append("- carry transitions:")
        for t in s["carry_transitions"]:
            L.append(f"  - {t['carry']}: {t['step_pct']:+.5f} %")
        L += [f"- mean step {rc['mean_step_pct']:.5f} %/code ({rc['mean_step_over_nominal']:.4f} x nominal)",
              f"- steps outside nominal +/- half-LSB: {rc['steps_outside_half_lsb_count']}; "
              f"max |deviation| {rc['max_abs_deviation_pct']:.5f} % ({rc['max_abs_dnl_lsb']:.3f} LSB) at {rc['max_abs_deviation_at']}", ""]
    (out / "summary.md").write_text("\n".join(L) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bench-dir", type=Path, required=True, help="prepare.py output dir")
    ap.add_argument("--reports-dir", type=Path, required=True, help="dir of report_<tag>.json files")
    ap.add_argument("--outdir", type=Path, required=True, help="NEW results directory")
    ap.add_argument("--manifest", type=Path, default=None, help="filled execution manifest (required unless synthetic)")
    ap.add_argument("--synthetic", action="store_true", help="label the run as synthetic fixture output")
    a = ap.parse_args()
    try:
        res = analyse_campaign(a.bench_dir, a.reports_dir, a.manifest, a.synthetic)
        write_run(a.outdir, res)
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"analyze.py: {e}")
    print(f"{res['banner']}: {len(res['curves'])} curve(s), all valid: {res['all_curves_valid']}; wrote {a.outdir}")
    return 0 if res["all_curves_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
