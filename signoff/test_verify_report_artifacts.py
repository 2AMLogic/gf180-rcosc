#!/usr/bin/env python3
"""Synthetic negative tests for the artifact-provenance and binding guards in
signoff/verify-report.py (issue #165).

Covers ``verify_pins``, ``_binding_shape_problems``, ``verify_bindings``,
``verify_inventories`` and ``verify_power_delivery_citation``. Grade-row
comparison (``grade_drift``) is owned by test_verify_report_drift.py (#163).

Stdlib ``unittest`` only. Each test builds a valid synthetic repository tree in
a temporary directory with REAL sha256 digests computed from the fixture
bytes, repoints the module's REPO_ROOT / artifact tables at it, then breaks
exactly one condition. No klt, PDK, simulator, network, or committed evidence
is read or written.

Run (CI: ``.github/workflows/offline-suites.yml``)::

    python3 -I signoff/test_verify_report_artifacts.py
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("verify_report", HERE / "verify-report.py")
vr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vr)

# Module attributes the fixture repoints; restored after every test.
_PATCHED = (
    "REPO_ROOT",
    "PINNED_ARTIFACTS",
    "INVENTORIES",
    "LVS_ENVELOPE",
    "LVS_INPUTS",
    "ITEM11_ERC_ENVELOPE",
    "ITEM11_ERC_ARTIFACT",
    "ITEM11_ERC_SPEC",
)

GDS = "layout/cells/rcosc_top.gds"
SPEC = "layout/erc-supply-spec.json"
ERC = "layout/reports/rcosc_top.erc.json"
LVS = "layout/reports/rcosc_top.lvs.json"
DRC = "layout/reports/rcosc_top.drc.json"
EXTRACTED = "layout/reports/rcosc_top.extracted.spice"
REFSPICE = "layout/lvs_ref/rcosc_top.spice"
DESIGN_INV = "signoff/design-sources-inventory.md"
TB_INV = "signoff/testbench-inventory.md"
PROPOSAL = "docs/chipalooza/challenge-5-proposal.md"
WORKFLOW = ".github/workflows/signoff.yml"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory_text(paths):
    rows = "".join(f"| `{p}` | purpose |\n" for p in paths)
    return "# inventory\n\n| Path | Purpose |\n|---|---|\n" + rows


class Fixture:
    """A valid synthetic tree plus the manifest/fresh-report that match it."""

    def __init__(self, root: Path):
        self.root = root
        self.write(GDS, b"gds-bytes-v1")
        self.write(SPEC, b'{"supply": "VDD"}')
        self.write(PROPOSAL, b"proposal")
        self.write(WORKFLOW, b"name: signoff\n")
        self.write(EXTRACTED, b"extracted netlist")
        self.write(REFSPICE, b"reference netlist")
        self.write("signoff/listed-a.txt", b"a")
        self.write("signoff/listed-b.txt", b"b")
        self.write(DESIGN_INV, inventory_text(["signoff/listed-a.txt"]).encode())
        self.write(TB_INV, inventory_text(["signoff/listed-b.txt"]).encode())

        gds = sha(self.read(GDS))
        # item -> (envelope rel path, artifact rel path, bound?)
        self.table = {
            "1": ("signoff/design-sources-envelope.json", DESIGN_INV, True),
            "2": ("signoff/layout-envelope.json", GDS, True),
            "3": (DRC, GDS, False),
            "8": ("signoff/characterization-envelope.json", PROPOSAL, False),
            "9": ("signoff/testbench-envelope.json", TB_INV, True),
            "10": ("signoff/repo-hygiene-envelope.json", WORKFLOW, True),
        }
        self.manifest = {"evidence": {}}
        for item, (env, art, bound) in self.table.items():
            digest = sha(self.read(art))
            envelope = {"provenance": {"input": {"content_hash": "sha256:" + digest}}}
            if bound:
                envelope["kind"] = "generic"
                envelope["t1_item"] = int(item)
                envelope["provenance"]["input"]["path"] = {"path": art, "scope": "repo"}
            self.write_json(env, envelope)
            self.manifest["evidence"][item] = {"file": env, "content_hash": "sha256:" + digest}

        self.write_json(
            LVS,
            {
                "environment": {
                    "layout_sha256": sha(self.read(EXTRACTED)),
                    "reference_sha256": sha(self.read(REFSPICE)),
                }
            },
        )
        self.write_json(
            ERC,
            {
                "provenance": {
                    "input": {"content_hash": "sha256:" + gds},
                    "spec": {"content_hash": "sha256:" + sha(self.read(SPEC))},
                }
            },
        )
        self.manifest["evidence"]["11"] = [
            {"file": ERC, "content_hash": "sha256:" + gds},
            {"file": LVS},
        ]
        self.fresh = {
            "items": [
                {
                    "id": int(i),
                    "status": "met",
                    "citation": {"artifact_binding": {"t1_item": int(i), "input_verified": True}},
                }
                for i in vr_bound_items()
            ]
        }

    def write(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def read(self, rel):
        return (self.root / rel).read_bytes()

    def write_json(self, rel, obj):
        self.write(rel, json.dumps(obj).encode())

    def load_json(self, rel):
        return json.loads(self.read(rel))

    def patch_module(self):
        r = self.root
        vr.REPO_ROOT = r
        vr.PINNED_ARTIFACTS = {i: (r / e, r / a) for i, (e, a, _) in self.table.items()}
        vr.INVENTORIES = (r / DESIGN_INV, r / TB_INV)
        vr.LVS_ENVELOPE = r / LVS
        vr.LVS_INPUTS = ((r / EXTRACTED, "layout_sha256"), (r / REFSPICE, "reference_sha256"))
        vr.ITEM11_ERC_ENVELOPE = r / ERC
        vr.ITEM11_ERC_ARTIFACT = r / GDS
        vr.ITEM11_ERC_SPEC = r / SPEC


def vr_bound_items():
    return vr.ARTIFACT_BOUND_ITEMS


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = {n: getattr(vr, n) for n in _PATCHED}
        self.addCleanup(self._restore)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fx = Fixture(Path(tmp.name).resolve())
        self.fx.patch_module()

    def _restore(self):
        for n, v in self._saved.items():
            setattr(vr, n, v)

    def assertOneProblem(self, problems, *needles):
        self.assertEqual(len(problems), 1, problems)
        for n in needles:
            self.assertIn(n, problems[0])

    def assertSomeProblem(self, problems, *needles):
        self.assertTrue(problems, "expected at least one problem")
        joined = "\n".join(problems)
        for n in needles:
            self.assertIn(n, joined)


class PinTests(Base):
    def pins(self):
        return vr.verify_pins(self.fx.manifest)

    def test_valid_fixture_has_no_problems(self):
        self.assertEqual(self.pins(), [])
        self.assertEqual(vr.verify_bindings(self.fx.fresh), [])
        self.assertEqual(vr.verify_inventories(), [])
        self.assertEqual(vr.verify_power_delivery_citation(self.fx.manifest["evidence"]), [])

    def test_artifact_bytes_changed_without_refreshing_digest(self):
        self.fx.write(WORKFLOW, b"name: signoff\n# edited\n")
        problems = self.pins()
        self.assertOneProblem(problems, "item 10 citation", "changed since the evidence")

    def test_gds_change_flags_every_citation_pinning_it(self):
        self.fx.write(GDS, b"gds-bytes-v2")
        joined = "\n".join(self.pins())
        self.assertIn("item 2 citation", joined)
        self.assertIn("item 3 citation", joined)
        self.assertIn("item 11 citation", joined)

    def test_manifest_pin_differs_from_envelope_hash(self):
        # Envelope still matches the artifact; only the manifest pin is wrong.
        self.fx.manifest["evidence"]["8"]["content_hash"] = "sha256:" + sha(b"other")
        self.assertOneProblem(self.pins(), "item 8 citation", "manifest pin", "does not match")

    def test_envelope_hash_differs_from_artifact_independently(self):
        # Manifest pin and envelope agree with each other but not the artifact.
        stale = "sha256:" + sha(b"stale")
        env = self.fx.load_json(DRC)
        env["provenance"]["input"]["content_hash"] = stale
        self.fx.write_json(DRC, env)
        self.fx.manifest["evidence"]["3"]["content_hash"] = stale
        problems = self.pins()
        self.assertOneProblem(problems, "item 3 citation", "currently hashes to")
        self.assertNotIn("manifest pin", problems[0])

    def test_missing_content_hash_pin_rejected(self):
        del self.fx.manifest["evidence"]["8"]["content_hash"]
        self.assertOneProblem(self.pins(), "item 8 citation", "content_hash pin")

    def test_manifest_cites_unexpected_file_rejected(self):
        self.fx.manifest["evidence"]["3"]["file"] = "layout/reports/other.json"
        self.assertOneProblem(self.pins(), "item 3 citation", "expects")

    def test_missing_bound_artifact_rejected(self):
        (self.fx.root / PROPOSAL).unlink()
        self.assertOneProblem(self.pins(), "item 8 citation", "does not exist")

    def test_lvs_netlist_changed_without_envelope_refresh(self):
        self.fx.write(EXTRACTED, b"extracted netlist edited")
        self.assertOneProblem(self.pins(), "unpinned LVS citation", "layout_sha256")


class BindingShapeTests(Base):
    def edit_env(self, rel, fn):
        env = self.fx.load_json(rel)
        fn(env)
        self.fx.write_json(rel, env)

    def test_wrong_artifact_path_in_bound_envelope(self):
        self.edit_env(
            "signoff/layout-envelope.json",
            lambda e: e["provenance"]["input"].update(path={"path": "layout/cells/other.gds", "scope": "repo"}),
        )
        self.assertOneProblem(
            vr.verify_pins(self.fx.manifest), "item 2 citation", "provenance.input.path", GDS
        )

    def test_wrong_path_scope_rejected(self):
        self.edit_env(
            "signoff/layout-envelope.json",
            lambda e: e["provenance"]["input"].update(path={"path": GDS, "scope": "absolute"}),
        )
        self.assertOneProblem(vr.verify_pins(self.fx.manifest), "provenance.input.path")

    def test_bare_string_path_rejected(self):
        # A bare string has no scope, so it is not the expected repo binding.
        self.edit_env(
            "signoff/layout-envelope.json", lambda e: e["provenance"]["input"].update(path=GDS)
        )
        self.assertOneProblem(vr.verify_pins(self.fx.manifest), "provenance.input.path")

    def test_wrong_t1_item_in_bound_envelope(self):
        self.edit_env("signoff/testbench-envelope.json", lambda e: e.update(t1_item=1))
        self.assertOneProblem(vr.verify_pins(self.fx.manifest), "item 9 citation", "t1_item 1")

    def test_string_t1_item_rejected(self):
        self.edit_env("signoff/testbench-envelope.json", lambda e: e.update(t1_item="9"))
        self.assertOneProblem(vr.verify_pins(self.fx.manifest), "item 9 citation", "integer 9")

    def test_non_generic_kind_rejected(self):
        self.edit_env("signoff/design-sources-envelope.json", lambda e: e.update(kind="native"))
        self.assertOneProblem(vr.verify_pins(self.fx.manifest), "item 1 citation", "generic")

    def test_shape_helper_directly(self):
        env = self.fx.load_json("signoff/layout-envelope.json")
        ok = vr._binding_shape_problems(
            "l", "2", env, vr.PINNED_ARTIFACTS["2"][0], vr.PINNED_ARTIFACTS["2"][1]
        )
        self.assertEqual(ok, [])
        env["t1_item"] = 3
        bad = vr._binding_shape_problems(
            "l", "2", env, vr.PINNED_ARTIFACTS["2"][0], vr.PINNED_ARTIFACTS["2"][1]
        )
        self.assertOneProblem(bad, "t1_item 3")


class BindingVerificationTests(Base):
    def row(self, item):
        return next(r for r in self.fx.fresh["items"] if r["id"] == int(item))

    def test_met_without_artifact_binding_rejected(self):
        del self.row("2")["citation"]["artifact_binding"]
        self.assertOneProblem(vr.verify_bindings(self.fx.fresh), "item 2", "without an artifact_binding")

    def test_met_without_citation_rejected(self):
        del self.row("1")["citation"]
        self.assertOneProblem(vr.verify_bindings(self.fx.fresh), "item 1", "without an artifact_binding")

    def test_input_not_verified_rejected(self):
        self.row("9")["citation"]["artifact_binding"]["input_verified"] = False
        self.assertOneProblem(vr.verify_bindings(self.fx.fresh), "item 9", "input_verified")

    def test_binding_for_wrong_item_rejected(self):
        self.row("10")["citation"]["artifact_binding"]["t1_item"] = 9
        self.assertOneProblem(vr.verify_bindings(self.fx.fresh), "item 10", "t1_item")

    def test_unmet_item_is_not_required_to_be_bound(self):
        row = self.row("2")
        row["status"] = "unmet"
        del row["citation"]
        self.assertEqual(vr.verify_bindings(self.fx.fresh), [])


class InventoryTests(Base):
    def test_missing_listed_path_rejected(self):
        (self.fx.root / "signoff/listed-a.txt").unlink()
        self.assertOneProblem(
            vr.verify_inventories(), "design-sources-inventory.md", "signoff/listed-a.txt", "does not exist"
        )

    def test_inventory_without_recognized_rows_rejected(self):
        self.fx.write(TB_INV, b"# inventory\n\n- signoff/listed-b.txt\n| path | purpose |\n")
        self.assertOneProblem(vr.verify_inventories(), "testbench-inventory.md", "lists no paths")

    def test_missing_inventory_file_rejected(self):
        (self.fx.root / DESIGN_INV).unlink()
        self.assertOneProblem(vr.verify_inventories(), "design-sources-inventory.md", "missing")

    def test_directory_listed_path_is_accepted(self):
        (self.fx.root / "somedir").mkdir()
        self.fx.write(DESIGN_INV, inventory_text(["somedir"]).encode())
        self.assertEqual(vr.verify_inventories(), [])


class PowerDeliveryTests(Base):
    def check(self):
        return vr.verify_power_delivery_citation(self.fx.manifest["evidence"])

    def test_missing_lvs_half_rejected(self):
        ev = self.fx.manifest["evidence"]
        ev["11"] = [p for p in ev["11"] if p["file"] != LVS]
        self.assertOneProblem(self.check(), "item 11 citation", LVS)

    def test_missing_erc_half_rejected(self):
        ev = self.fx.manifest["evidence"]
        ev["11"] = [p for p in ev["11"] if p["file"] != ERC]
        self.assertOneProblem(self.check(), "item 11 citation", "no ERC part")

    def test_erc_part_without_pin_rejected(self):
        del self.fx.manifest["evidence"]["11"][0]["content_hash"]
        self.assertOneProblem(self.check(), "no ERC part carrying a content_hash")

    def test_non_list_entry_rejected(self):
        self.fx.manifest["evidence"]["11"] = {"file": ERC}
        self.assertOneProblem(self.check(), "compound list entry")

    def test_missing_entry_rejected(self):
        del self.fx.manifest["evidence"]["11"]
        self.assertOneProblem(self.check(), "compound list entry")

    def test_spec_bytes_changed_without_updating_erc_digest(self):
        self.fx.write(SPEC, b'{"supply": "VDD", "extra": 1}')
        self.assertOneProblem(self.check(), "item 11 citation", "spec hash", "erc-supply-spec.json")

    def test_manifest_pin_differs_from_erc_envelope(self):
        self.fx.manifest["evidence"]["11"][0]["content_hash"] = "sha256:" + sha(b"other")
        problems = self.check()
        self.assertOneProblem(problems, "manifest pin", "does not match")

    def test_gds_changed_without_erc_rerun(self):
        self.fx.write(GDS, b"gds-bytes-v2")
        self.assertOneProblem(self.check(), "currently hashes to")


if __name__ == "__main__":
    unittest.main()
