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

Manifest preflight (issue #87): when the campaign directory already holds a
frozen `manifest.json`, nothing is submitted until the bench reproduces it --
`sha256(<bench>/provenance.json)` must equal `manifest.json:provenance_sha256`
and every DUT netlist copy in the bench must hash to
`manifest.json:netlists.<variant>.sha256`.  A netlist that moved on `main`
after the freeze (e.g. a sizing change landing mid-campaign) therefore stops
the run instead of silently appending jobs measured on a different design to
the same curve.  A campaign directory with no manifest yet (the first slice)
skips the check and says so.

    python3 -I sim/trim-dense/run_batch.py --bench-dir B --out-dir R [--limit N]
"""
import argparse
import hashlib
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


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bench_netlists(bench: Path) -> dict[str, set[str]]:
    """variant -> the sha256(s) of the DUT netlist copies prepare.py wrote into the bench."""
    found: dict[str, set[str]] = {}
    for p in sorted(bench.glob("*/*/rcosc_top_*.spice")):
        found.setdefault(p.parent.parent.name, set()).add(sha256_file(p))
    return found


def manifest_problems(bench: Path, out: Path) -> list[str]:
    """Reasons this bench must not be appended to this campaign (empty == safe).

    Returns [] when the campaign has no frozen manifest yet (first slice).
    """
    mpath = out / "manifest.json"
    man = read_json(mpath)
    if man is None:
        return []
    bad = []
    want = man.get("provenance_sha256")
    prov = bench / "provenance.json"
    got = sha256_file(prov) if prov.is_file() else None
    if want and got != want:
        bad.append(f"provenance.json sha256 {got} != manifest provenance_sha256 {want}")
    netlists = man.get("netlists") or {}
    for variant, hashes in sorted(bench_netlists(bench).items()):
        frozen = (netlists.get(variant) or {}).get("sha256")
        if frozen is None:
            bad.append(f"variant {variant!r} is in the bench but not in manifest netlists")
        elif hashes != {frozen}:
            bad.append(
                f"variant {variant!r} netlist sha256 {sorted(hashes)} != manifest "
                f"{frozen} (path {(netlists.get(variant) or {}).get('path')})")
    return bad


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
    problems = manifest_problems(bench, out)
    if problems:
        raise SystemExit(
            "run_batch.py: this bench does not reproduce the campaign's frozen manifest; "
            "nothing was submitted.\n  - " + "\n  - ".join(problems)
            + "\nRegenerate the bench from the manifest's netlists (recover a moved netlist from "
              "git history by its recorded sha256), or start a new campaign directory.")
    man = read_json(out / "manifest.json")
    if man is None:
        print("manifest preflight: no manifest.json in the campaign dir yet (first slice); not checked")
    else:
        print(f"manifest preflight: OK (provenance_sha256 {man.get('provenance_sha256')}, "
              f"netlists {{{', '.join(f'{v}={h}' for v, hs in sorted(bench_netlists(bench).items()) for h in sorted(hs))}}})")
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
