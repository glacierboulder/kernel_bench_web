"""Add an immutable identity record for versioned OCCT libraries and DRAWEXE."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build_job', type=Path)
    args = parser.parse_args()
    job = args.build_job.resolve()
    receipt = json.loads((job / 'receipt.json').read_text())
    if receipt['status'] != 'built' or not receipt['source_unchanged']:
        raise ValueError('build did not complete with an unchanged source')
    build = job / 'build'
    files = [p for p in build.rglob('*')
             if p.is_file() and not p.is_symlink()
             and ('.so' in p.name or p.name.startswith('DRAWEXE'))]
    if not any(p.name.startswith('DRAWEXE') for p in files):
        raise ValueError('DRAWEXE is missing')
    record = {
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'build_receipt_sha256': sha256(job / 'receipt.json'),
        'libraries': {str(p.relative_to(build)): sha256(p) for p in sorted(files)},
        'scope': 'Current compiled binaries, including versioned shared libraries',
    }
    with (job / 'binary-manifest.json').open('x') as output:
        output.write(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'job': job.name, 'binary_count': len(files)}))


if __name__ == '__main__':
    main()
