"""Export issue #1543 geometry using its original C++ construction."""
import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / 'framework'))
    os.environ['BENCH_CONFIG'] = '/home/lzy/cad-bench-experiment/config.json'
    from backend.source_cache import tree_sha256
    from backend.sandbox import command, limits, monitor
    with (root / 'compiler.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        runtime = root / 'jobs/occt-7.9.3-build-01'
        receipt = json.loads((runtime / 'receipt.json').read_text())
        binaries = json.loads((runtime / 'binary-manifest.json').read_text())
        if receipt['status'] != 'built' or tree_sha256(runtime / 'source') != receipt['source_tree_sha256']:
            raise ValueError('input generator runtime source is not verified')
        for name, expected in binaries['libraries'].items():
            if digest(runtime / 'build' / name) != expected:
                raise ValueError('input generator runtime binary changed')
        work = root / 'jobs' / args.label
        work.mkdir(parents=True, exist_ok=False)
        shutil.copy2(root / 'incoming/github1543-generate-inputs.cpp', work / 'generate.cpp')
        (work / 'inputs').mkdir()
        libraries = ['TKOffset', 'TKBO', 'TKBool', 'TKPrim', 'TKShHealing', 'TKTopAlgo',
                     'TKGeomAlgo', 'TKBRep', 'TKGeomBase', 'TKG3d', 'TKG2d', 'TKMath', 'TKernel']
        libdir = '/workspace/build/lin64/clang/lib'
        mounts = [(runtime / 'source', '/workspace/source', False),
                  (runtime / 'build', '/workspace/build', False)]
        env = {'LD_LIBRARY_PATH': libdir}
        compiler = ['clang++-10', '-std=c++17', '-O0',
                    '-I/workspace/build/include/opencascade', '/workspace/generate.cpp',
                    '-L' + libdir, '-Wl,-rpath,' + libdir,
                    *['-l' + name for name in libraries], '-o', '/workspace/generate']
        for name, action, timeout in [('compile', compiler, 180),
                                      ('generate', ['/workspace/generate', '/workspace/inputs'], 180)]:
            with (work / (name + '.log')).open('w') as log:
                process = subprocess.Popen(command(work, mounts=mounts, env=env) + action,
                                           stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True, preexec_fn=limits)
                code = monitor(process, timeout, disk_root=work)
            if code != 0:
                raise RuntimeError(name + ' failed, see its preserved log')
        files = {p.name: digest(p) for p in (work / 'inputs').glob('*.brep')}
        if len(files) != 4:
            raise ValueError('input export is incomplete')
        record = {'source_commit': receipt['source_commit'],
                  'source_tree_sha256': receipt['source_tree_sha256'],
                  'binary_manifest_sha256': digest(runtime / 'binary-manifest.json'),
                  'generator_sha256': digest(work / 'generate.cpp'), 'inputs': files,
                  'compile_log_sha256': digest(work / 'compile.log'),
                  'generate_log_sha256': digest(work / 'generate.log'),
                  'model_called': False}
        (work / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
