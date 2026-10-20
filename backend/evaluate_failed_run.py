"""Evaluate actual outputs of an ended failed run, without resuming or fabricating a report."""
import json
from pathlib import Path
import sys
import time
from .app import DATA, get_run
from .evaluator import evaluate_single
from .model_gateway import classify_gateway_failure, gateway_forwarded_request_count
from .records import event, save
from .submission import materialize

def evaluate_failure(run_id):
    run=get_run(run_id)
    if run['mode']!='live' or run['status'] not in ('failed','timed_out','interrupted'):
        raise SystemExit('Only ended failed real runs can be evaluated here')
    root=DATA/'runs'/run_id
    started=time.monotonic()
    event(run_id,'collecting','收集失败运行的实际产物；不伪造缺失的 agent 报告')
    changed=materialize(root/'frozen-task/repo',root/'agent-workspace/repo',root/'patch.diff')
    report=root/'agent-workspace/report.md'
    if report.is_file() and not report.is_symlink() and report.stat().st_size<=1024**2:
        (root/'report.md').write_text(report.read_text())
    if run.get('plan1a_protocol'):
        from .issue_reports import collect
        current=get_run(run_id);current['submission_contract']=collect(current,root);current['issue_reports']=current['submission_contract']['reports'];save(current)
    event(run_id,'evaluating','完全断网的评测器检查真实提交完整性')
    task_kind = {
        'occt_boolean_group_visible_544_506_847': 'visible3',
        'occt_boolean_group_visible_690_693_172': 'visible4',
        'occt_boolean_group_visible_370_872_1452': 'visible5',
        'occt_boolean_group_visible_690_693_172_370_1452': 'visible5all',
    }.get(run['task']['id'], 'single')
    code,result=evaluate_single(root,frozen_task=root/'frozen-task',task_kind=task_kind)
    audit=json.loads((root/'gateway-audit.json').read_text())
    current=get_run(run_id)
    agent_error=current.get('agent_error',current.get('error'))
    limit = current.get('provenance', {}).get('gateway_requests', 60)
    gateway_failure=classify_gateway_failure(
        audit,request_limit=limit,agent_outcome=current.get('agent_outcome'))
    if gateway_failure:
        current['gateway_failure']=gateway_failure
        current['failure_kind']=gateway_failure['failure_kind']
        if gateway_failure['source'] in ('local_policy','inferred_local_policy'):
            current['error']=(f"Local model gateway rejected the request: {gateway_failure['reason']} "
                              f"(used {gateway_failure['used']} of {gateway_failure['limit']}).")
        else:
            current['error']=(f"Upstream model service returned HTTP {gateway_failure['http_status']}; gateway source="
                              f"{gateway_failure['source']}.")
    else:
        current['failure_kind']='agent_wall_timeout' if run['status']=='timed_out' else run.get('failure_kind','execution_error')
    if run.get('plan1a_protocol'):
        from .study import evaluation_record
        current['evaluation_id']=evaluation_record(run_id,result,code)['id']
    current['changed_files']=changed
    current['evaluation_returncode']=code
    current['evaluation']=result
    current['evaluation_passed']=bool(result.get('passed')) and code==0
    current['evaluation_phase']='submission_validation' if not result.get('tests') else 'tests'
    current['agent_error']=agent_error
    current['report']=(root/'report.md').read_text() if (root/'report.md').is_file() else 'Agent 未提交报告。此文字是平台状态说明。'
    forwarded_requests=gateway_forwarded_request_count(audit)
    current['gateway_request_count']=forwarded_requests
    current['evaluation_elapsed_seconds']=round(time.monotonic()-started,2)
    current['checks']=[dict(issue_id=None,name='必需提交文件完整性',status='passed' if result.get('report',{}).get('provided') and changed else 'failed',detail={'changed_files':changed,'report_provided':result.get('report',{}).get('provided',False)})]
    def issue_id(test_name):
        return next((f'occt-{number}' for number in
                     ('544', '506', '847', '690', '693', '172', '370', '872', '1452')
                     if number in test_name), None)
    current['checks'] += [dict(issue_id=issue_id(t['test']),name=t['test'],status='passed' if t['passed'] else 'failed',detail=t.get('result')) for t in result.get('tests',[])] or [dict(issue_id=i['id'],name='公开复现',status='not_run',detail='缺少有效提交，未进入修复后的编译及复现') for i in run['task']['issues']]
    current['artifacts']=['agent.jsonl','patch.diff','evaluation.json','provenance.json','gateway-audit.json','run-summary.md']
    if run.get('plan1a_protocol'):
        current['artifacts'] += ['issue-reports.json','plan1a-protocol.json'] + (['new-tests.zip'] if (root/'new-tests.zip').exists() else [])
    if (root/'report.md').is_file():
        current['artifacts'].append('report.md')
    summary=f'''# 首题真实运行记录

Run: {run_id}

DSH 0.2.0-rc.2 / {current['agent']['model']}。外部网络隔离，仅固定模型网关。

模型上游请求数：{forwarded_requests}。源码改动文件：{len(changed)}。Agent 报告存在：{(root/'report.md').is_file()}。
agent 阶段耗时：{current['elapsed_seconds']} 秒。
评测器真实运行，返回 {code}；通过：{current['evaluation_passed']}；测试数：{len(result.get('tests', []))}。
这不是修复成功，也不能据此推断 agent 无法修复该问题。

离线基线对照已单独完成：编译成功，#544 在约 15 秒 CPU 限制处失败。
本轮没有自动追加请求、扩大预算或向模型发送私有评测材料。
'''
    (root/'run-summary.md').write_text(summary)
    save(current)
    event(run_id,'failed',current['error'])
    return {'id':run_id,'requests':forwarded_requests,'changed_files':changed,'evaluation_exit':code,'report_provided':result.get('report',{}).get('provided'), 'checks':current['checks']}

if __name__=='__main__':
    print(json.dumps(evaluate_failure(sys.argv[1]),ensure_ascii=False,indent=2))
