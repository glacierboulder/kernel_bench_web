"""Persist real-run progress independently of a browser or API process."""
import json
import secrets
from pathlib import Path
from .app import DATA, db, get_run, now

ARTIFACT_NAMES = {'repro-resource-events.jsonl', 'resource-limit-agent-workspace.json', 'resource-limit-evaluation-workspace.json', 'patch.diff', 'report.md', 'findings.jsonl', 'agent.jsonl', 'evaluation.json', 'worker.log', 'provenance.json', 'gateway-audit.json', 'run-summary.md', 'issue-reports.json', 'new-tests.zip', 'plan1a-protocol.json'}

def save(run):
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT payload FROM runs WHERE id=?',(run['id'],)).fetchone()
        if old and json.loads(old['payload']).get('cancel_requested'):
            run['cancel_requested']=True
        conn.execute('INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                     (run['id'], json.dumps(run, ensure_ascii=False)))


def begin(task, agent, note=''):
    run = dict(id=secrets.token_hex(8), created_at=now(), mode='live', status='preparing',
               task=task, agent=agent, note=note, events=[], checks=[], artifacts=[],
               elapsed_seconds=None, cost=None, report='运行中，尚未提交。')
    directory = DATA / 'runs' / run['id']
    directory.mkdir(parents=True, mode=0o700)
    try:
        if task.get('source_id') and task.get('version') != 'proto-1':
            from .freeze import freeze_catalog_task
            run['task_snapshot'] = freeze_catalog_task(task, directory)
    except Exception:
        import shutil
        shutil.rmtree(directory, ignore_errors=True)
        raise
    save(run)
    return run


def event(run_id, stage, message):
    run = get_run(run_id)
    run['status'] = stage
    run['events'].append(dict(seq=len(run['events']) + 1, at=now(), stage=stage, message=message))
    save(run)
    return run


def artifact_path(run_id, name):
    if name not in ARTIFACT_NAMES:
        raise ValueError('不允许的产物名称')
    root = (DATA / 'runs' / run_id).resolve()
    path = root / name
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise FileNotFoundError(name)
    return path


def request_cancel(run_id):
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
        if not old:
            raise ValueError('实验不存在')
        run=json.loads(old['payload'])
        if run['mode']!='live' or run['status'] not in ('queued','preparing','running','collecting','evaluating'):
            raise ValueError('实验当前无法取消')
        run['cancel_requested']=True
        if run['status']=='queued':
            run['status']='cancelled'
        conn.execute('UPDATE runs SET payload=? WHERE id=?',(json.dumps(run,ensure_ascii=False),run_id))
    return run
