#!/usr/bin/env python3
"""Resumable batch-fleet driver for the sim/trim-dense request set (issue #87).

Reads the request files written by prepare.py (`<bench>/<variant>/<corner>/
request_cXX.json`) and submits each one with `klt sim <request> --backend batch
-o <out>/jobs/<tag> --format json`.  The report (stdout) is saved as
`<out>/reports/report_<tag>.json` (the name analyze.py expects) and one line per
finished submission is appended to `<out>/ledger.jsonl` (tag, job id, receipt
state, report path, UTC time).

Policy (host rules): every request is executed on the Spot batch fleet; there is
no local fallback, a failed submission is recorded and never retried locally,
and concurrency is capped at MAX_CONCURRENT (2).  Resume: a request whose
`jobs/<tag>/batch-receipt.json` has `state == "done"` and whose report file
exists is skipped, so an interrupted campaign continues without resubmitting
finished jobs.  A failed or errored request is re-submitted on the next run
only with --retry-failed.

    python3 -I sim/trim-dense/run_batch.py --bench-dir B --out-dir R [--limit N]
"""
import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MAX_CONCURRENT = 2  # host rule: never above 2 on a shared dispatch worker


def find_requests(bench: Path) -> list[tuple[str, Path]]:
    """(tag, request path) for every request_cXX.json, ordered by tag."""
    found = []
    for p in sorted(bench.glob("*/*/request_c*.json")):
        variant, corner, code = p.parent.parent.name, p.parent.name, p.stem.split("_c", 1)[1]
        found.append((f"{variant}_{corner}_c{code}", p))
    return found


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def is_done(out: Path, tag: str) -> bool:
    receipt = read_json(out / "jobs" / tag / "batch-receipt.json")
    return bool(receipt) and receipt.get("state") == "done" and (out / "reports" / f"report_{tag}.json").is_file()


def run_one(tag: str, req: Path, out: Path, klt: list[str], lock: threading.Lock) -> dict:
    jobdir = out / "jobs" / tag
    jobdir.mkdir(parents=True, exist_ok=True)
    cmd = klt + ["sim", str(req), "--backend", "batch", "-o", str(jobdir), "--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    (jobdir / "stderr.txt").write_text(proc.stderr)
    report = out / "reports" / f"report_{tag}.json"
    if proc.stdout.strip():
        report.write_text(proc.stdout)
    receipt = read_json(jobdir / "batch-receipt.json") or {}
    rep = read_json(report) or {}
    row = {
        "tag": tag,
        "exit": proc.returncode,
        "job_id": receipt.get("job_id"),
        "state": receipt.get("state", "no-receipt"),
        "report_status": rep.get("status"),
        "report": str(report.relative_to(out)) if report.is_file() else None,
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with lock, (out / "ledger.jsonl").open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def drive(bench: Path, out: Path, klt: list[str], limit: int | None = None,
          retry_failed: bool = False, workers: int = MAX_CONCURRENT, only: str | None = None) -> list[dict]:
    if workers < 1 or workers > MAX_CONCURRENT:
        raise SystemExit(f"run_batch.py: --workers must be 1..{MAX_CONCURRENT} (host rule)")
    (out / "reports").mkdir(parents=True, exist_ok=True)
    reqs = [(t, p) for t, p in find_requests(bench) if only is None or only in t]
    attempted = {r["tag"] for r in map(json.loads, (out / "ledger.jsonl").read_text().splitlines())} \
        if (out / "ledger.jsonl").is_file() else set()
    todo = []
    for tag, p in reqs:
        if is_done(out, tag):
            continue
        if tag in attempted and not retry_failed:
            continue
        todo.append((tag, p))
    if limit is not None:
        todo = todo[:limit]
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda tp: run_one(tp[0], tp[1], out, klt, lock), todo))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bench-dir", required=True, type=Path, help="prepare.py output directory")
    ap.add_argument("--out-dir", required=True, type=Path, help="campaign results dir (created if absent, resumed if present)")
    ap.add_argument("--klt", default="klt", help="klt command (e.g. 'uvx --from klayout-tools==0.9.0 klt')")
    ap.add_argument("--limit", type=int, default=None, help="submit at most N pending requests this session")
    ap.add_argument("--only", default=None, help="substring filter on the request tag")
    ap.add_argument("--workers", type=int, default=MAX_CONCURRENT)
    ap.add_argument("--retry-failed", action="store_true", help="re-submit requests already attempted but not done")
    a = ap.parse_args()
    rows = drive(a.bench_dir, a.out_dir, a.klt.split(), a.limit, a.retry_failed, a.workers, a.only)
    bad = [r for r in rows if r["state"] != "done"]
    print(f"submitted {len(rows)} request(s); {len(rows) - len(bad)} done, {len(bad)} not done")
    for r in bad:
        print(f"  NOT DONE {r['tag']}: exit={r['exit']} state={r['state']} status={r['report_status']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
