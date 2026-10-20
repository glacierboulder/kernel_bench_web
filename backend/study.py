"""Immutable study protocols and independently versioned evidence/assets."""
import hashlib
import fcntl
import json
import secrets
from pathlib import Path
from .app import DATA, db, get_run, now, rows
from .proto_config import PROTO

TABLES={'experiments','evaluations','assets'}

def put(table,item,immutable=True):
    if table not in TABLES:raise ValueError('invalid table')
    with db() as c:
        c.execute('INSERT INTO '+table+' VALUES (?,?)'+('' if immutable else ' ON CONFLICT(id) DO UPDATE SET payload=excluded.payload'),(item['id'],json.dumps(item,ensure_ascii=False)))
    return item

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def snapshot_files(folder):
    from .submission import source_files
    h=hashlib.sha256()
    for name,p in sorted(source_files(folder).items()):h.update(name.encode()+b'\0'+bytes.fromhex(digest(p)))
    return h.hexdigest()

def protocol(repeats=2,request_limit=200, *, task_ids=None, wall_seconds=1800):
    from .dsh_config import cumulative_request_limit,MODEL,output_token_limit
    from .worker import TASK_SPECS
    groups=task_ids or ['occt_boolean_group_visible_370_872_1452','occt_boolean_group_visible_690_693_172']
    if len(set(groups))!=len(groups) or any(g not in TASK_SPECS for g in groups):raise ValueError('Invalid task selection')
    if not 60<=wall_seconds<=14400:raise ValueError('Invalid wall budget')
    tasks=[]
    available=rows('tasks')
    for identity in groups:
        spec=TASK_SPECS[identity]
        if not spec.get('task_dir'):
            raise ValueError(f'Legacy execution bundle is unavailable for {identity}')
        task=next((t for t in available if t['id']==identity
                   and t['version']==spec['legacy_version']
                   and t.get('source_hash')==spec['legacy_manifest_sha256']),None)
        if task is None:
            raise ValueError(f'Frozen legacy task version is unavailable for {identity}')
        tasks.append(task)
    item={'id':secrets.token_hex(8),'created_at':now(),'title':'Plan 1A · 两组独立联合修复','phase':'1A', 'task_snapshots':tasks,
          'agent':{'id':'dsh-plan1a','name':'DSH · V4.1 Flash / Plan 1A','adapter':'dsh','model':MODEL,'timeout_minutes':wall_seconds/60},
          'repeats':repeats,'request_limit':cumulative_request_limit(request_limit),'wall_seconds':wall_seconds,'max_output_tokens':output_token_limit(),
          'baseline':'3e80fad1779e4fab620d1ab1982bfd7722b6c92b','knowledge':None,
          'prompt_version':'plan1a-v1','submission_version':'issue-reports-v1',
          'evaluator_sha256':digest(Path(__file__).with_name('eval_driver.py')),
          'upstream_evaluator_sha256':digest(PROTO/'private/evaluators/run_eval.py'),
          'regression_sha256':digest(Path(__file__).resolve().parents[1]/'config/regressions/analytic_boxes/reproduce.cpp'),
          'input_policy':'remove upstream fix PR/commit references in frozen public task; no history, no M0',
          'qualification_policy':{'version':'plan1a-asset-admission-v1','asset_admission_success_per_group':2,
                                  'kernel_min_success_per_group':1,'plan1b_requires_verified_kernel_and_knowledge':True},
          'gate':{'asset_admission_success_per_group':2,'kernel_min_success_per_group':1,'combined_regression_required':True,
                  'limitations':'Two complete independent successes per group meet Plan 1A asset admission; one successful run can still produce a K1/M0 for Plan 1B after independent verification.'}}
    if task_ids is not None:
        item.update(asset_policy='independent_group', evaluation_suites=[TASK_SPECS[g]['evaluator_task'] for g in groups])
        item['gate']={'asset_admission_success_per_group':2,'kernel_min_success_per_group':1,'combined_regression_required':False,
                      'limitations':'Two successes per group meet Plan 1A asset admission; each individually successful patch can form its own K1/M0 and proceed to Plan 1B after verification.'}
    for t in tasks:
        t['task_tree_sha256']=snapshot_files(TASK_SPECS[t['id']]['task_dir'])
    return item

