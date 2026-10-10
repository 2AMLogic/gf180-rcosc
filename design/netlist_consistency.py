"""Offline consistency guard for the simulation DUT netlist representations.

Compares design/netlist/pvt_tb.spice (canonical), design/netlist/rcosc_top.spice
(independently generated peer) and every current tracked bench copy
sim/**/rcosc_top_schematic.spice, as a multiset of normalized logical
statements per subcircuit (ordered port lists significant).

PDK-free, simulator-free, network-free; it only reads files and runs local
`git ls-files` / `git show`. It never writes anything.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CANONICAL = "design/netlist/pvt_tb.spice"
PEER = "design/netlist/rcosc_top.spice"
COPY_RE = re.compile(r"^sim/(?:.*/)?rcosc_top_schematic\.spice$")
ARCHIVE_DIRS = ("results", "batch-attempts")
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_WRAP_SUBCKT = re.compile(r"^\*\*\.subckt\b", re.I)
_WRAP_ENDS = re.compile(r"^\*\*\.ends\b", re.I)


@dataclass
class Subckt:
    ports: list
    stmts: Counter
    commented: bool = False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(stmt: str) -> str:
    """Lowercase and collapse whitespace outside single-quoted expressions."""
    out, buf, in_q = [], [], False
    for part in re.split(r"(')", stmt):
        if part == "'":
            in_q = not in_q
            buf.append(part)
        elif in_q:
            buf.append(part)
        else:
            buf.append(re.sub(r"\s+", " ", part.lower()))
    out = "".join(buf)
    return out.strip()


def logical_statements(text: str):
    """Yield (statement, commented_wrapper) with continuations joined."""
    stmts = []
    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        if _WRAP_SUBCKT.match(s) or _WRAP_ENDS.match(s):
            stmts.append([s[2:], True])
            continue
        if s.startswith("*"):
            continue
        if s.startswith("+"):
            if not stmts:
                raise ValueError("continuation line with no preceding statement")
            stmts[-1][0] += " " + s[1:]
            continue
        stmts.append([s, False])
    return [(normalize(a), b) for a, b in stmts]


def parse(text: str):
    """Return (subckts: dict name -> Subckt, top_level: Counter)."""
    subckts, top = {}, Counter()
    cur = None
    for stmt, wrapped in logical_statements(text):
        toks = stmt.split()
        head = toks[0]
        if head == ".subckt":
            if cur is not None:
                raise ValueError(f"nested .subckt {toks[1]!r}")
            if len(toks) < 2:
                raise ValueError("malformed .subckt")
            name = toks[1]
            if name in subckts:
                raise ValueError(f"duplicate subcircuit {name!r}")
            cur = Subckt(toks[2:], Counter(), wrapped)
            subckts[name] = cur
            cur_name = name
        elif head == ".ends":
            if cur is None:
                raise ValueError(".ends without .subckt")
            if len(toks) > 1 and toks[1] != cur_name:
                raise ValueError(f".ends {toks[1]!r} closes {cur_name!r}")
            cur = None
        elif head == ".end":
            continue
        elif cur is not None:
            cur.stmts[stmt] += 1
        else:
            top[stmt] += 1
    if cur is not None:
        raise ValueError(f"unterminated .subckt {cur_name!r}")
    return subckts, top


def adapt_klt(subckts: dict, label: str, errors: list) -> dict:
    """Fold the documented klt-PEX pin-order wrapper back to canonical form."""
    if "rcosc_top_core" not in subckts:
        return subckts
    core = subckts["rcosc_top_core"]
    wrap = subckts.get("rcosc_top")
    if wrap is None:
        errors.append(f"{label}: klt adapter: rcosc_top_core present but no rcosc_top wrapper")
        return subckts
    expect = f"xcore {' '.join(core.ports)} rcosc_top_core"
    if list(wrap.stmts.elements()) != [expect]:
        errors.append(
            f"{label}: subckt rcosc_top: klt adapter must contain exactly one "
            f"'{expect}'; found {sorted(wrap.stmts.elements())}"
        )
    if wrap.ports != sorted(core.ports):
        errors.append(
            f"{label}: subckt rcosc_top: klt adapter ports {wrap.ports} are not "
            f"the alphabetical ports {sorted(core.ports)} of rcosc_top_core"
        )
    out = {k: v for k, v in subckts.items() if k != "rcosc_top_core"}
    out["rcosc_top"] = core
    return out


def compare(ref: dict, other: dict, label: str) -> list:
    errors = []
    for name in sorted(set(ref) | set(other)):
        if name not in other:
            errors.append(f"{label}: subckt {name}: missing subcircuit")
            continue
        if name not in ref:
            errors.append(f"{label}: subckt {name}: extra subcircuit")
            continue
        a, b = ref[name], other[name]
        if a.ports != b.ports:
            errors.append(
                f"{label}: subckt {name}: port list differs: "
                f"expected {' '.join(a.ports)} got {' '.join(b.ports)}"
            )
        for s in sorted((a.stmts - b.stmts).elements()):
            errors.append(f"{label}: subckt {name}: missing statement: {s}")
        for s in sorted((b.stmts - a.stmts).elements()):
            errors.append(f"{label}: subckt {name}: extra statement: {s}")
    return errors


def load_hierarchy(text: str, label: str, errors: list, canonical=False):
    try:
        subckts, top = parse(text)
    except ValueError as e:
        errors.append(f"{label}: parse error: {e}")
        return None
    if canonical:
        # the testbench wrapper (commented **.subckt pvt_tb) and top-level
        # bench statements are not part of the DUT hierarchy
        return {k: v for k, v in subckts.items() if not v.commented}
    for s in sorted(top):
        errors.append(f"{label}: unexpected top-level statement outside subckt: {s}")
    return adapt_klt(subckts, label, errors)


def check_dut_text(canon_hier: dict, text: str, label: str) -> list:
    errors: list = []
    h = load_hierarchy(text, label, errors)
    if h is not None:
        errors += compare(canon_hier, h, label)
    return errors


def _read_provenance(path: Path, label: str, errors: list):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        errors.append(f"{label}: malformed provenance {path}: {e}")
        return None
    dut = data.get("dut") if isinstance(data, dict) else None
    if not isinstance(dut, dict):
        errors.append(f"{label}: provenance {path}: missing 'dut' object")
        return None
    return data, dut


def _need(dut: dict, keys, path, label, errors):
    ok = True
    for k in keys:
        if not isinstance(dut.get(k), str) or not dut[k]:
            errors.append(f"{label}: provenance {path}: missing/malformed dut.{k}")
            ok = False
    return ok


def check_current_provenance(copy: Path, copy_bytes: bytes, canon_bytes: bytes, label: str) -> list:
    prov = copy.parent / "provenance.json"
    if not prov.is_file():
        return []
    errors: list = []
    r = _read_provenance(prov, label, errors)
    if r is None:
        return errors
    _, dut = r
    if not _need(dut, ("source", "source_sha256", "extracted_sha256"), prov, label, errors):
        return errors
    if dut["source"] != CANONICAL:
        errors.append(f"{label}: provenance {prov}: dut.source is {dut['source']!r}, expected {CANONICAL!r}")
    if dut["source_sha256"] != sha256_bytes(canon_bytes):
        errors.append(
            f"{label}: provenance {prov}: dut.source_sha256 {dut['source_sha256']} "
            f"!= current {CANONICAL} sha256 {sha256_bytes(canon_bytes)}"
        )
    if dut["extracted_sha256"] != sha256_bytes(copy_bytes):
        errors.append(
            f"{label}: provenance {prov}: dut.extracted_sha256 {dut['extracted_sha256']} "
            f"!= copy sha256 {sha256_bytes(copy_bytes)}"
        )
    return errors


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True).stdout


def check_archive(copy: Path, root: Path) -> list:
    """Validate an archived copy against its recorded historical source."""
    label = str(copy)
    errors: list = []
    prov = copy.parent / "provenance.json"
    if not prov.is_file():
        return [f"{label}: unverifiable: no adjacent provenance.json"]
    r = _read_provenance(prov, label, errors)
    if r is None:
        return errors
    data, dut = r
    if not _need(dut, ("source", "source_sha256", "extracted_sha256"), prov, label, errors):
        return errors
    sha = dut.get("source_git_sha") or data.get("source_git_sha") or data.get("git_sha")
    if not isinstance(sha, str) or not SHA_RE.match(sha):
        return [f"{label}: unverifiable: provenance {prov} records no resolvable source commit"]
    try:
        src = git(root, "show", f"{sha}:{dut['source']}")
    except (subprocess.CalledProcessError, OSError):
        return [f"{label}: unverifiable: cannot resolve {sha}:{dut['source']}"]
    if sha256_bytes(src) != dut["source_sha256"]:
        errors.append(f"{label}: historical source sha256 {sha256_bytes(src)} != recorded {dut['source_sha256']}")
    cb = copy.read_bytes()
    if sha256_bytes(cb) != dut["extracted_sha256"]:
        errors.append(f"{label}: copy sha256 {sha256_bytes(cb)} != recorded {dut['extracted_sha256']}")
    if errors:
        return errors
    ch = load_hierarchy(src.decode(), f"{sha}:{dut['source']}", errors, canonical=True)
    if ch is None:
        return errors
    return errors + check_dut_text(ch, cb.decode(), label)


def discover(root: Path) -> list:
    out = git(root, "ls-files").decode().splitlines()
    res = []
    for p in out:
        if COPY_RE.match(p) and not any(d in p.split("/") for d in ARCHIVE_DIRS):
            res.append(p)
    return sorted(res)


def run(root: Path, archives=()) -> list:
    errors: list = []
    cpath = root / CANONICAL
    try:
        canon_bytes = cpath.read_bytes()
    except OSError as e:
        return [f"{CANONICAL}: unreadable: {e}"]
    canon = load_hierarchy(canon_bytes.decode(), CANONICAL, errors, canonical=True)
    if canon is None:
        return errors
    try:
        errors += check_dut_text(canon, (root / PEER).read_text(), PEER)
    except OSError as e:
        errors.append(f"{PEER}: unreadable: {e}")
    for rel in discover(root):
        p = root / rel
        data = p.read_bytes()
        errors += check_dut_text(canon, data.decode(), rel)
        errors += check_current_provenance(p, data, canon_bytes, rel)
    for a in archives:
        errors += check_archive(Path(a), root)
    return errors


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--archive", action="append", default=[],
                    help="validate an archived copy against its recorded historical source")
    args = ap.parse_args(argv)
    root = Path(args.repo_root)
    errors = run(root, args.archive)
    for e in errors:
        print(f"FAIL {e}")
    if errors:
        print(f"netlist consistency: {len(errors)} problem(s)")
        return 1
    print("netlist consistency: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
