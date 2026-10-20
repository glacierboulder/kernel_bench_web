import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from backend.model_gateway import Gateway
from backend.preflight import verify
from backend.dsh_config import patch_config
from backend.sandbox import command, limits, PYTHON

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.environ.get('BENCH_SANDBOX_TEST')=='1','explicit host namespace test')
class SandboxTests(unittest.TestCase):
    def test_boundary_and_gateway_bridge(self):
        from backend.tool_paths import executable
        try:
            node = executable('Node', env_name='BENCH_NODE', config_name='node', default='node')
        except RuntimeError as error:
            self.skipTest(str(error))
        self.assertTrue(all(verify().values()))
        with tempfile.TemporaryDirectory(prefix='cadai-smoke-') as directory:
            root=Path(directory)
            for name in ['workspace','control','gateway','state']:
                (root/name).mkdir()
            shutil.copy2(ROOT/'backend/sandbox_entry.py',root/'control/entry.py')
            patch_config(root/'control/overlay.yml')
            gateway=Gateway(root/'gateway/api.sock','host-only-test-key','deepseek-v4-pro')
            gateway.start()
            code=f'''
import os, subprocess, urllib.request, urllib.error
assert os.environ.get('DEEPSEEK_API_KEY') == 'placeholder'
try:
    urllib.request.urlopen('http://127.0.0.1:18991/forbidden',timeout=5)
    raise AssertionError('gateway allowed arbitrary path')
except urllib.error.HTTPError as error:
    assert error.code == 403
result=subprocess.run([{node!r},'/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js','--profile','headless','--patch','/control/overlay.yml','--help'],capture_output=True,text=True,timeout=60)
print(result.stdout)
print(result.stderr)
assert result.returncode == 0
'''
            args=command(root/'workspace',mounts=[(ROOT/'runtime/dsh','/runtime',False),(root/'control','/control',False),(root/'gateway','/gateway',False),(root/'state','/state',True)],env={'DEEPSEEK_API_KEY':'placeholder','DSH_HOME':'/state'})
            try:
                result=subprocess.run(args+[PYTHON,'/control/entry.py',PYTHON,'-c',code],capture_output=True,text=True,timeout=90,preexec_fn=limits)
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                self.assertEqual(gateway.requests,0)
            finally:
                gateway.close()
