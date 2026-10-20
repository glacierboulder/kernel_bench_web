"""Isolated Plan 1B DSH worker; uses its own queue and never claims Plan 1A runs."""
import argparse
import fcntl
import io
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import threading
import time
import zipfile

from . import worker as runtime
from .app import DATA, db, now, rows
from .dsh_config import MODEL, output_token_limit, patch_config
from .dsh_protocol import DshStream
from .live_status import status as live_status
from .model_gateway import Gateway
from .plan1b import _asset, _asset_root, _get, _prompt, _save, input_bundle, submit_output
from .sandbox import command, monitor, stop
from .submission import materialize, source_files
from .settings import SETTINGS
from .tool_paths import executable

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'runtime' / 'dsh'
CLI = '/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'
MAX_TURN_CONTINUATIONS = 1


def heartbeat(status, run_id=None, worker_id='plan1b'):
    directory=DATA/'plan1b-workers';directory.mkdir(exist_ok=True)
    path=directory/(worker_id+'.json')
    temporary=path.with_suffix('.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps({'worker_id':worker_id,'pid':os.getpid(),'status':status,'run_id':run_id,'at':time.time()}))
    temporary.replace(path)


def _save_run(run):
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT payload FROM exploration_runs WHERE id=?', (run['id'],)).fetchone()
        if row and json.loads(row['payload']).get('cancel_requested'):
            run['cancel_requested'] = True
        conn.execute('UPDATE exploration_runs SET payload=? WHERE id=?', (json.dumps(run, ensure_ascii=False), run['id']))


def _event(run_id, stage, message):
    run = _get('exploration_runs', run_id)
    run['status'] = stage
    run.setdefault('events', []).append({'at': now(), 'stage': stage, 'message': message})
    _save_run(run)
    return run


def claim(worker_id='plan1b'):
    # Plan 1B waits while any established worker is using the shared host.
    if live_status(DATA)['worker_status'] == 'busy':
        return None
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute("SELECT id,payload FROM exploration_runs WHERE json_extract(payload,'$.status')='queued' ORDER BY rowid LIMIT 1").fetchone()
        if not row:
            return None
        run = json.loads(row['payload'])
        run.update(status='running', worker_id=worker_id, started_at=now())
        run.setdefault('events', []).append({'at': now(), 'stage': 'running', 'message': 'Plan 1B 专用隔离 worker 已领取任务'})
        conn.execute('UPDATE exploration_runs SET payload=? WHERE id=?', (json.dumps(run, ensure_ascii=False), run['id']))
        return run


def reconcile_interrupted_runs(worker_id='plan1b'):
    for run in rows('exploration_runs'):
        if run.get('status') in ('running', 'collecting') and run.get('worker_id')==worker_id:
            run.update(status='interrupted', error='Plan 1B worker restarted; no automatic paid retry', interrupted_at=now())
            run.setdefault('events', []).append({'at': now(), 'stage': 'interrupted', 'message': 'Worker 重启；保留当前会话与产物，不自动重试模型请求'})
            _save_run(run)


def _limits(cpus, wall_seconds):
    def apply():
        os.nice(10)
        os.sched_setaffinity(0, cpus)
        cpu_limit = min(28800, max(1800, wall_seconds))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 5))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (512, 512))
        resource.setrlimit(resource.RLIMIT_AS, (32 * 1024**3,) * 2)
    return apply


def _copy_input_files(run, experiment, workspace, control, mounts):
    # Reuse the same frozen input bundle that is downloadable from the web UI.
    bundle, _ = input_bundle(experiment['id'], run['id'])
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        workspace.joinpath('execution_protocol.json').write_bytes(archive.read('execution_protocol.json'))
        workspace.joinpath('output-schema.json').write_bytes(archive.read('output-schema.json'))
        workspace.joinpath('agent_prompt.md').write_bytes(archive.read('agent_prompt.md'))
    b0_root = DATA / 'explorations' / experiment['id'] / 'B0'
    (workspace / 'B0').mkdir()
    mounts.append((b0_root, '/workspace/B0', False))
    if run['arm'] == 'with_m0':
        knowledge = _asset(run['m0_id'], 'knowledge')
        source = _asset_root(knowledge['id']) / 'knowledge.json'
        (workspace / 'M0').mkdir()
        target = workspace / 'M0' / 'knowledge.json'
        target.touch()
        mounts.append((source, '/workspace/M0/knowledge.json', False))


