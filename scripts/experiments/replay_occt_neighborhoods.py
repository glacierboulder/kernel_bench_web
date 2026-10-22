"""Replay admitted neighborhoods through frozen supervisor materials.

Run in the project's conda environment. --runtimes is a local JSON mapping
group IDs to build_dir, resource_dir and optional toolchain (clang or gcc).
No compilation, network access or model calls occur.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.catalog import public_task, validate_bundle
from backend.evaluator import _prepare_control
from backend.freeze import freeze_catalog_task, verify_snapshot
from backend.settings import SETTINGS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtimes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    runtimes = json.loads(args.runtimes.read_text())
    bundle = validate_bundle(SETTINGS.benchmark_root)
    coverage = json.loads((bundle['root'] / 'evaluation/provenance/neighborhood-v2-coverage.json').read_text())
    results = []
    for row in coverage['groups']:
        group = bundle['groups'][(row['group_id'], row['group_version'])]
        runtime = runtimes[group['id']]
        run_root = args.output / group['id']
        manifest = freeze_catalog_task(public_task(bundle, group), run_root)
        snapshot = run_root / 'benchmark-snapshot'
        verify_snapshot(snapshot)
        suite = json.loads((snapshot / 'suite.json').read_text())
        control, _ = _prepare_control(run_root, None, [suite], group['kind'], group['source_id'], snapshot)
        case_root = control / 'cases/bundle'
        selected = {r['checkpoint']['id'] for r in row['checkpoints']}
        if not selected or len(selected) != len(row['checkpoints']):
            raise ValueError('coverage must select unique nonempty checkpoints per group')
        if not selected <= {cp['id'] for cp in suite['checkpoints']}:
            raise ValueError('coverage selects checkpoints absent from the frozen suite')
        executed = set()
        for checkpoint in suite['checkpoints']:
            if checkpoint['id'] not in selected:
                continue
            target = case_root / checkpoint['case']
            timeout = checkpoint.get('runner_options', {}).get('case_timeout_seconds', checkpoint['timeout_seconds'])
            command = [sys.executable, str(control / 'scripts/run_draw_case.py'),
                       '--build-dir', runtime['build_dir'], '--resource-dir', runtime['resource_dir'],
                       '--case-dir', str(target.parent), '--script', target.name,
                       '--timeout-seconds', str(timeout),
                       '--cpu-limit-seconds', str(max(1, timeout - 3))]
            env = dict(os.environ, BENCH_TOOLCHAIN_NAME=runtime.get('toolchain', 'clang'))
            env['MANTIS_NEIGHBOR_LOG_DIR'] = str((run_root / (checkpoint['id'] + '-measurements')).resolve())
            process = subprocess.run(command, capture_output=True, text=True, env=env,
                                     timeout=timeout + 30)
            record = {'group_id': group['id'], 'checkpoint_id': checkpoint['id'],
                      'snapshot_sha256': manifest['snapshot_sha256'],
                      'script_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                      'returncode': process.returncode}
            try:
                record['oracle'] = json.loads(process.stdout)
            except ValueError:
                record['oracle'] = {'passed': False, 'stdout': process.stdout, 'stderr': process.stderr}
            record['passed'] = process.returncode == 0 and record['oracle'].get('passed') is True
            (run_root / (checkpoint['id'] + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            results.append(record)
            executed.add(checkpoint['id'])
            print(json.dumps({k: record[k] for k in ('group_id', 'checkpoint_id', 'passed')}), flush=True)
        if executed != selected:
            raise ValueError('frozen replay skipped selected checkpoints')
    summary = {'cases': len(results), 'passed': sum(r['passed'] for r in results), 'results': results,
               'model_calls': 0, 'builds': 0}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    expected = sum(len(row['checkpoints']) for row in coverage['groups'])
    return 0 if summary['cases'] == expected > 0 and summary['cases'] == summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
