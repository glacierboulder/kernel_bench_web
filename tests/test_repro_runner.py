import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from backend.repro_runner import run

class ReproductionTests(unittest.TestCase):
    def test_memory_failure_is_local_and_next_command_runs(self):
        result=run([sys.executable,'-c','x=bytearray(512*1024**2)'],wall=5,cpu=3,memory_mib=128)
        self.assertNotEqual(result['return_code'],0)
        self.assertIn('MemoryError',result['stderr_tail'])
        self.assertEqual(run([sys.executable,'-c','print("still alive")'],wall=5,memory_mib=128)['return_code'],0)

    def test_cleanup_after_leader_exits(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'escaped'
            child='import time;time.sleep(.4);open('+repr(str(marker))+',"w").write("leaked")'
            parent='import subprocess,sys;subprocess.Popen([sys.executable,"-c",'+repr(child)+'])'
            result=run([sys.executable,'-c',parent],wall=3,memory_mib=128)
            self.assertEqual(result['return_code'],0)
            import time;time.sleep(.6)
            self.assertFalse(marker.exists())

    def test_timeout_cleans_group_and_returns_json_data(self):
        result=run([sys.executable,'-c','import time;time.sleep(10)'],wall=1,cpu=3,memory_mib=128)
        self.assertTrue(result['timed_out'])
        self.assertLess(result['elapsed_seconds'],3)

class GuardTests(unittest.TestCase):
    def test_native_fallback_kills_only_reproduction(self):
        import json
        import shutil
        import time
        from backend.repro_guard import ReproGuard
        with tempfile.TemporaryDirectory() as d:
            workspace=Path(d)/'workspace';workspace.mkdir()
            binary=workspace/'repro';shutil.copy2('/bin/sleep',binary)
            target=subprocess.Popen([str(binary),'10'],start_new_session=True)
            unrelated=subprocess.Popen(['/bin/sleep','.4'])
            try:
                guard=ReproGuard(workspace)
                fields=Path(f'/proc/{target.pid}/stat').read_text().rsplit(')',1)[1].split()
                guard.seen[(target.pid,fields[19])]=time.monotonic()-121
                guard.check({target.pid})
                self.assertEqual(target.wait(timeout=2),-9)
                self.assertEqual(unrelated.wait(timeout=2),0)
                evidence=json.loads(guard.audit.read_text())
                self.assertEqual(evidence['reason'],'wall')
            finally:
                if target.poll() is None:target.kill();target.wait()
                if unrelated.poll() is None:unrelated.kill();unrelated.wait()
