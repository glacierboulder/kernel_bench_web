import json
import os
import stat
import tempfile
import unittest
import uuid
from pathlib import Path

from backend.codex_protocol import CodexStream
from backend.codex_adapter import CodexAdapter
from backend.recovery import RecoveryBudget


class CodexProtocolTests(unittest.TestCase):
    def test_structured_events_usage_and_explicit_resume(self):
        identity=str(uuid.uuid4());stream=CodexStream()
        stream.feed(json.dumps({"type":"thread.started","thread_id":identity}))
        stream.feed(json.dumps({"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":4}}))
        value=stream.finish(0)
        self.assertEqual(value["status"],"completed")
        self.assertEqual(value["session_id"],identity)
        self.assertEqual(value["usage"]["input_tokens"],12)
        self.assertIsNone(value["api_request_count"])
        adapter=CodexAdapter({"codex_cli":"/bin/echo","codex_version":"unused"})
        self.assertIn(identity,adapter.argv("continue",session_id=identity))
        with self.assertRaises(ValueError):
            adapter.argv("continue",session_id="--last")

    def test_malformed_truncated_failure_and_missing_usage(self):
        stream=CodexStream();stream.feed("{");stream.feed(b"x"*(CodexStream.MAX_LINE_BYTES+1))
        value=stream.finish(0)
        self.assertEqual(value["status"],"protocol_error")
        self.assertTrue(value["output_truncated"])
        stream=CodexStream();stream.feed(json.dumps({"type":"turn.completed"}))
        value=stream.finish(0)
        self.assertEqual(value["status"],"completed")
        self.assertIsNone(value["usage"])
        stream=CodexStream();stream.feed(json.dumps({"type":"turn.failed"}))
        self.assertEqual(stream.finish(1)["status"],"failed")

    def test_recovery_is_bounded_inspect_first_and_session_bound(self):
        budget=RecoveryBudget()
        self.assertEqual(budget.decide("rate_limit",process_exited=False,session_id="id")["action"],"wait_for_exit")
        self.assertEqual(budget.decide("unknown_connection",process_exited=True,session_id="id")["action"],"inspect")
        first=budget.decide("tool_review_refusal",process_exited=True,session_id="id")
        self.assertEqual(first["action"],"resume_session")
        second=budget.decide("tool_review_refusal",process_exited=True,session_id="id")
        self.assertEqual(second["reason"],"repeated_tool_refusal")
        self.assertEqual(budget.used_total,1)
        self.assertEqual(budget.decide("authentication_failure",process_exited=True,session_id="id")["action"],"stop")

    def test_fake_cli_process_and_rate_limit_resume_use_same_session(self):
        identity=str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);binary=root/'fake-codex'
            binary.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
home=pathlib.Path(os.environ["CODEX_HOME"]); marker=home/"calls"
count=int(marker.read_text()) if marker.exists() else 0
marker.write_text(str(count+1))
(home/"argv").open("a").write(json.dumps(sys.argv[1:])+"\\n")
print(json.dumps({"type":"thread.started","thread_id":"'''+identity+'''"}),flush=True)
if count==0:
 print(json.dumps({"type":"error","codexErrorInfo":{"httpStatusCode":429,"code":"rate_limit_exceeded"}}),flush=True)
 raise SystemExit(1)
print(json.dumps({"type":"turn.completed","usage":{"input_tokens":8,"output_tokens":3}}),flush=True)
''')
            binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
            adapter=CodexAdapter({"codex_cli":str(binary)})
            result=adapter.run("finish the task",workspace=root,home=root/'home',
                               session_home=root/'state',timeout_seconds=10)
            self.assertEqual(result["status"],"completed")
            self.assertEqual(result["first_status"],"failed")
            self.assertEqual(result["session_id"],identity)
            self.assertEqual(result["attempts"][0]["decision"]["action"],"resume_session")
            self.assertEqual(result["final"]["usage"]["input_tokens"],8)
            self.assertEqual((root/'state/calls').read_text(),"2")
            argv=[json.loads(line) for line in (root/'state/argv').read_text().splitlines()]
            self.assertIn(identity,argv[1])
            self.assertEqual(result["recovery_budget"],{"limit":2,"used":1,"remaining":1,"tool_refusals_used":0})

    def test_fake_cli_normal_completion_preserves_session_and_usage(self):
        identity=str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);binary=root/'fake-codex'
            binary.write_text('''#!/usr/bin/env python3
