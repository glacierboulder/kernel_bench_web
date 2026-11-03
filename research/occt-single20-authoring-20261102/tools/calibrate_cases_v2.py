"""Execute reviewed DRAW cases in isolation using the shared strict oracle."""
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


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--build-job', required=True)
    parser.add_argument('--issue', required=True)
    parser.add_argument('--case-plan', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    framework = root / 'framework'
    os.environ['BENCH_CONFIG'] = '/home/lzy/cad-bench-experiment/config.json'
    sys.path.insert(0, str(framework))
    from backend.source_cache import tree_sha256
    from backend.sandbox import command, limits, monitor
    from backend.runtime.assertion_oracle import validate_base_result, completed_failure_status

    with (root / 'compiler.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        build_job = root / 'jobs' / args.build_job
        build_receipt = json.loads((build_job / 'receipt.json').read_text())
        if build_receipt.get('status') != 'built':
            raise ValueError('selected build is not ready')
        if tree_sha256(build_job / 'source') != build_receipt['source_tree_sha256']:
            raise ValueError('selected source changed')
        for name, expected in build_receipt['libraries'].items():
            if sha256(build_job / 'build' / name) != expected:
                raise ValueError('compiled library identity changed')
        work = root / 'jobs' / args.label
        work.mkdir(parents=True, exist_ok=False)
        shutil.copytree(root / 'incoming/single20', work / 'cases')
        plan = json.loads(args.case_plan.read_text())
        results = {}
        shutil.copy2(args.case_plan, work / 'case-plan.json')
        shutil.copy2(__file__, work / 'worker.py')
        for checkpoint in plan['cases']:
            case = work / 'cases' / checkpoint['script']
            expected_ids = checkpoint['expected_assertion_ids']
            folder = work / case.stem
            folder.mkdir()
            local = folder / 'cases'
            shutil.copytree(work / 'cases', local)
            local_case = local / ('occt-' + args.issue) / '1' / case.name
            env = {'BENCH_TOOLCHAIN_NAME': 'clang-o0', 'CASROOT': '/occt-source',
                   'BENCH_EXTRA_LIBRARY_PATH': '/home/lzy/cad-bench-experiment/runtime/py311/lib',
                   'BENCH_TCL_LIBRARY_DIR': '/home/lzy/cad-bench-experiment/runtime/py311/lib'}
            argv = command(folder, mounts=[(build_job / 'source', '/occt-source', False),
                                           (build_job / 'build', '/occt-build', False),
                                           (framework / 'backend/runtime/public_draw.py', '/public_draw.py', False)], env=env)
            argv += [sys.executable, '/public_draw.py', '--build-dir', '/occt-build',
                     '--resource-dir', '/occt-source/src', '--case-dir', '/workspace/cases/occt-' + args.issue + '/1',
                     '--script', case.name, '--timeout-seconds', '90', '--cpu-limit-seconds', '90', '--address-space-gib', '4']
            with (folder / 'runner.log').open('w') as log:
                process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True, preexec_fn=limits)
                code = monitor(process, 110, disk_root=folder)
            try:
                base = json.loads((folder / 'runner.log').read_text())
                result = validate_base_result(base, {'expected_assertion_ids': expected_ids, 'expected_failure_lines': []})
                result['status'] = completed_failure_status(result)
            except (ValueError, KeyError) as exc:
                result = {'status': 'runner_error', 'passed': False, 'error': str(exc)}
            result.update(case=case.name, runner_process_code=code, case_sha256=sha256(local_case),
                          log_sha256=sha256(folder / 'runner.log'))
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            results[case.stem] = {'status': result['status'], 'passed': result['passed']}
            print(case.stem, results[case.stem], flush=True)
        record = {'label': args.label, 'model_called': False, 'source_commit': build_receipt['source_commit'],
                  'source_tree_sha256': build_receipt['source_tree_sha256'], 'build_receipt_sha256': sha256(build_job / 'receipt.json'),
                  'results': results, 'finished_at': datetime.now(timezone.utc).isoformat()}
        (work / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
