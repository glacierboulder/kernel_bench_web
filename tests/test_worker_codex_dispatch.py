import copy
import json
import os
import stat
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from backend import worker


@unittest.skipUnless(os.environ.get("BENCH_SANDBOX_TEST") == "1", "explicit host namespace test")
class WorkerCodexDispatchTests(unittest.TestCase):
    def test_worker_runs_fake_codex_and_persists_session_and_cumulative_budget(self):
        identity = str(uuid.uuid4())
        run_id = "fake-codex-worker-run"
        api_key = "FAKE_WORKER_SECRET_DO_NOT_FORWARD"
        source_id = "fake-source"
        suite_id = "fake-suite"

        with tempfile.TemporaryDirectory(prefix="worker-codex-") as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            package = root / "node_modules" / "@openai" / "codex"
            (package / "bin").mkdir(parents=True)
            entry = package / "bin" / "codex.js"
            entry.write_text(
                "#!/usr/bin/env node\n"
                "const fs=require('fs');\n"
                "if(process.argv.includes('--version')){if(process.env.OPENAI_API_KEY)process.exit(92);console.log('codex-cli fake-1');process.exit(0);}\n"
                "if(JSON.stringify(process.env).includes('FAKE_WORKER_SECRET_DO_NOT_FORWARD')){console.error('key leaked');process.exit(91);}\n"
                "if(process.env.BENCH_CXX!=='c++'){console.error('toolchain env missing');process.exit(94);}\n"
                "fs.writeFileSync('/workspace/repo/fake-worker-change.txt','saved');\n"
                "fs.writeFileSync('/workspace/report.md','fake worker report\\n');\n"
                f"console.log(JSON.stringify({{type:'thread.started',thread_id:'{identity}'}}));\n"
                "console.log(JSON.stringify({type:'turn.completed',usage:{input_tokens:7,output_tokens:3}}));\n",
                encoding="utf-8",
            )
            entry.chmod(entry.stat().st_mode | stat.S_IXUSR)

            snapshot = data / "runs" / run_id / "benchmark-snapshot"
            (snapshot / "visible" / "issue_544").mkdir(parents=True)
            (snapshot / "visible" / "issue_544" / "statement.md").write_text("fake public issue")
            (snapshot / "tools").mkdir()
            (snapshot / "tools" / "build.sh").write_text("#!/bin/sh\nexit 0\n")
            (snapshot / "toolchain.json").write_text(json.dumps({
                "schema_version": 1, "id": "fake-toolchain",
                "executables": {"cmake": "cmake", "c_compiler": "cc", "cxx_compiler": "c++"},
                "compiler_output_directory": "clang", "compiler_jobs_max": 2,
            }))
            supervisor = snapshot / "supervisor" / "legacy"
            supervisor.mkdir(parents=True)
            (supervisor / "run_eval.py").write_text("# frozen evaluator fixture\n")
            (snapshot / "suite.json").write_text(json.dumps({"id": suite_id, "version": "1"}))

            task_id = "fake-codex-task"
            task = {
                "id": task_id,
                "version": "1",
                "source_hash": "fake-group-hash",
                "issues": [{"id": "occt-544", "title": "fake", "body": "fake issue"}],
            }
            record = {
                "id": run_id,
                "status": "preparing",
                "task": task,
                "agent": {"id": "fake-codex", "adapter": "codex", "model": "fake-model", "timeout_minutes": 1},
                "events": [],
                "artifacts": [],
                "prior_request_count": 0,
                "cumulative_request_limit": 3,
            }
            saved = {"value": copy.deepcopy(record)}

            def get_run(_identity):
                return copy.deepcopy(saved["value"])

            def save_run(value):
                saved["value"] = copy.deepcopy(value)

            spec = {
                "catalog_version": "1",
                "legacy_version": None,
                "source_id": source_id,
                "suite_id": suite_id,
                "suite_version": "1",
                "evaluator_task": "single",
                "issues": "#544",
                "wall_seconds": 60,
            }
            manifest = {
                "task_id": task_id,
                "task_version": "1",
                "source_id": source_id,
                "suite_id": suite_id,
                "suite_version": "1",
                "source_commit": "fake-commit",
                "source_tree_sha256": "fake-tree-sha",
                "toolchain_id": "fake-toolchain",
            }

            def materialize_source(_snapshot, destination):
                destination = Path(destination)
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "base.txt").write_text("baseline\n")

            config = dict(worker.SETTINGS.config.get("codex", {}))
            config.update({
                "codex_cli": str(entry),
                "codex_version": "codex-cli fake-1",
                "model": "fake-model",
                "codex_live_enabled": True,
                "codex_isolation_verified": True,
                "max_output_tokens": 64,
            })
            patches = [
                patch.dict(worker.SETTINGS.config, {"codex": config}),
                patch.object(worker, "DATA", data),
                patch.object(worker, "TASK_SPECS", {task_id: spec}),
                patch.object(worker, "verify", return_value={"sandbox": "ok"}),
                patch.object(worker, "get_run", side_effect=get_run),
                patch.object(worker, "save", side_effect=save_run),
                patch.object(worker, "event"),
                patch("backend.freeze.verify_snapshot", return_value=manifest),
                patch("backend.freeze.materialize_source", side_effect=materialize_source),
                patch("backend.worker.evaluate_single", return_value=(0, {"passed": True, "tests": []})),
                patch("backend.public_results.public_evaluation", side_effect=lambda result, _run: result),
                patch.dict(os.environ, {"OPENAI_API_KEY": api_key}),
            ]
            with patches[0]:
                with patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11]:
                    worker.run_task(copy.deepcopy(record))

            final = saved["value"]
            self.assertEqual(final["status"], "completed")
            self.assertEqual(final["session_id"], identity)
            self.assertEqual(final["agent_outcome"], "completed")
            self.assertEqual(final["gateway_request_count"], 0)
            self.assertEqual(final["cumulative_request_count"], 0)
            self.assertEqual(final["request_budget_remaining"], 3)
            self.assertEqual(final["cumulative_request_limit"], 3)
            self.assertIn("patch.diff", final["artifacts"])
            self.assertIn("evaluation.json", final["artifacts"])
            self.assertTrue((data / "runs" / run_id / "patch.diff").stat().st_size > 0)
            event_text = (data / "runs" / run_id / "agent.jsonl").read_text()
            self.assertNotIn(api_key, event_text)


if __name__ == "__main__":
    unittest.main()
