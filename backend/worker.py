"""Single-worker, persistent OCCT execution. No arbitrary shell/API commands."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import traceback
import re

from .app import DATA, ROOT, db, get_run, now, rows
from .records import begin, event, save
from .dsh_protocol import DshStream
from .model_gateway import (Gateway, classify_gateway_failure,
                            gateway_forwarded_request_count)
from .preflight import verify
from .sandbox import command, limits, monitor, PYTHON, stop
from .submission import materialize, source_files
from .evaluator import evaluate_single
from .catalog import validate_bundle
from .proto_config import BENCHMARK_ROOT, PROTO
from .settings import SETTINGS
from .tool_paths import executable
from .toolchain import environment as toolchain_environment

RUNTIME = ROOT / 'runtime/dsh'
CLI = '/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'
from .dsh_config import MODEL, cumulative_request_limit, patch_config, output_token_limit


def _load_task_specs():
    """Build task dispatch from catalog manifests and recorded legacy provenance."""
    catalog_path=BENCHMARK_ROOT/'catalog.json'
    dispatch_path=BENCHMARK_ROOT/'evaluation'/'provenance'/'legacy-dispatch.json'
    if not catalog_path.is_file():
        return {}
    # Validate identity rules before building maps keyed by group ID. In
    # particular, same-ID group versions are forbidden and must never be
    # silently shadowed by whichever catalog row happens to appear last.
    validate_bundle(BENCHMARK_ROOT)
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    dispatch=(json.loads(dispatch_path.read_text(encoding='utf-8')).get('groups',{})
              if dispatch_path.is_file() else {})
    suites={(item['id'],item['version']):item for item in catalog.get('evaluation_suites',[])}
    specs={}
    for reference in catalog.get('groups',[]):
        path=BENCHMARK_ROOT/reference['path']
        group=json.loads(path.read_text(encoding='utf-8'))
        suite_ref=group['evaluation_suite']
        suite_reference=suites.get((suite_ref['id'],suite_ref['version']))
        if not suite_reference:
            continue
        suite_manifest=json.loads((BENCHMARK_ROOT/suite_reference['path']).read_text(encoding='utf-8'))
        legacy=dispatch.get(group['id'],{})
        legacy_task_dir=(PROTO/'tasks'/legacy['legacy_task_folder'] if legacy.get('legacy_task_folder') else None)
        task_manifest=(legacy_task_dir/'task.json') if legacy_task_dir else None
        actual_hash=hashlib.sha256(task_manifest.read_bytes()).hexdigest() if task_manifest and task_manifest.is_file() else None
        expected_hash=legacy.get('legacy_task_manifest_sha256')
        if actual_hash != expected_hash:
            legacy_task_dir=None
        issues=', '.join('#'+member['issue_id'].removeprefix('occt-') for member in group['members'])
        specs[group['id']]={'task_dir':legacy_task_dir,
            'evaluator_task':suite_manifest.get('legacy_task_kind','single'),'issues':issues,
            'legacy_version':'proto-1' if legacy_task_dir else None,'legacy_manifest_sha256':expected_hash,
            'catalog_version':group['version'],'group':group,
            'source_id':group['source_id'],'suite_id':suite_ref['id'],'suite_version':suite_ref['version'],
            'wall_seconds':group['budget']['wall_seconds'],'group_manifest':path}
    return specs


TASK_SPECS = _load_task_specs()

def heartbeat(status, run_id=None):
    path = DATA / 'worker-status.json'
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(pid=os.getpid(), status=status, run_id=run_id, at=time.time())))
    tmp.replace(path)




def claim():
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        r = conn.execute("SELECT id,payload FROM runs WHERE json_extract(payload,'$.status')='queued' ORDER BY rowid LIMIT 1").fetchone()
        if not r:
            return None
        run = json.loads(r['payload'])
        run['status'] = 'preparing'
        conn.execute('UPDATE runs SET payload=? WHERE id=?', (json.dumps(run), run['id']))
        return run


def run_task(run, request_limit=None):
    identity = run['id']
    root = DATA / 'runs' / identity
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = time.monotonic()
    gateway = None
    proc = None
    codex_config={}
    codex_model=None
    def cancelled():
        heartbeat('busy', identity)
        return get_run(identity).get('cancel_requested', False)
    try:
        spec = TASK_SPECS.get(run['task']['id'])
        catalog_run=bool(spec and run['task'].get('version')==spec['catalog_version'])
        legacy_run=bool(spec and run['task'].get('version')==spec['legacy_version'])
        adapter_name=run.get('agent',{}).get('adapter')
        if not spec or not (catalog_run or legacy_run) or adapter_name not in {'dsh','codex'}:
            raise ValueError('真实执行需要题库登记的 OCCT 题目与已注册适配器')
        if adapter_name=='codex':
            from .codex_adapter import CodexAdapter
            codex_config=SETTINGS.config.get('codex',{})
            codex_probe=CodexAdapter(codex_config).probe()
            if not codex_probe.get('live_enabled'):
                raise ValueError('Codex live disabled: worker-side credential proxy and sandbox isolation are not verified')
            codex_model=codex_config.get('model')
            if run.get('agent',{}).get('model') not in ('',codex_model):
                raise ValueError('Codex model is not in the trusted worker configuration')
        snapshot_root=root/'benchmark-snapshot'
        snapshot_manifest=None
        if catalog_run:
            from .freeze import verify_snapshot
            snapshot_manifest=verify_snapshot(snapshot_root)
            if (snapshot_manifest.get('task_id')!=run['task']['id'] or
                    snapshot_manifest.get('task_version')!=run['task']['version'] or
                    snapshot_manifest.get('source_id')!=spec['source_id'] or
                    snapshot_manifest.get('suite_id')!=spec['suite_id'] or
                    snapshot_manifest.get('suite_version')!=spec['suite_version']):
                raise ValueError('frozen benchmark snapshot does not match the queued task')
        else:
            if not spec.get('task_dir') or run['task'].get('source_hash') != spec['legacy_manifest_sha256']:
                raise ValueError('legacy task version is unavailable or changed')
            task_manifest=spec['task_dir']/'task.json'
            if not task_manifest.is_file() or run['task'].get('source_hash') != hashlib.sha256(task_manifest.read_bytes()).hexdigest():
                raise ValueError('legacy task manifest hash mismatch')
        if adapter_name=='dsh' and run['agent'].get('model') not in ('', MODEL):
            raise ValueError('model is not enabled in the trusted runtime')
        prior = run.get('prior_request_count', 0)
        total_limit = run.get('cumulative_request_limit') or request_limit or cumulative_request_limit()
        total_limit = cumulative_request_limit(total_limit)
        current = get_run(identity)
        current['cumulative_request_limit'] = total_limit
        save(current)
        remaining = total_limit - prior
        if remaining <= 0:
            raise ValueError('Cumulative model request budget is exhausted')
        key = os.environ.get('DEEPSEEK_API_KEY') if adapter_name=='dsh' else os.environ.get('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('trusted model API key is unavailable to worker')
        if run.get('experiment_id'):
            if catalog_run:
                raise ValueError('Plan 1A protocol currently requires its frozen proto-1 task version')
            from .study import rows as study_rows, snapshot_files, digest
            experiment=next(e for e in study_rows('experiments') if e['id']==run['experiment_id'])
            qualification=next((e for e in study_rows('evaluations') if e.get('kind')=='qualification' and e.get('experiment_id')==experiment['id']),None)
            if not qualification or not qualification.get('eligible'):
                raise ValueError('infrastructure: baseline qualification missing or ineligible')
            if snapshot_files(spec['task_dir']) != run['task']['task_tree_sha256']:
                raise ValueError('infrastructure: task files changed after protocol freeze')
            if digest(ROOT/'backend/eval_driver.py')!=run['plan1a_protocol']['evaluator_sha256'] or digest(PROTO/'private/evaluators/run_eval.py')!=run['plan1a_protocol']['upstream_evaluator_sha256'] or digest(ROOT/'config/regressions/analytic_boxes/reproduce.cpp')!=run['plan1a_protocol']['regression_sha256']:
                raise ValueError('infrastructure: evaluator changed after protocol freeze')
        boundary = verify()
        control = root / 'control'; control.mkdir()
        workspace = root / 'agent-workspace'
        frozen_task=root/'frozen-task'
        parent_root=DATA/'runs'/run['parent_run_id'] if run.get('parent_run_id') else None
        if catalog_run:
            from .freeze import materialize_source
            frozen_task.mkdir(mode=0o700)
            materialize_source(snapshot_root,frozen_task/'repo')
            shutil.copytree(snapshot_root/'visible',frozen_task/'visible')
            shutil.copytree(snapshot_root/'tools',frozen_task/'tools')
            issue_lines='\n\n'.join(f"## {issue['id']} · {issue.get('title','')}\n\n{issue.get('body','')}"
                                     for issue in run['task']['issues'])
            (frozen_task/'README.md').write_text(
                '# OCCT shared benchmark task\n\n'
                f"Task: {run['task']['id']}@{run['task']['version']}\n"
                f"Locked source: {snapshot_manifest['source_commit']}\n\n"
                'Edit only repo/. Public issue statements and reproduction materials are under visible/. '
                'Build with tools/build.sh repo build and run supplied public cases with '
                'tools/run_draw_case.py. Submit patch.diff and report.md.\n\n'+issue_lines+'\n',
                encoding='utf-8')
        else:
            shutil.copytree(parent_root/'frozen-task' if parent_root else spec['task_dir'],frozen_task)
        # Repair provenance is supervisor-only for every agent-facing version.
        for path in [frozen_task/'README.md',*list((frozen_task/'visible').rglob('*.md'))]:
            if not path.is_file() or path.is_symlink():
                continue
            text=path.read_text(encoding='utf-8')
            text=re.sub(r'Upstream relation:.*?(?:[.]|$)', '', text, flags=re.S)
            text=re.sub(r'The public upstream fix references.*?(?:\n\n|$)', '',text,flags=re.S)
            path.write_text(text,encoding='utf-8')
        if run.get('plan1a_protocol'):
            shutil.copy2(ROOT/'backend/eval_driver.py',root/'frozen-driver.py')
            (root/'plan1a-protocol.json').write_text(json.dumps(run['plan1a_protocol'],indent=2))
        shutil.copytree(parent_root/'agent-workspace' if parent_root else frozen_task,workspace)
        if not catalog_run:
            shutil.copy2(parent_root/'frozen-evaluator.py' if parent_root else PROTO/'private/evaluators/run_eval.py',root/'frozen-evaluator.py')
            shutil.copy2(parent_root/'frozen-runner.py' if parent_root else PROTO/'scripts/run_draw_case.py',root/'frozen-runner.py')
        tree=hashlib.sha256()
        for name,path in sorted(source_files(frozen_task).items()):
            tree.update(name.encode()+b'\0'+hashlib.sha256(path.read_bytes()).digest())
        # Build concurrency is bounded without altering the original task.
        build_script = workspace / 'tools/build.sh'
        build_script.write_text(build_script.read_text().replace('--parallel 8', '--parallel 2'))
        home = root / 'dsh-home'
        if parent_root:
            shutil.copytree(parent_root/'dsh-home',home)
        else:
            home.mkdir()
        gateway_dir = root / 'gateway'; gateway_dir.mkdir(mode=0o700)
        configured_output=run.get('plan1a_protocol',{}).get('max_output_tokens')
        if configured_output is None and run.get('experiment_id'):
            configured_output=experiment['max_output_tokens']
        max_output_tokens=output_token_limit(configured_output)
        patch_config(control / 'overlay.yml',max_output_tokens)
        shutil.copy2(ROOT / 'backend/sandbox_entry.py', control / 'entry.py')
        shutil.copy2(ROOT/'backend/repro_runner.py',control/'repro_runner.py')
        shutil.copy2(ROOT/'backend/repro_runner.py',workspace/'tools/run_repro.py')
        prompt = f'''Solve the OCCT task in /workspace. Read README.md and the visible issue materials for {spec['issues']}.
You must investigate the supplied source and reproduce every visible issue, fix them in repo/, build with tools/build.sh repo build, and run every supplied visible reproduction with the bounded run_draw_case.py tool (and the visible C++ reproducer where provided). Use python3, not python, to invoke Python scripts. No dependency installation or public internet is available. Do not use subagents. Do not modify task tools or visible inputs. Only changes under repo/ are submitted as a patch, materialized by the supervisor. Save a concise report to /workspace/report.md describing root cause, changed files, exact validation commands/results and remaining limits. Do not invent test results. Use at most two compiler jobs. The outer environment is already isolated: filesystem access outside the task, real API credentials and all public/campus network are absent. Your only network route is the fixed model gateway. You have {run.get('plan1a_protocol',{}).get('wall_seconds',spec['wall_seconds'] if catalog_run else 1800)/60:g} minutes for this initial run. Finish with the report even if a fix cannot be completed.'''
        if run.get('resumed_session_id'):
            previous_failure=run.get('parent_gateway_failure')
            if previous_failure:
                prior_gateway_note=(
                    'Supervisor gateway audit classification for the previous attempt: '
                    +json.dumps(previous_failure,sort_keys=True)+'. Treat this audit-derived '
                    'classification as source evidence; the CLI AUTH label alone is not a diagnosis.')
            else:
                prior_gateway_note=(
                    'The previous CLI error has no verified gateway-source classification. '
                    'Do not infer credential validity or invalidity from the CLI AUTH label alone.')
            prompt = ("Continue the SAME task and workspace. "+prior_gateway_note+
                      " Build files remain in /workspace/build. Previous background jobs are terminated; rerun the build with its preserved cache rather than querying old job IDs. The model is now DeepSeek V4.1 Flash. You have at most 30 minutes. Batch source reads and wait for long builds instead of frequent polling. Do not install dependencies or use subagents. Fix repo/, validate with the supplied bounded tool, and write /workspace/report.md with honest results before finishing. Only source edits are materialized by the supervisor. Prioritize delivering the report within budget.")
        else:
            prompt += " Batch source reads; avoid frequent build polling. Deliver report.md even if you cannot complete the fix."
        if catalog_run and spec['evaluator_task']=='active':
            prompt += " This is an active-search task: submit /workspace/findings.jsonl as JSON Lines with input, repro, and observation fields. Refer to files relative to /workspace and include only files you created in the task workspace. An empty file is valid when no candidates are found; format validity does not score discovery quality."
        prompt += " For EVERY custom compiled C++ reproduction and debugger run, use the protected runner: python /control/repro_runner.py --wall 18 --cpu 15 --memory-mib 4096 -- /workspace/path/to/binary. For debugging use --wall 60 --cpu 60 before -- gdb ... . The runner returns JSON even on timeout/failure and kills the entire process group, including leftover children after the parent exits. Do not launch reproductions in the background or use bare timeout / kill $! as substitutes. Compile outside this runner with at most two compiler jobs. A host fallback caps workspace-native executables at 4 GiB virtual address space, 3 GiB RSS, 60s CPU and 120s elapsed, terminating only the reproduction subtree; the agent continues. Read the JSON failure and keep diagnosing, then deliver the report."
        prompt += f" Cumulative request limit: {total_limit}; previously used: {prior}; remaining for this continuation: {remaining}."
        if run.get('plan1a_protocol'):
            prompt += ''' Additionally write /workspace/issue-reports.json as a JSON list with exactly one entry per public issue. Each entry must contain issue_id (occt-N), root_cause (string; explicitly label uncertainty), evidence (list of exact observations/commands), changed_files (list of relative repo paths), validation (list of commands/results), limitations (list). Write incremental reports early, including unresolved issues. Put any new regression tests in /workspace/new-tests/ with reproduction instructions. Source patch and independent evaluator determine repair scores; report claims do not. Do not change visible inputs, task tools, or evaluation criteria.'''
        (root / 'prompt.txt').write_text(prompt)
        wall_seconds=run.get('plan1a_protocol',{}).get('wall_seconds',spec['wall_seconds'] if catalog_run else 1800)
        evaluator_source=(snapshot_root/'supervisor'/'legacy'/'run_eval.py' if catalog_run else root/'frozen-evaluator.py')
        provenance = dict(source_tree_sha256=tree.hexdigest(), evaluator_sha256=hashlib.sha256(evaluator_source.read_bytes()).hexdigest(),
                          agent_adapter=adapter_name,agent_version=('0.2.0-rc.2' if adapter_name=='dsh' else codex_config.get('codex_version')),
                          model=(run['agent'].get('model') or MODEL) if adapter_name=='dsh' else codex_model,
                          prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(), overlay_sha256=hashlib.sha256((control/'overlay.yml').read_bytes()).hexdigest(),
                          runtime_lock_sha256=(hashlib.sha256((RUNTIME/'package-lock.json').read_bytes()).hexdigest() if adapter_name=='dsh' else None),
                          source_hash=run['task'].get('source_hash'), isolation=boundary,
                          source_id=spec['source_id'] if catalog_run else None,
                          source_commit=snapshot_manifest.get('source_commit') if catalog_run else None,
                          source_tree_sha256_locked=snapshot_manifest.get('source_tree_sha256') if catalog_run else None,
                          suite_id=spec['suite_id'] if catalog_run else None,
                          suite_version=spec['suite_version'] if catalog_run else None,
                          benchmark_snapshot_sha256=snapshot_manifest.get('snapshot_sha256') if catalog_run else None,
                          agent_wall_seconds=wall_seconds, evaluator_wall_seconds=2400, gateway_requests=remaining, cumulative_request_limit=total_limit, prior_request_count=prior,
                          cpu_affinity=sorted(os.sched_getaffinity(0))[:2], nice=10,
                          per_request_max_output_tokens=max_output_tokens, compiler_jobs=2, reproduction_limits={"runner_as_mib":4096,"runner_wall_seconds":18,"runner_cpu_seconds":15,"fallback_rss_mib":3072,"fallback_cpu_seconds":60,"fallback_wall_seconds":120,"guard_sha256":hashlib.sha256((ROOT/"backend/repro_guard.py").read_bytes()).hexdigest(),"runner_sha256":hashlib.sha256((control/"repro_runner.py").read_bytes()).hexdigest()},
                          network=('unshare-net; fixed DeepSeek Messages Unix gateway only' if adapter_name=='dsh'
                                   else 'unshare-all; fixed OpenAI Responses Unix gateway; no credential in sandbox'))
        task_tool_env={}
        if catalog_run:
            task_tool_env=toolchain_environment(snapshot_manifest['toolchain_id'],
                profile_path=snapshot_root/'toolchain.json')
        (root / 'provenance.json').write_text(json.dumps(provenance, indent=2))
        current = get_run(identity);current['provenance']=provenance;save(current)
        if adapter_name=='dsh':
            gateway = Gateway(gateway_dir / 'api.sock', key, MODEL, max_requests=remaining, max_output_tokens=max_output_tokens)
            gateway.start()
            mounts = [(RUNTIME, '/runtime', False), (home, '/state', True),
                      (control, '/control', False), (gateway_dir, '/gateway', False)]
            env = dict(DSH_HOME='/state', DEEPSEEK_API_KEY='gateway-placeholder-not-a-secret',
                       DEEPSEEK_BASE_URL=f'http://{SETTINGS.gateway_host}:{SETTINGS.gateway_port}/anthropic',
                       BENCH_GATEWAY_HOST=SETTINGS.gateway_host, BENCH_GATEWAY_PORT=str(SETTINGS.gateway_port),
                       DSH_PERMISSION_MODE='danger-full-access', NODE_TLS_REJECT_UNAUTHORIZED='1')
            env.update(task_tool_env)
            env['BENCH_TOOLCHAIN_PREFIX']=str(SETTINGS.python_prefix)
            node_binary=executable('Node.js',env_name='BENCH_NODE',
                                   config_name='node',default='node')
            args = command(workspace, mounts=mounts, env=env) + [PYTHON, '/control/entry.py',
                    node_binary, CLI, '--profile', 'headless', '--patch', '/control/overlay.yml', '--json']
            if run.get('resumed_session_id'):
                args += ['--session-id', run['resumed_session_id']]
            args += ['-']
            parser = DshStream()
            event(identity, 'running', 'DSH 真实执行；外部网络隔离，仅开放固定模型网关')
            stderr = (root / 'agent-stderr.log').open('w')
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                                    text=True, start_new_session=True, preexec_fn=limits)
            proc.stdin.write(prompt);proc.stdin.close()
            errors = []
            def read_events():
                try:
                    with (root / 'agent.jsonl').open('w') as stream:
                        for line in proc.stdout:
                            line = line.replace(key, '[REDACTED]')
                            stream.write(line);stream.flush()
                            try:
                                item = parser.feed(line)
                                live = get_run(identity)
                                if parser.session_id:
                                    live['session_id'] = parser.session_id
                                live['usage_steps'] = parser.usage
                                live['events'].append(dict(seq=len(live['events'])+1, at=now(),stage='running',
                                                           message=json.dumps(item,ensure_ascii=False)[:6000]))
                                save(live)
                            except (ValueError, json.JSONDecodeError) as exc:
                                errors.append(type(exc).__name__)
                except Exception as exc:
                    errors.append(type(exc).__name__)
            reader = threading.Thread(target=read_events,daemon=True);reader.start()
            try:
                code = monitor(proc, min(wall_seconds, run['agent']['timeout_minutes']*60), cancelled, workspace, guard_reproductions=True)
            finally:
                reader.join(timeout=10);stderr.close()
                (root / 'gateway-audit.json').write_text(json.dumps(gateway.audit,indent=2))
                gateway.close();gateway=None
            current=get_run(identity);current['agent_returncode']=code;current['protocol_errors']=errors;current['agent_outcome']=parser.reason;save(current)
            if not parser.completed(code):
                diagnostic=(root/'agent-stderr.log').read_text(errors='replace').replace(key,'[REDACTED]')[-2000:]
                raise RuntimeError('DSH did not complete: '+diagnostic)
        else:
            from .codex_adapter import CodexAdapter
            codex=CodexAdapter(codex_config)
            event(identity,'running','Codex CLI 真实执行；bubblewrap 无网络沙箱仅开放固定 Responses 代理')
            event_stream=(root/'agent.jsonl').open('w',encoding='utf-8')
            def codex_event(item):
                event_stream.write(json.dumps(item,ensure_ascii=False)+'\n');event_stream.flush()
                live=get_run(identity)
                if item.get('type')=='thread.started':
                    live['session_id']=item.get('thread_id')
                live['events'].append(dict(seq=len(live['events'])+1,at=now(),stage='running',
                                           message=json.dumps(item,ensure_ascii=False)[:6000]))
                save(live)
            try:
                codex_result=codex.run_isolated(prompt,workspace=workspace,control=control,
                    gateway_dir=gateway_dir,api_key=key,model=codex_model,request_limit=remaining,
                    max_output_tokens=codex_config.get('max_output_tokens',4096),
                    timeout_seconds=min(wall_seconds,run['agent']['timeout_minutes']*60),
                    cancelled=cancelled,on_event=codex_event,session_id=run.get('resumed_session_id'),
                    task_env=task_tool_env)
            finally:
                event_stream.close()
            (root/'gateway-audit.json').write_text(json.dumps(codex_result.get('gateway_audit',[]),indent=2))
            code=0 if codex_result['status']=='completed' else 1
            errors=[]
            current=get_run(identity)
            current['agent_returncode']=code
            current['agent_outcome']=codex_result['status']
            current['usage']=codex_result.get('usage')
            current['codex_recovery_budget']=codex_result.get('recovery_budget')
            current['gateway_request_count']=codex_result.get('api_request_count')
            current['cumulative_request_count']=prior+(codex_result.get('api_request_count') or 0)
            current['request_budget_remaining']=max(0,total_limit-current['cumulative_request_count'])
            current['cumulative_request_limit']=total_limit
            current['codex_attempts']=codex_result.get('attempts',[])
            save(current)
            if code!=0:
                diagnostic=(codex_result.get('stderr_tail') or '')[-2000:].replace(key,'[REDACTED]')
                raise RuntimeError('Codex CLI did not complete: '+codex_result['status']+' '+diagnostic)
        event(identity,'collecting','收集真实提交；监督器相对原始源码生成补丁')
        changes=materialize(frozen_task/'repo',workspace/'repo',root/'patch.diff')
        report=workspace/'report.md'
        if report.is_symlink() or not report.is_file() or report.stat().st_size>1024**2:
            raise ValueError('report missing, symlink, or too large')
        (root/'report.md').write_text(report.read_text().replace(key,'[REDACTED]'))
        current=get_run(identity);current['changed_files']=changes;current['report']=(root/'report.md').read_text();
        current['artifacts']=['patch.diff','report.md','agent.jsonl'];save(current)
        if run.get('plan1a_protocol'):
            from .issue_reports import collect
            current=get_run(identity);current['submission_contract']=collect(current,root,key)
            current['issue_reports']=current['submission_contract']['reports']
            current['artifacts'] += ['issue-reports.json','plan1a-protocol.json'] + (['new-tests.zip'] if (root/'new-tests.zip').exists() else [])
            save(current)
        event(identity,'evaluating','独立无网络沙箱：应用补丁、编译、逐问题复现和解析几何回归')
        if spec['evaluator_task']=='active' and (workspace/'findings.jsonl').is_file():
            finding_file=workspace/'findings.jsonl'
            if finding_file.is_symlink() or finding_file.stat().st_size>2*1024**2:
                raise ValueError('findings.jsonl is a symlink or exceeds 2 MiB')
            shutil.copy2(finding_file,root/'findings.jsonl')
            current=get_run(identity);current['artifacts'].append('findings.jsonl');save(current)
        elif catalog_run and spec['evaluator_task']=='active':
            (root/'findings.jsonl').write_text('',encoding='utf-8')
            current=get_run(identity);current['artifacts'].append('findings.jsonl');save(current)
        eval_kwargs={}
        if catalog_run:
            eval_kwargs=dict(source_id=spec['source_id'],group_id=run['task']['id'],
                suite_ref={'id':spec['suite_id'],'version':spec['suite_version']},
                suite_snapshot=json.loads((snapshot_root/'suite.json').read_text(encoding='utf-8')),
                snapshot_root=snapshot_root,allow_empty_findings=spec['evaluator_task']=='active')
        eval_code, result = evaluate_single(root, cancelled, frozen_task, spec['evaluator_task'],**eval_kwargs)
        current=get_run(identity)
        def issue_id(test_name):
            return next((f'occt-{number}' for number in
                         ('544', '506', '847', '690', '693', '172', '370', '872', '1452')
                         if number in test_name), None)
        current['checks']=[dict(issue_id=t.get('issue_id') or issue_id(t['test']),name=t['test'],
            status='passed' if t['passed'] else 'failed',detail=t.get('result')) for t in result.get('tests',[])]
        current['evaluation_returncode']=eval_code
        current['evaluation_passed']=bool(result.get('passed')) and eval_code==0
        if run.get('plan1a_protocol'):
            from .study import evaluation_record
            evaluation=evaluation_record(identity,result,eval_code)
            current['evaluation_id']=evaluation['id']
            current['gateway_request_count']=len(json.loads((root/'gateway-audit.json').read_text()))
        current['evaluation']=result
        from .public_results import public_evaluation
        public_result=public_evaluation(result,current)
        (root/'evaluation.json').write_text(json.dumps(public_result,ensure_ascii=False,indent=2),encoding='utf-8')
        current['artifacts'] += ['evaluation.json','provenance.json','gateway-audit.json']
        current['artifacts'] += [n for n in ['repro-resource-events.jsonl','resource-limit-agent-workspace.json','resource-limit-evaluation-workspace.json'] if (root/n).is_file() and n not in current['artifacts']]
        current['elapsed_seconds']=round(time.monotonic()-started,2)
        current['status']='completed' if result.get('passed') and eval_code==0 and current.get('submission_contract',{}).get('passed',True) else 'failed'
        current['failure_kind']=(None if current['status']=='completed' else 'submission_invalid' if not current.get('submission_contract',{}).get('passed',True) or result.get('failure_stage')=='submission' or result.get('patch_error') else 'build_error' if not current['checks'] else 'fix_failed')
        save(current)
        if current['status']=='completed':
            (DATA/'live-verified.json').write_text(json.dumps(dict(run_id=identity,at=now(),task_id=current['task']['id'],
                task_version=current['task']['version'],adapter=current['agent']['adapter'],source_hash=current['task'].get('source_hash'))))
        event(identity,current['status'],'真实评测通过' if current['status']=='completed' else '真实评测未通过；详见评测结果')
    except Exception as exc:
        if proc and proc.poll() is None:
            stop(proc)
        if gateway:
            (root/'gateway-audit.json').write_text(json.dumps(gateway.audit,indent=2))
            gateway.close()
        message=str(exc)
        for secret_name in ('DEEPSEEK_API_KEY','OPENAI_API_KEY'):
            secret=os.environ.get(secret_name)
            if secret:
                message=message.replace(secret,'[REDACTED]')
        current=get_run(identity)
        current['agent_error']=message
        audit_path=root/'gateway-audit.json'
        try:
            gateway_audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.is_file() else []
        except (OSError, json.JSONDecodeError):
            gateway_audit=[]
        gateway_failure=classify_gateway_failure(
            gateway_audit,
            request_limit=(current.get('provenance') or {}).get('gateway_requests'),
            agent_outcome=current.get('agent_outcome'))
        if gateway_failure:
            current['gateway_failure']=gateway_failure
            current['failure_kind']=gateway_failure['failure_kind']
            if gateway_failure['source'] in ('local_policy','inferred_local_policy'):
                current['error']=(f"Local model gateway rejected the request: {gateway_failure['reason']} "
                                  f"(used {gateway_failure['used']} of {gateway_failure['limit']}).")
            else:
                current['error']=(f"Upstream model service returned HTTP {gateway_failure['http_status']}; "
                                  f"gateway source={gateway_failure['source']}.")
        else:
            current['failure_kind']='infrastructure_error' if message.startswith('infrastructure:') or message.startswith('Evaluator failed before JSON output:') else 'execution_error'
            current['error']=message
        current['elapsed_seconds']=round(time.monotonic()-started,2)
        for name in ['agent.jsonl','evaluation.json']:
            if (root/name).is_file() and name not in current['artifacts']:
                current['artifacts'].append(name)
        save(current)
        event(identity,'timed_out' if isinstance(exc,TimeoutError) else 'cancelled' if message=='cancelled' else 'failed',message)
        if (root/'frozen-task').is_dir() and (root/'gateway-audit.json').is_file() and not (root/'evaluation-workspace').exists() and message!='cancelled':
            try:
                from .evaluate_failed_run import evaluate_failure
                evaluate_failure(identity)
            except Exception as evaluation_error:
                event(identity,'failed',message+'; submission evaluation error: '+type(evaluation_error).__name__)
        current=get_run(identity)
        current['artifacts'] += [n for n in ['repro-resource-events.jsonl','resource-limit-agent-workspace.json','resource-limit-evaluation-workspace.json'] if (root/n).is_file() and n not in current['artifacts']]
        save(current)
        if run.get('plan1a_protocol') and not current.get('evaluation_id') and current.get('failure_kind')=='infrastructure_error':
            from .study import evaluation_record
            current['evaluation_id']=evaluation_record(identity,{'failure_stage':'infrastructure','error':message,'tests':[],'passed':False},None,'infrastructure')['id']
            save(current)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--first',action='store_true')
    parser.add_argument('--task-id', choices=tuple(TASK_SPECS), help='task to queue with --first')
    parser.add_argument('--request-limit', type=int, help='cumulative model-request cap; overrides BENCH_CUMULATIVE_REQUEST_LIMIT')
    parser.add_argument('--resume-run')
    options=parser.parse_args()
    with (DATA/'worker.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Interrupted records are never silently resubmitted to a paid API.
        for item in rows('runs'):
            if item['mode']=='live' and item.get('worker_id') in (None,'legacy') and item['status'] in ('preparing','running','collecting','evaluating'):
                event(item['id'],'interrupted','Worker 重启；保留会话，不自动重新调用模型')
        request_limit = cumulative_request_limit(options.request_limit)
        if options.first:
            task_id = options.task_id or 'occt_boolean_single_544'
            task=next(t for t in rows('tasks') if t['id']==task_id)
            agent=dict(id='dsh-flash-v1',name='DSH · DeepSeek V4.1 Flash',adapter='dsh',model=MODEL,timeout_minutes=30)
            with db() as conn:
                conn.execute('INSERT OR IGNORE INTO agents VALUES (?,?)',(agent['id'],json.dumps(agent)))
            run=begin(task,agent,f'{task_id} 真实执行：独立 bwrap 沙箱与专用模型网关')
            run['cumulative_request_limit'] = request_limit
            save(run)
            event(run['id'],'queued','真实任务已入队')
            print('RUN_ID='+run['id'],flush=True)
        if options.resume_run:
            parent=get_run(options.resume_run)
            if parent.get('task',{}).get('version')!='proto-1':
                raise ValueError('Catalog task recovery is disabled until inspect-first resume is implemented')
            if parent['status'] not in ('failed','timed_out','interrupted') or not parent.get('session_id'):
                raise ValueError('Only an ended persisted DSH session can be resumed')
            prior = 0
            ancestor = parent
            seen = set()
            while ancestor:
                if ancestor['id'] in seen:
                    raise ValueError('Cyclic run ancestry')
                seen.add(ancestor['id'])
                audit_path = DATA/'runs'/ancestor['id']/'gateway-audit.json'
                ancestor_audit=json.loads(audit_path.read_text())
                prior += gateway_forwarded_request_count(ancestor_audit)
                ancestor = get_run(ancestor['parent_run_id']) if ancestor.get('parent_run_id') else None
            if prior >= request_limit:
                raise ValueError(f'Configured cumulative {request_limit} request limit exhausted')
            agent=dict(id='dsh-flash-v1',name='DSH · DeepSeek V4.1 Flash',adapter='dsh',model=MODEL,timeout_minutes=30)
            with db() as conn:
                conn.execute('INSERT OR IGNORE INTO agents VALUES (?,?)',(agent['id'],json.dumps(agent)))
            resumed=begin(parent['task'],agent,f'累计请求上限 {request_limit}；切换 V4.1 Flash 后恢复原会话与构建工作区')
            parent_audit_path=DATA/'runs'/parent['id']/'gateway-audit.json'
            parent_audit=json.loads(parent_audit_path.read_text())
            parent_gateway_failure=classify_gateway_failure(
                parent_audit,
                request_limit=(parent.get('provenance') or {}).get('gateway_requests'),
                agent_outcome=parent.get('agent_outcome'))
            resumed.update(parent_run_id=parent['id'],resumed_session_id=parent['session_id'],
                prior_request_count=prior,cumulative_request_limit=request_limit,
                parent_gateway_failure=parent_gateway_failure,
                model_switch={'from':parent['agent']['model'],'to':MODEL})
            save(resumed)
            event(resumed['id'],'queued','恢复实验入队；独立记录追加预算')
            print('RUN_ID='+resumed['id'],flush=True)
        while True:
            heartbeat('idle')
            item=claim()
            if item:
                run_task(item, request_limit)
                if item.get('experiment_id'):
                    from .plan1a import finalize
                    try:
                        finalize(item['experiment_id'],lambda: (heartbeat('combination',None) or False))
                    except Exception as exc:
                        print('ASSET_FINALIZE_ERROR='+type(exc).__name__+': '+str(exc),flush=True)
            if options.once:
                break
            time.sleep(2)
        heartbeat('stopped')

if __name__=='__main__':
    main()
