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
        self.assertEqual(bundle["counts"],{"issues":83,"groups":83,"evaluation_suites":114})
        self.assertEqual(len(bundle["groups"]),83)
        self.assertIn(("NG-04R-v2","1"),bundle["groups"])
        task=public_task(bundle,bundle["groups"][("occt_boolean_group_visible_544","1")])
        self.assertEqual(task["evaluation_suite"],{"id":"occt-group-544","version":"1"})
        serialized=json.dumps(task,ensure_ascii=False).lower()
        self.assertNotIn("hidden_issue_506",serialized)
        self.assertNotIn("evaluator_path",serialized)
        self.assertEqual(len(task["issues"]),1)

    def test_current_suite_checkpoint_inventory(self):
        bundle=validate_bundle(BUNDLE)
        suites=bundle["suites"]
        referenced={(group["evaluation_suite"]["id"],group["evaluation_suite"]["version"])
                    for group in bundle["groups"].values()}
        # Historical B55 and the opt-in extensions are selectable by version.
        self.assertEqual(set(suites)-referenced,{
            ("occt-bf-suite-b55-27310-27773-27252-oracle-v2","1"),
            ("occt-boolean-regression-1511c7e9","1"),
            ("occt-544-samedomain-regression","1"),
            ("occt-26243-version-regression","1"),
            ("mantis-32942-version-regression","1"),
            ("mantis-31470-version-regression","1"),
            ("occt-33570-version-regression","1"),
            ("occt-github-1371-version-regression","1"),
            ("mantis-29972-version-regression","1"),
            ("mantis-30703-version-regression","1"),
            ("occt-27227-version-regression","1"),
            ("occt-31835-version-regression","1"),
            ("occt-23612-version-regression","1"),
            ("occt-24313-version-regression","1"),
            ("occt-25818-version-regression","1"),
            ("occt-26796-version-regression","1"),
            ("occt-27780-version-regression","1"),
            ("occt-github-1163-version-regression","1"),
            ("occt-30082-version-regression","1"),
            ("occt-30082-ng05t-version-regression","1"),
            ("occt-github-1702-version-regression","1"),
            ("occt-github-1701-version-regression","1"),
            ("occt-32929-version-regression","1"),
            ("occt-github-1177-version-regression","1"),
            ("occt-github-1501-version-regression","1"),
            ("occt-github-1550-tangents-version-regression","1"),
            ("occt-github-1738-edge8-version-regression","1"),
            ("occt-single20-28195-checks","2"),
            ("occt-single20-25542-checks","2"),
            ("occt-25237-suite","2"), ("occt-28366-suite","2")})
        self.assertIn(("occt-bf-suite-b55-27310-27773-27252-geometry-v2","1"),referenced)
        checkpoints=[checkpoint for suite in suites.values() for checkpoint in suite["checkpoints"]]
        self.assertEqual(len(checkpoints),458)
        self.assertTrue(all(checkpoint["required"] for checkpoint in checkpoints))
        self.assertEqual({category:sum(cp["category"]==category for cp in checkpoints)
                          for category in ("original","neighborhood","regression")},
                         {"original":124,"neighborhood":205,"regression":129})
        self.assertEqual(sum(len(suites[key]["checkpoints"]) for key in referenced),392)

    def test_extended_common_suites_are_opt_in_and_preserve_v1(self):
        bundle = validate_bundle(BUNDLE)
        for issue, neighborhood, regression in (
            ("28195", "28195-neighborhood_axis31", "28195-regression_z90"),
            ("25542", "25542-neighborhood_down", "25542-regression_up"),
            ("25237", "tilted_edges", "overlapping_subarcs"),
            ("28366", "placed_section", "offset_section"),
        ):
            with self.subTest(issue=issue):
                suite_id = (f"occt-single20-{issue}-checks" if issue in ("25542","28195")
                            else f"occt-{issue}-suite")
                group_id, = bundle["suites"][(suite_id, "1")]["group_ids"]
                group = bundle["groups"][(group_id, "1")]
                self.assertEqual(group["evaluation_suite"], {"id": suite_id, "version": "1"})
                old = bundle["suites"][(suite_id, "1")]
                new = bundle["suites"][(suite_id, "2")]
                self.assertEqual(new["checkpoints"][:4], old["checkpoints"])
                self.assertTrue(set(old["support_files"]).issubset(new["support_files"]))
                self.assertEqual([(c["id"], c["category"], c["visibility"], c["required"])
                                  for c in new["checkpoints"][4:]], [
                    (neighborhood, "neighborhood", "public", True),
                    (regression, "regression", "public", True),
                ])

    def test_boolean_regression_reuses_the_single_qualified_z90_checkpoint(self):
        bundle = validate_bundle(BUNDLE)
        suite = bundle["suites"][("occt-boolean-regression-1511c7e9", "1")]
        original = bundle["suites"][("occt-single20-28195-checks", "2")]
        checkpoint, = suite["checkpoints"]
        self.assertEqual(checkpoint, next(c for c in original["checkpoints"] if c["id"] == "28195-regression_z90"))
        self.assertEqual(suite["source_ids"], ["occt-single20-1511c7e90f1a"])
        self.assertEqual(suite["group_ids"], ["occt-single20-28195"])
        self.assertEqual({Path(p).name for p in suite["support_files"]},
                         {"bug28195_solidsKO.brep", "rotated_common.tcl", "z90.points", "assertions.tcl", "solid_checks.tcl"})

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
