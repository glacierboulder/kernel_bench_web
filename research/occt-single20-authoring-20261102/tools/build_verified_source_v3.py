"""Build one verified source copy with the repository's shared public build tool."""
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
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, record):
    path.write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-tree', required=True)
    parser.add_argument('--git-tree', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tcl-prefix', type=Path, required=True)
    parser.add_argument('--inverse-patch', type=Path)
    parser.add_argument('--reuse-build', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    framework = root / 'framework'
    os.environ['BENCH_CONFIG'] = '/home/lzy/cad-bench-experiment/config.json'
    sys.path.insert(0, str(framework))
    from backend.source_cache import tree_sha256
    from backend.sandbox import command, limits, monitor

    with (root / 'compiler.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        work = root / 'jobs' / args.label
        work.mkdir(parents=True, exist_ok=False)
        record = {'label': args.label, 'started_at': datetime.now(timezone.utc).isoformat(),
                  'source_commit': args.commit, 'git_tree': args.git_tree,
                  'source_tree_sha256': args.source_tree, 'model_called': False,
                  'compiler_jobs': 2, 'toolchain': 'occt-v4-clang10-o0-tcl86',
                  'worker_sha256': digest(__file__), 'status': 'preparing'}
        save(work / 'receipt.json', record)
        shutil.copy2(__file__, work / 'worker.py')
        try:
            if tree_sha256(args.source) != args.source_tree:
                raise ValueError('source copy origin tree identity mismatch')
            source = work / 'source'
            shutil.copytree(args.source, source, ignore=shutil.ignore_patterns('.git'), symlinks=True)
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            subprocess.run(['git', 'add', '--all', '--force'], cwd=source, check=True)
            tree = subprocess.check_output(['git', 'write-tree'], cwd=source, text=True).strip()
            if tree != args.git_tree:
                raise ValueError('copied complete Git tree mismatch')
            changed_files = []
            if args.inverse_patch:
                original_commit = subprocess.check_output(['git', 'cat-file', 'commit', args.commit], cwd=args.source)
                stored = subprocess.check_output(['git', 'hash-object', '-t', 'commit', '-w', '--stdin'],
                                                 cwd=source, input=original_commit).decode().strip()
                if stored != args.commit:
                    raise ValueError('base commit object mismatch')
                (source / '.git/shallow').write_text(args.commit + '\n')
                subprocess.run(['git', 'update-ref', 'HEAD', args.commit], cwd=source, check=True)
                patch = args.inverse_patch.resolve()
                shutil.copy2(patch, work / 'inverse-upstream.patch')
                subprocess.run(['git', 'apply', '--reverse', '--check', '--ignore-space-change', str(patch)], cwd=source, check=True)
                subprocess.run(['git', 'apply', '--reverse', '--ignore-space-change', str(patch)], cwd=source, check=True)
                changed_files = subprocess.check_output(['git', 'diff', '--name-only'], cwd=source, text=True).splitlines()
                subprocess.run(['git', 'add', '--all', '--force'], cwd=source, check=True)
                derived_tree = subprocess.check_output(['git', 'write-tree'], cwd=source, text=True).strip()
                commit_env = dict(os.environ, GIT_AUTHOR_NAME='Benchmark Curator', GIT_AUTHOR_EMAIL='benchmark@localhost',
                                  GIT_COMMITTER_NAME='Benchmark Curator', GIT_COMMITTER_EMAIL='benchmark@localhost',
                                  GIT_AUTHOR_DATE='2026-11-02T00:00:00+00:00', GIT_COMMITTER_DATE='2026-11-02T00:00:00+00:00')
                message = ('Curated OCCT baseline: inverse source patch ' + digest(patch) + '\n').encode()
                derived_commit = subprocess.check_output(['git', 'commit-tree', derived_tree, '-p', args.commit],
                                                        cwd=source, input=message, env=commit_env).decode().strip()
                subprocess.run(['git', 'update-ref', 'HEAD', derived_commit], cwd=source, check=True)
                reference_patch = subprocess.check_output(['git', 'diff', '--binary', derived_commit, args.commit], cwd=source)
                (work / 'reference.patch').write_bytes(reference_patch)
                record.update(origin_commit=args.commit, origin_tree_sha256=args.source_tree,
                              source_commit=derived_commit, git_tree=derived_tree,
                              source_tree_sha256=tree_sha256(source), source_kind='curator-derived inverse patch',
                              inverse_patch_sha256=digest(patch), reference_patch_sha256=digest(work / 'reference.patch'),
                              changed_files=changed_files)
            if args.reuse_build:
                prior = json.loads((args.reuse_build.parent / 'receipt.json').read_text())
                if prior.get('status') != 'built':
                    raise ValueError('cache build is incomplete')
                for name, expected in prior['libraries'].items():
                    if digest(args.reuse_build / name) != expected:
                        raise ValueError('cache library identity mismatch')
                shutil.copytree(args.reuse_build, work / 'build', symlinks=True)
                for name in changed_files:
                    os.utime(source / name, None)
                record['cache_receipt_sha256'] = digest(args.reuse_build.parent / 'receipt.json')
            helper = framework / 'benchmarks/occt/tools/occt-v4-clang10-o0/build.sh'
            snapshot = work / 'build.sh'
            shutil.copy2(helper, snapshot)
            record['build_helper_sha256'] = digest(snapshot)
            record['status'] = 'building'
            save(work / 'receipt.json', record)
            started = time.monotonic()
            environment = {'BENCH_TOOLCHAIN_NAME': 'clang-o0', 'BENCH_COMPILER_JOBS': '2',
                           'BENCH_TCL_INCLUDE_DIR': str(args.tcl_prefix / 'include'),
                           'BENCH_TCL_LIBRARY': str(args.tcl_prefix / 'lib/libtcl8.6.so'),
                           'BENCH_TCL_LIBRARY_DIR': str(args.tcl_prefix / 'lib')}
            argv = command(work, env=environment) + ['bash', '/workspace/build.sh', '/workspace/source', '/workspace/build']
            with (work / 'build.log').open('w') as log:
                process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True, preexec_fn=limits)
                code = monitor(process, 3600, disk_root=work)
            record.update(build_exit_code=code, build_seconds=time.monotonic() - started,
                          build_log_sha256=digest(work / 'build.log'),
                          status='built' if code == 0 else 'build/configuration error')
            record['libraries'] = {str(p.relative_to(work / 'build')): digest(p)
                                   for p in (work / 'build').rglob('*.so') if p.is_file() and not p.is_symlink()}
        except Exception as exc:
            record.update(status='preparation or infrastructure error', error=str(exc))
        finally:
            if (work / 'source').exists():
                record['final_source_tree_sha256'] = tree_sha256(work / 'source')
                record['source_unchanged'] = record['final_source_tree_sha256'] == record['source_tree_sha256']
            record['finished_at'] = datetime.now(timezone.utc).isoformat()
            save(work / 'receipt.json', record)
        print(json.dumps({'label': args.label, 'status': record['status']}))
        return 0 if record['status'] == 'built' and record['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
