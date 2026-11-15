#!/usr/bin/env python3
"""Paired engine-version comparison and bench attestation for sim/trim-dense
(issue #378).

`analyze.py` deliberately refuses a version-mixed campaign and requires a
complete 256-code curve, so it is the wrong tool for a sparse paired A/B
sample.  This script is the two small jobs the A/B needs, offline, with no
simulator:

`compare`  Read two report sets (`report_<tag>.json`, one dir per engine
           version) and report, per curve and overall, the paired per-code
           frequency delta `100 * (f_B / f_A - 1)` [%] -- median, mean, min,
           max and the count whose |delta| exceeds the ratified half-LSB
           (40/255 = 0.156863 %, DR-0003 Row 2) -- alongside the per-code
           pairs.  A tag present in only one set is REPORTED, never dropped;
           unpaired tags and non-passing reports fail the run (exit 1).
           Diagnostic-code tallies per curve are informational only.

`attest`   Confirm that an A/B bench reproduces a frozen campaign's requests
           byte-for-byte once the engine-version pin key is removed (which is
           what makes the comparison paired: the simulator is the only changed
           input), and audit the A/B reports' environment (uniform engine
           version / build hash / models hash, distinct remote job ids).

Both modes are read-only except `compare --out-json PATH`, which refuses to
overwrite.  Neither mode submits anything.

Usage:
    python3 -I sim/trim-dense/compare_engine.py compare \\
        --reports-a DIR --reports-b DIR [--curves c1,c2] [--out-json PATH]

    python3 -I sim/trim-dense/compare_engine.py attest \\
        --ab-bench DIR --ab-prov provenance.json --frozen-prov provenance.json \\
        [--pin-key engine_version] [--tags t1,t2] \\
        [--ab-reports DIR] [--expect-engine 47] [--expect-models-sha HEX64]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

_SIM_DIR = Path(__file__).resolve().parent.parent
if str(_SIM_DIR) not in sys.path:
    sys.path.insert(0, str(_SIM_DIR))
import analyze  # noqa: E402  single source of HALF_LSB_PCT (DR-0003 Row 2)

OK_STATUS = {"pass"}
PIN_DEFAULT = "engine_version"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def split_tag(stem: str) -> tuple[str, int] | None:
    """`report_<variant>_<corner>_cXX` -> (curve, code); None if not a report tag.

    Corner tags (`tt_27C_3p3V`, ...) hold no lowercase `_c`, so the last
    `_c` separator is always the code's."""
    if not stem.startswith("report_"):
        return None
    stem = stem[len("report_"):]
    if "_c" not in stem:
        return None
    curve, _, code = stem.rpartition("_c")
    if not (len(code) == 2 and all(ch in "0123456789ABCDEF" for ch in code)):
        return None
    return curve, int(code, 16)


def read_report(p: Path) -> tuple[dict | None, list[str]]:
    """(extracted record, problems).  The record is None when unusable."""
    rep = read_json(p)
    if rep is None:
        return None, [f"{p.name}: unreadable or not JSON"]
    tag = split_tag(p.stem)
    if tag is None:
        return None, [f"{p.name}: not a report_<variant>_<corner>_cXX name"]
    curve, code = tag
    env = rep.get("environment") or {}
    problems = []
    rec = {
        "curve": curve, "code": code,
        "engine_version": env.get("engine_version"),
        "binary_sha256": (env.get("engine_build") or {}).get("binary_sha256"),
        "models_lib_sha256": env.get("models_lib_sha256"),
        "job_id": (env.get("remote") or {}).get("job_id"),
        "diagnostics": (rep.get("diagnostic_counts") or {}).get("by_code") or {},
    }
    if rep.get("status") not in OK_STATUS:
        problems.append(f"{p.name}: report status {rep.get('status')!r} != pass")
    corners = rep.get("corners") or []
    if len(corners) != 1:
        problems.append(f"{p.name}: {len(corners)} corners, expected 1")
    else:
        c = corners[0]
        rec["corner_status"] = c.get("status")
        if c.get("status") not in OK_STATUS:
            problems.append(f"{p.name}: corner status {c.get('status')!r} != pass")
        meas = [m for m in (c.get("measurements") or []) if m.get("name") == "fosc"]
        if len(meas) != 1:
            problems.append(f"{p.name}: {len(meas)} fosc measurements, expected 1")
        else:
            m = meas[0]
            v = m.get("value")
            if m.get("status") not in OK_STATUS:
                problems.append(f"{p.name}: fosc status {m.get('status')!r} != pass")
            elif not isinstance(v, (int, float)) or isinstance(v, bool) \
                    or not math.isfinite(v) or v <= 0:
                problems.append(f"{p.name}: fosc value {v!r} not finite positive")
            else:
                rec["fosc_hz"] = float(v)
    if problems:
        return None, problems
    return rec, []


