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
            build.mkdir();source.mkdir();work.mkdir()
            draw_runner=root/"draw_runner.py"
            draw_runner.write_text(
                "import argparse,json\n"
                "from pathlib import Path\n"
                "p=argparse.ArgumentParser()\n"
                "p.add_argument('--build-dir');p.add_argument('--resource-dir');p.add_argument('--case-dir')\n"
                "p.add_argument('--script');p.add_argument('--timeout-seconds');p.add_argument('--cpu-limit-seconds')\n"
                "a=p.parse_args();script=Path(a.case_dir)/a.script;text=script.read_text()\n"
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

    def test_missing_draw_case_fails_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cases=root/"cases";case_dir=cases/"issues/new-check"
            case_dir.mkdir(parents=True);(case_dir/"reproduce.tcl").write_text("puts TEST_DONE_FALLBACK\n")
            build=root/"build";source=root/"source";work=root/"work"
            build.mkdir();source.mkdir();work.mkdir()
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
