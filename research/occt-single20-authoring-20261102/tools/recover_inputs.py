"""Retrieve named public dataset blobs and verify pinned Git content identities."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

DATASET_COMMIT = 'd78a7a9e6de57699261fa03641ec1b5bafac39a1'


def download(item, destination):
    name, record = item
    path = destination / name
    url = f"https://raw.githubusercontent.com/a-betenev/opencascade-dataset/{DATASET_COMMIT}/{record['folder']}/{name}"
    result = {'name': name, 'url': url, 'expected_git_blob': record['sha']}
    if not path.exists():
        transfer = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--location',
                                   '--connect-timeout', '10', '--max-time', '60', url, '-o', str(path)],
                                  capture_output=True, text=True)
        if transfer.returncode:
            result.update(status='download_failed', error=transfer.stderr)
            return result
    data = path.read_bytes()
    blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    result.update(status='verified' if blob == record['sha'] else 'content_mismatch',
                  bytes=len(data), git_blob_sha=blob, sha256=hashlib.sha256(data).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for row in json.loads(args.inventory.read_text()):
        files.update(row['found'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda item: download(item, args.destination), sorted(files.items())))
    args.report.write_text(json.dumps(results, indent=2) + '\n')
    print([(r['name'], r['status']) for r in results])


if __name__ == '__main__':
    main()
