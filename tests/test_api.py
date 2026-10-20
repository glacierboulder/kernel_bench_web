import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        env = dict(os.environ, BENCH_DATA_DIR=cls.temp.name, BENCH_TOKEN='test-token')
        subprocess.run([sys.executable, '-m', 'backend.import_proto'], cwd=ROOT, env=env, check=True, capture_output=True)
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        cls.proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                cls.request('/api/state')
                break
            except OSError:
                time.sleep(.05)
        else:
            cls.proc.terminate()
            raise RuntimeError('API 启动失败')

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.temp.cleanup()

    @classmethod
    def request(cls, path, payload=None, token=True, origin=None, method=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer test-token'
        if origin:
            headers['Origin'] = origin
        req = Request(cls.base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    def test_auth_and_origin(self):
        self.assertIn('tasks',self.request('/api/state', token=False))
        with self.assertRaises(HTTPError) as error:
            self.request('/api/state', origin='https://evil.example')
        self.assertEqual(error.exception.code, 403)

    def test_demo_snapshot_and_execution_gate(self):
        state = self.request('/api/state')
        self.assertEqual(sum(t['version']=='1' for t in state['tasks']), 7)
        visible3 = next(t for t in state['tasks'] if t['id'] == 'occt_boolean_group_visible_544_506_847' and t['version']=='1')
        self.assertEqual([i['id'] for i in visible3['issues']], ['occt-544', 'occt-506', 'occt-847'])
        self.assertFalse(visible3['has_hidden_checks'])
        for task_id, issue_ids in {
            'occt_boolean_group_visible_690_693_172': ['occt-690', 'occt-693', 'occt-172'],
            'occt_boolean_group_visible_370_872_1452': ['occt-370', 'occt-872', 'occt-1452'],
            'occt_boolean_group_visible_690_693_172_370_1452': ['occt-690', 'occt-693', 'occt-172', 'occt-370', 'occt-1452'],
        }.items():
            task = next(t for t in state['tasks'] if t['id'] == task_id and t['version']=='1')
            self.assertEqual([i['id'] for i in task['issues']], issue_ids)
            self.assertFalse(task['has_hidden_checks'])
        five = next(t for t in state['tasks'] if t['id'] == 'occt_boolean_group_visible_690_693_172_370_1452' and t['version']=='1')
        self.assertIn('Crash when applying', five['issues'][-1]['body'])
        self.assertNotIn('readme',five)
        a = self.request('/api/agents', {'name':'测试 DSH', 'adapter':'dsh', 'model':'test', 'timeout_minutes':30})
        task = state['tasks'][0]
        payload = dict(task_id=task['id'], task_version=task['version'], agent_id=a['id'], mode='demo')
        run = self.request('/api/runs', payload)
        self.assertEqual(run['task'], task)
        self.assertEqual(run['agent'], a)
        self.assertTrue(all(c['status'] == 'not_run' for c in run['checks']))
        self.assertEqual(self.request('/api/runs/' + run['id'] + '/export'), run)
        payload['mode'] = 'live'
        with self.assertRaises(HTTPError) as error:
            self.request('/api/runs', payload)
        self.assertEqual(error.exception.code, 409)
        with self.assertRaises(HTTPError):
            self.request('/api/agents', {'name':'bad', 'adapter':'arbitrary-command'})

    def test_live_queue_cancel_and_artifact_boundary(self):
        marker = Path(self.temp.name) / 'live-verified.json'
        heartbeat = Path(self.temp.name) / 'worker-status.json'
        marker.write_text('{}')
        heartbeat.write_text(json.dumps({'at': time.time(), 'status': 'idle'}))
        try:
            state = self.request('/api/state')
            self.assertTrue(state['execution_enabled'])
            task = next(t for t in state['tasks'] if t['id']=='occt_boolean_single_544')
            run = self.request('/api/runs', dict(task_id=task['id'],task_version=task['version'],agent_id='dsh-default',mode='live'))
            self.assertEqual(run['status'],'queued')
            self.assertEqual(run['mode'],'live')
            cancelled = self.request('/api/runs/'+run['id']+'/cancel', {})
            self.assertEqual(cancelled['status'],'cancelled')
            self.assertTrue(cancelled['cancel_requested'])
            self.assertEqual(self.request('/api/runs/'+run['id']+'/events')['status'],'cancelled')
            with self.assertRaises(HTTPError) as error:
                self.request('/api/runs/'+run['id']+'/artifacts/report.md')
            self.assertEqual(error.exception.code,404)
            group = next(t for t in self.request('/api/state')['tasks'] if t['id']=='occt_boolean_group_visible_544_506_847')
            group_run = self.request('/api/runs', dict(task_id=group['id'],task_version=group['version'],agent_id='dsh-default',mode='live'))
            self.assertEqual(group_run['status'],'queued')
            self.assertEqual(group_run['task']['has_hidden_checks'],False)
            self.assertEqual(self.request('/api/runs/'+group_run['id']+'/cancel', {})['status'],'cancelled')
            for task_id in ('occt_boolean_group_visible_690_693_172', 'occt_boolean_group_visible_370_872_1452', 'occt_boolean_group_visible_690_693_172_370_1452'):
                task = next(t for t in self.request('/api/state')['tasks'] if t['id'] == task_id)
                task_run = self.request('/api/runs', dict(task_id=task_id, task_version=task['version'],
                                                          agent_id='dsh-default', mode='live'))
                self.assertEqual(task_run['status'], 'queued')
                self.assertEqual(self.request('/api/runs/'+task_run['id']+'/cancel', {})['status'], 'cancelled')
        finally:
            marker.unlink()
            heartbeat.unlink()

    def test_editable_note_survives_worker_save(self):
        task=self.request('/api/state')['tasks'][0]
        run=self.request('/api/runs',dict(task_id=task['id'],task_version=task['version'],agent_id='dsh-default',mode='demo'))
        path='/api/runs/'+run['id']
        note=self.request(path+'/note',{'text':'8192 output token limit; <test>'},method='PATCH')
        self.assertEqual(self.request(path)['annotation'],note)
        env=dict(os.environ,BENCH_DATA_DIR=self.temp.name)
        code="from backend.records import save; from backend.app import get_run; save(get_run("+repr(run['id'])+"))"
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,check=True)
        self.assertEqual(self.request(path+'/export')['annotation'],note)
        self.assertEqual(self.request(path)['checks'],run['checks'])
        with self.assertRaises(HTTPError) as error:
            self.request(path+'/note',{'text':'x'*2001},method='PATCH')
        self.assertEqual(error.exception.code,422)

    def test_group_registration_and_immutable_version(self):
        item = dict(id='multi-issue-test', version='1', title='Two public issues', kind='group', base_commit='abc',
                    issues=[dict(id='a', visibility='public'), dict(id='b', visibility='public')],
                    budget=dict(scope='group', wall_clock_minutes=120), has_hidden_checks=False)
        file = Path(self.temp.name) / 'manifest.json'
        file.write_text(json.dumps(item))
        env = dict(os.environ, BENCH_DATA_DIR=self.temp.name)
        result = subprocess.run([sys.executable,'-m','backend.register',str(file)], cwd=ROOT, env=env, capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        task = next(t for t in self.request('/api/state')['tasks'] if t['id']==item['id'])
        self.assertEqual(len(task['issues']),2)
        item['title']='changed'
        file.write_text(json.dumps(item))
        result = subprocess.run([sys.executable,'-m','backend.register',str(file)], cwd=ROOT, env=env, capture_output=True)
        self.assertNotEqual(result.returncode,0)

if __name__ == '__main__':
    unittest.main()
