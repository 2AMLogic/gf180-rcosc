#!/usr/bin/env python3
"""Batch-set driver for the row-2 screen / full request sets (issue #460, #482).

Same policy as sim/trim-dense/run_batch.py (host rules: every request on the
Spot batch fleet, no local fallback, failed submissions recorded, resumable)
but submits through `klt sim --batch-set` (one fleet invocation for up to
--group requests, --max-in-flight at once) instead of one invocation per
request, which is what keeps a several-hundred-request screen inside one
session.

Grouping and client pin (2AMLogic/klayout-tools#7180): `DEFAULT_KLT` stays
pinned to `klayout-tools==0.9.0` for engine/stamp comparability with the #87
dense campaign.  In 0.9.0, `klt sim --batch-set` cross-wires members whose
netlist files share a basename across request directories (#7180).  Pending
requests are therefore grouped by their `<bench>/<variant>/<corner>/` parent
directory and chunked up to `--group` within each directory (never mixing
variants or corners, with or without `--variant`), and `run_group()` rejects
straddling batches defensively.

Every member gets its own directory under
`<out>/jobs/<variant>/<corner>/<request-stem>/` by klt; the member report named
by the envelope's `requests[].report` is copied to
`<out>/reports/report_<tag>.json` (the naming analyze.py and analyze_screen.py
read), and one JSONL line per submitted member (or unreadable group envelope)
is appended to `<out>/ledger.jsonl`.

Resume: a request whose `reports/report_<tag>.json` already exists is skipped,
and `salvage()` recovers finished member reports from
`jobs/<variant>/<corner>/<request-stem>/report.json` before submission so an
interrupted run continues without resubmitting finished requests.  A legacy
variant-only `jobs/<variant>/<request-stem>/report.json` path (which can hold a
report from a pre-#482 straddling batch) is left pending for resubmission
unless its netlist/request identity can be uniquely verified against the bench.

    python3 -I sim/row2-trimsize/run_set.py --bench-dir B --out-dir R \
        [--variant NAME] [--group 64] [--max-in-flight 8] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
# Pinned to 0.9.0 for comparability with the #87 dense campaign; 0.9.0 has
# 2AMLogic/klayout-tools#7180 (--batch-set cross-wires shared netlist basenames),
# prevented structurally here by batching within one (variant, corner) directory.
DEFAULT_KLT = ["uvx", "--from", "klayout-tools==0.9.0", "klt"]
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


def job_dir(jobs_root: Path, variant: str, req_path: Path) -> Path:
    """Per-(variant, corner) job directory: <jobs_root>/<variant>/<corner>."""
    return jobs_root / variant / req_path.parent.name


def chunk_requests(reqs: list[tuple[str, str, Path]],
                   group: int) -> list[list[tuple[str, str, Path]]]:
    """Group sorted pending requests by their <bench>/<variant>/<corner>/
    parent directory and slice each directory into batches of at most `group`."""
    if group < 1:
        raise ValueError(f"--group must be >= 1; got {group}")
    by_dir: dict[Path, list[tuple[str, str, Path]]] = {}
    for item in reqs:
        by_dir.setdefault(item[2].parent.resolve(), []).append(item)
    chunks: list[list[tuple[str, str, Path]]] = []
    for items in by_dir.values():
        for i in range(0, len(items), group):
            chunks.append(items[i:i + group])
    return chunks


def _resolve_report_src(gdir: Path, rep_rel: str) -> Path:
    if rep_rel.startswith(str(gdir)):
        return gdir / Path(rep_rel).relative_to(gdir)
    rep_path = Path(rep_rel)
    if rep_path.is_absolute():
        return rep_path
    cand = gdir / rep_rel.lstrip("/")
    if not cand.is_file() and (REPO / rep_path).is_file():
        return REPO / rep_path
    return cand


def run_group(klt: list[str], reqs: list[tuple[str, str, Path]], out: Path,
              max_in_flight: int) -> list[dict]:
    if not reqs:
        return []
    dirs = {(v, p.parent.name, p.parent.resolve()) for _, v, p in reqs}
    if len(dirs) != 1:
        raise ValueError(
            "run_group requires requests from a single (variant, corner) directory; got "
            + ", ".join(sorted(f"{v}/{c}" for v, c, _ in dirs))
        )
    if len({p.name for _, _, p in reqs}) != len(reqs):
        raise ValueError("run_group received duplicate request basenames")
    tag0, v0, p0 = reqs[0]
    gdir = job_dir(out / "jobs", v0, p0)
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
    by_exact = {str(r["request"]): r for r in env["requests"]
                if isinstance(r, dict) and "request" in r}
    by_name = {Path(str(r["request"])).name: r for r in env["requests"]
               if isinstance(r, dict) and "request" in r}
    for tag, v, p in reqs:
        m = by_exact.get(str(p)) or by_name.get(p.name)
        rep_rel = (m or {}).get("report")
        row = {"tag": tag, "exit": proc.returncode, "elapsed_s": round(dt),
               "member_state": (m or {}).get("state"), "report_rel": rep_rel}
        if rep_rel:
            src = _resolve_report_src(gdir, str(rep_rel))
            dst = out / "reports" / f"report_{tag}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                dst.write_text(src.read_text())
                row["report"] = str(dst.relative_to(out))
            except OSError as e:
                row["copy_error"] = str(e)
        rows.append(row)
    return rows


def _sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def _request_netlist_info(req_path: Path) -> tuple[Path | None, str | None, str | None]:
    req_sha = _sha256_file(req_path)
    try:
        doc = json.loads(req_path.read_text())
    except (OSError, ValueError):
        return None, None, req_sha
    if not isinstance(doc, dict) or not isinstance(doc.get("netlist"), str):
        return None, None, req_sha
    tb_path = (req_path.parent / doc["netlist"]).resolve()
    return tb_path, _sha256_file(tb_path), req_sha


def _is_passing_report(doc: object) -> bool:
    if not isinstance(doc, dict):
        return False
    return not (str(doc.get("status")).lower() in ("failed", "error", "refused") or doc.get("refused"))


def _legacy_identity_verified(
    report_doc: dict,
    legacy_dir: Path,
    req_path: Path,
    bench_info: dict[Path, tuple[Path | None, str | None, str | None]],
) -> bool:
    """True only when a legacy jobs/<variant>/<stem>/report.json unambiguously
    proves it measured `req_path` and no other request in the bench."""
    env = report_doc.get("environment")
    got_net_sha = env.get("netlist_sha256") if isinstance(env, dict) else None
    tb_path, exp_net_sha, exp_req_sha = bench_info[req_path.resolve()]
    if not isinstance(got_net_sha, str) or exp_net_sha is None or got_net_sha != exp_net_sha:
        return False

    matched_req_sha = False
    receipt_path = legacy_dir / "batch-receipt.json"
    if receipt_path.is_file():
        try:
            rec = json.loads(receipt_path.read_text())
        except (OSError, ValueError):
            return False
        if not isinstance(rec, dict):
            return False
        if "request_sha256" in rec:
            if exp_req_sha is None or rec["request_sha256"] != exp_req_sha:
                return False
            matched_req_sha = True

    net_meta = report_doc.get("netlist")
    if isinstance(net_meta, dict) and isinstance(net_meta.get("path"), str) and net_meta["path"]:
        np = Path(net_meta["path"])
        resolved_np = np.resolve() if np.is_absolute() else (REPO / np).resolve()
        return tb_path is not None and resolved_np == tb_path

    if matched_req_sha:
        matches = sum(1 for _, nsha, rsha in bench_info.values()
                      if nsha == exp_net_sha and rsha == exp_req_sha)
    else:
        matches = sum(1 for _, nsha, _ in bench_info.values() if nsha == exp_net_sha)
    return matches == 1


def salvage(jobs_root: Path, out: Path, reqs: list[tuple[str, str, Path]],
            bench: Path | None = None) -> int:
    """Copy already-finished fleet member reports
    (jobs/<variant>/<corner>/<request-stem>/report.json) into reports/.  A
    member report only exists once klt collected that job from the fleet, so it
    is valid measured evidence for its request; salvaging lets an interrupted
    driver resume without resubmitting finished members whose group envelope was
    never written.  Legacy variant-only paths (jobs/<variant>/<request-stem>/)
    can hold reports from a pre-#482 straddling batch and remain pending unless
    their request identity can be uniquely verified against the full bench."""
    if not reqs:
        return 0
    bench_info: dict[Path, tuple[Path | None, str | None, str | None]] | None = None
    n = 0
    for tag, v, p in reqs:
        dst = out / "reports" / f"report_{tag}.json"
        if dst.is_file():
            continue
        src = job_dir(jobs_root, v, p) / p.stem / "report.json"
        if src.is_file():
            try:
                d = json.loads(src.read_text())
            except (OSError, ValueError):
                continue
            if not _is_passing_report(d):
                continue
            env = d.get("environment") if isinstance(d.get("environment"), dict) else None
            if env is not None and "netlist_sha256" in env:
                _, exp_net_sha, _ = _request_netlist_info(p)
                if exp_net_sha is not None and env.get("netlist_sha256") != exp_net_sha:
                    continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text())
            n += 1
            continue

        legacy_dir = jobs_root / v / p.stem
        legacy_src = legacy_dir / "report.json"
        if not legacy_src.is_file():
            continue
        try:
            d = json.loads(legacy_src.read_text())
        except (OSError, ValueError):
            continue
        if not _is_passing_report(d):
            continue
        if bench_info is None:
            bench_root = bench if bench is not None else p.parent.parent.parent
            bench_info = {q.resolve(): _request_netlist_info(q)
                          for _, _, q in find_requests(bench_root, None)}
        bench_info.setdefault(p.resolve(), _request_netlist_info(p))
        if not _legacy_identity_verified(d, legacy_dir, p, bench_info):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(legacy_src.read_text())
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="row-2 batch-set driver")
    ap.add_argument("--bench-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--variant", default=None, help="restrict to one bench variant")
    ap.add_argument("--group", type=int, default=64,
                    help="max requests per single-(variant, corner) batch-set invocation")
    ap.add_argument("--max-in-flight", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="stop after N new submissions")
    ap.add_argument("--klt", nargs="+", default=DEFAULT_KLT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    bench, out = args.bench_dir, args.out_dir
    if not bench.is_dir():
        print(f"error: no bench at {bench}", file=sys.stderr)
        return 1
    if args.group < 1:
        print(f"error: --group must be >= 1 (got {args.group})", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    reqs = find_requests(bench, args.variant)
    if not reqs:
        print(f"error: no request_c*.json under {bench}", file=sys.stderr)
        return 1
    n_salv = salvage(out / "jobs", out, reqs, bench)
    if n_salv:
        print(f"salvaged {n_salv} finished member reports from a previous driver run")
    todo = [(t, v, p) for t, v, p in reqs if not (out / "reports" / f"report_{t}.json").is_file()]
    print(f"{len(reqs)} requests, {len(reqs) - len(todo)} already reported, {len(todo)} to run")
    if args.dry_run:
        for t, v, p in todo:
            print(" ", t)
        return 0

    chunks = chunk_requests(todo, args.group)
    n_sub = 0
    for g_idx, chunk in enumerate(chunks, 1):
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
        print(f"group {g_idx}: {ok}/{len(rows)} reports written "
              f"({rows[0]['tag']} .. {rows[-1]['tag']})")
    missing = sum(1 for t, _, _ in reqs if not (out / "reports" / f"report_{t}.json").is_file())
    print(f"done; {missing} requests still without a report")
    return 0 if missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
