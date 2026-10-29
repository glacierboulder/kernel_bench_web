import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.catalog import public_task,validate_bundle
from backend.evaluator import _prepare_control
from backend.freeze import freeze_catalog_task,verify_snapshot
from backend.settings import SETTINGS


class FreezeTests(unittest.TestCase):
    def test_catalog_task_freezes_public_and_supervisor_materials(self):
        bundle=validate_bundle(SETTINGS.benchmark_root)
        group=bundle["groups"][("occt_boolean_single_544","1")]
        task=public_task(bundle,group)
        cached=SETTINGS.cache_dir/"sources"/group["source_id"]
        if not (cached/"source.json").is_file():
            self.skipTest("verified local source cache has not been prepared")
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=freeze_catalog_task(task,root)
            snapshot=root/"benchmark-snapshot"
            self.assertTrue(result["frozen"])
            self.assertTrue((snapshot/"visible/issue_544/reproduce.tcl").is_file())
            self.assertTrue((snapshot/"supervisor/legacy/run_eval.py").is_file())
            self.assertFalse((snapshot/"visible/hidden_issue_506").exists())
            verify_snapshot(snapshot)

    def test_suite_version_can_advance_without_changing_the_group_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"bundle"
            shutil.copytree(SETTINGS.benchmark_root,root)
            catalog_path=root/"catalog.json"
            catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
            original=next(item for item in catalog["evaluation_suites"]
                          if item["id"]=="occt-visible3" and item["version"]=="1")
            suite=json.loads((root/original["path"]).read_text(encoding="utf-8"))
            version_two={**suite,"version":"2","checkpoints":[
                *suite["checkpoints"],
                {**suite["checkpoints"][0],"id":"neighborhood-fixture",
                 "category":"neighborhood","required":False},
            ]}
            target=Path("evaluation/suites/legacy/occt-group-544-506-847/2.json")
            (root/target).parent.mkdir(parents=True,exist_ok=True)
            (root/target).write_text(json.dumps(version_two,indent=2)+"\n",encoding="utf-8")
            catalog["evaluation_suites"].append({"id":"occt-visible3","version":"2","path":target.as_posix()})
            catalog_path.write_text(json.dumps(catalog,indent=2)+"\n",encoding="utf-8")

            bundle=validate_bundle(root)
            group=bundle["groups"][("occt_boolean_group_visible_544_506_847","1")]
            task=public_task(bundle,group)
            with patch("backend.freeze.SETTINGS",replace(SETTINGS,benchmark_root=root)):
                result=freeze_catalog_task(task,Path(directory)/"run",
                    suite_override={"id":"occt-visible3","version":"2"})
            snapshot=Path(directory)/"run/benchmark-snapshot"
            frozen=json.loads((snapshot/"suite.json").read_text(encoding="utf-8"))
            self.assertEqual(result["suite_version"],"2")
            self.assertEqual(frozen["version"],"2")
            self.assertEqual(frozen["checkpoints"][-1]["category"],"neighborhood")
            self.assertEqual(bundle["groups"][(group["id"],group["version"])]["evaluation_suite"]["version"],"1")
            self.assertEqual(json.loads((root/original["path"]).read_text())["version"],"1")

    def test_mantis_catalog_paths_alias_to_locked_dispatch_routes(self):
        bundle=validate_bundle(SETTINGS.benchmark_root)
        group=bundle["groups"].get(("NG-04R-v2","1"))
        if group is None:
            self.skipTest("five-group OCCT bundle has not been merged")
        cached=SETTINGS.cache_dir/"sources"/group["source_id"]
        if not (cached/"source.json").is_file():
            self.skipTest("verified NG-04R source cache has not been prepared")
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=freeze_catalog_task(public_task(bundle,group),root)
            snapshot=root/"benchmark-snapshot"
            frozen=json.loads((snapshot/"suite.json").read_text(encoding="utf-8"))
            manifest=json.loads((snapshot/"snapshot.json").read_text(encoding="utf-8"))
            aliases=manifest["case_path_aliases"]
            self.assertEqual(len(aliases),3)
            self.assertTrue(all(item["catalog_case"].startswith("issues/occt-") and
                                item["evaluator_case"].startswith("issues/mantis-")
                                for item in aliases))

            case_root=snapshot/"supervisor"/"cases"/"bundle"
            lock=json.loads((snapshot/"supervisor"/"evaluator_assets"/
                             "five_group_execution"/"dispatch_lock.json").read_text(encoding="utf-8"))
            adapter_path=snapshot/"supervisor"/"legacy"/"scripts"/"run_draw_case.py"
            with patch("sys.dont_write_bytecode",True):
                spec=importlib.util.spec_from_file_location("frozen_five_group_draw_adapter",adapter_path)
                adapter=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(adapter)
            for checkpoint in frozen["checkpoints"]:
                case=checkpoint["case"]
                route=lock["checkpoint_routes"][case]
                self.assertEqual(route["checkpoint_id"],checkpoint["id"])
                self.assertEqual(route["group_id"],group["id"])
                self.assertEqual(route["suite"],f'{frozen["id"]}@{frozen["version"]}')
                target=case_root/case
                self.assertTrue(target.is_file(),case)
                with patch.dict("os.environ", {"BENCH_FROZEN_CASE_ROOT":str(case_root)}):
                    selected=adapter._route(target,adapter._contract())
                self.assertEqual(selected["checkpoint_id"],checkpoint["id"])
                self.assertEqual(selected["engine"]["path"],lock["runner_routes"][route["origin"]]["path"])
                self.assertTrue(adapter._asset(selected["engine"]).is_file())
            self.assertEqual(result["case_path_aliases"],aliases)
            verify_snapshot(snapshot)

    def test_non_snapshot_manifest_runtime_keeps_dispatch_assets_available(self):
        bundle=validate_bundle(SETTINGS.benchmark_root)
        group=bundle["groups"].get(("NG-04R-v2","1"))
        if group is None:
            self.skipTest("five-group OCCT bundle has not been merged")
        cached=SETTINGS.cache_dir/"sources"/group["source_id"]
        if not (cached/"source.json").is_file():
            self.skipTest("verified NG-04R source cache has not been prepared")
        suite_ref=group["evaluation_suite"]
        suite=bundle["suites"][(suite_ref["id"],suite_ref["version"])]
        with tempfile.TemporaryDirectory() as directory:
            control,source_dir=_prepare_control(Path(directory),None,[suite],"group",
                                                group["source_id"])
            self.assertEqual(source_dir,cached/"source")
            self.assertTrue((control/"private"/"evaluator_assets"/
                             "five_group_execution"/"dispatch_lock.json").is_file())
            frozen=json.loads((control/"suite.json").read_text(encoding="utf-8"))
            case_root=control/"cases"/"bundle"
            lock=json.loads((control/"private"/"evaluator_assets"/
                             "five_group_execution"/"dispatch_lock.json").read_text(encoding="utf-8"))
            adapter_path=control/"scripts"/"run_draw_case.py"
            with patch("sys.dont_write_bytecode",True):
                spec=importlib.util.spec_from_file_location("live_five_group_draw_adapter",adapter_path)
                adapter=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(adapter)
            for checkpoint in frozen["checkpoints"]:
                case=checkpoint["case"]
                route=lock["checkpoint_routes"][case]
                self.assertEqual(route["checkpoint_id"],checkpoint["id"])
                self.assertEqual(route["group_id"],group["id"])
                target=case_root/case
                self.assertTrue(target.is_file(),case)
                with patch.dict("os.environ", {"BENCH_FROZEN_CASE_ROOT":str(case_root)}):
                    selected=adapter._route(target,adapter._contract())
                self.assertEqual(selected["checkpoint_id"],checkpoint["id"])
                self.assertEqual(selected["engine"]["path"],lock["runner_routes"][route["origin"]]["path"])
                self.assertTrue(adapter._asset(selected["engine"]).is_file())

    def test_snapshot_hash_detects_changes_after_enqueue(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);payload=root/"issue/statement.md"
            payload.parent.mkdir();payload.write_text("frozen public statement")
            digest=hashlib.sha256()
            digest.update(b"issue/statement.md\0"+hashlib.sha256(payload.read_bytes()).digest())
            (root/"snapshot.json").write_text(json.dumps({"snapshot_sha256":digest.hexdigest()}))
            self.assertEqual(verify_snapshot(root)["snapshot_sha256"],digest.hexdigest())
            payload.write_text("changed after queue")
            with self.assertRaisesRegex(ValueError,"changed after queueing"):
                verify_snapshot(root)


if __name__=="__main__":
    unittest.main()
