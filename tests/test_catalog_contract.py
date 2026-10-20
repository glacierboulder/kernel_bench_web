import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.catalog import CatalogError,public_task,validate_bundle


ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/"benchmarks"/"occt"


class CatalogContractTests(unittest.TestCase):
    def test_current_catalog_maps_legacy_tasks_and_only_public_issue_material(self):
        bundle=validate_bundle(BUNDLE)
        self.assertEqual(bundle["counts"],{"issues":24,"groups":12,"evaluation_suites":12})
        self.assertEqual(len(bundle["groups"]),12)
        self.assertIn(("NG-04R-v2","1"),bundle["groups"])
        task=public_task(bundle,bundle["groups"][("occt_boolean_group_visible_544","1")])
        self.assertEqual(task["evaluation_suite"],{"id":"occt-group-544","version":"1"})
        serialized=json.dumps(task,ensure_ascii=False).lower()
        self.assertNotIn("hidden_issue_506",serialized)
        self.assertNotIn("evaluator_path",serialized)
        self.assertEqual(len(task["issues"]),1)

    def _copy_bundle(self):
        temporary=tempfile.TemporaryDirectory()
        target=Path(temporary.name)/"bundle"
        shutil.copytree(BUNDLE,target)
        self.addCleanup(temporary.cleanup)
        return target

    def test_duplicate_group_member_is_rejected(self):
        root=self._copy_bundle();path=root/"groups/legacy/occt-group-544/1.json"
        value=json.loads(path.read_text());value["members"].append(dict(value["members"][0]))
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(CatalogError,"duplicate"):
            validate_bundle(root)

    def test_group_update_requires_a_new_id(self):
        root=self._copy_bundle()
        catalog_path=root/"catalog.json"
        catalog=json.loads(catalog_path.read_text())
        catalog["groups"].append({
            "id":"occt_boolean_single_544","version":"2",
            "path":"groups/legacy/occt-single-544/2.json"
        })
        second=root/"groups/legacy/occt-single-544/2.json"
        value=json.loads((root/"groups/legacy/occt-single-544/1.json").read_text())
        value["version"]="2"
        second.write_text(json.dumps(value))
        catalog_path.write_text(json.dumps(catalog))
        with self.assertRaisesRegex(CatalogError,"group updates require a new group id"):
            validate_bundle(root)

    def test_draw_case_is_the_only_script_setting(self):
        root=self._copy_bundle()
        suite_path=root/"evaluation/suites/legacy/occt-single-544/1.json"
        suite=json.loads(suite_path.read_text())
        suite["checkpoints"][0].setdefault("runner_options",{})["script"]="other.tcl"
        suite_path.write_text(json.dumps(suite))
        with self.assertRaisesRegex(CatalogError,"case is the only DRAW script path"):
            validate_bundle(root)

    def test_escaping_public_material_is_rejected(self):
        root=self._copy_bundle();path=root/"issues/occt-544/1/issue.json"
        value=json.loads(path.read_text());value["public_materials"][0]="../../../../etc/passwd"
        path.write_text(json.dumps(value))
        with self.assertRaises(CatalogError):
            validate_bundle(root)

    def test_bad_budget_and_untrusted_runner_are_rejected(self):
        root=self._copy_bundle();path=root/"groups/legacy/occt-group-544/1.json"
        value=json.loads(path.read_text());value["budget"]["wall_seconds"]=0
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(CatalogError,"budget"):
            validate_bundle(root)
        root=self._copy_bundle();path=root/"evaluation/suites/legacy/occt-single-544/1.json"
        value=json.loads(path.read_text());value["checkpoints"][0]["runner"]="arbitrary-shell"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(CatalogError,"runner/oracle"):
            validate_bundle(root)

    def test_conflicting_catalog_content_cannot_reuse_an_existing_version(self):
        root=self._copy_bundle()
        with tempfile.TemporaryDirectory() as data_dir:
            env=dict(os.environ,BENCH_DATA_DIR=data_dir,BENCHMARK_ROOT=str(root))
            env.pop("BENCH_CONFIG",None)
            env.pop("BENCH_PROTO_ROOT",None)
            imported=subprocess.run([sys.executable,"-m","backend.import_proto"],cwd=ROOT,
                                    env=env,capture_output=True,text=True)
            self.assertEqual(imported.returncode,0,imported.stderr)
            connection=sqlite3.connect(Path(data_dir)/"bench.sqlite3")
            try:
                original_payload=connection.execute("select payload from tasks where id=? and version=?",
                    ("occt_boolean_single_544","1")).fetchone()[0]
            finally:
                connection.close()

            group_path=root/"groups/legacy/occt-single-544/1.json"
            value=json.loads(group_path.read_text(encoding="utf-8"))
            value["title"] += " changed"
            group_path.write_text(json.dumps(value),encoding="utf-8")
            conflict=subprocess.run([sys.executable,"-m","backend.import_proto"],cwd=ROOT,
                                    env=env,capture_output=True,text=True)
            self.assertNotEqual(conflict.returncode,0)
            self.assertIn("题目版本已存在且内容不同",conflict.stderr)
            connection=sqlite3.connect(Path(data_dir)/"bench.sqlite3")
            try:
                row=connection.execute("select payload from tasks where id=? and version=?",
                                       ("occt_boolean_single_544","1")).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(row)
            self.assertEqual(row[0],original_payload)


if __name__=="__main__":
    unittest.main()
