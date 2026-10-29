"""Single joint task repeats must remain independent and never merge legacy patches."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class GroupBatchTests(unittest.TestCase):
    def test_three_independent_runs_and_branch_scoped_assets(self):
        from backend.worker import TASK_SPECS
        if any(not TASK_SPECS.get(identity,{}).get('task_dir') for identity in ['occt_boolean_group_visible_690_693_172_370_1452']):
            self.skipTest('historical legacy execution fixture is absent; current catalog tasks are tested separately')
        with tempfile.TemporaryDirectory() as directory:
            script='''
import backend.import_proto
from unittest.mock import patch
from backend.study import protocol,put,queue_experiment,rows
from backend.records import save
from backend.plan1a import finalize
p=protocol(3,500,task_ids=['occt_boolean_group_visible_690_693_172_370_1452'],wall_seconds=9000)
assert p['evaluation_suites']==['visible5all']
queue_experiment(p)
r=[r for r in rows('runs') if r.get('experiment_id')==p['id']]
assert len(r)==3 and {x['attempt'] for x in r}=={1,2,3}
assert all(not x.get('parent_run_id') and x['cumulative_request_limit']==500 and x['plan1a_protocol']['wall_seconds']==9000 for x in r)
for i,x in enumerate(r):
 x.update(status='completed',evaluation_passed=i==0,submission_contract={'passed':True})
 save(x)
with patch('backend.assets.candidate',return_value={'id':'candidate','status':'candidate'}) as candidate,patch('backend.assets.verify_asset',return_value={'status':'verified'}) as verify:
 finalize(p['id'])
 candidate.assert_called_once_with([r[0]['id']])
 assert verify.call_args.kwargs['suites']==['visible5all']
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=dict(os.environ,BENCH_DATA_DIR=directory),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
