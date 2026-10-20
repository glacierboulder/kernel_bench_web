import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.settings import SETTINGS
from backend.worker import _load_task_specs


class CatalogOnlyWorkerDispatchTests(unittest.TestCase):
    def test_new_group_is_registered_without_legacy_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"bundle"
            shutil.copytree(SETTINGS.benchmark_root,root)
            (root/"evaluation/provenance/legacy-dispatch.json").unlink()
            catalog_path=root/"catalog.json"
            catalog=json.loads(catalog_path.read_text())
            original=next(item for item in catalog["groups"] if item["id"]=="occt_boolean_group_visible_544_506_847")
            group=json.loads((root/original["path"]).read_text())
            group["id"]="fixture_group_without_dispatch"
            group_path=Path("groups/fixture_group_without_dispatch/1.json")
            (root/group_path).parent.mkdir(parents=True)
            (root/group_path).write_text(json.dumps(group))
            catalog["groups"].append({"id":group["id"],"version":group["version"],"path":group_path.as_posix()})
            suite_ref=group["evaluation_suite"]
            suite_reference=next(item for item in catalog["evaluation_suites"]
                                 if item["id"]==suite_ref["id"] and item["version"]==suite_ref["version"])
            suite_path=root/suite_reference["path"]
            suite=json.loads(suite_path.read_text())
            suite["group_ids"].append(group["id"])
            suite_path.write_text(json.dumps(suite))
            catalog_path.write_text(json.dumps(catalog))

            with patch("backend.worker.BENCHMARK_ROOT",root), patch("backend.worker.PROTO",root/"no-proto"):
                specs=_load_task_specs()
            spec=specs["fixture_group_without_dispatch"]
            self.assertEqual(spec["catalog_version"],"1")
            self.assertIsNone(spec["legacy_version"])
            self.assertIsNone(spec["task_dir"])
            self.assertEqual(spec["suite_id"],suite_ref["id"])


if __name__=="__main__":
    unittest.main()