def _queue_experiment(item, persist=True):
    if persist:put('experiments',item)
    if any(r.get('experiment_id')==item['id'] for r in rows('runs')):raise ValueError('Experiment already started')
    # Publish fully initialized queued records in one transaction. A worker
    # restart must never see a transient preparing record without ownership.
    pending=[]
    for attempt in range(1,item['repeats']+1):
        for task in item['task_snapshots']:
            identity=secrets.token_hex(8)
            (DATA/'runs'/identity).mkdir(parents=True,mode=0o700)
            timestamp=now()
            run=dict(id=identity,created_at=timestamp,mode='live',status='queued',
                     task=task,agent=item['agent'],note=f"Plan 1A / repeat {attempt}; clean K0; no M0",
                     events=[dict(seq=1,at=timestamp,stage='queued',message='固定协议独立重复运行；等待基线资格检查')],
                     checks=[],artifacts=[],elapsed_seconds=None,cost=None,report='运行中，尚未提交。',
                     experiment_id=item['id'],attempt=attempt,cumulative_request_limit=item['request_limit'],
                     plan1a_protocol={k:item[k] for k in ('prompt_version','submission_version','evaluator_sha256','upstream_evaluator_sha256','regression_sha256','wall_seconds','input_policy','max_output_tokens')})
            pending.append(run)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT 1 FROM runs WHERE json_extract(payload,'$.experiment_id')=? LIMIT 1",(item['id'],)).fetchone():raise ValueError('Experiment already started')
        for run in pending:c.execute('INSERT INTO runs VALUES (?,?)',(run['id'],json.dumps(run,ensure_ascii=False)))
    return item

def queue_experiment(item,persist=True):
    # Serialize API/operator starts across processes without locking the worker.
    with (DATA/'experiment-start.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _queue_experiment(item,persist)


def evaluation_record(run_id,result,code,kind='repair',directory=None):
    run=get_run(run_id) if run_id else None
    root=Path(directory) if directory else DATA/'runs'/run_id
    stages=[]
    if not result.get('baseline'):
        provided=bool(result.get('report',{}).get('provided'))
        stages.append({'name':'submission','status':'passed' if provided else 'failed'})
        patch_path=root/'patch.diff'
        patch_applied=result.get('patch_bytes') is not None
        patch_failed=patch_path.is_file() and result.get('failure_stage')=='submission'
        stages.append({'name':'patch_application','status':'passed' if patch_applied else 'failed' if patch_failed else 'not_run'})
    for phase in ('configure','build'):
        code_phase=(result.get('build',{}).get(phase) or {}).get('return_code')
        stages.append({'name':phase,'status':'not_run' if code_phase is None else 'passed' if code_phase==0 else 'failed'})
    stages.extend({'name':t['test'],'status':'passed' if t['passed'] else 'failed'} for t in result.get('tests',[]))
    item={'id':secrets.token_hex(8),'created_at':now(),'run_id':run_id,'experiment_id':run.get('experiment_id') if run else None,
          'kind':kind,'result':result,'returncode':code,'stages':stages,
          'patch_sha256':digest(root/'patch.diff') if (root/'patch.diff').exists() else None,
          'evaluator_sha256':digest(root/'frozen-driver.py') if (root/'frozen-driver.py').exists() else digest(Path(__file__).with_name('eval_driver.py'))}
    put('evaluations',item)
    return item

def summary(item):
    members=set(item.get('member_run_ids',[]))
    runs=[r for r in rows('runs') if r['id'] in members] if 'member_run_ids' in item else [r for r in rows('runs') if r.get('experiment_id')==item['id']]
    policy=item.get('qualification_policy') or {'version':'plan1a-asset-admission-v1',
                                                'asset_admission_success_per_group':2,
                                                'kernel_min_success_per_group':1,
                                                'plan1b_requires_verified_kernel_and_knowledge':True}
    # Older protocols used repeat_success_per_group and asset_min_success_per_group.
    # Keep those records readable while separating batch admission from K1 creation.
    admission_required=int(policy.get('asset_admission_success_per_group',policy.get('repeat_success_per_group',2)))
    asset_required=int(policy.get('kernel_min_success_per_group',policy.get('asset_min_success_per_group',1)))
    groups=[]
    for t in item['task_snapshots']:
        attempts=[r for r in runs if r['task']['id']==t['id']]
        good=sum(r.get('evaluation_passed',False) and r.get('submission_contract',{}).get('passed',False) for r in attempts)
        groups.append({'task_id':t['id'],'evaluation_successes':sum(bool(r.get('evaluation_passed')) for r in attempts),'successes':good,'attempts':sum(not r.get('exclude_from_agent_score') for r in attempts),'infrastructure_failures':sum(bool(r.get('exclude_from_agent_score')) for r in attempts),'required':admission_required,'asset_required':asset_required})
    qualification=next((e for e in rows('evaluations') if e.get('kind')=='qualification' and e.get('experiment_id')==item['id']),None)
    asset_admission_passed=all(g['successes']>=g['required'] for g in groups)
    kernel_coverage_passed=all(g['successes']>=g['asset_required'] for g in groups)
    return {**item,'runs':[r['id'] for r in runs],'groups':groups,'qualification':qualification,
            'qualification_policy':policy,'repeatability_qualified':asset_admission_passed,
            'asset_admission_passed':asset_admission_passed,'kernel_coverage_passed':kernel_coverage_passed,
            'repair_gate_passed':asset_admission_passed,
            'status':'archived' if item.get('archived_at') else 'draft' if not runs else 'running' if any(r['status'] in ('queued','preparing','running','collecting','evaluating') for r in runs) else 'ended'}
