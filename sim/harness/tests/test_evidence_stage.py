"""Issue #196: ``sim/evidence_stage.py`` stages a campaign in scratch and
commits only a manifest and the run summary; every failure is fail closed.

Stdlib only; ``klt`` is the emulation from ``test_evidence_store``.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import evidence_stage as stg  # noqa: E402
from harness import evidence_store as es  # noqa: E402
from test_evidence_store import fake_klt  # noqa: E402


class StageTest(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name).resolve()
        (self.root / "sim/bench").mkdir(parents=True)

    def staged(self, **kw):
        with mock.patch.object(es, "preflight"):
            st = stg.open_stage("bench", "20261023T000000Z", repo_root=self.root, **kw)
        (st.corners / st.runid).mkdir()
        (st.corners / st.runid / "a.log").write_text("log a\n")
        (st.results / st.runid).mkdir()
        (st.results / st.runid / "results.csv").write_text("x\n1\n")
        (st.results / st.runid / st.summary_name).write_text("# run\n")
        return st

    def put(self, store, **kw):
        return lambda files, repo: es.put_files(files, repo, run=fake_klt(store, **kw))

    def test_stores_and_commits_only_manifest_and_summary(self):
        st = self.staged()
        m = st.finish(put=self.put({}))
        names = [e["name"] for e in json.loads(m.read_text())["entries"]]
        self.assertEqual(names, ["sim/bench/corners/20261023T000000Z/a.log",
                                 "sim/bench/results/20261023T000000Z/results.csv"])
        self.assertTrue(all(json.loads(m.read_text())["entries"][i]["uri"].startswith("artifact:")
                            for i in (0, 1)))
        self.assertIn("## Stored evidence", st.summary_path.read_text())
        self.assertEqual(sorted(p.name for p in (self.root / "sim/bench").rglob("*") if p.is_file()),
                         ["summary.md"])

    def test_readme_summary_name(self):
        st = self.staged(summary_name="README.md")
        st.finish(put=self.put({}))
        self.assertTrue((self.root / "sim/bench/results/20261023T000000Z/README.md").is_file())

    def test_failed_put_commits_nothing_and_keeps_scratch(self):
        st = self.staged()
        with self.assertRaises(es.StoreError):
            st.finish(put=self.put({}, fail="broker_unreachable"))
        self.assertFalse((self.root / "manifests").exists())
        self.assertFalse((self.root / "sim/bench/results").exists())
        self.assertTrue((st.corners / st.runid / "a.log").is_file())

    def test_finish_or_report_exit_codes(self):
        st = self.staged()
        with mock.patch.object(es, "put_files", side_effect=es.StoreError("down")), \
                mock.patch("sys.stderr"):
            self.assertEqual(stg.finish_or_report(st), 10)
        self.assertFalse((self.root / "manifests").exists())

    def test_preflight_failure_raises_before_creating_scratch(self):
        with mock.patch.object(es, "preflight", side_effect=es.StoreError("no broker")):
            with self.assertRaises(es.StoreError):
                stg.open_stage("bench", "r1", repo_root=self.root)
        self.assertFalse((self.root / "sim/build").exists())

    def test_unset_broker_fails_closed(self):
        with mock.patch.dict("os.environ", {}, clear=False) as env:
            env.pop(es.ENV_BROKER, None)
            with self.assertRaisesRegex(es.StoreError, "unset"):
                stg.open_stage("bench", "r1", repo_root=self.root)
        self.assertFalse((self.root / "sim/build").exists())

    def test_existing_manifest_refuses_run_id(self):
        (self.root / "manifests/artifacts").mkdir(parents=True)
        (self.root / "manifests/artifacts/bench-r1.manifest.json").write_text("{}")
        with mock.patch.object(es, "preflight"):
            with self.assertRaisesRegex(es.StoreError, "append-only"):
                stg.open_stage("bench", "r1", repo_root=self.root)


if __name__ == "__main__":
    unittest.main()