def _output_zip(run, experiment, workspace, root, key, parser, gateway_audit, started):
    report = workspace / 'exploration_report.md'
    findings = workspace / 'findings.jsonl'
    files = {}
    total_bytes = 0
    limit = 250 * 1024**2
    def add_file(name, path, redact=False):
        nonlocal total_bytes
        if path.is_symlink() or not path.is_file():
            return
        if total_bytes + path.stat().st_size > limit:
            raise RuntimeError('Plan 1B 输出包超过 250 MiB 限制')
        content = path.read_bytes()
        if redact:
            content = content.replace(key.encode(), b'[REDACTED]')
        total_bytes += len(content)
        if total_bytes > limit:
            raise RuntimeError('Plan 1B 输出包超过 250 MiB 限制')
        files[name] = content
    for name, path in (('exploration_report.md', report), ('findings.jsonl', findings)):
        add_file(name, path, redact=True)
    patch = root / 'materialized.patch.diff'
    try:
        materialize(_asset_root(experiment['kernel']['id']) / 'kernel', workspace / 'repo', patch)
        if patch.stat().st_size:
            add_file('patch.diff', patch)
    except (OSError, ValueError) as error:
        raise RuntimeError('无法从 agent 工作区安全生成 K1 补丁：' + str(error))
    allowed_roots = ('generators', 'cases', 'new_tests')
    for dirname in allowed_roots:
        folder = workspace / dirname
        if not folder.exists():
            continue
        collected = source_files(folder)
        for relative, path in collected.items():
            add_file(f'{dirname}/{relative}', path)
    alternate = workspace / 'new-tests'
    if alternate.exists():
        for relative, path in source_files(alternate).items():
            add_file(f'new-tests/{relative}', path)
    for name in ('knowledge_candidates.json',):
        path = workspace / name
        add_file(name, path)
    trace = root / 'agent.jsonl'
    if trace.is_file():
        add_file('agent.jsonl', trace, redact=True)
    usage = parser.usage or []
    metadata = {'elapsed_seconds': round(time.monotonic() - started, 3), 'request_count': len(gateway_audit),
                'model': MODEL, 'runtime_version': 'dsh-0.2.0-rc.2', 'adapter': 'dsh',
                'completion_reason': (parser.reason or {}).get('kind', 'unknown'),
                'continuations': run.get('continuation_count', 0), 'incomplete': bool(run.get('incomplete'))}
    if usage and all(isinstance(x, dict) for x in usage):
        for key_name in ('input_tokens', 'output_tokens'):
            counts = [x.get(key_name) for x in usage]
            if all(isinstance(x, (int, float)) for x in counts):
                metadata[key_name] = sum(counts)
    metadata_bytes = json.dumps(metadata, ensure_ascii=False, indent=2).encode()
    if total_bytes + len(metadata_bytes) > limit:
        raise RuntimeError('Plan 1B 输出包超过 250 MiB 限制')
    files['run-metadata.json'] = metadata_bytes
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return archive.getvalue()


