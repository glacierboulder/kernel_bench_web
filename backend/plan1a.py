"""Operator launch/finalize commands; no hidden auto-resubmission or budget expansion."""
import argparse
import fcntl
import json
from .app import DATA,rows
from .study import queue_experiment,summary,put

def launch(identity):
    item=next(e for e in rows('experiments') if e['id']==identity)
    if item.get('retrospective') or item.get('archived_at'):raise ValueError('Historical grouping cannot launch new runs')
    q=next((e for e in rows('evaluations') if e.get('experiment_id')==identity and e.get('kind')=='qualification'),None)
    if not q or not q.get('eligible'):raise ValueError('Baseline qualification must pass before paid runs')
    return queue_experiment(item,persist=False)

def _finalize(identity,cancel=lambda: False):
    from .assets import candidate,verify_asset
    e=next(e for e in rows('experiments') if e['id']==identity)
    if e.get('retrospective') or e.get('archived_at'):return None
    s=summary(e)
    if s['status']!='ended':return None
    if e.get('asset_policy')=='independent_group':
        results=[]
        for run_id in s['runs']:
            run=next(r for r in rows('runs') if r['id']==run_id)
            if not run.get('evaluation_passed') or not run.get('submission_contract',{}).get('passed'):continue
            if any(a.get('experiment_id')==identity and a.get('source_runs')==[run_id] for a in rows('assets')):continue
            asset=candidate([run_id]);asset['experiment_id']=identity;put('assets',asset,False)
            if asset['status']=='candidate':asset=verify_asset(asset['id'],cancel,suites=e['evaluation_suites'])
            results.append(asset)
        return results
    if any(a.get('experiment_id')==identity for a in rows('assets')):return None
    if not s['kernel_coverage_passed']:
        from .worker import TASK_SPECS
        results=[]
        for run_id in s['runs']:
            run=next(r for r in rows('runs') if r['id']==run_id)
            if not run.get('evaluation_passed') or not run.get('submission_contract',{}).get('passed'):continue
            asset=candidate([run_id]);asset['experiment_id']=identity;put('assets',asset,False)
            if asset['status']=='candidate':
                suite=TASK_SPECS[run['task']['id']]['evaluator_task']
                asset=verify_asset(asset['id'],cancel,suites=[suite])
            results.append(asset)
        item={'id':identity+'-gate','kind':'gate','label':'Plan 1A 组合 K1 覆盖','status':'partial','experiment_id':identity,
              'reason':'组合 K1 需要每个题组至少一次提交完整且修复评测通过。两次成功才达到 Plan 1A 资产准入标准；此覆盖状态不限制其他已验证 K1/M0 进入 Plan 1B。'}
        return results+[put('assets',item)]
    selected=['7cffea2fbbe1c80b']
    for task in e['task_snapshots']:
        run=sorted((r for r in rows('runs') if r.get('experiment_id')==identity and r['task']['id']==task['id'] and r.get('evaluation_passed') and r.get('submission_contract',{}).get('passed')),key=lambda r:r['attempt'])[0]
        selected.append(run['id'])
    asset=candidate(selected);asset['experiment_id']=identity;put('assets',asset,False)
    if asset['status']=='candidate':asset=verify_asset(asset['id'],cancel)
    return asset

def finalize(identity,cancel=lambda: False):
    with (DATA/'asset-finalize.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return None
        return _finalize(identity,cancel)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','finalize']);p.add_argument('experiment_id');a=p.parse_args()
    print(json.dumps(launch(a.experiment_id) if a.action=='launch' else finalize(a.experiment_id),ensure_ascii=False,indent=2))
