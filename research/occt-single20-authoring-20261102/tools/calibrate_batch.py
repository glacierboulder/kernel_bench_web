"""Run explicit calibration jobs when their immutable builds are ready."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    for row in json.loads(args.plan.read_text()):
        deadline = time.monotonic() + 7200
        receipt = args.root / 'jobs' / row['build_job'] / 'receipt.json'
        binary_receipt = receipt.parent / 'binary-manifest.json'
        while True:
            state = json.loads(receipt.read_text()) if receipt.exists() else {}
            if state.get('status') == 'built' and binary_receipt.is_file():
                break
            if state.get('status') in {'build/configuration error', 'preparation or infrastructure error'}:
                raise RuntimeError('dependency build failed: ' + row['build_job'])
            if time.monotonic() > deadline:
                raise TimeoutError('dependency build is not ready: ' + row['build_job'])
            time.sleep(10)
        subprocess.run([
            sys.executable, str(Path(__file__).with_name('calibrate_cases.py')),
            '--root', str(args.root), '--label', row['label'],
            '--build-job', row['build_job'], '--issue', str(row['issue']),
            '--case-plan', str(args.root / 'incoming' / row.get(
                'plan', 'm' + str(row['issue']) + '-calibration-plan.json')),
        ], check=True)


if __name__ == '__main__':
    main()
