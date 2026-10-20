import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .adapters import REGISTRY
from .live_status import status as live_status
from .settings import SETTINGS

ROOT = Path(__file__).resolve().parents[1]
DATA = SETTINGS.data_dir
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
DB = DATA / 'bench.sqlite3'
app = FastAPI(title='CADAI Agent Bench', docs_url=None, redoc_url=None, openapi_url=None)

def public_experiment(item):
    from .study import summary
    from .public_results import public_evaluation_record
    value=summary(item)
    if value.get('qualification'):
        runs_by_id={run['id']:run for run in rows('runs')}
        value['qualification']=public_evaluation_record(value['qualification'],runs_by_id)
    return value

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def db():
    conn = sqlite3.connect(DB, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

with db() as c:
    c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS tasks (id TEXT, version TEXT, payload TEXT NOT NULL, PRIMARY KEY(id, version));
    CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS run_notes (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS explorations (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS exploration_runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    ''')
    if not c.execute('SELECT 1 FROM agents LIMIT 1').fetchone():
        item = dict(id='dsh-default', name='DSH · 默认配置', adapter='dsh', model='', timeout_minutes=120)
        c.execute('INSERT INTO agents VALUES (?,?)', (item['id'], json.dumps(item)))

@app.middleware('http')
async def security(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': '拒绝跨域请求'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
    if request.url.path.startswith(('/api/', '/static/')) or request.url.path == '/':
        response.headers['Cache-Control'] = 'no-store'
    return response

def rows(table):
    with db() as c:
        return [json.loads(r['payload']) for r in c.execute(f'SELECT payload FROM {table} ORDER BY rowid DESC')]

def get_run(run_id):
    with db() as c:
        r = c.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
    if not r:
        raise HTTPException(404, '实验不存在')
    return json.loads(r['payload'])

def with_note(run, notes=None):
    if notes is None:
        with db() as c:
            row=c.execute('SELECT payload FROM run_notes WHERE id=?',(run['id'],)).fetchone()
        note=json.loads(row['payload']) if row else {'text':''}
    else:note=notes.get(run['id'],{'text':''})
    return {**run,'annotation':note}

@app.get('/api/state')
def state():
    dsh_launch_enabled=SETTINGS.config.get('dsh_live_enabled') is True
    live = live_status(DATA,explicit_launch=dsh_launch_enabled)
    adapters = {key: dict(value) for key, value in REGISTRY.items()}
    adapters['dsh'].update(available=live['enabled'], reason=('真实执行可用（已验证题目）' if live['verified'] else
        '已显式开放首次验证任务' if live['explicit_launch'] and live['worker_online'] else
        '固定版本已安装；首次真实任务需显式启用且 worker 在线'))
    from .codex_adapter import CodexAdapter
    codex=CodexAdapter(SETTINGS.config.get('codex',{})).probe()
    adapters['codex'].update(available=codex['available'],live_enabled=codex['live_enabled'],reason=codex['reason'])
    with db() as c:notes={r['id']:json.loads(r['payload']) for r in c.execute('SELECT * FROM run_notes')}
    from .public_results import public_run,public_evaluation_record,public_asset
    run_values=rows('runs');runs_by_id={item['id']:item for item in run_values}
    from .public_issues import enrich_task
    tasks = [enrich_task(task) for task in rows('tasks')]
    from .plan1b import state_snapshot as plan1b_state
    return dict(experiments=[public_experiment(e) for e in rows('experiments')],
                evaluations=[public_evaluation_record(item,runs_by_id) for item in rows('evaluations')],
                assets=[public_asset(item) for item in rows('assets')], tasks=tasks, agents=rows('agents'),
                runs=[with_note(public_run(r),notes) for r in run_values], adapters=adapters,
                execution_enabled=live['enabled'],
                live_capabilities={'dsh':live['enabled'],'codex':codex['live_enabled']},
                live=live, plan1b=plan1b_state(),
                worker=f"在线 · {live['worker_count']} worker" if live['worker_online'] else '离线', access_control='SSH server account')


class AgentInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    adapter: str
    model: str = Field(default='', max_length=120)
    timeout_minutes: int = Field(default=120, ge=1, le=480)

@app.post('/api/agents', status_code=201)
def create_agent(value: AgentInput):
    if value.adapter not in REGISTRY:
        raise HTTPException(422, '未注册的 agent 类型')
    item = dict(id=secrets.token_hex(8), **value.model_dump())
    with db() as c:
        c.execute('INSERT INTO agents VALUES (?,?)', (item['id'], json.dumps(item)))
    return item

class RunInput(BaseModel):
    task_id: str
    task_version: str
    agent_id: str
    mode: str = 'demo'
    note: str = Field(default='', max_length=1000)

@app.post('/api/runs', status_code=201)
def create_run(value: RunInput):
    if value.mode not in ('demo', 'live'):
        raise HTTPException(422, '无效运行模式')
    task = next((t for t in rows('tasks') if t['id'] == value.task_id and t['version'] == value.task_version), None)
    if task:
        # Keep the run snapshot identical to the public task shown by /api/state.
        from .public_issues import enrich_task
        task = enrich_task(task)
    agent = next((a for a in rows('agents') if a['id'] == value.agent_id), None)
    if not task or not agent:
        raise HTTPException(422, '题目版本或 agent 配置不存在')
    if value.mode == 'live':
        from .records import begin, event
        from .worker import TASK_SPECS
        if agent['adapter']=='dsh' and not live_status(
                DATA,explicit_launch=SETTINGS.config.get('dsh_live_enabled') is True)['enabled']:
            raise HTTPException(409, 'DSH 真实执行需首次验证通过，或显式启用首次验证任务并确保 worker 在线')
        if agent['adapter']=='codex':
            from .codex_adapter import CodexAdapter
            probe=CodexAdapter(SETTINGS.config.get('codex',{})).probe()
            if not probe.get('live_enabled'):
                raise HTTPException(409, 'Codex live 已关闭：'+probe.get('reason','认证隔离未验证'))
        spec=TASK_SPECS.get(task['id'])
        supported_versions={spec.get('catalog_version')} if spec else set()
        if spec and spec.get('legacy_version'):
            supported_versions.add(spec['legacy_version'])
        supported=bool(spec and task['version'] in supported_versions)
        if not supported or agent['adapter'] not in {'dsh','codex'}:
            raise HTTPException(409, '真实执行仅支持目录中登记的 OCCT 题目与已接入的适配器')
        if agent['adapter']=='dsh' and agent.get('model') not in ('', 'deepseek-flash'):
            raise HTTPException(422, '真实执行仅支持 deepseek-flash')
        try:
            item = begin(task, agent, value.note)
        except (ValueError,OSError,KeyError) as error:
            raise HTTPException(409, '无法冻结该题目；请检查已验证的源码缓存和题库版本') from error
        return event(item['id'], 'queued', '真实任务已入队；将调用外部模型 API 并产生费用')
    stamp = now()
    events = [dict(seq=i + 1, stage=stage, message=message) for i, (stage, message) in enumerate([
        ('preparing', '演示：冻结题目版本与 agent 配置'),
        ('running', '演示：展示共享工作区与统一提交的执行过程'),
        ('collecting', '演示：收集 patch / report / findings'),
        ('evaluating', '演示：保留逐 issue 检查项与全组结果'),
        ('completed', '演示回放结束；未调用模型、未编译、未执行评测')])]
    checks = [dict(issue_id=i['id'], name='公开复现检查', status='not_run') for i in task['issues']]
    if task['has_hidden_checks']:
        checks.append(dict(issue_id=None, name='隐藏检查（详情不公开）', status='not_run'))
    if task['kind'] == 'active':
        checks.append(dict(issue_id=None, name='findings 格式验证（不评价发现质量）', status='not_run'))
    item = dict(id=secrets.token_hex(8), created_at=stamp, mode='demo', status='demo_completed',
                task=task, agent=agent, note=value.note, events=events, checks=checks,
                artifacts=[], elapsed_seconds=None, cost=None, report='这是框架演示记录，没有真实提交或评测结果。')
    with db() as c:
        c.execute('INSERT INTO runs VALUES (?,?)', (item['id'], json.dumps(item)))
    from .public_results import public_run
    return with_note(public_run(item))

@app.get('/api/runs/{run_id}')
def detail(run_id: str):
    from .public_results import public_run
    return with_note(public_run(get_run(run_id)))

@app.get('/api/runs/{run_id}/export')
def export(run_id: str):
    from .public_results import public_run
    return JSONResponse(with_note(public_run(get_run(run_id))), headers={'Content-Disposition': f'attachment; filename="run-{run_id}.json"'})

@app.post('/api/runs/{run_id}/cancel')
def cancel_run(run_id: str):
    from .records import request_cancel
    try:
        from .public_results import public_run
        return public_run(request_cancel(run_id))
    except ValueError as error:
        raise HTTPException(409, str(error))


@app.get('/api/runs/{run_id}/events')
def run_events(run_id: str, after: int = 0):
    from .public_results import public_run
    run = public_run(get_run(run_id))
    return {'status': run['status'], 'events': [e for e in run['events'] if e['seq'] > after]}

@app.get('/api/runs/{run_id}/artifacts/{name}')
def download_artifact(run_id: str, name: str):
    from .records import artifact_path
    run = get_run(run_id)
    if name not in run.get('artifacts', []):
        raise HTTPException(404, '产物不存在')
    try:
        path = artifact_path(run_id, name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, '产物不存在')
    return FileResponse(path, media_type='application/zip' if name.endswith('.zip') else 'text/plain', filename=name)

app.mount('/static', StaticFiles(directory=ROOT / 'frontend'), name='static')

@app.get('/')
def index():
    return FileResponse(ROOT / 'frontend' / 'index.html')

class ExperimentInput(BaseModel):
    repeats: int = Field(default=2,ge=1,le=5)
    request_limit: int = Field(default=200,ge=1,le=10000)
    name: str = Field(default='Plan 1A · 两组独立联合修复',max_length=100)

@app.post('/api/experiments',status_code=201)
def create_experiment(value: ExperimentInput):
    from .study import protocol,put,summary
    item=protocol(value.repeats,value.request_limit);item['title']=value.name
    put('experiments',item)
    return public_experiment(item)

@app.get('/api/experiments/{identity}')
def experiment_detail(identity: str):
    item=next((e for e in rows('experiments') if e['id']==identity),None)
    if not item:raise HTTPException(404,'批次不存在')
    return public_experiment(item)

@app.get('/api/evaluations/{identity}')
def evaluation_detail(identity: str):
    item=next((e for e in rows('evaluations') if e['id']==identity),None)
    if not item:raise HTTPException(404,'评测不存在')
    from .public_results import public_evaluation_record
    runs_by_id={run['id']:run for run in rows('runs')}
    return public_evaluation_record(item,runs_by_id)

@app.get('/api/assets/{identity}/{name}')
def asset_file(identity: str,name: str):
    item=next((a for a in rows('assets') if a['id']==identity),None)
    if not item or name not in {'manifest.json','patch.diff','knowledge.json','evaluation.json','benchmark.zip'}:raise HTTPException(404,'资产不存在')
    root=(DATA/'assets'/identity).resolve();path=root/name
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):raise HTTPException(404,'资产不存在')
    if name in {'evaluation.json','manifest.json'}:
        from .public_results import public_evaluation,public_asset
        try:
            value=json.loads(path.read_text(encoding='utf-8'))
            return JSONResponse(public_evaluation(value) if name=='evaluation.json' else public_asset(value))
        except (OSError,ValueError,json.JSONDecodeError):raise HTTPException(404,'资产不存在')
    media = 'application/zip' if name.endswith('.zip') else 'text/plain'
    return FileResponse(path,media_type=media,filename=name)

@app.post('/api/experiments/{identity}/start')
def start_experiment(identity: str):
    if not live_status(DATA,explicit_launch=SETTINGS.config.get('dsh_live_enabled') is True)['enabled']:
        raise HTTPException(409,'启动需首次验证通过，或显式启用首次验证任务并确保 worker 在线')
    from .plan1a import launch
    try:return launch(identity)
    except (ValueError,StopIteration) as e:raise HTTPException(409,str(e))

class RunNoteInput(BaseModel):
    text: str = Field(default='',max_length=2000)

@app.patch('/api/runs/{run_id}/note')
def update_run_note(run_id: str,value: RunNoteInput):
    get_run(run_id)
    note={'text':value.text,'updated_at':now()}
    with db() as c:
        c.execute('INSERT INTO run_notes VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(run_id,json.dumps(note,ensure_ascii=False)))
    return note

class Plan1BInput(BaseModel):
    name: str = Field(default='Plan 1B · M0 主动探索对照', min_length=1, max_length=100)
    kernel_id: str
    knowledge_id: str | None = None
    agent_id: str
    repeats_per_arm: int = Field(default=2, ge=2, le=2)
    request_limit: int = Field(default=500, ge=1, le=10000)
    wall_seconds: int = Field(default=2700, ge=300, le=28800)
    discovery_mode: str = 'open_exploration'

@app.post('/api/explorations', status_code=201)
def create_plan1b(value: Plan1BInput):
    from .plan1b import create_exploration
    try:
        return create_exploration(value.model_dump())
    except ValueError as error:
        raise HTTPException(409, str(error))

@app.get('/api/explorations/{identity}')
def plan1b_detail(identity: str):
    from .plan1b import exploration_detail
    try:
        return exploration_detail(identity)
    except ValueError as error:
        raise HTTPException(404, str(error))

@app.post('/api/explorations/{identity}/start')
def start_plan1b(identity: str):
    from .plan1b import queue_exploration
    try:
        return queue_exploration(identity)
    except ValueError as error:
        raise HTTPException(409, str(error))

@app.post('/api/explorations/{identity}/runs/{run_id}/cancel')
def cancel_plan1b(identity: str, run_id: str):
    from .plan1b import cancel_exploration_run
    try:
        return cancel_exploration_run(identity, run_id)
    except ValueError as error:
        raise HTTPException(409, str(error))

@app.get('/api/explorations/{identity}/runs/{run_id}/input')
def plan1b_input_bundle(identity: str, run_id: str):
    from .plan1b import input_bundle
    from fastapi.responses import StreamingResponse
    import io
    try:
        archive, filename = input_bundle(identity, run_id)
    except ValueError as error:
        raise HTTPException(404, str(error))
    return StreamingResponse(io.BytesIO(archive), media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@app.post('/api/explorations/{identity}/runs/{run_id}/submission', status_code=201)
async def submit_plan1b_output(identity: str, run_id: str, request: Request):
    from .plan1b import submit_output
    if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/zip':
        raise HTTPException(415, '请上传 application/zip 格式的 Plan 1B 输出包')
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>250*1024*1024:raise HTTPException(413,'输出包超过 250 MiB 限制')
        chunks.append(chunk)
    payload=b''.join(chunks)
    try:
        return submit_output(identity, run_id, payload)
    except ValueError as error:
        raise HTTPException(422, str(error))

@app.get('/api/explorations/{identity}/runs/{run_id}/artifacts/{name:path}')
def plan1b_output_artifact(identity: str, run_id: str, name: str):
    from .plan1b import output_artifact
    try:
        path = output_artifact(identity, run_id, name)
    except ValueError as error:
        raise HTTPException(404, str(error))
    return FileResponse(path, media_type='application/zip' if path.suffix == '.zip' else 'application/octet-stream', filename=path.name)

class FindingReviewInput(BaseModel):
    input_contract_passed: bool
    replays: list[bool]
    oracle_violation_confirmed: bool
    novelty: str = Field(pattern='^(new_issue|known_issue_neighborhood|unknown)$')
    known_issue_reference: str | None = Field(default=None, max_length=200)
    duplicate_of: str | None = Field(default=None, max_length=100)
    root_cause_key: str = Field(min_length=1, max_length=200)
    evidence: list[str] = Field(min_length=1, max_length=30)
    patch: dict | None = None

@app.put('/api/findings/{identity}/review')
def review_plan1b_finding(identity: str, value: FindingReviewInput):
    from .plan1b import review_finding
    try:
        return review_finding(identity, value.model_dump())
    except ValueError as error:
        raise HTTPException(409, str(error))

class Plan1BPromoteInput(BaseModel):
    finding_ids: list[str] = Field(min_length=1, max_length=500)

@app.post('/api/explorations/{identity}/promote')
def promote_plan1b_assets(identity: str, value: Plan1BPromoteInput):
    from .plan1b import promote_assets
    try:
        return promote_assets(identity, value.finding_ids)
    except ValueError as error:
        raise HTTPException(409, str(error))