def run_task(run, cpus):
    identity = run['id']
    root = DATA / 'explorations' / run['exploration_id'] / 'runs' / identity
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = time.monotonic()
    gateway = None
    proc = None
    gateway_audit = []
    try:
        experiment = _get('explorations', run['exploration_id'])
        if not experiment or run['agent'].get('adapter') != 'dsh' or run['agent'].get('model') != MODEL:
            raise ValueError('Plan 1B run configuration is not enabled by the trusted DSH runtime')
        key = os.environ.get('DEEPSEEK_API_KEY')
        if not key:
            raise RuntimeError('DEEPSEEK_API_KEY is unavailable to Plan 1B worker')
        kernel_root = _asset_root(experiment['kernel']['id']) / 'kernel'
        workspace = root / 'agent-workspace'
        workspace.mkdir(mode=0o700)
        (workspace / 'repo').mkdir()
        shutil.rmtree(workspace / 'repo')
        shutil.copytree(kernel_root, workspace / 'repo', ignore=shutil.ignore_patterns('.git', '__pycache__'))
        control = root / 'control'; control.mkdir(mode=0o700)
        home = root / 'dsh-home'; home.mkdir(mode=0o700)
        gateway_dir = root / 'gateway'; gateway_dir.mkdir(mode=0o700)
        (control / 'overlay.yml').write_text('')
        patch_config(control / 'overlay.yml', run['max_output_tokens'])
        shutil.copy2(ROOT / 'backend' / 'sandbox_entry.py', control / 'entry.py')
        shutil.copy2(ROOT/'backend/repro_runner.py',control/'repro_runner.py')
        mounts = [(RUNTIME, '/runtime', False), (home, '/state', True), (control, '/control', False), (gateway_dir, '/gateway', False)]
        _copy_input_files(run, experiment, workspace, control, mounts)
        tools=workspace/'tools';tools.mkdir()
        source=DATA/'explorations'/experiment['id']/'B0'/'suites'
        suite=next(source.iterdir())
        for name in ('build.sh','run_draw_case.py'):
            shutil.copy2(suite/'tools'/name,tools/name)
        build=tools/'build.sh';build.write_text(build.read_text().replace('--parallel 8','--parallel 2'))
        shutil.copy2(ROOT/'backend/repro_runner.py',tools/'run_repro.py')
        env = {'DSH_HOME': '/state', 'DEEPSEEK_API_KEY': 'gateway-placeholder-not-a-secret',
               'DEEPSEEK_BASE_URL': f'http://{SETTINGS.gateway_host}:{SETTINGS.gateway_port}/anthropic',
               'BENCH_GATEWAY_HOST': SETTINGS.gateway_host, 'BENCH_GATEWAY_PORT': str(SETTINGS.gateway_port),
               'DSH_PERMISSION_MODE': 'danger-full-access',
               'NODE_TLS_REJECT_UNAUTHORIZED': '1'}
        prompt = _prompt(run, experiment) + f"\nOnly use the provided workspace; do not use subagents. Cumulative request limit for this run: {run['request_limit']}."
        prompt += "\nUse /workspace/tools/build.sh repo build (the local copy caps compiler jobs at two). Run every custom C++ reproduction/debugger through python /control/repro_runner.py --wall 18 --cpu 15 --memory-mib 4096 -- <command>; debugging may use --wall 60 --cpu 60. Do not leave background reproductions running. The runner cleans the full process group even after its leader exits. Host fallback bounds workspace-native programs to 4 GiB address space, 3 GiB RSS, 60s CPU and 120s elapsed and kills only their subtree. A local limit is an observation to report and diagnose, not evidence by itself of a valid defect. The entire exploration budget, including builds, is shared. Deliver exploration_report.md and findings.jsonl early; an empty findings.jsonl is valid when no candidates are found. Save all candidate inputs, generator and replay commands before patching."
        (root/'runtime-protocol.json').write_text(json.dumps({'runner_sha256':__import__('hashlib').sha256((control/'repro_runner.py').read_bytes()).hexdigest(),'guard_sha256':__import__('hashlib').sha256((ROOT/'backend/repro_guard.py').read_bytes()).hexdigest(),'compile_slots':2,'cpus':sorted(cpus)},indent=2))
        max_tokens = output_token_limit(run['max_output_tokens'])
        gateway = Gateway(gateway_dir / 'api.sock', key, MODEL, max_requests=run['request_limit'], max_output_tokens=max_tokens)
        protocol_errors = []
        parser = DshStream()
        continuation_count = 0
        partial_max_tokens = False
        gateway.start()
        _event(identity, 'running', 'DSH 在独立 bubblewrap 沙箱运行；外部网络关闭，仅开放固定模型网关')
        try:
            while True:
                remaining = run['wall_seconds'] - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError('wall clock budget exceeded')
                node_binary=executable('Node.js','BENCH_NODE','node','node')
                invocation = command(workspace, mounts=mounts, env=env) + [runtime.PYTHON, '/control/entry.py', node_binary, CLI,
                    '--profile', 'headless', '--patch', '/control/overlay.yml', '--json']
                if parser.session_id:
                    invocation += ['--session-id', parser.session_id]
                invocation += ['-']
                current_prompt = prompt if continuation_count == 0 else (
                    'Continue the same task in this same session and workspace. The previous turn reached its output-token limit. '
                    'Inspect the files already written, continue the remaining work, and make sure the required report and findings '
                    'are complete. Do not discard or duplicate valid work. Keep the original safety, scope, and budget instructions.')
                stderr = (root / 'agent-stderr.log').open('a')
                try:
                    proc = subprocess.Popen(invocation, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, text=True,
                                            start_new_session=True, preexec_fn=_limits(cpus, max(1, int(remaining))))
                except Exception:
                    stderr.close()
                    raise
                proc.stdin.write(current_prompt); proc.stdin.close()

                def read_events(process=proc):
                    try:
                        with (root / 'agent.jsonl').open('a') as log:
                            for line in process.stdout:
                                safe_line = line.replace(key, '[REDACTED]')
                                log.write(safe_line); log.flush()
                                try:
                                    # Parse the same redacted bytes that are retained in the
                                    # trace, so an echoed credential can never reach run state.
                                    item = parser.feed(safe_line)
                                    record = _get('exploration_runs', identity)
                                    record['session_id'] = parser.session_id
                                    record['usage_steps'] = parser.usage
                                    record['continuation_count'] = continuation_count
                                    if item.get('type') in ('status', 'error', 'final'):
                                        record.setdefault('events', []).append({'at': now(), 'stage': 'running', 'message': json.dumps(item, ensure_ascii=False)[:3000]})
                                    _save_run(record)
                                except (ValueError, json.JSONDecodeError) as error:
                                    protocol_errors.append(type(error).__name__)
                    except OSError as error:
                        protocol_errors.append(type(error).__name__)
                reader = threading.Thread(target=read_events, daemon=True)
                reader.start()
                try:
                    def should_cancel():
                        heartbeat('busy', identity, run.get('worker_id', 'plan1b'))
                        return bool(_get('exploration_runs', identity).get('cancel_requested'))
                    code = monitor(proc, remaining, should_cancel, workspace, guard_reproductions=True)
                finally:
                    reader.join(timeout=10)
                    stderr.close()
                outcome = (parser.reason or {}).get('kind')
                can_continue = (outcome == 'max_tokens' and code == 1 and parser.final is not None
                                and parser.session_id and not parser.errors and not protocol_errors
                                and continuation_count < min(MAX_TURN_CONTINUATIONS, int(run.get('continuation_limit', 1))))
                if can_continue:
                    continuation_count += 1
                    record = _get('exploration_runs', identity)
                    record['continuation_count'] = continuation_count
                    record.setdefault('events', []).append({'at': now(), 'stage': 'running', 'message': 'DSH 达到单次输出上限；在同一会话内进行一次有界续接，共享请求和壁钟预算'})
                    _save_run(record)
                    continue
                partial_max_tokens = (outcome == 'max_tokens' and code in (0, 1) and parser.final is not None
                                      and parser.session_id and not parser.errors and not protocol_errors)
                break
        finally:
            gateway_audit = list(gateway.audit)
            (root / 'gateway-audit.json').write_text(json.dumps(gateway.audit, ensure_ascii=False, indent=2))
            gateway.close(); gateway = None
        if not parser.completed(code) and not partial_max_tokens:
            diagnostic = (root / 'agent-stderr.log').read_text(errors='replace').replace(key, '[REDACTED]')[-2000:]
            raise RuntimeError('DSH did not complete (reason=' + str((parser.reason or {}).get('kind')) + '): ' + diagnostic)
        current = _get('exploration_runs', identity)
        current.update(status='collecting', agent_returncode=code, protocol_errors=protocol_errors, agent_outcome=parser.reason,
                       continuation_count=continuation_count, incomplete=partial_max_tokens)
        _save_run(current)
        archive = _output_zip(current, experiment, workspace, root, key, parser, gateway_audit, started)
        current = _get('exploration_runs', identity)
        current.update(status='collecting', elapsed_seconds=round(time.monotonic() - started, 3), gateway_requests=len(gateway_audit))
        _save_run(current)
        submit_output(experiment['id'], identity, archive, allow_running=True)
        final = _get('exploration_runs', identity)
        if partial_max_tokens and final.get('status', '').startswith('submitted'):
            final.update(status='submitted_incomplete', incomplete_reason='max_tokens_after_bounded_continuation')
        if 'gateway-audit.json' not in final.get('artifacts', []):
            final.setdefault('artifacts', []).append('gateway-audit.json')
        final['events'] = final.get('events', []) + [{'at': now(), 'stage': final['status'], 'message': '输出包已归档并按 Plan 1B schema 检查'}]
        _save_run(final)
    except Exception as error:
        if proc and proc.poll() is None:
            stop(proc)
        if gateway:
            (root / 'gateway-audit.json').write_text(json.dumps(gateway.audit, ensure_ascii=False, indent=2))
            gateway.close()
        message = str(error)
        secret = os.environ.get('DEEPSEEK_API_KEY')
        if secret:
            message = message.replace(secret, '[REDACTED]')
        current = _get('exploration_runs', identity)
        current.update(status='cancelled' if message == 'cancelled' else 'timed_out' if isinstance(error, TimeoutError) else 'failed',
                       error=message, elapsed_seconds=round(time.monotonic() - started, 3))
        existing = current.setdefault('artifacts', [])
        for name in ('agent.jsonl', 'gateway-audit.json'):
            if (root / name).is_file() and name not in existing:
                existing.append(name)
        _save_run(current)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker-id', default='plan1b')
    parser.add_argument('--cpus', required=True, help='Two allowed logical CPUs disjoint from active workers, e.g. 2,3')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    cpus = {int(value) for value in args.cpus.split(',')}
    if len(cpus) != 2 or not cpus <= os.sched_getaffinity(0):
        parser.error('--cpus must contain exactly two allowed CPUs')
    if not args.worker_id.replace('-', '').replace('_', '').isalnum() or len(args.worker_id) > 40:
        parser.error('invalid worker id')
    lock_dir=DATA/'plan1b-workers';lock_dir.mkdir(exist_ok=True)
    lock_path=lock_dir/(args.worker_id+'.lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.sched_setaffinity(0, cpus)
        try:
            reconcile_interrupted_runs(args.worker_id)
            while True:
                if live_status(DATA)['worker_status'] == 'busy':
                    heartbeat('waiting_for_existing_workers', worker_id=args.worker_id)
                    run = None
                else:
                    heartbeat('idle', worker_id=args.worker_id)
                    run = claim(args.worker_id)
                if run:
                    run['worker_id'] = args.worker_id
                    _save_run(run)
                    heartbeat('busy', run['id'], args.worker_id)
                    run_task(run, cpus)
                if args.once:
                    break
                time.sleep(2)
        finally:
            heartbeat('stopped', worker_id=args.worker_id)


if __name__ == '__main__':
    main()
