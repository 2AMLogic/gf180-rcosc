"""Synthetic regression suite for netlist_consistency (offline, no PDK/sim)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlist_consistency as nc  # noqa: E402

CORE = """\
.subckt top a b c
XU1 a b leaf
R1 a c 10k
R2 a c 10k
M1 a b c c nfet L=0.5u W='2*1u'
+ nf=1
.ends
.subckt leaf p q
C1 p q 1p
.ends
"""

TB = "** sch_path: x\n**.subckt pvt_tb\nXD a 0 c top\n**.ends\n\n" + CORE + "\n.end\n"
PEER_TXT = ("**.subckt top a b c\n*.iopin a\nXU1 a b leaf\nR1 a c 10k\nR2 a c 10k\n"
            "M1 a b c c nfet L=0.5u W='2*1u' nf=1\n**.ends\n\n"
            ".subckt leaf p q\nC1 p q 1p\n.ends\n\n.end\n")
KLT_PEX = (CORE.replace(".subckt top a b c", ".subckt rcosc_top_core a b c")
           + ".subckt rcosc_top a b c\nXcore a b c rcosc_top_core\n.ends rcosc_top\n")
# the klt adapter is specific to rcosc_top; use an rcosc_top-named fixture
TOP = CORE.replace("top", "rcosc_top")
TB = TB.replace("top", "rcosc_top").replace("rcosc_rcosc_top", "rcosc_top")


def canon_hier(text=None):
    errs = []
    h = nc.load_hierarchy(text or TB, "canon", errs, canonical=True)
    assert not errs
    return h


def check(text):
    return nc.check_dut_text(canon_hier(), text, "copy")


def test_baseline_peer_and_self_pass():
    assert check(TOP) == []
    assert check(PEER_TXT.replace("top", "rcosc_top")) == []


def test_formatting_equivalents_pass():
    t = TOP.replace(".subckt", ".SUBCKT").replace("R1 a c 10k", "r1   a\tc  10K")
    t = "* comment\n\n" + t.replace("nf=1", "").replace("+ ", "+ nf=1 ") + "\n.end\n"
    assert check(t) == []
    # statement order
    lines = TOP.splitlines()
    lines[2], lines[3] = lines[3], lines[2]
    assert check("\n".join(lines) + "\n") == []
    # commented xschem wrapper
    t = TOP.replace(".subckt rcosc_top a b c", "**.subckt rcosc_top a b c", 1).replace(
        ".ends", "**.ends", 1)
    assert check(t) == []


def test_klt_adapter_passes_and_rejects_extra_device():
    assert check(KLT_PEX) == []
    bad = KLT_PEX.replace("Xcore a b c rcosc_top_core", "Xcore a b c rcosc_top_core\nR9 a b 1")
    assert any("klt adapter" in e for e in check(bad))
    bad = KLT_PEX.replace("Xcore a b c", "Xcore a c b")
    assert any("klt adapter" in e for e in check(bad))
    bad = KLT_PEX.replace(".subckt rcosc_top a b c", ".subckt rcosc_top b a c")
    assert any("klt adapter" in e for e in check(bad))


def _fails(mutated, needle):
    errs = check(mutated)
    assert errs, "mutation unexpectedly passed"
    assert any(needle in e and "subckt " in e and e.startswith("copy") for e in errs), errs


def test_electrical_mutations_fail():
    _fails(TOP.replace("rcosc_top a b c", "rcosc_top a c b"), "port list differs")
    _fails(TOP.replace("R1 a c 10k", "R1 a b 10k"), "missing statement: r1 a c 10k")
    _fails(TOP.replace("nfet", "pfet"), "extra statement")
    _fails(TOP.replace("W='2*1u'", "W='3*1u'"), "w='3*1u'")
    _fails(TOP.replace("nf=1", "nf=2"), "nf=2")
    _fails(TOP.replace("R2 a c 10k\n", ""), "missing statement")
    _fails(TOP.replace("R2 a c 10k\n", "R2 a c 10k\nR2 a c 10k\n"), "extra statement")
    _fails(TOP.replace("XU1 a b leaf", "XU1 a b leaf2"), "leaf2")
    _fails(TOP.replace("C1 p q 1p", "C1 p q 2p"), "c1 p q 2p")


def test_continuation_join_changes_detected():
    _fails(TOP.replace("+ nf=1", "+ nf=3"), "nf=3")


# ---- provenance ----------------------------------------------------------

def _tree(tmp_path, prov=None, copy=TOP):
    (tmp_path / "design/netlist").mkdir(parents=True)
    (tmp_path / "design/netlist/pvt_tb.spice").write_text(TB)
    (tmp_path / "design/netlist/rcosc_top.spice").write_text(PEER_TXT.replace("top", "rcosc_top"))
    d = tmp_path / "sim/bench"
    d.mkdir(parents=True)
    (d / "rcosc_top_schematic.spice").write_text(copy)
    if prov is not None:
        base = {"source": nc.CANONICAL,
                "source_sha256": nc.sha256_bytes(TB.encode()),
                "extracted_sha256": nc.sha256_bytes(copy.encode())}
        base.update(prov)
        base = {k: v for k, v in base.items() if v is not None}
        (d / "provenance.json").write_text(json.dumps({"dut": base}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_tree_passes_with_matching_and_without_provenance(tmp_path):
    assert nc.run(_tree(tmp_path, {})) == []


def test_no_provenance_still_compared(tmp_path):
    root = _tree(tmp_path / "a", None, TOP.replace("10k", "11k"))
    assert any("sim/bench/rcosc_top_schematic.spice" in e for e in nc.run(root))
    assert nc.run(_tree(tmp_path / "b", None)) == []


def test_source_hash_mismatch(tmp_path):
    errs = nc.run(_tree(tmp_path, {"source_sha256": "0" * 64}))
    assert any("source_sha256" in e for e in errs)


def test_extracted_hash_mismatch(tmp_path):
    errs = nc.run(_tree(tmp_path, {"extracted_sha256": "1" * 64}))
    assert any("extracted_sha256" in e for e in errs)


def test_wrong_source_path(tmp_path):
    assert any("dut.source is" in e for e in nc.run(_tree(tmp_path, {"source": "x.spice"})))


def test_malformed_and_missing_fields(tmp_path):
    errs = nc.run(_tree(tmp_path / "a", {"source_sha256": None}))
    assert any("missing/malformed dut.source_sha256" in e for e in errs)
    root = _tree(tmp_path / "b", {})
    (root / "sim/bench/provenance.json").write_text("{not json")
    assert any("malformed provenance" in e for e in nc.run(root))
    (root / "sim/bench/provenance.json").write_text('{"dut": 3}')
    assert any("missing 'dut'" in e for e in nc.run(root))


def test_discovery_excludes_archives(tmp_path):
    root = _tree(tmp_path, None)
    for sub in ("results/old", "batch-attempts/x"):
        d = root / "sim/bench" / sub
        d.mkdir(parents=True)
        (d / "rcosc_top_schematic.spice").write_text(TOP.replace("10k", "99k"))
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    assert nc.discover(root) == ["sim/bench/rcosc_top_schematic.spice"]
    assert nc.run(root) == []


def _commit(root, msg="c"):
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=root, check=True, env=env)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def _archive_fixture(tmp_path, sha_field=True):
    """Old copy valid against the historical source, stale vs today's source."""
    root = _tree(tmp_path, None)
    sha = _commit(root)
    old_src = TB
    # today's DUT changes after the recorded commit
    (root / CANON_PATH).write_text(TB.replace("10k", "12k"))
    arch = root / "sim/bench/results/run1"
    arch.mkdir(parents=True)
    (arch / "rcosc_top_schematic.spice").write_text(TOP)
    dut = {"source": nc.CANONICAL,
           "source_sha256": nc.sha256_bytes(old_src.encode()),
           "extracted_sha256": nc.sha256_bytes(TOP.encode())}
    if sha_field:
        dut["source_git_sha"] = sha
    (arch / "provenance.json").write_text(json.dumps({"dut": dut}))
    return root, arch / "rcosc_top_schematic.spice"


