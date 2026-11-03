"""Preserve complete evidence in a deduplicated tar and retain reviewable logs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def retain(relative):
    excluded = {'cases', 'control', 'evaluation-control', 'runtime', 'data',
                'home', 'tmp', 'source', 'build', '__pycache__'}
    if excluded.intersection(relative.parts):
        return False
    if 'benchmark-snapshot' in relative.parts:
        position = relative.parts.index('benchmark-snapshot')
        remainder = relative.parts[position+1:]
        return (len(remainder) == 1 and relative.suffix == '.json') or (
            '/'.join(remainder) == 'supervisor/evaluator_assets/unified_runtime/contract.json')
    return relative.suffix in {'.json', '.log', '.txt', '.py', '.tcl', '.cpp', '.sh', '.patch', '.raw'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    jobs = args.jobs.resolve(strict=True)
    destination = args.destination.absolute()
    destination.mkdir(parents=True, exist_ok=False)
    complete = destination/'jobs-full'
    jobs.rename(complete)
    jobs.mkdir()
    archive = destination/'occt-single20-evidence-20261103.tar.gz'
    temporary = archive.with_suffix(archive.suffix+'.part')
    first_paths = {}
    raw_bytes = 0
    file_count = 0
    kept_count = 0
    with tarfile.open(temporary, 'x:gz', compresslevel=6) as output:
        output.add(complete, arcname='jobs', recursive=False)
        for path in sorted(complete.rglob('*')):
            relative = path.relative_to(complete)
            name = 'jobs/'+relative.as_posix()
            info = output.gettarinfo(str(path), arcname=name)
            if path.is_file() and not path.is_symlink():
                file_count += 1
                raw_bytes += path.stat().st_size
                digest = sha256(path)
                key = (digest, info.mode)
                if key in first_paths:
                    info.type = tarfile.LNKTYPE
                    info.linkname = first_paths[key]
                    info.size = 0
                    output.addfile(info)
                else:
                    first_paths[key] = name
                    with path.open('rb') as stream:
                        output.addfile(info, stream)
                if retain(relative):
                    target = jobs/relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
                    kept_count += 1
            else:
                output.addfile(info)
    temporary.rename(archive)
    record = {
        'archive': archive.name,
        'sha256': sha256(archive),
        'bytes': archive.stat().st_size,
        'regular_files': file_count,
        'uncompressed_file_bytes': raw_bytes,
        'distinct_content_and_mode_pairs': len(first_paths),
        'compact_review_files': kept_count,
        'format': 'gzip tar, with safe jobs-relative hard links for identical content and mode',
        'scope': 'All collected authoring input snapshots, frozen evaluator snapshots, raw logs, '
                 'result JSON, worker copies and binary identity records. Source checkouts and '
                 'compiled runtime caches remain identified by their pinned hashes.',
        'restore': 'Extract into an empty directory, then use jobs as --evidence-root for '
                   'tools/finalize_qualification.py.',
    }
    args.manifest.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
