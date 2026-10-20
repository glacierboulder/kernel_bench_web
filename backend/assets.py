"""Reconstructible kernel/knowledge candidates; independent combination validation."""
import argparse
import json
import secrets
import shutil
import subprocess
import re
from pathlib import Path
from .app import DATA,ROOT,get_run,now,rows
from .study import put,digest,snapshot_files,evaluation_record
from .submission import materialize
from .evaluator import evaluate_task,PROTO


def candidate(run_ids):
    if not run_ids or len(set(run_ids))!=len(run_ids):raise ValueError('Select distinct successful runs')
    runs=[get_run(r) for r in run_ids]
    if any(not r.get('evaluation_passed') or r.get('evaluation_returncode')!=0 or r['mode']!='live' for r in runs):raise ValueError('Only independently verified real patches are eligible')
    if any(r.get('plan1a_protocol') and not r.get('submission_contract',{}).get('passed') for r in runs):raise ValueError('Per-issue submission contract incomplete')
    baseline=runs[0]['task']['base_commit']
    if any(r['task']['base_commit']!=baseline for r in runs):raise ValueError('Cannot combine different baselines')
    identity=secrets.token_hex(8);root=DATA/'assets'/identity;root.mkdir(parents=True,mode=0o700)
    first=DATA/'runs'/run_ids[0]
    original=first/'frozen-task/repo'
    original_hash=snapshot_files(original)
    shutil.copytree(first/'frozen-task',root/'frozen-task')
    source=root/'kernel';shutil.copytree(original,source)
    sources=[];knowledge=[]
    asset={'id':identity,'created_at':now(),'kind':'kernel','label':'K1 候选','status':'candidate','baseline':baseline,'source_runs':run_ids,'sources':sources,'scope':'visible issues plus analytic Boolean regression; not full upstream suite'}
    try:
        for r in runs:
            folder=DATA/'runs'/r['id']
            if snapshot_files(folder/'frozen-task/repo')!=original_hash:raise ValueError('Frozen baseline source differs')
            p=folder/'patch.diff'
            expected=next((e['patch_sha256'] for e in rows('evaluations') if e.get('run_id')==r['id'] and e.get('kind')=='repair'),None)
            if expected and digest(p)!=expected:raise ValueError('Patch changed after evaluation')
            for check in (True,False):
                cmd=['git','apply',*(['--check'] if check else []),'--whitespace=nowarn',str(p.resolve())]
                result=subprocess.run(cmd,cwd=source,capture_output=True,text=True,timeout=60)
                if result.returncode:raise ValueError('Patch conflict for '+r['id']+': '+result.stderr[-1000:])
            sources.append({'run_id':r['id'],'patch_sha256':digest(p),'evaluation_id':r.get('evaluation_id'),'task_id':r['task']['id']})
            reports=r.get('issue_reports')
            if not reports:
                text=(folder/'report.md').read_text()
                reports=[]
                for i in r['task']['issues']:
                    number=i['id'].removeprefix('occt-')
                    match=re.search(r'### Issue #'+re.escape(number)+r'\b.*?(?=\n### |\n## |\Z)',text,re.S)
                    reports.append({'issue_id':i['id'],'root_cause':match.group(0) if match else None,
                        'evidence':['Original report.md and agent.jsonl; see their hashes.'],
                        'limitations':['Legacy report section extracted deterministically; explanation remains an agent claim.']})
            for report in reports:
                knowledge.append({'issue_id':report['issue_id'],'run_id':r['id'],'patch_sha256':digest(p),
                    'claim':report,'report_sha256':digest(folder/'report.md'),'trajectory_sha256':digest(folder/'agent.jsonl'),
                    'evidence_status':'reproduction_verified; explanation is agent claim',
                    'scope':{'applicability':'limited to verified cases; generalization not established','unexplored':'neighbor/general geometric correctness require further evaluation'}})
        materialize(original,source,root/'patch.diff')
        asset.update(patch_sha256=digest(root/'patch.diff'),source_tree_sha256=snapshot_files(source))
    except ValueError as e:asset.update(status='conflict',error=str(e))
    put('assets',asset)
    m={'id':secrets.token_hex(8),'created_at':now(),'kind':'knowledge','label':'M0 候选','status':'evidence_linked','kernel_id':identity,'source_runs':run_ids,'entries':knowledge,
       'limitations':['Successful traces are retained; root-cause explanations are not independently proved by test success.','Not automatically supplied to Plan 1A agents.']}
    mroot=DATA/'assets'/m['id'];mroot.mkdir(parents=True,mode=0o700)
    (mroot/'knowledge.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));m['knowledge_sha256']=digest(mroot/'knowledge.json');put('assets',m)
    asset['knowledge_id']=m['id'];put('assets',asset,False)
    (root/'manifest.json').write_text(json.dumps(asset,ensure_ascii=False,indent=2))
    (mroot/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    return asset


def verify_asset(identity, cancel=lambda: False, *, suites=None):
    asset=next(a for a in rows('assets') if a['id']==identity)
    if asset.get('protocol')=='plan1b-kernel-v1':raise ValueError('Plan 1B 的 K2 需使用 B1-aware evaluator；不能用 Plan 1A 组合验证器代替。')
    if asset['kind']!='kernel' or asset['status']!='candidate':raise ValueError('Kernel must be a fresh conflict-free candidate')
    root=DATA/'assets'/identity
    if digest(root/'patch.diff')!=asset['patch_sha256'] or snapshot_files(root/'kernel')!=asset['source_tree_sha256']:raise ValueError('Asset content changed')
    (root/'report.md').write_text('Supervisor combination validation. Sources: '+', '.join(asset['source_runs']))
    (root/'plan1a-protocol.json').write_text('{}')
    shutil.copy2(ROOT/'backend/eval_driver.py',root/'frozen-driver.py')
    asset['status']='evaluating';put('assets',asset,False)
    try:
        selected=suites or ['visible3','visible4','visible5']
        asset['evaluation_suites']=selected
        code,result=evaluate_task(root,cancel=cancel,frozen_task=root/'frozen-task',task_kind=selected[0],suites=selected)
        e=evaluation_record(None,result,code,'combination',root)
        asset.update(status='verified' if result.get('passed') and code==0 else 'failed',evaluation_id=e['id'],evaluation=result,evaluator_sha256=digest(root/'frozen-driver.py'))
        if asset['status']=='verified':asset.update(label='K1',frozen_at=now())
    except Exception as e:asset.update(status='infrastructure_error',error=str(e))
    put('assets',asset,False);(root/'manifest.json').write_text(json.dumps(asset,ensure_ascii=False,indent=2))
    return asset

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['candidate','verify']);p.add_argument('ids',nargs='+');a=p.parse_args()
    result=candidate(a.ids) if a.action=='candidate' else verify_asset(a.ids[0])
    print(json.dumps(result,ensure_ascii=False,indent=2))