def load_set(rdir: Path, curves: set[str] | None) -> tuple[dict[tuple[str, int], dict], list[str]]:
    """{('curve', code): record} for usable reports; problem lines otherwise."""
    got: dict[tuple[str, int], dict] = {}
    problems: list[str] = []
    for p in sorted(rdir.glob("report_*.json")):
        tag = split_tag(p.stem)
        if tag and curves is not None and tag[0] not in curves:
            continue
        rec, probs = read_report(p)
        if rec is None:
            if curves is None or (tag and tag[0] in curves):
                problems.extend(probs)
            continue
        if rec["code"] < 0 or rec["code"] > 255:
            problems.append(f"{p.name}: code {rec['code']} out of range")
            continue
        key = (rec["curve"], rec["code"])
        if key in got:
            problems.append(f"{p.name}: duplicate report for {rec['curve']} code 0x{rec['code']:02X}")
            continue
        got[key] = rec
    return got, problems


def _uniform(records: list[dict], field: str) -> tuple[str | None, list[str]]:
    vals = sorted({str(r[field]) for r in records if r.get(field) is not None})
    if len(vals) == 1:
        return vals[0], []
    return None, [f"non-uniform {field} across reports: {vals}"]


def cmd_compare(a: argparse.Namespace) -> int:
    half_lsb = a.half_lsb_pct
    curves = {c.strip() for c in a.curves.split(",")} if a.curves else None
    set_a, probs_a = load_set(a.reports_a, curves)
    set_b, probs_b = load_set(a.reports_b, curves)
    problems = probs_a + probs_b
    if curves:
        missing = sorted(curves - {c for c, _ in set_a | set_b})
        problems += [f"curve {c!r}: no reports in either set" for c in missing]
    names = sorted({c for c, _ in set_a} | {c for c, _ in set_b})
    curves_out = []
    pooled = []
    for curve in names:
        codes_a = {code for c, code in set_a if c == curve}
        codes_b = {code for c, code in set_b if c == curve}
        pairs = sorted(codes_a & codes_b)
        only_a = sorted(codes_a - codes_b)
        only_b = sorted(codes_b - codes_a)
        problems += [f"{curve}: code 0x{c:02X} has no counterpart in --reports-b" for c in only_a]
        problems += [f"{curve}: code 0x{c:02X} has no counterpart in --reports-a" for c in only_b]
        rows = []
        deltas = []
        for code in pairs:
            ra, rb = set_a[(curve, code)], set_b[(curve, code)]
            delta = 100.0 * (rb["fosc_hz"] / ra["fosc_hz"] - 1.0)
            deltas.append(delta)
            pooled.append(delta)
            rows.append({
                "code": code, "code_hex": f"0x{code:02X}",
                "f_a_hz": ra["fosc_hz"], "f_b_hz": rb["fosc_hz"],
                "delta_pct": delta,
                "over_half_lsb": abs(delta) > half_lsb,
            })
        for label, recs in ((a.label_a, [set_a[(curve, c)] for c in pairs]),
                            (a.label_b, [set_b[(curve, c)] for c in pairs])):
            if recs:
                _, probs = _uniform(recs, "engine_version")
                problems += [f"{curve}: set {label}: {p}" for p in probs]
        diag: dict[str, int] = {}
        for recs in ([set_a[(curve, c)] for c in pairs], [set_b[(curve, c)] for c in pairs]):
            for r in recs:
                for k, v in r["diagnostics"].items():
                    diag[k] = diag.get(k, 0) + int(v)
        out = {
            "curve": curve,
            "label_a": a.label_a, "label_b": a.label_b,
            "n_pairs": len(rows),
            "unpaired_in_a": [f"0x{c:02X}" for c in only_b],
            "unpaired_in_b": [f"0x{c:02X}" for c in only_a],
            "delta_pct": {
                "median": statistics.median(deltas) if deltas else None,
                "mean": statistics.fmean(deltas) if deltas else None,
                "min": min(deltas) if deltas else None,
                "max": max(deltas) if deltas else None,
                "abs_over_half_lsb_count": sum(1 for d in deltas if abs(d) > half_lsb),
                "half_lsb_pct": half_lsb,
            },
            "diagnostic_codes": diag,
            "pairs": rows,
        }
        curves_out.append(out)
        if not rows:
            print(f"{curve}: n=0 paired codes"
                  + (f"  unpaired: a-only={out['unpaired_in_b']} b-only={out['unpaired_in_a']}"
                     if only_a or only_b else ""))
            continue
        d = out["delta_pct"]
        print(f"{curve}: n={out['n_pairs']} "
              f"median={d['median']:+.4f}% mean={d['mean']:+.4f}% "
              f"min={d['min']:+.4f}% max={d['max']:+.4f}% "
              f"|delta|>half-LSB({half_lsb:.6f}%): {d['abs_over_half_lsb_count']}/{out['n_pairs']}"
              + (f"  unpaired: a-only={out['unpaired_in_b']} b-only={out['unpaired_in_a']}"
                 if only_a or only_b else ""))
        for label, recs in ((a.label_a, [set_a[(curve, c)] for c in pairs]),
                            (a.label_b, [set_b[(curve, c)] for c in pairs])):
            if recs:
                ev, _ = _uniform(recs, "engine_version")
                bs, _ = _uniform(recs, "binary_sha256")
                print(f"  set {label}: engine_version={ev} binary_sha256={bs}")
        if diag:
            print(f"  diagnostics (informational): {diag}")
    overall = None
    if pooled:
        overall = {
            "n_pairs": len(pooled),
            "median": statistics.median(pooled),
            "mean": statistics.fmean(pooled),
            "min": min(pooled),
            "max": max(pooled),
            "abs_over_half_lsb_count": sum(1 for d in pooled if abs(d) > half_lsb),
        }
        print(f"OVERALL: n={overall['n_pairs']} median={overall['median']:+.4f}% "
              f"mean={overall['mean']:+.4f}% min={overall['min']:+.4f}% max={overall['max']:+.4f}% "
              f"|delta|>half-LSB: {overall['abs_over_half_lsb_count']}/{overall['n_pairs']}")
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if a.out_json:
        if a.out_json.exists():
            print(f"compare_engine.py: --out-json path exists, refusing to overwrite: {a.out_json}",
                  file=sys.stderr)
            return 2
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps({
            "kind": "trim-dense-paired-engine-comparison",
            "half_lsb_pct": half_lsb,
            "label_a": a.label_a, "label_b": a.label_b,
            "overall": overall, "curves": curves_out,
            "problems": problems,
        }, indent=2) + "\n")
        print(f"wrote {a.out_json}")
    if not pooled:
        print("compare_engine.py: no paired codes found", file=sys.stderr)
        return 1
    return 1 if problems else 0


