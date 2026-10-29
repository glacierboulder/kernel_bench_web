import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class StudyTests(unittest.TestCase):
    def test_existing_operator_budget_configuration_remains_customizable(self):
        from unittest.mock import patch
        from backend.dsh_config import cumulative_request_limit
        with patch.dict(os.environ,{'BENCH_CUMULATIVE_REQUEST_LIMIT':'411'}):
            self.assertEqual(cumulative_request_limit(),411)
            self.assertEqual(cumulative_request_limit(523),523)

    def test_report_membership_and_symlink_boundary(self):
        from backend.issue_reports import collect
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);w=p/'agent-workspace';w.mkdir()
            run={'task':{'issues':[{'id':'occt-690'},{'id':'occt-693'}]}}
            report=lambda i:dict(issue_id=i,root_cause='Uncertain; observed crash',evidence=['command returned -11'],changed_files=[],validation=['bounded repro failed'],limitations=['No fix'])
            (w/'issue-reports.json').write_text(json.dumps([report('occt-690')]))
            self.assertFalse(collect(run,p)['passed'])
            (w/'issue-reports.json').write_text(json.dumps([report('occt-690'),report('occt-693')]))
            self.assertTrue(collect(run,p)['passed'])
            (w/'new-tests').symlink_to('/etc',target_is_directory=True)
            self.assertFalse(collect(run,p)['passed'])

    def test_immutable_batch_custom_budget_and_no_double_launch(self):
        from backend.worker import TASK_SPECS
        if any(not TASK_SPECS.get(identity,{}).get('task_dir') for identity in ['occt_boolean_group_visible_370_872_1452', 'occt_boolean_group_visible_690_693_172']):
            self.skipTest('historical legacy execution fixture is absent; current catalog tasks are tested separately')
        with tempfile.TemporaryDirectory() as t:
            env=dict(os.environ,BENCH_DATA_DIR=t)
            script='''
import json,sqlite3
import backend.import_proto
from backend.study import protocol,put,queue_experiment,rows
p=protocol(2,317);put('experiments',p)
try:put('experiments',p)
except sqlite3.IntegrityError:pass
else:raise AssertionError('protocol overwritten')
queue_experiment(p,persist=False)
r=[x for x in rows('runs') if x.get('experiment_id')==p['id']]
assert len(r)==4 and len({x['id'] for x in r})==4
assert all(x['cumulative_request_limit']==317 and not x.get('parent_run_id') for x in r)
try:queue_experiment(p,persist=False)
except ValueError:pass
else:raise AssertionError('duplicate queue')
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_asset_rejects_changed_patch_and_conflicts(self):
        with tempfile.TemporaryDirectory() as t:
            env=dict(os.environ,BENCH_DATA_DIR=t)
            script='''
from pathlib import Path
from backend.app import DATA
from backend.records import begin,save
from backend.study import put,digest
from backend.assets import candidate
rs=[]
for replacement in ['b','c']:
 r=begin({'base_commit':'same','id':replacement,'issues':[{'id':replacement}]},{})
 root=DATA/'runs'/r['id'];(root/'frozen-task/repo').mkdir(parents=True)
 (root/'frozen-task/repo/file').write_text('a\\n')
 (root/'patch.diff').write_text('--- a/file\\n+++ b/file\\n@@ -1 +1 @@\\n-a\\n+'+replacement+'\\n')
 (root/'report.md').write_text('observations');(root/'agent.jsonl').write_text('{}\\n')
 r.update(evaluation_passed=True,evaluation_returncode=0);save(r);rs.append(r['id'])
 put('evaluations',{'id':r['id'],'run_id':r['id'],'kind':'repair','patch_sha256':digest(root/'patch.diff')})
assert candidate(rs)['status']=='conflict'
p=DATA/'runs'/rs[0]/'patch.diff';p.write_text(p.read_text()+'tampered')
assert candidate([rs[0]])['status']=='conflict'
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
