import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.catalog import validate_bundle


ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/"docs"/"benchmark-example"


class BenchmarkAuthoringExampleTests(unittest.TestCase):
    def test_example_validates_imports_and_can_enqueue_two_group_ids(self):
        with tempfile.TemporaryDirectory(prefix="benchmark-authoring-") as temporary:
            root=Path(temporary)/"bundle"
            shutil.copytree(EXAMPLE,root)
            bundle=validate_bundle(root)
            self.assertEqual(bundle["counts"],{"issues":2,"groups":2,"evaluation_suites":2})

            data=Path(temporary)/"data"
            env=dict(os.environ,BENCHMARK_ROOT=str(root),BENCH_DATA_DIR=str(data))
            env.pop("BENCH_PROTO_ROOT",None)
            env.pop("BENCH_CONFIG",None)
            imported=subprocess.run([sys.executable,"-m","backend.import_proto"],cwd=ROOT,
                                    env=env,capture_output=True,text=True)
            self.assertEqual(imported.returncode,0,imported.stderr)
            self.assertIn("导入 2 个 catalog 版本",imported.stdout)
            connection=sqlite3.connect(data/"bench.sqlite3")
            try:
                tasks={row[0]:json.loads(row[1]) for row in connection.execute(
                    "select id,payload from tasks")}
            finally:
                connection.close()
            self.assertEqual(set(tasks),{"manual-box-a-single","manual-box-pair"})
            self.assertEqual(len(tasks["manual-box-a-single"]["issues"]),1)
            self.assertEqual(len(tasks["manual-box-pair"]["issues"]),2)

            # Exercise the normal API queue path with source freezing stubbed.
            # No worker is started and the record stays in this temporary DB.
            enqueue_script="""
from unittest.mock import patch
import backend.app as api
from backend.app import AgentInput, RunInput
from backend.worker import TASK_SPECS

ids={"manual-box-a-single","manual-box-pair"}
assert ids <= set(TASK_SPECS)
tasks={item["id"]:item for item in api.rows("tasks")}
agent=api.create_agent(AgentInput(name="isolated queue fixture",adapter="dsh",model="deepseek-flash",timeout_minutes=5))
queued=[]
with patch("backend.app.live_status",return_value={"enabled":True}), \\
     patch("backend.freeze.freeze_catalog_task",return_value={"kind":"test-fixture","frozen":False}):
    for identity in sorted(ids):
        value=RunInput(task_id=identity,task_version="1",agent_id=agent["id"],mode="live")
        result=api.create_run(value)
        assert result["status"]=="queued"
        queued.append(result["task"]["id"])
assert set(queued)==ids
assert {row["status"] for row in api.rows("runs")}=={"queued"}
print("queued",",".join(sorted(queued)))
"""
            queued=subprocess.run([sys.executable,"-c",enqueue_script],cwd=ROOT,env=env,
                                  capture_output=True,text=True)
            self.assertEqual(queued.returncode,0,queued.stderr)
            self.assertIn("manual-box-a-single,manual-box-pair",queued.stdout)


if __name__=="__main__":
    unittest.main()
