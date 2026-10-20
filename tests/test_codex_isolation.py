import json
import os
import stat
import tempfile
import unittest
import uuid
from pathlib import Path

from backend.codex_adapter import CodexAdapter


@unittest.skipUnless(os.environ.get("BENCH_SANDBOX_TEST") == "1", "explicit host namespace test")
class CodexIsolationTests(unittest.TestCase):
    def test_fake_cli_runs_in_bubblewrap_without_worker_key_or_outbound_call(self):
        identity = str(uuid.uuid4())
        sentinel = "FAKE_WORKER_SECRET_DO_NOT_FORWARD"
        with tempfile.TemporaryDirectory(prefix="codex-isolation-") as directory:
            root = Path(directory)
            package = root / "node_modules" / "@openai" / "codex"
            (package / "bin").mkdir(parents=True)
            entry = package / "bin" / "codex.js"
            entry.write_text(
                "#!/usr/bin/env node\n"
                "const fs=require('fs');\n"
                "if(process.argv.includes('--version')){console.log('codex-cli fake-1');process.exit(0);}\n"
                "const env=JSON.stringify(process.env);\n"
                f"if(env.includes('{sentinel}')){{console.error('secret reached CLI');process.exit(91);}}\n"
                "if(process.env.BENCH_CXX!=='/usr/bin/c++'){console.error('trusted toolchain env missing');process.exit(92);}\n"
                "fs.writeFileSync('/workspace/repo/fake-result.txt','completed');\n"
                "fs.writeFileSync('/workspace/report.md','fake report\\n');\n"
                f"console.log(JSON.stringify({{type:'thread.started',thread_id:'{identity}'}}));\n"
                "console.log(JSON.stringify({type:'turn.completed',usage:{input_tokens:3,output_tokens:2}}));\n",
                encoding="utf-8",
            )
            entry.chmod(entry.stat().st_mode | stat.S_IXUSR)
            workspace = root / "workspace"
            for name in ("repo", "tools", "home"):
                (workspace / name).mkdir(parents=True, exist_ok=True)
            control = root / "control"
            control.mkdir()
            gateway_dir = root / "gateway"
            gateway_dir.mkdir()

            adapter = CodexAdapter({"codex_cli": str(entry)})
            result = adapter.run_isolated(
                "write a report", workspace=workspace, control=control,
                gateway_dir=gateway_dir, api_key=sentinel, model="fake-model",
                request_limit=3, max_output_tokens=64, timeout_seconds=20,
                task_env={"BENCH_CXX":"/usr/bin/c++","OPENAI_API_KEY":sentinel},
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["session_id"], identity)
            self.assertEqual(result["api_request_count"], 0)
            self.assertEqual(result["gateway_audit"], [])
            self.assertEqual((workspace / "repo/fake-result.txt").read_text(), "completed")
            self.assertEqual((workspace / "report.md").read_text(), "fake report\n")
            self.assertFalse((gateway_dir / "codex.sock").exists())


if __name__ == "__main__":
    unittest.main()