import json
print(json.dumps({"type":"thread.started","thread_id":"'''+identity+'''"}),flush=True)
print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"report saved"}}),flush=True)
print(json.dumps({"type":"turn.completed","usage":{"input_tokens":9,"output_tokens":5}}),flush=True)
''')
            binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
            result=CodexAdapter({"codex_cli":str(binary)}).run(
                "finish",workspace=root,home=root/'home',session_home=root/'state',timeout_seconds=10)
            self.assertEqual(result["status"],"completed")
            self.assertEqual(result["session_id"],identity)
            self.assertEqual(result["final"]["last_message"],"report saved")
            self.assertEqual(result["usage"]["input_tokens"],9)
            self.assertEqual(result["recovery_budget"]["used"],0)

    def test_fake_cli_cancellation_does_not_spend_recovery_budget(self):
        identity=str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);binary=root/'fake-codex'
            binary.write_text('''#!/usr/bin/env python3
import json,time
print(json.dumps({"type":"thread.started","thread_id":"'''+identity+'''"}),flush=True)
time.sleep(20)
''')
            binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
            started=__import__("time").monotonic()
            result=CodexAdapter({"codex_cli":str(binary)}).run(
                "wait",workspace=root,home=root/'home',session_home=root/'state',timeout_seconds=10,
                cancelled=lambda:__import__("time").monotonic()-started>.3)
            self.assertEqual(result["status"],"cancelled")
            self.assertEqual(result["session_id"],identity)
            self.assertEqual(result["attempts"],[])
            self.assertEqual(result["recovery_budget"]["used"],0)

    def test_repeated_refusal_stops_and_keeps_the_same_session(self):
        identity=str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);binary=root/'fake-codex'
            binary.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
home=pathlib.Path(os.environ["CODEX_HOME"]);calls=home/"calls"
count=int(calls.read_text()) if calls.exists() else 0;calls.write_text(str(count+1))
(home/"argv").open("a").write(json.dumps(sys.argv[1:])+"\\n")
print(json.dumps({"type":"thread.started","thread_id":"'''+identity+'''"}),flush=True)
print(json.dumps({"type":"error","recovery_reason":"tool_review_refusal"}),flush=True)
raise SystemExit(1)
''')
            binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
            result=CodexAdapter({"codex_cli":str(binary)}).run(
                "continue",workspace=root,home=root/'home',session_home=root/'state',timeout_seconds=10)
            self.assertEqual(result["status"],"failed")
            self.assertEqual(result["session_id"],identity)
            self.assertEqual(len(result["attempts"]),2)
            self.assertEqual(result["attempts"][1]["decision"]["reason"],"repeated_tool_refusal")
            self.assertEqual((root/'state/calls').read_text(),"2")
            self.assertIn(identity,json.loads((root/'state/argv').read_text().splitlines()[1]))
            self.assertEqual(result["recovery_budget"]["used"],1)
            self.assertEqual(result["recovery_budget"]["tool_refusals_used"],1)

    def test_cumulative_request_budget_is_not_reset_on_resume(self):
        identity=str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);binary=root/'fake-codex'
            binary.write_text('''#!/usr/bin/env python3
import json,os,pathlib
home=pathlib.Path(os.environ["CODEX_HOME"]);count_file=home/"requests"
count=int(count_file.read_text()) if count_file.exists() else 0;count_file.write_text(str(count+1))
print(json.dumps({"type":"thread.started","thread_id":"'''+identity+'''"}),flush=True)
print(json.dumps({"type":"error","recovery_reason":"rate_limit"}),flush=True)
raise SystemExit(1)
''')
            binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
            state=root/'state'
            counter=lambda:int((state/'requests').read_text()) if (state/'requests').exists() else 0
            result=CodexAdapter({"codex_cli":str(binary)}).run(
                "continue",workspace=root,home=root/'home',session_home=state,timeout_seconds=10,
                request_limit=2,request_counter=counter)
            self.assertEqual(result["status"],"failed")
            self.assertEqual(result["session_id"],identity)
            self.assertEqual((state/'requests').read_text(),"2")
            self.assertEqual(result["api_request_count"],2)
            self.assertEqual(result["cumulative_request_limit"],2)
            self.assertEqual(result["attempts"][-1]["decision"]["reason"],"cumulative_request_budget_exhausted")
            self.assertEqual(result["recovery_budget"]["used"],1)


if __name__=="__main__":
    unittest.main()
