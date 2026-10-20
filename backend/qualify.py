"""Offline baseline qualification; never consumes model requests."""
import argparse
import json
import secrets
import shutil
from .app import DATA,ROOT,rows
from .evaluator import evaluate_task,PROTO
from .study import put,evaluation_record

def qualify(experiment_id):
    root=DATA/'qualifications'/secrets.token_hex(8);root.mkdir(parents=True)
    shutil.copy2(PROTO/'private/evaluators/run_eval.py',root/'frozen-evaluator.py')
    shutil.copy2(ROOT/'backend/eval_driver.py',root/'frozen-driver.py')
    experiment=next(e for e in rows('experiments') if e['id']==experiment_id)
    suites=experiment.get('evaluation_suites',['visible4','visible5'])
    code,result=evaluate_task(root,task_kind=suites[0],suites=suites,baseline=True)
    e=evaluation_record(None,result,code,'qualification',root)
    # Immutable final qualification includes membership and exact expected failures.
    expected={'visible_issue_'+i['id'].removeprefix('occt-') for t in experiment['task_snapshots'] for i in t['issues']}
    tests={t['test']:t['passed'] for t in result.get('tests',[])}
    eligible=expected<=tests.keys() and all(not tests[t] for t in expected) and tests.get('regression_analytic_boxes',False)
    e.update(id=secrets.token_hex(8),experiment_id=experiment_id,eligible=eligible,
             root=str(root),expected_failures=sorted(expected))
    put('evaluations',e)
    print(json.dumps({'qualification_id':e['id'],'eligible':eligible,'tests':tests},ensure_ascii=False),flush=True)
    return eligible

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('experiment_id');a=p.parse_args()
    raise SystemExit(0 if qualify(a.experiment_id) else 1)
