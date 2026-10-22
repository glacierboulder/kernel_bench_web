import tempfile
import unittest
from pathlib import Path

from backend.suite_driver import _execute


class SuiteDriverTests(unittest.TestCase):
    def test_manifest_case_selects_each_draw_script_in_the_same_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cases=root/"cases";case_dir=cases/"issues/new-check"
            case_dir.mkdir(parents=True)
            one=case_dir/"one.tcl";one.write_text("puts TEST_DONE_ONE\n")
            two=case_dir/"two.tcl";two.write_text("puts TEST_DONE_TWO\n")
            build=root/"build";source=root/"source";work=root/"work"
            build.mkdir();source.mkdir();work.mkdir();(source/"src"/"DrawResources").mkdir(parents=True)
            draw_runner=root/"draw_runner.py"
            draw_runner.write_text(
                "import argparse,json,os\n"
                "from pathlib import Path\n"
                "p=argparse.ArgumentParser()\n"
                "p.add_argument('--build-dir');p.add_argument('--resource-dir');p.add_argument('--case-dir')\n"
                "p.add_argument('--script');p.add_argument('--timeout-seconds');p.add_argument('--cpu-limit-seconds')\n"
                "a=p.parse_args();script=Path(a.case_dir)/a.script;text=script.read_text()\n"
                "assert Path(a.resource_dir)/'DrawResources'; assert (Path(a.resource_dir)/'DrawResources').is_dir()\n"
                "assert Path(os.environ['CASROOT'])/'src' == Path(a.resource_dir)\n"
                "print(json.dumps({'return_code':0,'test_done_marker':'TEST_DONE' in text,"
                "'elapsed_seconds':0.01,'script':str(script),'stdout_tail':text}))\n"
            )
            spec={"id":"checkpoint_added_without_runner_code_change","runner":"draw_case_v1",
                  "oracle":"draw_test_done_v1","case":"issues/new-check/one.tcl",
                  "timeout_seconds":20,"runner_options":{"case_timeout_seconds":18}}
            result=_execute(spec,case_root=cases,build=build,source=source,work=work,draw_runner=draw_runner)
            self.assertTrue(result["passed"])
            self.assertEqual(result["result"]["elapsed_seconds"],0.01)
            self.assertEqual(Path(result["result"]["script"]).name,"one.tcl")
            self.assertIn("TEST_DONE_ONE",result["result"]["stdout_tail"])

            spec["case"]="issues/new-check/two.tcl"
            result=_execute(spec,case_root=cases,build=build,source=source,work=work,draw_runner=draw_runner)
            self.assertTrue(result["passed"])
            self.assertEqual(Path(result["result"]["script"]).name,"two.tcl")
            self.assertIn("TEST_DONE_TWO",result["result"]["stdout_tail"])

    def test_staged_geometry_record_uses_oracle_verdict(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "case.tcl").write_text("puts TEST_DONE\n")
            spec = {"id": "staged", "runner": "draw_case_v1", "case": "case.tcl", "timeout_seconds": 20}
            for schema in ("bf-group2-staged-run-v1", "bf-group3-staged-run-v1"):
                for status, code in (("geometry_pass", 0), ("geometry_fail", 1), ("not_run", 2)):
                    with self.subTest(schema=schema, status=status):
                        record = {"schema_version": schema, "process_return_code": code,
                                  "oracle": {"status": status}, "duration_seconds": 0.1}
                        envelope = {"return_code": code, "output_tail": json.dumps(record), "timed_out": False}
                        with patch("backend.suite_driver._run", return_value=envelope):
                            result = _execute(spec, case_root=root, build=root, source=root,
                                              work=root, draw_runner=root / "runner.py")
                        self.assertEqual(result["passed"], status == "geometry_pass")
                        self.assertEqual(result["result"]["runner_record"], record)

    def test_writable_bundle_preserves_frozen_files_and_hidden_helpers(self):
        from backend.suite_driver import _writable_case_root
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = root / "frozen"
            case = frozen / "issues/occt-test/1/public"
            case.mkdir(parents=True)
            (case / "case.tcl").write_bytes(b"puts TEST_DONE\n")
            assets = root / "private/evaluator_assets/group"
            assets.mkdir(parents=True)
            (assets / "oracle.tcl").write_bytes(b"# locked geometry helper\n")
            work = root / "work"
            work.mkdir()
            copied = _writable_case_root(frozen, work, assets.parent)
            self.assertEqual((copied / "issues/occt-test/1/public/case.tcl").read_bytes(), (case / "case.tcl").read_bytes())
            (copied / "issues/occt-test/1/public/images").mkdir()
            self.assertFalse((case / "images").exists())
            self.assertEqual((copied / "evaluation/cases/evaluator_assets/group/oracle.tcl").read_bytes(), (assets / "oracle.tcl").read_bytes())

    def test_missing_draw_case_fails_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cases=root/"cases";case_dir=cases/"issues/new-check"
            case_dir.mkdir(parents=True);(case_dir/"reproduce.tcl").write_text("puts TEST_DONE_FALLBACK\n")
            build=root/"build";source=root/"source";work=root/"work"
            build.mkdir();source.mkdir();work.mkdir();(source/"src"/"DrawResources").mkdir(parents=True)
            draw_runner=root/"draw_runner.py";invoked=draw_runner.with_suffix(".invoked")
            draw_runner.write_text(
                "from pathlib import Path\n"
                f"Path({str(invoked)!r}).write_text('invoked')\n"
                "print('{\"return_code\":0,\"test_done_marker\":true}')\n"
            )
            spec={"id":"missing-case","runner":"draw_case_v1","oracle":"draw_test_done_v1",
                  "case":"issues/new-check/missing.tcl","timeout_seconds":20}
            with self.assertRaises(FileNotFoundError):
                _execute(spec,case_root=cases,build=build,source=source,work=work,draw_runner=draw_runner)
            self.assertFalse(invoked.exists())


if __name__=="__main__":
    unittest.main()
