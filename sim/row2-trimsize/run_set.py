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
    by_tb_name: dict[str, Path] = {}
    for _, _, p in reqs:
        tb_p, _, _ = _request_netlist_info(p)
        if tb_p is not None:
            prev = by_tb_name.setdefault(tb_p.name, tb_p)
            if prev != tb_p:
                raise ValueError(
                    f"run_group received distinct netlists sharing basename {tb_p.name!r}"
                )
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


_SUBMISSION_ONLY_BATCH_FIELDS = ("capacity_wait_s", "max_concurrent_jobs")


def _sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / ".git").exists():
            return cand
    return REPO


def _klt_request_digests(doc: dict) -> frozenset[str]:
    """Request-object SHA-256 digests emitted by pinned klayout-tools==0.9.0.

    Blocking `klt sim` / `--batch-set` (`sim_batch._run_batch_job`) hashes
    `json.dumps(request, sort_keys=True, default=str)` after folding CLI
    `--wait-for-capacity` (`float(CAPACITY_WAIT_S)`) into `request.batch`;
    `--submit-only` (`sim_batch_shards.request_sha256`) hashes canonical JSON
    with submission-only `batch` fields excluded.
    """
    digests = set()
    batch = doc.get("batch")
    batch_dict = batch if isinstance(batch, dict) else {}
    with_wait = {**doc, "batch": {**batch_dict, "capacity_wait_s": float(CAPACITY_WAIT_S)}}
    digests.add(hashlib.sha256(
        json.dumps(with_wait, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest())
    digests.add(hashlib.sha256(
        json.dumps(doc, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest())
    digests.add(hashlib.sha256(
        json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest())
    if isinstance(batch, dict) and any(k in batch for k in _SUBMISSION_ONLY_BATCH_FIELDS):
        kept = {k: v for k, v in batch.items() if k not in _SUBMISSION_ONLY_BATCH_FIELDS}
        stripped = {**doc, "batch": kept}
        digests.add(hashlib.sha256(
            json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest())
    return frozenset(digests)


def _request_netlist_info(req_path: Path) -> tuple[Path | None, str | None, frozenset[str]]:
    try:
        doc = json.loads(req_path.read_text())
    except (OSError, ValueError):
        return None, None, frozenset()
    if not isinstance(doc, dict):
        return None, None, frozenset()
    req_digests = _klt_request_digests(doc)
    net = doc.get("netlist")
    if not isinstance(net, str) or not net:
        return None, None, req_digests
    tb_path = (req_path.parent / net).resolve()
    return tb_path, _sha256_file(tb_path), req_digests


def _read_receipt_request_sha256(job_dir_path: Path) -> tuple[bool, str | None]:
    receipt_path = job_dir_path / "batch-receipt.json"
    if not receipt_path.is_file():
        return True, None
    try:
        rec = json.loads(receipt_path.read_text())
    except (OSError, ValueError):
        return False, None
    if not isinstance(rec, dict):
        return False, None
    if "request_sha256" in rec:
        rsha = rec["request_sha256"]
        if not isinstance(rsha, str) or not rsha:
            return False, None
        return True, rsha
    return True, None


def _resolve_report_netlist_path(report_doc: dict, repo_root: Path) -> tuple[bool, Path | None]:
    if "netlist" not in report_doc or report_doc["netlist"] is None:
        return True, None
    net_meta = report_doc["netlist"]
    if not isinstance(net_meta, dict):
        return False, None
    raw_path = net_meta.get("path")
    if raw_path is None:
        return True, None
    if not isinstance(raw_path, str) or not raw_path:
        return False, None
    np = Path(raw_path)
    return True, (np.resolve() if np.is_absolute() else (repo_root / np).resolve())


def _is_passing_report(doc: object) -> bool:
    if not isinstance(doc, dict):
        return False
    return not (str(doc.get("status")).lower() in ("failed", "error", "refused") or doc.get("refused"))


def _legacy_identity_verified(
    report_doc: dict,
    legacy_dir: Path,
    req_path: Path,
    bench_info: dict[Path, tuple[Path | None, str | None, frozenset[str]]],
    repo_root: Path = REPO,
) -> bool:
    """True only when a legacy jobs/<variant>/<stem>/report.json unambiguously
    proves it measured `req_path` and no other request in the bench."""
    env = report_doc.get("environment")
    got_net_sha = env.get("netlist_sha256") if isinstance(env, dict) else None
    if not isinstance(got_net_sha, str) or not got_net_sha:
        return False
    ok_rec, got_req_sha = _read_receipt_request_sha256(legacy_dir)
    if not ok_rec:
        return False
    ok_np, resolved_np = _resolve_report_netlist_path(report_doc, repo_root)
    if not ok_np:
        return False

    def _candidate_matches(info: tuple[Path | None, str | None, frozenset[str]]) -> bool:
        tb_p, nsha, rdigests = info
        if nsha is None or nsha != got_net_sha:
            return False
        if got_req_sha is not None and got_req_sha not in rdigests:
            return False
        if resolved_np is not None and (tb_p is None or tb_p != resolved_np):
            return False
        return True

    target = bench_info.get(req_path.resolve())
    if target is None or not _candidate_matches(target):
        return False
    return sum(1 for info in bench_info.values() if _candidate_matches(info)) == 1


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
    bench_root = bench if bench is not None else reqs[0][2].parent.parent.parent
    repo_root = _find_repo_root(bench_root)
    bench_info: dict[Path, tuple[Path | None, str | None, frozenset[str]]] | None = None
    n = 0
    for tag, v, p in reqs:
        dst = out / "reports" / f"report_{tag}.json"
        if dst.is_file():
            continue
        cdir = job_dir(jobs_root, v, p) / p.stem
        src = cdir / "report.json"
        if src.is_file():
            try:
                d = json.loads(src.read_text())
            except (OSError, ValueError):
                continue
            if not _is_passing_report(d):
                continue
            tb_path, exp_net_sha, exp_req_digests = _request_netlist_info(p)
            env = d.get("environment") if isinstance(d.get("environment"), dict) else None
            if env is not None and env.get("netlist_sha256") is not None:
                if exp_net_sha is not None and env.get("netlist_sha256") != exp_net_sha:
                    continue
            ok_rec, got_req_sha = _read_receipt_request_sha256(cdir)
            if not ok_rec or (got_req_sha is not None and exp_req_digests and got_req_sha not in exp_req_digests):
                continue
            ok_np, resolved_np = _resolve_report_netlist_path(d, repo_root)
            if not ok_np or (resolved_np is not None and tb_path is not None and resolved_np != tb_path):
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
            bench_info = {q.resolve(): _request_netlist_info(q)
                          for _, _, q in find_requests(bench_root, None)}
        bench_info.setdefault(p.resolve(), _request_netlist_info(p))
        if not _legacy_identity_verified(d, legacy_dir, p, bench_info, repo_root):
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
