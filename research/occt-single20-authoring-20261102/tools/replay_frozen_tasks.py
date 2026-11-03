"""Replay B/F through source cache, frozen public build, and the common adapter.

The plan selects explicit immutable build receipts. Compilation is serialized
with other authoring jobs. Warm objects are reused only for an identical source
tree, and the frozen public build command still configures and builds it.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    framework = root / 'framework'
    os.environ.update(
        BENCH_CONFIG='/home/lzy/cad-bench-experiment/config.json',
        BENCHMARK_ROOT=str(framework / 'benchmarks/occt'),
        BENCH_CACHE_DIR=str(root / 'cache'),
        BENCH_DATA_DIR=str(root / 'data'),
        BENCH_WORK_DIR=str(root / 'work'),
    )
    sys.path.insert(0, str(framework))
    from backend.catalog import public_task, validate_bundle
    from backend.evaluator import _prepare_control
    from backend.freeze import freeze_catalog_task, materialize_source, verify_snapshot
    from backend.source_cache import tree_sha256
    from backend.sandbox import command, limits, monitor
    from backend.runtime.public_build import apply_patch

    output = root / 'jobs' / args.label
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, output / 'worker.py')
    shutil.copy2(args.plan, output / 'plan.json')
    plan = json.loads(args.plan.read_text())
    bundle = validate_bundle(framework / 'benchmarks/occt')
    results = []
    with (root / 'compiler.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for selection in plan['tasks']:
            group = bundle['groups'][(selection['group_id'], '1')]
            for role, job_name in selection['build_jobs'].items():
                prior = root / 'jobs' / job_name
                receipt = json.loads((prior / 'receipt.json').read_text())
                binaries = json.loads((prior / 'binary-manifest.json').read_text())
                if receipt['status'] != 'built' or not binaries['libraries']:
                    raise ValueError('selected runtime lacks a verified build')
                if tree_sha256(prior / 'source') != receipt['source_tree_sha256']:
                    raise ValueError('runtime source changed')
                for name, expected in binaries['libraries'].items():
                    if digest(prior / 'build' / name) != expected:
                        raise ValueError('runtime binary changed')

                run = output / group['id'] / role
                manifest = freeze_catalog_task(public_task(bundle, group), run)
                snapshot = run / 'benchmark-snapshot'
                verify_snapshot(snapshot)
                suite = json.loads((snapshot / 'suite.json').read_text())
                control, _ = _prepare_control(run, None, [suite], group['kind'],
                                              group['source_id'], snapshot)
                workspace = run / 'runtime'
                workspace.mkdir()
                patch_hash = None
                reference_kind = 'locked_baseline'
                if role == 'f' and selection.get('natural_reference_source'):
                    reference = root / selection['natural_reference_source']
                    commit = receipt['source_commit']
                    tree = subprocess.check_output(
                        ['git', 'rev-parse', commit + '^{tree}'], cwd=reference, text=True).strip()
                    if tree != receipt['git_tree']:
                        raise ValueError('natural reference Git tree differs from runtime')
                    subprocess.run(['git', 'diff', '--exit-code', commit],
                                   cwd=reference, check=True, stdout=subprocess.DEVNULL)
                    source = workspace / 'source'
                    shutil.copytree(reference, source, symlinks=True,
                                    ignore=shutil.ignore_patterns('.git'))
                    reference_kind = 'natural_commit'
                else:
                    source = materialize_source(snapshot, workspace / 'source')
                if role == 'f' and selection.get('reference_patch'):
                    patch = framework / 'benchmarks/occt' / selection['reference_patch']
                    apply_patch(source, str(patch))
                    patch_hash = digest(patch)
                    reference_kind = 'patch_on_locked_baseline'
                if tree_sha256(source) != receipt['source_tree_sha256']:
                    raise ValueError('frozen baseline/reference differs from selected runtime')
                # Exact source identity was checked above. Preserve timestamps
                # from that runtime so git-archive extraction times do not force
                # unrelated translation units to compile again.
                for path in source.rglob('*'):
                    if path.is_file() and not path.is_symlink():
                        original = prior / 'source' / path.relative_to(source)
                        info = original.stat()
                        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
                shutil.copytree(prior / 'build', workspace / 'build', symlinks=True)
                environment = {
                    'BENCH_TOOLCHAIN_NAME': 'clang-o0', 'BENCH_COMPILER_JOBS': '2',
                    'BENCH_TCL_INCLUDE_DIR': '/home/lzy/cad-bench-experiment/runtime/py311/include',
                    'BENCH_TCL_LIBRARY': '/home/lzy/cad-bench-experiment/runtime/py311/lib/libtcl8.6.so',
                    'BENCH_TCL_LIBRARY_DIR': '/home/lzy/cad-bench-experiment/runtime/py311/lib',
                    'BENCH_EXTRA_LIBRARY_PATH': '/home/lzy/cad-bench-experiment/runtime/py311/lib',
                }
                argv = command(workspace, mounts=[(snapshot / 'tools', '/frozen-tools', False)],
                               env=environment)
                argv += ['bash', '/frozen-tools/build.sh', '/workspace/source', '/workspace/build']
                with (run / 'build.log').open('w') as log:
                    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                               start_new_session=True, preexec_fn=limits)
                    code = monitor(process, 3600, disk_root=workspace)
                if code != 0:
                    save(run / 'result.json', {'status': 'build_error', 'code': code})
                    raise ValueError('frozen public build failed')
                rebuilt_binaries = {
                    str(path.relative_to(workspace / 'build')): digest(path)
                    for path in (workspace / 'build').rglob('*')
                    if path.is_file() and not path.is_symlink()
                    and ('.so' in path.name or path.name.startswith('DRAWEXE'))
                }
                save(run / 'runtime-binaries.json', rebuilt_binaries)
                for checkpoint in suite['checkpoints']:
                    case_workspace = run / checkpoint['id']
                    case_workspace.mkdir()
                    shutil.copytree(control, case_workspace / 'control')
                    case_root = '/workspace/control/cases/bundle'
                    case_file = Path(case_root) / checkpoint['case']
                    env = dict(environment, CASROOT='/occt-source',
                               BENCH_FROZEN_CASE_ROOT=case_root)
                    argv = command(case_workspace, mounts=[(source, '/occt-source', False),
                                   (workspace / 'build', '/occt-build', False)], env=env)
                    argv += [sys.executable, '/workspace/control/scripts/run_draw_case.py',
                             '--build-dir', '/occt-build', '--resource-dir', '/occt-source/src',
                             '--case-dir', str(case_file.parent), '--script', case_file.name,
                             '--timeout-seconds', str(checkpoint['timeout_seconds']),
                             '--cpu-limit-seconds', str(checkpoint['timeout_seconds'])]
                    with (case_workspace / 'runner.log').open('w') as log:
                        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                                   start_new_session=True, preexec_fn=limits)
                        code = monitor(process, checkpoint['timeout_seconds'] + 30,
                                       disk_root=case_workspace)
                    oracle = json.loads((case_workspace / 'runner.log').read_text())
                    row = {'group_id': group['id'], 'role': role,
                           'checkpoint_id': checkpoint['id'], 'category': checkpoint['category'],
                           'source_commit': receipt['source_commit'],
                           'source_tree_sha256': receipt['source_tree_sha256'],
                           'reference_patch_sha256': patch_hash,
                           'reference_kind': reference_kind,
                           'snapshot_sha256': manifest['snapshot_sha256'],
                           'prebuild_binary_manifest_sha256': digest(prior / 'binary-manifest.json'),
                           'runtime_binaries_sha256': digest(run / 'runtime-binaries.json'),
                           'process_return_code': code, 'oracle': oracle}
                    save(case_workspace / 'result.json', row)
                    results.append(row)
                    print(group['id'], role, checkpoint['id'], oracle['status'], flush=True)
                if tree_sha256(source) != receipt['source_tree_sha256']:
                    raise ValueError('build or replay changed locked source')
                verify_snapshot(snapshot)
                save(run / 'verification.json', {
                    'snapshot_unchanged': True, 'source_unchanged': True,
                    'shared_public_build_exit_code': 0,
                    'build_log_sha256': digest(run / 'build.log'),
                    'runtime_binary_count': len(binaries['libraries']),
                })
    save(output / 'receipt.json', {'finished_at': datetime.now(timezone.utc).isoformat(),
                                  'model_calls': 0, 'checkpoints': results})


if __name__ == '__main__':
    main()
