import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ParallelTests(unittest.TestCase):
    def test_legacy_and_extra_worker_heartbeats(self):
        from backend.live_status import status
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'workers').mkdir()
            (p/'worker-status.json').write_text(json.dumps({'pid':1,'status':'busy','run_id':'original','at':time.time()}))
            (p/'workers/w2.json').write_text(json.dumps({'worker_id':'w2','pid':2,'status':'busy','run_id':'second','at':time.time()}))
            (p/'workers/stale.json').write_text(json.dumps({'status':'busy','at':time.time()-60}))
            s=status(p,False)
            self.assertEqual(s['worker_count'],2)
            self.assertEqual({w['run_id'] for w in s['workers']},{'original','second'})
            self.assertFalse(s['enabled'])

    def test_explicit_first_dsh_run_requires_live_worker(self):
        from backend.live_status import status
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            self.assertFalse(status(p,explicit_launch=True)['enabled'])
            (p/'worker-status.json').write_text(json.dumps({'status':'idle','at':time.time()}))
            first=status(p,explicit_launch=True)
            self.assertTrue(first['enabled'])
            self.assertFalse(first['verified'])
            self.assertTrue(first['explicit_launch'])
            (p/'worker-status.json').write_text(json.dumps({'status':'busy','at':time.time()-60}))
            self.assertFalse(status(p,explicit_launch=True)['enabled'])

    def test_atomic_claim_does_not_touch_running_experiment(self):
        with tempfile.TemporaryDirectory() as t:
            env=dict(os.environ,BENCH_DATA_DIR=t)
            setup='''
from backend.records import begin,event
for i in range(6):
 r=begin({'id':str(i)},{})
 event(r['id'],'running' if i==0 else 'queued','fixture')
'''
            subprocess.run([sys.executable,'-c',setup],cwd=ROOT,env=env,check=True)
            script="from backend.worker import claim; import json; print(json.dumps((claim() or {}).get('id')))"
            procs=[subprocess.Popen([sys.executable,'-c',script],cwd=ROOT,env=env,stdout=subprocess.PIPE,text=True) for _ in range(5)]
            results=[json.loads(p.communicate(timeout=20)[0]) for p in procs]
            self.assertEqual(len(set(results)),5)
            check="from backend.app import rows; assert len([r for r in rows('runs') if r['status']=='running'])==1"
            subprocess.run([sys.executable,'-c',check],cwd=ROOT,env=env,check=True)

if __name__=='__main__':unittest.main()
