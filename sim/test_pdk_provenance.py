"""Offline tests for sim/pdk_provenance.py (tmp-dir fixtures, no real PDK)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdk_provenance as pp  # noqa: E402

H1 = "c6d73a35f524070e85faff4a6a9eef49553ebc2b"
H2 = "f6eeac7d" + "0" * 32


def _volare(tmp_path, h=H1, sources=None):
    real = tmp_path / "volare/gf180mcu/versions" / h / "gf180mcuC"
    (real / "libs.tech/ngspice").mkdir(parents=True)
    if sources is not None:
        (real / "SOURCES").write_text(sources)
    root = tmp_path / "root"
    root.mkdir()
    (root / "gf180mcuC").symlink_to(real)
    return root


def test_versioned_symlink_only(tmp_path):
    r = pp.resolve_pdk_revision(_volare(tmp_path), "gf180mcuC")
    assert r == {"pdk_revision": H1, "pdk_revision_source": "volare-version-dir"}


def test_sources_and_version_dir_agree(tmp_path):
    root = _volare(tmp_path, sources=f"open_pdks {H1}\n")
    r = pp.resolve_pdk_revision(root, "gf180mcuC")
    assert r["pdk_revision"] == H1
    assert r["pdk_revision_source"] == "SOURCES+volare-version-dir"


def test_sources_metadata_plain_dir(tmp_path):
    (tmp_path / "gf180mcuC").mkdir()
    (tmp_path / "gf180mcuC/SOURCES").write_text(f"open_pdks {H2}\n")
    r = pp.resolve_pdk_revision(tmp_path, "gf180mcuC")
    assert r == {"pdk_revision": H2, "pdk_revision_source": "SOURCES"}


def test_disagreement_is_unknown(tmp_path):
    r = pp.resolve_pdk_revision(_volare(tmp_path, sources=f"open_pdks {H2}\n"),
                                "gf180mcuC")
    assert r["pdk_revision"] == "unknown" and "disagree" in r["pdk_revision_reason"]


def test_plain_directory_unknown(tmp_path):
    (tmp_path / "gf180mcuC").mkdir()
    r = pp.resolve_pdk_revision(tmp_path, "gf180mcuC")
    assert r["pdk_revision"] == "unknown"
    assert r["pdk_revision_reason"].strip()
    assert "pdk_revision_source" not in r


def test_malformed_metadata_unknown(tmp_path):
    d = tmp_path / "gf180mcuC"
    d.mkdir()
    for body in ("garbage\n", "open_pdks abc123\n", "open_pdks " + H1.upper() + "\n",
                 f"open_pdks {H1}\nopen_pdks {H2}\n", ""):
        (d / "SOURCES").write_text(body)
        r = pp.resolve_pdk_revision(tmp_path, "gf180mcuC")
        assert r["pdk_revision"] == "unknown", body
        assert r["pdk_revision_reason"]
    (d / "SOURCES").write_bytes(b"\xff\xfe\x00bad")
    assert pp.resolve_pdk_revision(tmp_path, "gf180mcuC")["pdk_revision"] == "unknown"


def test_broken_symlink_and_missing(tmp_path):
    (tmp_path / "gf180mcuC").symlink_to(tmp_path / "nowhere")
    assert pp.resolve_pdk_revision(tmp_path, "gf180mcuC")["pdk_revision"] == "unknown"
    assert pp.resolve_pdk_revision(tmp_path, "other")["pdk_revision"] == "unknown"


def test_non_hash_versions_dir_not_trusted(tmp_path):
    real = tmp_path / "versions/latest/gf180mcuC"
    real.mkdir(parents=True)
    r = pp.resolve_pdk_revision(real.parent.parent.parent / "versions/latest", "gf180mcuC")
    assert r["pdk_revision"] == "unknown"


def test_manifest_fields_portable(tmp_path):
    root = _volare(tmp_path)
    md = root / "gf180mcuC/libs.tech/ngspice"
    f = pp.manifest_fields(root, "gf180mcuC", md)
    assert f["model_dir"] == "gf180mcuC/libs.tech/ngspice"
    assert f["pdk"] == "gf180mcuC" and f["pdk_revision"] == H1
    blob = json.dumps(f)
    assert str(tmp_path) not in blob and "pdk_root" not in f


def test_model_dir_outside_root_omitted(tmp_path):
    root = _volare(tmp_path)
    f = pp.manifest_fields(root, "gf180mcuC", tmp_path / "elsewhere")
    assert "model_dir" not in f
    assert pp.portable_relpath(root, root) is None
    assert pp.portable_relpath(root / "x" / ".." / "y", root) is None


def test_unknown_always_has_reason_and_display(tmp_path):
    (tmp_path / "gf180mcuC").mkdir()
    f = pp.manifest_fields(tmp_path, "gf180mcuC")
    assert f["pdk_revision"] == "unknown" and f["pdk_revision_reason"]
    assert str(tmp_path) not in pp.display(f)


# -- driver wiring ----------------------------------------------------------
SIM = Path(__file__).resolve().parent


def test_iq_driver_manifest_carries_revision_no_host_paths(tmp_path):
    from _module_loader import load_module
    iq = load_module("ml_iq_sweep_65", SIM / "iq" / "iq_sweep.py", reuse=False)
    root = _volare(tmp_path, sources=f"open_pdks {H1}\n")
    fields = pp.manifest_fields(root, "gf180mcuC", root / "gf180mcuC/libs.tech/ngspice")
    out = tmp_path / "res"
    out.mkdir()
    row = {"process": "tt", "temp_c": 27, "vdd_v": 3.3, "code": 0x80,
           "iq_op_ua": 1.0, "iq_run_ua": 2.0, "f_mhz": 3.0, "log": "x.log"}
    iq.write_results("20990101T000000Z", [row], str(out), "ngspice-test", fields,
                     "abc1234", False, ["tt"], [0x80], "endpoints", 1.0, 1)
    text = (out / "manifest.json").read_text()
    m = json.loads(text)
    assert m["pdk_revision"] == H1 and m["pdk"] == "gf180mcuC"
    assert "pdk_root" not in m and m["model_dir"] == "gf180mcuC/libs.tech/ngspice"
    for f in out.iterdir():
        assert str(tmp_path) not in f.read_text(), f.name


def test_all_three_drivers_use_the_shared_helper():
    for rel in ("pvt/pvt_sweep.py", "pvt-postlayout/pex_pvt_sweep.py"):
        src = (SIM / rel).read_text()
        assert "pdk_provenance.manifest_fields(pdk_root, pdk, model_dir)" in src, rel
        assert '"pdk_root"' not in src and "str(model_dir)" not in src, rel
        assert "@ `{" not in src.split("PDK |")[1].split("\n")[0], rel
    src = (SIM / "iq" / "iq_sweep.py").read_text()
    assert "pdk_provenance.manifest_fields(pdk_root, pdk, model_dir)" in src
    assert '"pdk_root"' not in src
