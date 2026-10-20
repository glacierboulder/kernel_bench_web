"""Plan 1B protocol, output intake, independent review, and evidence promotion."""
import hashlib
import io
import json
import os
import secrets
import shutil
import stat
import subprocess
import time
import zipfile
from pathlib import Path, PurePosixPath

from .app import DATA, db, now, rows
from .study import digest, put, snapshot_files

MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_ARCHIVE_FILES = 5000
MAX_ARCHIVE_EXPANDED = 250 * 1024 * 1024
OUTPUT_ROOTS = {'generators', 'cases', 'new_tests', 'new-tests'}
OUTPUT_FILES = {'exploration_report.md', 'report.md', 'findings.jsonl', 'patch.diff', 'knowledge_candidates.json', 'agent.jsonl', 'run-metadata.json'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _save(table, item):
    with db() as conn:
        conn.execute('INSERT INTO ' + table + ' VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                     (item['id'], json.dumps(item, ensure_ascii=False)))
    return item


def _get(table, identity):
    with db() as conn:
        row = conn.execute('SELECT payload FROM ' + table + ' WHERE id=?', (identity,)).fetchone()
    return json.loads(row['payload']) if row else None


def _asset(identity, kind=None):
    value = next((a for a in rows('assets') if a.get('id') == identity), None)
    if not value or (kind and value.get('kind') != kind):
        raise ValueError('指定的资产不存在或类型不匹配')
    return value


def _asset_root(identity):
    root = (DATA / 'assets' / identity).resolve()
    if not root.is_relative_to((DATA / 'assets').resolve()) or root.is_symlink() or not root.is_dir():
        raise ValueError('资产目录不可用')
    return root


def _verified_kernel(asset):
    if asset.get('kind') != 'kernel' or asset.get('status') != 'verified':
        raise ValueError('Plan 1B 需要所选题组独立验证通过并冻结的 K1')
    root = _asset_root(asset['id'])
    if not (root / 'kernel').is_dir() or snapshot_files(root / 'kernel') != asset.get('source_tree_sha256'):
        raise ValueError('K1 内容与冻结清单不匹配')
    if not asset.get('evaluation_id'):
        raise ValueError('K1 缺少独立评测记录')
    return root


def _b0_source_files(source):
    source = Path(source)
    exact = ('README.md', 'task.json', 'tools/build.sh', 'tools/run_draw_case.py')
    paths = [source / name for name in exact]
    visible = source / 'visible'
    if visible.is_dir():
        for parent, dirs, files in os.walk(visible, followlinks=False):
            if any((Path(parent) / name).is_symlink() for name in dirs + files):
                raise ValueError('B0 公开材料中存在符号链接')
            paths.extend(Path(parent) / name for name in files)
    result = {}
    for path in paths:
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('B0 公开材料包含非普通文件或越界路径')
        result[path.relative_to(source).as_posix()] = path
    return result


def _b0_manifest(kernel, kernel_root):
    from .app import ROOT
    visible = []
    public_files = []
    for run_id in kernel.get('source_runs', []):
        run = next((r for r in rows('runs') if r.get('id') == run_id), None)
        if not run:
            raise ValueError('K1 来源运行记录缺失，无法冻结 B0')
        issues = [i.get('id') for i in run.get('task', {}).get('issues', [])]
        source = DATA / 'runs' / run_id / 'frozen-task'
        if not source.is_dir():
            raise ValueError('K1 来源运行缺少冻结公开测试材料，无法形成 B0')
        visible.append({'source_run_id': run_id, 'task_id': run['task']['id'], 'task_version': run['task']['version'], 'known_issue_ids': issues})
        files = []
        for relative, path in sorted(_b0_source_files(source).items()):
            target_name = f"suites/{run['task']['id']}/{relative}"
            files.append({'path': target_name, 'sha256': digest(path)})
            public_files.append({'source_run_id': run_id, **files[-1]})
        if not any(item['path'].endswith('/visible/issue.md') or '/visible/' in item['path'] for item in files):
            raise ValueError('K1 来源运行没有可冻结的公开 B0 案例')
    evaluator = ROOT / 'backend' / 'eval_driver.py'
    regression = ROOT / 'config' / 'regressions' / 'analytic_boxes' / 'reproduce.cpp'
    return {
        'id': 'occt-boolean-b0-v1',
        'kernel_id': kernel['id'],
        'kernel_tree_sha256': kernel['source_tree_sha256'],
        'known_issue_suites': visible,
        'public_files': public_files,
        'regression': {'id': 'analytic_boxes', 'path': 'regressions/analytic_boxes/reproduce.cpp', 'sha256': digest(regression)},
        'evaluator': {'id': 'plan1a-visible-suite-runner', 'sha256': digest(evaluator)},
        'scope': 'K1 来源中的已验证公开复现与解析 Boolean 回归；不代表完整 OCCT 上游测试。',
        'hidden_checks_in_agent_input': False,
    }


def _verify_frozen_inputs(experiment):
    kernel = _asset(experiment['kernel']['id'], 'kernel')
    root = _verified_kernel(kernel)
    if kernel.get('source_tree_sha256') != experiment['kernel']['source_tree_sha256']:
        raise ValueError('Plan 1B 批次引用的 K1 已变化')
    b0_root = DATA / 'explorations' / experiment['id'] / 'B0'
    manifest_path = b0_root / 'manifest.json'
    try:
        manifest_hash = hashlib.sha256(_json(json.loads(manifest_path.read_text())).encode()).hexdigest() if manifest_path.is_file() else None
    except (OSError, json.JSONDecodeError):
        manifest_hash = None
    if manifest_hash != experiment.get('b0_sha256'):
        raise ValueError('B0 清单与批次冻结版本不匹配')
    expected_files = list(experiment['b0'].get('public_files', []))
    expected_files.append({'path': experiment['b0']['regression']['path'], 'sha256': experiment['b0']['regression']['sha256']})
    for entry in expected_files:
        relative = _safe_rel(entry['path'])
        path = b0_root.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file() or digest(path) != entry['sha256']:
            raise ValueError('B0 文件与冻结版本不匹配：' + relative)
    if experiment.get('knowledge'):
        knowledge = _asset(experiment['knowledge']['id'], 'knowledge')
        path = _asset_root(knowledge['id']) / 'knowledge.json'
        if (knowledge.get('kernel_id') != kernel['id'] or knowledge.get('knowledge_sha256') != experiment['knowledge']['sha256']
                or not path.is_file() or digest(path) != experiment['knowledge']['sha256']):
            raise ValueError('M0 文件与批次冻结版本不匹配')
    return root


def _verify_candidate_files(finding):
    candidate = finding['candidate']
    folder = DATA / 'explorations' / finding['exploration_id'] / 'runs' / finding['exploration_run_id'] / 'submission'
    for path_key, hash_key in (('input_path', 'input_sha256'), ('generator_path', 'generator_sha256')):
        relative = _safe_rel(candidate[path_key])
        path = folder.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file() or digest(path) != candidate[hash_key]:
            raise ValueError('候选文件与提交时哈希不匹配：' + relative)


def _freeze_b0(kernel, identity):
    root = DATA / 'explorations' / identity
    b0_root = root / 'B0'
    b0_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for run_id in kernel.get('source_runs', []):
        source = DATA / 'runs' / run_id / 'frozen-task'
        run = next(r for r in rows('runs') if r['id'] == run_id)
        prefix = f"suites/{run['task']['id']}/"
        for relative, path in _b0_source_files(source).items():
            target = b0_root / prefix / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(path.read_bytes())
    from .app import ROOT
    regression = ROOT / 'config' / 'regressions' / 'analytic_boxes' / 'reproduce.cpp'
    target = b0_root / 'regressions' / 'analytic_boxes' / 'reproduce.cpp'
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_bytes(regression.read_bytes())
    return b0_root


def _prompt(run, experiment):
    m0_line = ('\n- 已知修复知识：`M0/knowledge.json`（只在本臂提供）' if run['arm'] == 'with_m0'
               else '\n- 已知修复知识：本臂不提供 M0。')
    return f'''# Plan 1B 主动探索任务

本次运行：`{run['id']}`；对照臂：`{run['arm']}`；独立重复：{run['repeat']}。

## 输入

- 工作源码是冻结的 K1：SHA256 `{experiment['kernel']['source_tree_sha256']}`；执行器将其作为唯一可修改的源码树挂载到 `/workspace/repo`。
- 初始回归集是 B0：`B0/manifest.json` 及清单列出的公开案例和解析 Boolean 回归。
- 模块说明：OCCT Boolean 几何运算；实现范围以冻结源码 `repo/src/MODULES.cmake` 和相关源文件为准。
- 运行入口：`B0/suites/<task-id>/tools/build.sh`、`run_draw_case.py`；最多两个编译任务。
{m0_line}
- 本轮不提供新目标 issue、隐藏目标细节、参考补丁或隐藏评分反馈。

## 任务

利用可见输入提出风险假设，编写生成器或变异脚本，保存种子、参数、输入和重放命令。新候选须在未修改的 K1 上符合输入契约、稳定重放，并由明确的 oracle 证明期望与实际行为不符。按根因合并重复候选；在报告中分别标记新问题、已知问题的邻域扩展或暂不能判断。可继续尝试修复，并检查新反例、邻域和全部 B0。预算为 {experiment['wall_seconds']} 秒、最多 {experiment['request_limit']} 个模型请求、至多 {run.get('continuation_limit', 1)} 次有限续接；续接沿用同一 DSH 会话、工作区、累计请求上限及壁钟预算。构建、探索和验证都计入运行预算。

## 提交格式

在工作区根目录提交：

- `exploration_report.md`：搜索范围、风险假设、命令/工具、结果、局限和成本。
- `findings.jsonl`：每行一个候选，字段见 `output-schema.json`；没有候选时提交空文件。
- `generators/` 和 `cases/`：生成/变异脚本，以及候选输入和重放所需元数据。
- `patch.diff`：可选，基于 K1 的统一源码补丁。
- `new_tests/`：可选，提交建议加入 B1 的测试和重放说明。
- `knowledge_candidates.json`：可选，带证据引用、适用范围和限制的新知识。
- `run-metadata.json`：可选，记录实际耗时、请求/token 数、成本、模型和运行时版本。

不要把生成数量或自述的根因当作发现成功。平台会独立检查输入契约、至少三次重放、oracle 和根因去重；补丁还需在干净 K1 上检查新反例、邻域和全部 B0。未确认候选保持待核验，未修复问题保持 open。
'''


def state_snapshot():
    experiments = rows('explorations')
    runs = rows('exploration_runs')
    findings = rows('findings')
    return {
        'experiments': [exploration_summary(e, runs, findings) for e in experiments],
        'runs': runs,
        'findings': findings,
        'worker': worker_status(),
    }


def worker_status():
    paths=list((DATA/'plan1b-workers').glob('*.json'))
    legacy=DATA/'plan1b-worker-status.json'
    if not paths:paths=[legacy]
    workers=[]
    for path in paths:
        try:
            value=json.loads(path.read_text())
            if value.get('status') in ('idle','busy','waiting_for_existing_workers') and time.time()-float(value.get('at',0))<=10:workers.append(value)
        except (OSError,ValueError,json.JSONDecodeError):pass
    status='busy' if any(w['status']=='busy' for w in workers) else 'waiting_for_existing_workers' if any(w['status']=='waiting_for_existing_workers' for w in workers) else 'idle' if workers else 'offline'
    return {'online':bool(workers),'status':status,'worker_count':len(workers),'workers':workers}


def exploration_summary(experiment, runs=None, findings=None):
    runs = rows('exploration_runs') if runs is None else runs
    findings = rows('findings') if findings is None else findings
    related_runs = [r for r in runs if r.get('exploration_id') == experiment['id']]
    related_findings = [f for f in findings if f.get('exploration_id') == experiment['id']]
    arms = []
    for arm in ('without_m0', 'with_m0'):
        selected = [r for r in related_runs if r['arm'] == arm]
        confirmed_findings = [f for f in related_findings if f.get('arm') == arm and f.get('review', {}).get('status') == 'confirmed']
        arms.append({'arm': arm, 'planned': len(selected), 'submitted': sum(r.get('status', '').startswith('submitted') or r.get('status') == 'contract_failed' for r in selected),
                     'confirmed': len(confirmed_findings),
                     'new_issues': sum(f.get('review', {}).get('novelty') == 'new_issue' for f in confirmed_findings),
                     'known_neighborhoods': sum(f.get('review', {}).get('novelty') == 'known_issue_neighborhood' for f in confirmed_findings),
                     'novelty_unknown': sum(f.get('review', {}).get('novelty') == 'unknown' for f in confirmed_findings),
                     'repair_passed': sum(f.get('review', {}).get('repair_status') == 'passed' for f in related_findings if f.get('arm') == arm)})
    terminal = ('submitted', 'submitted_incomplete', 'submitted_with_contract_errors', 'contract_failed', 'failed', 'timed_out', 'cancelled', 'interrupted')
    active = ('queued', 'running', 'collecting')
    status = ('assets_promoted' if experiment.get('promotions') else
              'ended' if related_runs and all(r.get('status') in terminal for r in related_runs) else
              'running' if any(r.get('status') in active for r in related_runs) else 'prepared')
    return {**experiment, 'runs': [r['id'] for r in related_runs], 'findings': [f['id'] for f in related_findings], 'arms': arms, 'status': status}


def create_exploration(config):
    if config.get('discovery_mode') != 'open_exploration':
        raise ValueError('当前首版只支持开放探索；受控盲测需先登记独立隐藏目标包')
    kernel = _asset(config['kernel_id'], 'kernel')
    kernel_root = _verified_kernel(kernel)
    agent = next((a for a in rows('agents') if a.get('id') == config['agent_id']), None)
    if not agent:
        raise ValueError('Agent 配置不存在')
    from .dsh_config import MODEL, output_token_limit
    if agent.get('adapter') != 'dsh' or agent.get('model') not in ('', MODEL):
        raise ValueError('当前 Plan 1B 首轮只支持 DSH / DeepSeek V4.1 Flash')
    agent_snapshot = {**agent, 'model': MODEL}
    knowledge = None
    if config.get('knowledge_id'):
        knowledge = _asset(config['knowledge_id'], 'knowledge')
        if knowledge.get('kernel_id') != kernel['id'] or knowledge.get('status') not in ('evidence_linked', 'verified'):
            raise ValueError('M0 必须来自同一冻结 K1 的 Plan 1A 成功轨迹')
        knowledge_path = _asset_root(knowledge['id']) / 'knowledge.json'
        if not knowledge_path.is_file() or digest(knowledge_path) != knowledge.get('knowledge_sha256'):
            raise ValueError('M0 内容与冻结清单不匹配')
    else:
        raise ValueError('有/无 M0 对照必须指定一个与 K1 对应的 M0 资产')
    from .app import ROOT
    identity = secrets.token_hex(8)
    b0 = _b0_manifest(kernel, kernel_root)
    b0_root = _freeze_b0(kernel, identity)
    record = {
        'id': identity, 'created_at': now(), 'title': config['name'], 'phase': '1B',
        'discovery_mode': 'open_exploration',
        'kernel': {'id': kernel['id'], 'source_tree_sha256': kernel['source_tree_sha256'], 'evaluation_id': kernel['evaluation_id']},
        'b0': b0, 'b0_sha256': hashlib.sha256(_json(b0).encode()).hexdigest(),
        'knowledge': ({'id': knowledge['id'], 'sha256': knowledge['knowledge_sha256']} if knowledge else None),
        'agent': agent_snapshot, 'repeats_per_arm': config['repeats_per_arm'],
        'request_limit': config['request_limit'], 'wall_seconds': config['wall_seconds'], 'continuation_limit': 1,
        'max_output_tokens': output_token_limit(os.environ.get('BENCH_PLAN1B_MAX_OUTPUT_TOKENS', '8192')), 'compile_slots': 2,
        'prompt_version': 'plan1b-open-exploration-v1', 'output_schema_version': 'plan1b-findings-v1',
        'input_policy': 'same K1 and B0; M0 only in with_m0 arm; no new target issue, hidden target details, reference patch, or hidden score',
        'evaluator': {'source_sha256': digest(ROOT / 'backend' / 'eval_driver.py'), 'review_protocol': 'contract + 3 deterministic replays + independent oracle + root-cause dedup; patch: clean K1 + case + neighborhood + B0'},
        'created_assets': [],
    }
    _save('explorations', record)
    out_dir = DATA / 'explorations' / identity
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    (b0_root / 'manifest.json').write_text(json.dumps(b0, ensure_ascii=False, indent=2))
    (out_dir / 'manifest.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    for repeat in range(1, config['repeats_per_arm'] + 1):
        for arm in ('without_m0', 'with_m0'):
            run_id = secrets.token_hex(8)
            run = {'id': run_id, 'exploration_id': identity, 'created_at': now(), 'arm': arm, 'repeat': repeat,
                   'status': 'prepared', 'agent': agent_snapshot, 'kernel_id': kernel['id'], 'kernel_sha256': kernel['source_tree_sha256'],
                   'b0_id': b0['id'], 'b0_sha256': hashlib.sha256(_json(b0).encode()).hexdigest(),
                   'm0_id': knowledge['id'] if knowledge and arm == 'with_m0' else None,
                   'request_limit': config['request_limit'], 'wall_seconds': config['wall_seconds'], 'compile_slots': 2,
                   'continuation_limit': 1,
                   'max_output_tokens': record['max_output_tokens'], 'artifacts': [], 'finding_ids': []}
            if run['m0_id'] is None:
                run.pop('m0_id')
            _save('exploration_runs', run)
            (out_dir / 'runs' / run_id).mkdir(parents=True, exist_ok=True, mode=0o700)
    return exploration_detail(identity)


def exploration_detail(identity):
    item = _get('explorations', identity)
    if not item:
        raise ValueError('Plan 1B 批次不存在')
    summary = exploration_summary(item)
    summary['run_records'] = [r for r in rows('exploration_runs') if r.get('exploration_id') == identity]
    summary['finding_records'] = [f for f in rows('findings') if f.get('exploration_id') == identity]
    return summary


def queue_exploration(identity):
    if not worker_status().get('online'):
        raise ValueError('Plan 1B 独立 worker 未在线；先启动 backend.plan1b_worker')
    experiment = _get('explorations', identity)
    if not experiment:
        raise ValueError('Plan 1B 批次不存在')
    if experiment.get('execution_started_at'):
        raise ValueError('该批次已启动，不能重复排队')
    _verify_frozen_inputs(experiment)
    runs = [r for r in rows('exploration_runs') if r.get('exploration_id') == identity]
    if not runs or any(r.get('status') != 'prepared' for r in runs):
        raise ValueError('只有全部运行槽位均为 prepared 的批次可以启动')
    for run in runs:
        run.update(status='queued', queued_at=now(), events=[{'at': now(), 'stage': 'queued', 'message': '等待 Plan 1B 专用 worker'}])
        _save('exploration_runs', run)
    experiment['execution_started_at'] = now()
    _save('explorations', experiment)
    (DATA / 'explorations' / identity / 'manifest.json').write_text(json.dumps(experiment, ensure_ascii=False, indent=2))
    return exploration_detail(identity)


def cancel_exploration_run(identity, run_id):
    run = _get('exploration_runs', run_id)
    if not run or run.get('exploration_id') != identity:
        raise ValueError('Plan 1B 运行不存在')
    if run.get('status') not in ('queued', 'running', 'collecting'):
        raise ValueError('Plan 1B 运行当前无法取消')
    run['cancel_requested'] = True
    if run['status'] == 'queued':
        run['status'] = 'cancelled'
    run.setdefault('events', []).append({'at': now(), 'stage': run['status'], 'message': '收到取消请求'})
    _save('exploration_runs', run)
    return run


def input_bundle(identity, run_id):
    experiment = _get('explorations', identity)
    run = _get('exploration_runs', run_id)
    if not experiment or not run or run.get('exploration_id') != identity:
        raise ValueError('Plan 1B 运行不存在')
    _verify_frozen_inputs(experiment)
    protocol = {'protocol': 'plan1b-input-v1', 'exploration_id': identity, 'run_id': run_id,
                'arm': run['arm'], 'repeat': run['repeat'], 'kernel': experiment['kernel'], 'b0': experiment['b0'],
                'agent': experiment['agent'], 'budget': {'request_limit': run['request_limit'], 'wall_seconds': run['wall_seconds'],
                'max_output_tokens': run['max_output_tokens'], 'compile_slots': run['compile_slots'],
                'continuations': run.get('continuation_limit', 1)},
                'discovery_mode': experiment['discovery_mode'], 'input_policy': experiment['input_policy'],
                'module_spec': {'kernel': 'Open CASCADE Technology', 'area': 'Boolean geometry operations',
                                'module_index': 'K1/src/MODULES.cmake', 'inspect_scope': 'derive exact implementation scope from the frozen K1 source'},
                'tool_entry': {'build': 'B0/suites/<task-id>/tools/build.sh', 'replay': 'B0/suites/<task-id>/tools/run_draw_case.py',
                               'compile_jobs': run['compile_slots']}}
    if run['arm'] == 'with_m0':
        protocol['knowledge'] = experiment['knowledge']
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('execution_protocol.json', json.dumps(protocol, ensure_ascii=False, indent=2))
        b0_root = DATA / 'explorations' / identity / 'B0'
        for path in sorted(b0_root.rglob('*')):
            if path.is_file() and not path.is_symlink():
                zf.write(path, 'B0/' + path.relative_to(b0_root).as_posix())
        zf.writestr('agent_prompt.md', _prompt(run, experiment))
        zf.writestr('output-schema.json', json.dumps({
            'schema': 'plan1b-findings-v1', 'format': 'JSON Lines; one JSON object per candidate',
            'required': {'candidate_id': 'unique string', 'k1_sha256': 'must equal frozen K1 hash',
                         'input_path': 'relative path under cases/', 'input_sha256': 'SHA256 of input file',
                         'generator_path': 'relative path under generators/', 'generator_sha256': 'SHA256 of generator file',
                         'seed': 'string or number', 'parameters': 'object', 'repro_command': 'string',
                         'expected': 'description/object', 'actual': 'description/object', 'oracle': 'independent criterion',
                         'applicability': 'input contract and range'},
            'optional': {'knownness': ['new_issue', 'known_issue_neighborhood', 'unknown'],
                         'known_issue_reference': 'known issue/root-cause reference when applicable'},
                         'other_outputs': ['exploration_report.md', 'generators/', 'cases/', 'patch.diff (optional)',
                              'new_tests/ (optional)', 'knowledge_candidates.json (optional)', 'run-metadata.json (optional: duration, requests, tokens, cost, model/runtime)'],
            'knowledge_candidates_schema': {'required': ['candidate_id', 'claim', 'evidence_candidate_ids', 'scope', 'limitations']},
        }, ensure_ascii=False, indent=2))
        if run['arm'] == 'with_m0':
            knowledge = _asset(run['m0_id'], 'knowledge')
            source = _asset_root(knowledge['id']) / 'knowledge.json'
            zf.write(source, 'M0/knowledge.json')
    return archive.getvalue(), f'plan1b-{identity}-{run_id}.zip'


def _safe_rel(raw):
    if not isinstance(raw, str) or not raw or '\\' in raw or '\x00' in raw:
        raise ValueError('候选引用路径必须是非空 POSIX 相对路径')
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ('', '.', '..') for part in path.parts):
        raise ValueError('候选引用路径越界')
    return path.as_posix()


def _archive_extract(run_folder, payload):
    if not payload or len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError('输出包为空或超过 250 MiB 限制')
    entries = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError('输出包文件数超过限制')
        for info in infos:
            name = info.filename.rstrip('/')
            if not name:
                continue
            rel = _safe_rel(name)
            mode = info.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if stat.S_ISLNK(mode) or file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('输出包不能包含符号链接或特殊文件')
            first = PurePosixPath(rel).parts[0]
            if first not in OUTPUT_ROOTS and rel not in OUTPUT_FILES:
                raise ValueError('输出包包含协议外文件：' + rel)
            if info.is_dir():
                continue
            total += info.file_size
            if total > MAX_ARCHIVE_EXPANDED:
                raise ValueError('输出包解压体积超过 250 MiB')
            if info.file_size > MAX_ARCHIVE_EXPANDED or (info.compress_size and info.file_size / info.compress_size > 250):
                raise ValueError('输出包包含异常压缩条目')
            if rel in entries:
                raise ValueError('输出包存在重复路径')
            entries[rel] = zf.read(info)
    if 'report.md' in entries:
        if 'exploration_report.md' in entries:
            raise ValueError('请只提交 exploration_report.md')
        entries['exploration_report.md'] = entries.pop('report.md')
    if 'exploration_report.md' not in entries or 'findings.jsonl' not in entries:
        raise ValueError('输出包必须含 exploration_report.md 和 findings.jsonl')
    if not entries['exploration_report.md'].strip():
        raise ValueError('exploration_report.md 不能为空')
    out = run_folder / 'submission'
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    for rel, content in entries.items():
        dest = out.joinpath(*PurePosixPath(rel).parts)
        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if dest.exists() or dest.is_symlink():
            raise ValueError('提交目录已有同名文件')
        with dest.open('xb') as f:
            f.write(content)
    return out, entries


def _validate_candidate(candidate, entries, kernel_sha):
    errors = []
    if not isinstance(candidate, dict):
        return ['每行必须是 JSON object']
    required = ('candidate_id', 'k1_sha256', 'input_path', 'input_sha256', 'generator_path', 'generator_sha256',
                'seed', 'parameters', 'repro_command', 'expected', 'actual', 'oracle', 'applicability')
    for key in required:
        if key not in candidate or candidate[key] is None or candidate[key] == '':
            errors.append(f'missing:{key}')
    if candidate.get('k1_sha256') != kernel_sha:
        errors.append('k1_sha256_mismatch')
    refs = (('input_path', 'input_sha256', 'cases/'), ('generator_path', 'generator_sha256', 'generators/'))
    for path_key, hash_key, prefix in refs:
        if path_key not in candidate:
            continue
        try:
            path = _safe_rel(candidate[path_key])
            if not path.startswith(prefix):
                errors.append(f'{path_key}_must_be_under_{prefix}')
            raw = entries.get(path)
            if raw is None:
                errors.append(f'{path_key}_not_in_submission')
            elif candidate.get(hash_key) != hashlib.sha256(raw).hexdigest():
                errors.append(f'{hash_key}_mismatch')
        except ValueError:
            errors.append(f'{path_key}_invalid')
    if not isinstance(candidate.get('parameters'), dict):
        errors.append('parameters_must_be_object')
    for key in ('repro_command', 'oracle', 'applicability'):
        if not isinstance(candidate.get(key), str) or not candidate.get(key).strip():
            errors.append(f'{key}_must_be_nonempty_string')
    if candidate.get('knownness') is not None and candidate.get('knownness') not in ('new_issue', 'known_issue_neighborhood', 'unknown'):
        errors.append('knownness_invalid')
    if candidate.get('knownness') == 'known_issue_neighborhood' and not str(candidate.get('known_issue_reference') or '').strip():
        errors.append('known_issue_reference_required_for_neighborhood')
    if not isinstance(candidate.get('candidate_id'), str) or not candidate.get('candidate_id').strip() or len(candidate.get('candidate_id', '')) > 100:
        errors.append('candidate_id_invalid')
    return errors


def submit_output(identity, run_id, payload, *, allow_running=False):
    experiment = _get('explorations', identity)
    run = _get('exploration_runs', run_id)
    if not experiment or not run or run.get('exploration_id') != identity:
        raise ValueError('Plan 1B 运行不存在')
    _verify_frozen_inputs(experiment)
    if run.get('status') != 'prepared' and not (allow_running and run.get('status') in ('running', 'collecting')):
        raise ValueError('该运行已提交输出，不能覆盖原始结果')
    folder = DATA / 'explorations' / identity / 'runs' / run_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive_path = folder / 'submission.zip'
    archive_path.write_bytes(payload)
    try:
        out, entries = _archive_extract(folder, payload)
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        run.update(status='contract_failed', submission_sha256=hashlib.sha256(payload).hexdigest(), contract_errors=[str(error)], submitted_at=now())
        run['artifacts'] = ['submission.zip']
        _save('exploration_runs', run)
        if isinstance(error, ValueError):
            return run
        raise ValueError('无法读取输出包')
    errors = []
    candidates = []
    seen = set()
    lines = entries['findings.jsonl'].decode('utf-8', errors='replace').splitlines()
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f'findings.jsonl:{line_no}:invalid_json:{error.msg}')
            continue
        candidate_errors = _validate_candidate(candidate, entries, experiment['kernel']['source_tree_sha256'])
        cid = candidate.get('candidate_id') if isinstance(candidate, dict) else None
        candidate_key = cid if isinstance(cid, str) else json.dumps(cid, ensure_ascii=False, sort_keys=True)
        if candidate_key in seen:
            candidate_errors.append('duplicate_candidate_id_in_submission')
        seen.add(candidate_key)
        finding = {'id': secrets.token_hex(10), 'candidate_id': cid, 'exploration_id': identity, 'exploration_run_id': run_id,
                   'arm': run['arm'], 'repeat': run['repeat'], 'candidate': candidate, 'contract_errors': candidate_errors,
                   'contract_passed': not candidate_errors, 'status': 'awaiting_independent_review' if not candidate_errors else 'contract_failed',
                   'created_at': now()}
        _save('findings', finding)
        candidates.append(finding)
    knowledge_entries = []
    if 'knowledge_candidates.json' in entries:
        try:
            knowledge = json.loads(entries['knowledge_candidates.json'].decode('utf-8'))
            if not isinstance(knowledge, list):
                errors.append('knowledge_candidates.json_must_be_array')
            else:
                known_candidate_ids = {f['candidate_id'] for f in candidates if f.get('candidate_id') and f.get('contract_passed')}
                for index, entry in enumerate(knowledge):
                    required = ('candidate_id', 'claim', 'evidence_candidate_ids', 'scope', 'limitations')
                    if not isinstance(entry, dict) or any(key not in entry for key in required):
                        errors.append(f'knowledge_candidates.json:{index + 1}:missing_required_fields')
                        continue
                    if not isinstance(entry['candidate_id'], str) or not entry['candidate_id'].strip():
                        errors.append(f'knowledge_candidates.json:{index + 1}:invalid_candidate_id')
                    if (not isinstance(entry['evidence_candidate_ids'], list) or not entry['evidence_candidate_ids']
                            or not all(isinstance(x, str) for x in entry['evidence_candidate_ids'])
                            or not set(entry['evidence_candidate_ids']).issubset(known_candidate_ids)):
                        errors.append(f'knowledge_candidates.json:{index + 1}:invalid_evidence_refs')
                    if not entry['claim'] or not entry['scope'] or not isinstance(entry['limitations'], list):
                        errors.append(f'knowledge_candidates.json:{index + 1}:invalid_claim_scope_or_limitations')
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append('knowledge_candidates.json_invalid_json')
    run_metadata = None
    if 'run-metadata.json' in entries:
        try:
            run_metadata = json.loads(entries['run-metadata.json'].decode('utf-8'))
            if not isinstance(run_metadata, dict):
                errors.append('run-metadata.json_must_be_object')
                run_metadata = None
            else:
                allowed_metadata = {'elapsed_seconds', 'request_count', 'input_tokens', 'output_tokens', 'cost', 'model', 'runtime_version', 'adapter', 'completion_reason', 'continuations', 'incomplete'}
                if set(run_metadata) - allowed_metadata:
                    errors.append('run-metadata.json:contains_unrecognized_fields')
                for key in ('elapsed_seconds', 'request_count', 'input_tokens', 'output_tokens', 'cost'):
                    if key in run_metadata and (not isinstance(run_metadata[key], (int, float)) or isinstance(run_metadata[key], bool) or run_metadata[key] < 0):
                        errors.append(f'run-metadata.json:invalid_{key}')
                if 'continuations' in run_metadata and (not isinstance(run_metadata['continuations'], int) or run_metadata['continuations'] < 0):
                    errors.append('run-metadata.json:invalid_continuations')
                if 'incomplete' in run_metadata and not isinstance(run_metadata['incomplete'], bool):
                    errors.append('run-metadata.json:invalid_incomplete')
                for key in ('model', 'runtime_version', 'adapter', 'completion_reason'):
                    if key in run_metadata and (not isinstance(run_metadata[key], str) or len(run_metadata[key]) > 300):
                        errors.append(f'run-metadata.json:invalid_{key}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append('run-metadata.json_invalid_json')
    run.update(status='submitted_with_contract_errors' if errors or any(not f['contract_passed'] for f in candidates) else 'submitted',
               submitted_at=now(), submission_sha256=hashlib.sha256(payload).hexdigest(),
               contract_errors=errors, finding_ids=[f['id'] for f in candidates], artifacts=['submission.zip', *sorted(entries)],
               artifact_hashes={name: hashlib.sha256(raw).hexdigest() for name, raw in entries.items()})
    if run_metadata is not None:
        run['actual_run_metadata'] = run_metadata
        elapsed = run_metadata.get('elapsed_seconds')
        requests = run_metadata.get('request_count')
        run['budget_overrun'] = bool((elapsed is not None and elapsed > run['wall_seconds'])
                                     or (requests is not None and requests > run['request_limit']))
    if 'patch.diff' in entries:
        run['patch_sha256'] = hashlib.sha256(entries['patch.diff']).hexdigest()
    _save('exploration_runs', run)
    return run


def output_artifact(identity, run_id, name):
    run = _get('exploration_runs', run_id)
    if not run or run.get('exploration_id') != identity or name not in run.get('artifacts', []):
        raise ValueError('运行产物不存在')
    folder = DATA / 'explorations' / identity / 'runs' / run_id
    if name == 'submission.zip':
        path = folder / name
    elif name in ('gateway-audit.json', 'agent-stderr.log'):
        path = folder / name
    else:
        rel = _safe_rel(name)
        path = folder / 'submission' / Path(*PurePosixPath(rel).parts)
        if not path.is_file() and (folder / rel).is_file():
            path = folder / rel
    root = folder.resolve()
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('运行产物不可用')
    return path


def review_finding(identity, review):
    finding = _get('findings', identity)
    if not finding:
        raise ValueError('候选发现不存在')
    experiment = _get('explorations', finding['exploration_id'])
    _verify_frozen_inputs(experiment)
    if not finding.get('contract_passed'):
        raise ValueError('输出协议不通过的候选不能确认')
    _verify_candidate_files(finding)
    if finding.get('review'):
        raise ValueError('独立评测记录已冻结，不能覆盖')
    if len(review['replays']) != 3:
        raise ValueError('必须记录三次确定性重放结果')
    if review.get('novelty') not in ('new_issue', 'known_issue_neighborhood', 'unknown'):
        raise ValueError('必须标记为新问题、已知问题邻域扩展或暂不能判断')
    if review['novelty'] == 'known_issue_neighborhood' and not str(review.get('known_issue_reference') or '').strip():
        raise ValueError('已知问题邻域扩展必须引用对应的已知问题或根因')
    if not review.get('root_cause_key', '').strip() or not any(str(x).strip() for x in review.get('evidence', [])):
        raise ValueError('必须记录根因去重键和至少一条独立评测证据')
    duplicate_ref = review.get('duplicate_of')
    duplicate_finding = next((f for f in rows('findings') if duplicate_ref and (f.get('id') == duplicate_ref or f.get('candidate_id') == duplicate_ref)), None)
    if duplicate_ref and not duplicate_finding:
        raise ValueError('重复项引用的候选不存在')
    if duplicate_finding and duplicate_finding.get('id') == identity:
        raise ValueError('候选不能重复引用自身')
    patch_result = review.get('patch')
    repair_status = 'not_attempted'
    if patch_result and patch_result.get('attempted'):
        folder = DATA / 'explorations' / finding['exploration_id'] / 'runs' / finding['exploration_run_id'] / 'submission'
        patch_path = folder / 'patch.diff'
        if not patch_path.is_file() or not patch_result.get('patch_sha256') or digest(patch_path) != patch_result['patch_sha256']:
            raise ValueError('补丁 SHA256 与提交文件不匹配')
        required = ('applied_clean', 'new_case_passed', 'neighborhood_passed', 'b0_passed')
        if (any(key not in patch_result or not isinstance(patch_result[key], bool) for key in required)
                or not patch_result.get('evidence') or not any(str(x).strip() for x in patch_result['evidence'])):
            raise ValueError('修复评测须包含干净 K1、新反例、邻域、B0 结果和证据')
        repair_status = 'passed' if all(patch_result[k] for k in required) else 'failed'
    duplicate_of = duplicate_finding['id'] if duplicate_finding else None
    if not duplicate_of:
        key = ' '.join(review['root_cause_key'].casefold().split())
        duplicate = next((f for f in rows('findings') if f['id'] != identity and f.get('exploration_id') == finding['exploration_id']
                          and f.get('review', {}).get('status') == 'confirmed'
                          and ' '.join(f['review'].get('root_cause_key', '').casefold().split()) == key), None)
        if duplicate:
            duplicate_finding = duplicate
            duplicate_of = duplicate['id']
    confirmed = (review['input_contract_passed'] and all(review['replays']) and review['oracle_violation_confirmed']
                 and not duplicate_of)
    status = 'duplicate' if duplicate_of else ('confirmed' if confirmed else 'not_confirmed')
    finding['review'] = {**review, 'duplicate_of': duplicate_of,
                         'duplicate_candidate_id': duplicate_finding.get('candidate_id') if duplicate_finding else None,
                         'status': status, 'repair_status': repair_status, 'reviewed_at': now()}
    finding['status'] = status
    _save('findings', finding)
    return finding


def _knowledge_from_run(run_id):
    run = _get('exploration_runs', run_id)
    path = DATA / 'explorations' / run['exploration_id'] / 'runs' / run_id / 'submission' / 'knowledge_candidates.json'
    if not path.is_file():
        return []
    value = json.loads(path.read_text())
    return value if isinstance(value, list) else []


def promote_assets(identity, finding_ids):
    experiment = _get('explorations', identity)
    if not experiment:
        raise ValueError('Plan 1B 批次不存在')
    _verify_frozen_inputs(experiment)
    if experiment.get('promotions'):
        return experiment['promotions']
    if len(set(finding_ids)) != len(finding_ids):
        raise ValueError('候选列表有重复项')
    selected = []
    for fid in finding_ids:
        finding = _get('findings', fid)
        if not finding or finding.get('exploration_id') != identity or finding.get('review', {}).get('status') != 'confirmed':
            raise ValueError('只能晋级本批次中经独立确认且去重的发现')
        _verify_candidate_files(finding)
        selected.append(finding)
    if not selected:
        raise ValueError('没有可晋级的确认发现')
    asset_ids = []
    b1_id = secrets.token_hex(8)
    b1_root = DATA / 'assets' / b1_id
    b1_root.mkdir(parents=True, mode=0o700)
    manifest_findings = []
    new_test_files = []
    new_test_runs = set()
    included_bytes = 0
    with zipfile.ZipFile(b1_root / 'benchmark.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        for finding in selected:
            run_id = finding['exploration_run_id']
            folder = DATA / 'explorations' / identity / 'runs' / run_id / 'submission'
            case_path = _safe_rel(finding['candidate']['input_path'])
            generator_path = _safe_rel(finding['candidate']['generator_path'])
            for rel in (case_path, generator_path):
                source_file = folder.joinpath(*PurePosixPath(rel).parts)
                included_bytes += source_file.stat().st_size
                if included_bytes > MAX_ARCHIVE_EXPANDED:
                    raise ValueError('晋级 B1 的归档内容超过 250 MiB 限制')
                zf.write(source_file, f'findings/{finding["id"]}/{rel}')
            manifest_findings.append({'finding_id': finding['id'], 'candidate_id': finding['candidate_id'], 'arm': finding['arm'],
                                      'run_id': run_id, 'candidate': finding['candidate'], 'review': finding['review']})
            if run_id not in new_test_runs:
                new_test_runs.add(run_id)
                for folder_name in ('new_tests', 'new-tests'):
                    test_root = folder / folder_name
                    if not test_root.is_dir():
                        continue
                    for parent, dirs, files in os.walk(test_root, followlinks=False):
                        if any((Path(parent) / name).is_symlink() for name in dirs + files):
                            raise ValueError('new_tests 中存在符号链接或特殊路径')
                        for filename in files:
                            source_file = Path(parent) / filename
                            rel = source_file.relative_to(folder).as_posix()
                            included_bytes += source_file.stat().st_size
                            if included_bytes > MAX_ARCHIVE_EXPANDED:
                                raise ValueError('晋级 B1 的归档内容超过 250 MiB 限制')
                            target = f'proposals/{run_id}/{rel}'
                            zf.write(source_file, target)
                            new_test_files.append({'run_id': run_id, 'path': rel, 'archive_path': target,
                                                   'sha256': digest(source_file)})
    b1 = {'id': b1_id, 'created_at': now(), 'kind': 'benchmark', 'label': 'B1 · Plan 1B 确认测试集', 'status': 'verified',
          'exploration_id': identity, 'kernel_id': experiment['kernel']['id'], 'source_findings': [f['id'] for f in selected],
          'findings': manifest_findings, 'proposed_test_files': new_test_files,
          'archive_sha256': digest(b1_root / 'benchmark.zip'), 'scope': '仅包含独立确认、输入合法且按根因去重的候选及相应新测试提案。'}
    (b1_root / 'manifest.json').write_text(json.dumps(b1, ensure_ascii=False, indent=2))
    put('assets', b1); asset_ids.append(b1_id)

    repair_runs = {}
    for finding in selected:
        if finding.get('review', {}).get('repair_status') == 'passed':
            repair_runs.setdefault(finding['exploration_run_id'], []).append(finding)
    for run_id, group in repair_runs.items():
        run = _get('exploration_runs', run_id)
        folder = DATA / 'explorations' / identity / 'runs' / run_id / 'submission'
        patch_path = folder / 'patch.diff'
        if not patch_path.is_file():
            continue
        kernel_id = secrets.token_hex(8)
        root = DATA / 'assets' / kernel_id
        root.mkdir(parents=True, mode=0o700)
        (root / 'patch.diff').write_bytes(patch_path.read_bytes())
        parent_root = _asset_root(experiment['kernel']['id'])
        source_root = root / 'kernel'
        try:
            shutil.copytree(parent_root / 'kernel', source_root, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            _validate_patch_paths(source_root, patch_path)
            checked = subprocess.run(['git', 'apply', '--check', '--whitespace=nowarn', str(patch_path.resolve())],
                                     cwd=source_root, capture_output=True, text=True, timeout=60)
            if checked.returncode:
                raise ValueError(checked.stderr[-1000:] or 'patch does not apply to frozen K1')
            applied = subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch_path.resolve())],
                                     cwd=source_root, capture_output=True, text=True, timeout=60)
            if applied.returncode:
                raise ValueError(applied.stderr[-1000:] or 'patch application failed')
            kernel_status = 'candidate'
            kernel_error = None
            tree_sha = snapshot_files(source_root)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            kernel_status = 'conflict'
            kernel_error = str(error)
            tree_sha = None
        kernel_candidate = {'id': kernel_id, 'created_at': now(), 'kind': 'kernel', 'protocol': 'plan1b-kernel-v1', 'label': 'K2 候选 · Plan 1B 修复',
                            'status': kernel_status, 'parent_kernel_id': experiment['kernel']['id'], 'source_exploration_id': identity,
                            'source_run_id': run_id, 'source_findings': [f['id'] for f in group],
                            'patch_sha256': digest(root / 'patch.diff'), 'source_tree_sha256': tree_sha, 'error': kernel_error,
                            'independent_review': [{'finding_id': f['id'], 'review': f['review']} for f in group],
                            'scope': '已根据独立评测通过记录在冻结 K1 上应用补丁；仍需平台侧组合验证后才可冻结为 K2。'}
        (root / 'manifest.json').write_text(json.dumps(kernel_candidate, ensure_ascii=False, indent=2))
        put('assets', kernel_candidate); asset_ids.append(kernel_id)

    promoted_ids = {f['id'] for f in selected}
    knowledge_entries = []
    run_ids = sorted({f['exploration_run_id'] for f in selected})
    for run_id in run_ids:
        for entry in _knowledge_from_run(run_id):
            if not isinstance(entry, dict) or not isinstance(entry.get('evidence_candidate_ids'), list):
                continue
            refs = [f['id'] for f in selected if f['candidate_id'] in entry['evidence_candidate_ids']]
            if refs and set(refs).issubset(promoted_ids):
                knowledge_entries.append({**entry, 'evidence_finding_ids': refs, 'source_run_id': run_id})
    if knowledge_entries:
        mid = secrets.token_hex(8)
        root = DATA / 'assets' / mid
        root.mkdir(parents=True, mode=0o700)
        knowledge = {'id': mid, 'created_at': now(), 'kind': 'knowledge', 'label': 'M1 · Plan 1B 经证据关联的探索知识',
                     'status': 'evidence_linked', 'parent_m0_id': experiment.get('knowledge', {}).get('id') if experiment.get('knowledge') else None,
                     'kernel_id': experiment['kernel']['id'], 'source_exploration_id': identity, 'entries': knowledge_entries,
                     'limitations': ['只关联已确认发现；知识主张仍需按条目核验适用范围。']}
        (root / 'knowledge.json').write_text(json.dumps(knowledge, ensure_ascii=False, indent=2))
        knowledge['knowledge_sha256'] = digest(root / 'knowledge.json')
        (root / 'manifest.json').write_text(json.dumps(knowledge, ensure_ascii=False, indent=2))
        put('assets', knowledge); asset_ids.append(mid)
    experiment['promotions'] = {'created_at': now(), 'asset_ids': asset_ids, 'b1_id': b1_id,
                                'confirmed_finding_ids': [f['id'] for f in selected]}
    _save('explorations', experiment)
    (DATA / 'explorations' / identity / 'manifest.json').write_text(json.dumps(experiment, ensure_ascii=False, indent=2))
    return experiment['promotions']


def _validate_patch_paths(source_root, patch_path):
    for line in patch_path.read_text(errors='strict').splitlines():
        if line.startswith('diff --git '):
            parts = line.split()
            if len(parts) != 4:
                raise ValueError('unsupported diff header')
            names = parts[2:]
        elif line.startswith(('--- ', '+++ ')):
            name = line[4:].split('\t', 1)[0]
            names = [] if name == '/dev/null' else [name]
        else:
            continue
        for name in names:
            name = name.removeprefix('a/').removeprefix('b/')
            path = PurePosixPath(name)
            if path.is_absolute() or any(part in ('', '.', '..') for part in path.parts) or '\\' in name:
                raise ValueError('patch contains an unsafe source path')
            target = source_root.joinpath(*path.parts)
            if not target.resolve().is_relative_to(source_root.resolve()) or any(p.is_symlink() for p in (target, *target.parents) if p != source_root.parent):
                raise ValueError('patch targets a symlink or path outside K1')