CANON_PATH = "design/netlist/pvt_tb.spice"


def test_archive_checked_against_historical_not_current(tmp_path):
    root, copy = _archive_fixture(tmp_path)
    # against today's canonical the same bytes would fail
    errs = nc.check_dut_text(canon_hier((root / CANON_PATH).read_text()), TOP, "x")
    assert errs
    assert nc.check_archive(copy, root) == []


def test_archive_historical_semantic_mismatch_fails(tmp_path):
    root, copy = _archive_fixture(tmp_path)
    bad = TOP.replace("10k", "13k")
    copy.write_text(bad)
    prov = copy.parent / "provenance.json"
    d = json.loads(prov.read_text())
    d["dut"]["extracted_sha256"] = nc.sha256_bytes(bad.encode())
    prov.write_text(json.dumps(d))
    assert any("subckt" in e for e in nc.check_archive(copy, root))


def test_archive_without_commit_is_unverifiable(tmp_path):
    root, copy = _archive_fixture(tmp_path, sha_field=False)
    errs = nc.check_archive(copy, root)
    assert errs and "unverifiable" in errs[0]


def test_archive_unresolvable_commit_fails(tmp_path):
    root, copy = _archive_fixture(tmp_path)
    prov = copy.parent / "provenance.json"
    d = json.loads(prov.read_text())
    d["dut"]["source_git_sha"] = "deadbeef" * 5
    prov.write_text(json.dumps(d))
    assert "unverifiable" in nc.check_archive(copy, root)[0]


def test_archive_hash_mismatch(tmp_path):
    root, copy = _archive_fixture(tmp_path)
    prov = copy.parent / "provenance.json"
    d = json.loads(prov.read_text())
    d["dut"]["source_sha256"] = "2" * 64
    prov.write_text(json.dumps(d))
    assert any("historical source sha256" in e for e in nc.check_archive(copy, root))


def test_committed_tree_passes():
    root = Path(__file__).resolve().parent.parent
    assert nc.run(root) == []
