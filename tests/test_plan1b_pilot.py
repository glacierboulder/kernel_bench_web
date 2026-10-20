import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class PilotTests(unittest.TestCase):
    def test_input_control_output_intake_and_worker_ownership(self):
        with tempfile.TemporaryDirectory() as d:
            script='''
import io,json,zipfile
from unittest.mock import patch
from backend.app import DATA,rows,now
from backend.study import put,snapshot_files,digest
from backend.plan1b import create_exploration,input_bundle,submit_output,_save
source=DATA/'runs/source/frozen-task'
(source/'visible').mkdir(parents=True)
(source/'visible/issue.md').write_text('fixture input')
(source/'README.md').write_text('fixture')
root=DATA/'assets/kernel';(root/'kernel').mkdir(parents=True)
(root/'kernel/test').write_text('fixture')
put('assets',dict(id='kernel',kind='kernel',status='verified',evaluation_id='fixture',source_tree_sha256=snapshot_files(root/'kernel'),source_runs=['source']))
_save('runs',dict(id='source',task=dict(id='fixture',version='1',issues=[dict(id='occt-1')]),status='completed'))
mroot=DATA/'assets/knowledge';mroot.mkdir()
(mroot/'knowledge.json').write_text('[]')
put('assets',dict(id='knowledge',kind='knowledge',status='evidence_linked',kernel_id='kernel',knowledge_sha256=digest(mroot/'knowledge.json')))
e=create_exploration(dict(kernel_id='kernel',knowledge_id='knowledge',agent_id='dsh-default',name='fixture',discovery_mode='open_exploration',repeats_per_arm=2,request_limit=500,wall_seconds=2700))
r=e['run_records'];assert len(r)==4
assert {x['arm'] for x in r}=={'with_m0','without_m0'}
for run in r:
 bundle,_=input_bundle(e['id'],run['id'])
 with zipfile.ZipFile(io.BytesIO(bundle)) as z:assert ('M0/knowledge.json' in z.namelist())==(run['arm']=='with_m0')
 assert run['kernel_sha256']==r[0]['kernel_sha256'] and run['b0_sha256']==r[0]['b0_sha256']
b=io.BytesIO()
with zipfile.ZipFile(b,'w') as z:z.writestr('exploration_report.md','No confirmed finding.');z.writestr('findings.jsonl','')
result=submit_output(e['id'],r[0]['id'],b.getvalue());assert result['status']=='submitted',result
from backend.plan1b_worker import reconcile_interrupted_runs
_save('exploration_runs',dict(r[1],status='running',worker_id='pilot-a'))
_save('exploration_runs',dict(r[2],status='running',worker_id='pilot-b'))
reconcile_interrupted_runs('pilot-a')
assert next(x for x in rows('exploration_runs') if x['id']==r[2]['id'])['status']=='running'
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=dict(os.environ,BENCH_DATA_DIR=d,BENCH_TOKEN=''),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
