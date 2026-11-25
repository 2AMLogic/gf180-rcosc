#!/usr/bin/env python3
"""Batch-set driver for the row-2 screen / full request sets (issue #460).

Same policy as sim/trim-dense/run_batch.py (host rules: every request on the
Spot batch fleet, no local fallback, failed submissions recorded, resumable)
but submits through `klt sim --batch-set` (one fleet invocation for up to
--group requests, --max-in-flight at once) instead of one invocation per
request, which is what keeps a several-hundred-request screen inside one
session.  Every member gets its own directory under
<out>/jobs/<variant>/<request-stem>/ by klt; the member report named by the
envelope's `requests[].report` is copied to <out>/reports/report_<tag>.json
(the naming analyze.py and analyze_screen.py read), and one JSONL line per
finished group is appended to <out>/ledger.jsonl.

Resume: a request whose report file already exists is skipped, so an
interrupted run continues without resubmitting finished requests.

    python3 -I sim/row2-trimsize/run_set.py --bench-dir B --out-dir R \
        [--variant NAME] [--group 64] [--max-in-flight 8] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_KLT = ["uvx", "--from", "klayout-tools==0.9.0", "klt"]  # the #87 campaign client
CAPACITY_WAIT_S = 600      # host rule: every batch submission waits for capacity
CAPACITY_RETRIES = 4


def find_requests(bench: Path, variant: str | None) -> list[tuple[str, str, Path]]:
    """All request_*.json under <bench>/<variant>/<corner-dir>/.

    Tag = <variant>_<corner-dir>_<stem> (stem = filename between `request_`
    and `.json`).  The screen/full generators use stem `cXX`, so their tags are
    identical to the original `variant_corner_cXX` scheme; the pricing
    generators use stems like `tt_cA0` / `ss_v30` / `cFF_v33`.
    """
    found = []
    for p in sorted(bench.glob("*/*/request_*.json")):
        v, stem = p.parent.parent.name, p.stem[len("request_"):]
        if variant and v != variant:
            continue
        found.append((f"{v}_{p.parent.name}_{stem}", v, p))
    return found


def run_group(klt: list[str], reqs: list[tuple[str, str, Path]], out: Path,
              max_in_flight: int) -> list[dict]:
    tag0 = reqs[0][0]
    gdir = out / "jobs" / reqs[0][1]
    gdir.mkdir(parents=True, exist_ok=True)
    cmd = klt + ["sim", "--batch-set", *[str(r[2]) for r in reqs],
                 "--max-in-flight", str(max_in_flight),
                 "--capacity-retries", str(CAPACITY_RETRIES),
                 "--wait-for-capacity", str(CAPACITY_WAIT_S),
                 "-o", str(gdir), "--format", "json"]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    dt = time.time() - t0
    (gdir / f"envelope-{tag0}.stderr").write_text(proc.stderr)
    env = None
    for line in proc.stdout.splitlines():
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if isinstance(j, dict) and "requests" in j:
            env = j
    rows = []
    if env is None:
        try:
            env = json.loads(proc.stdout)
        except ValueError:
            env = None
    if not isinstance(env, dict) or not isinstance(env.get("requests"), list):
        rows.append({"tag": tag0, "exit": proc.returncode, "state": "envelope_unreadable",
                     "elapsed_s": round(dt)})
        return rows
    members = {str(r["request"]).split("/")[-1]: r for r in env["requests"]
               if isinstance(r, dict) and "request" in r}
    for tag, v, p in reqs:
        m = members.get(p.name)
        rep_rel = (m or {}).get("report")
        row = {"tag": tag, "exit": proc.returncode, "elapsed_s": round(dt),
               "member_state": (m or {}).get("state"), "report_rel": rep_rel}
        if rep_rel:
            src = gdir / Path(str(rep_rel)).relative_to(gdir) if str(rep_rel).startswith(str(gdir)) \
                else gdir / str(rep_rel).lstrip("/")
            dst = out / "reports" / f"report_{tag}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                dst.write_text(src.read_text())
                row["report"] = str(dst.relative_to(out))
            except OSError as e:
                row["copy_error"] = str(e)
        rows.append(row)
    return rows


def salvage(jobs_root: Path, out: Path, reqs: list[tuple[str, str, Path]]) -> int:
    """Copy already-finished fleet member reports (jobs/<variant>/<request-stem>/
    report.json) into reports/.  A member report only exists once klt collected
    that job from the fleet, so it is valid measured evidence for its request;
    salvaging lets an interrupted driver resume without resubmitting finished
    members whose group envelope was never written."""
    n = 0
    for tag, v, p in reqs:
        dst = out / "reports" / f"report_{tag}.json"
        if dst.is_file():
            continue
        src = jobs_root / v / p.stem / "report.json"
        if src.is_file():
            try:
                d = json.loads(src.read_text())
            except (OSError, ValueError):
                continue
            if str(d.get("status")).lower() in ("failed", "error", "refused") or d.get("refused"):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text())
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="row-2 batch-set driver")
    ap.add_argument("--bench-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--variant", default=None, help="restrict to one bench variant")
    ap.add_argument("--group", type=int, default=64, help="requests per batch-set invocation")
    ap.add_argument("--max-in-flight", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="stop after N new submissions")
    ap.add_argument("--klt", nargs="+", default=DEFAULT_KLT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    bench, out = args.bench_dir, args.out_dir
    if not bench.is_dir():
        print(f"error: no bench at {bench}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    reqs = find_requests(bench, args.variant)
    if not reqs:
        print(f"error: no request_c*.json under {bench}", file=sys.stderr)
        return 1
    n_salv = salvage(out / "jobs", out, reqs)
    if n_salv:
        print(f"salvaged {n_salv} finished member reports from a previous driver run")
    todo = [(t, v, p) for t, v, p in reqs if not (out / "reports" / f"report_{t}.json").is_file()]
    print(f"{len(reqs)} requests, {len(reqs) - len(todo)} already reported, {len(todo)} to run")
    if args.dry_run:
        for t, v, p in todo:
            print(" ", t)
        return 0

    n_sub = 0
    for i in range(0, len(todo), args.group):
        chunk = todo[i:i + args.group]
        if args.limit is not None and n_sub >= args.limit:
            print("limit reached; stopping")
            break
        rows = run_group(args.klt, chunk, out, args.max_in_flight)
        n_sub += len(chunk)
        with (out / "ledger.jsonl").open("a") as fh:
            for row in rows:
                row["utc"] = datetime.now(timezone.utc).isoformat()
                fh.write(json.dumps(row) + "\n")
        ok = sum(1 for r in rows if r.get("report"))
        print(f"group {i // args.group + 1}: {ok}/{len(rows)} reports written "
              f"({rows[0]['tag']} .. {rows[-1]['tag']})")
    missing = sum(1 for t, _, _ in reqs if not (out / "reports" / f"report_{t}.json").is_file())
    print(f"done; {missing} requests still without a report")
    return 0 if missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