def cmd_attest(a: argparse.Namespace) -> int:
    ab_prov = read_json(a.ab_prov)
    frozen = read_json(a.frozen_prov)
    if not isinstance(ab_prov, dict) or not isinstance(frozen, dict):
        print("compare_engine.py: unreadable provenance JSON", file=sys.stderr)
        return 2
    ab_req = {e["tag"]: e for e in ab_prov.get("requests", [])}
    fz_req = {e["tag"]: e for e in frozen.get("requests", [])}
    tags = sorted(set(ab_req) & set(fz_req)) if not a.tags \
        else sorted(t.strip() for t in a.tags.split(","))
    problems = []
    for t in a.tags.split(",") if a.tags else []:
        t = t.strip()
        if t not in ab_req:
            problems.append(f"tag {t}: not in the A/B bench provenance")
        if t not in fz_req:
            problems.append(f"tag {t}: not in the frozen provenance")
    pinned = unpinned = 0
    for t in tags:
        if t not in ab_req or t not in fz_req:
            continue  # already reported above
        ea, ef = ab_req[t], fz_req[t]
        rf = a.ab_bench / ea["request"]
        raw = rf.read_bytes() if rf.is_file() else None
        if raw is None or sha256_bytes(raw) != ea["sha256"]["request"]:
            problems.append(f"{t}: bench request file does not match its own provenance sha256")
            continue
        req = read_json(rf)
        if req is None:
            problems.append(f"{t}: bench request file unreadable")
            continue
        if a.pin_key in req:
            del req[a.pin_key]
            pinned += 1
        else:
            unpinned += 1
        canonical = (json.dumps(req, indent=2) + "\n").encode()
        if sha256_bytes(canonical) != ef["sha256"]["request"]:
            problems.append(f"{t}: request hash (pin {a.pin_key!r} removed) "
                            f"{sha256_bytes(canonical)} != frozen {ef['sha256']['request']}")
        if ea["sha256"]["netlist"] != ef["sha256"]["netlist"]:
            problems.append(f"{t}: testbench hash {ea['sha256']['netlist']} != frozen "
                            f"{ef['sha256']['netlist']}")
    print(f"attested {len(tags)} tag(s): {pinned} carried the {a.pin_key!r} key, "
          f"{unpinned} did not; testbench hashes identical throughout")
    if a.ab_reports:
        recs, probs = load_set(a.ab_reports, None)
        problems += probs
        if recs:
            ev, p1 = _uniform(list(recs.values()), "engine_version")
            bs, p2 = _uniform(list(recs.values()), "binary_sha256")
            ms, p3 = _uniform(list(recs.values()), "models_lib_sha256")
            problems += p1 + p2 + p3
            jobs = [r["job_id"] for r in recs.values()]
            if any(j is None for j in jobs):
                problems.append("report(s) without environment.remote.job_id")
            dup = {j for j in jobs if jobs.count(j) > 1}
            if dup:
                problems.append(f"duplicate remote job ids: {sorted(dup)}")
            print(f"A/B reports: n={len(recs)} engine_version={ev} "
                  f"engine_build.binary_sha256={bs} models_lib_sha256={ms} "
                  f"remote job ids distinct={len(set(jobs)) == len(jobs)}")
            if a.expect_engine and ev != a.expect_engine:
                problems.append(f"reports engine_version {ev!r} != expected {a.expect_engine!r}")
            if a.expect_models_sha and ms != a.expect_models_sha:
                problems.append(f"reports models_lib_sha256 {ms!r} != expected {a.expect_models_sha!r}")
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if not tags:
        print("compare_engine.py: no tags attested", file=sys.stderr)
        return 1
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)

    c = sub.add_parser("compare", help="paired per-code frequency delta between two report sets")
    c.add_argument("--reports-a", required=True, type=Path, help="baseline report dir (e.g. ngspice-46)")
    c.add_argument("--reports-b", required=True, type=Path, help="candidate report dir (e.g. ngspice-47)")
    c.add_argument("--label-a", default="A")
    c.add_argument("--label-b", default="B")
    c.add_argument("--curves", default=None, help="comma-separated curve tags (default: all present)")
    c.add_argument("--half-lsb-pct", type=float, default=analyze.HALF_LSB_PCT)
    c.add_argument("--out-json", type=Path, default=None, help="NEW file for the machine-readable result")

    t = sub.add_parser("attest", help="confirm A/B bench requests equal a frozen campaign's, pin removed")
    t.add_argument("--ab-bench", required=True, type=Path, help="A/B bench dir (prepare.py output)")
    t.add_argument("--ab-prov", required=True, type=Path, help="A/B bench provenance.json")
    t.add_argument("--frozen-prov", required=True, type=Path, help="frozen campaign provenance.json")
    t.add_argument("--pin-key", default=PIN_DEFAULT, help="request key to remove before comparison")
    t.add_argument("--tags", default=None, help="comma-separated tags (default: all common tags)")
    t.add_argument("--ab-reports", type=Path, default=None, help="A/B report dir to audit")
    t.add_argument("--expect-engine", default=None, help="required uniform engine_version")
    t.add_argument("--expect-models-sha", default=None, help="required uniform models_lib_sha256")

    a = ap.parse_args()
    if a.mode == "compare":
        return cmd_compare(a)
    return cmd_attest(a)


if __name__ == "__main__":
    sys.exit(main())
