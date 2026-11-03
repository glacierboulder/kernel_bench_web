"""Materialize one official archive and require its exact complete Git tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / 'framework'))
    os.environ['BENCH_CONFIG'] = '/home/lzy/cad-bench-experiment/config.json'
    from backend.source_cache import tree_sha256
    source = root / 'prepared' / args.label / 'source'
    source.mkdir(parents=True, exist_ok=False)
    metadata = json.loads(args.metadata.read_text())
    with tarfile.open(args.archive, 'r:gz') as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts[1:]
            if not parts:
                continue
            if '..' in parts or not (member.isdir() or member.isfile()):
                raise ValueError('unsupported archive member')
            destination = source.joinpath(*parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(member).read())
                destination.chmod(member.mode & 0o777)
                os.utime(destination, (member.mtime, member.mtime))
    subprocess.run(['git', 'init', '-q', str(source)], check=True)
    subprocess.run(['git', 'add', '--all', '--force'], cwd=source, check=True)
    tree = subprocess.check_output(['git', 'write-tree'], cwd=source, text=True).strip()
    if tree != metadata['tree']['sha']:
        raise ValueError('official complete tree identity mismatch')
    from recover_git_commit import recover
    commit_bytes = recover(metadata)
    commit = subprocess.check_output(['git', 'hash-object', '-t', 'commit', '-w', '--stdin'],
                                     cwd=source, input=commit_bytes).decode().strip()
    if commit != metadata['sha']:
        raise ValueError('exact official commit bytes mismatch')
    (source / '.git/shallow').write_text(commit + '\n')
    subprocess.run(['git', 'update-ref', 'HEAD', commit], cwd=source, check=True)
    (source.parent / 'commit.raw').write_bytes(commit_bytes)
    record = {'source_commit': metadata['sha'], 'git_tree': tree, 'source_tree_sha256': tree_sha256(source),
              'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
              'source_directory': str(source), 'status': 'verified_complete_tree'}
    (source.parent / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
