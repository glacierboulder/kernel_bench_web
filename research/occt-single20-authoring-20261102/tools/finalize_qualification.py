"""Audit the complete local evidence and emit the final single-issue matrix."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.catalog import validate_bundle, public_task
from backend.freeze import verify_snapshot

REPLAYS = [2, 3, 5, 6, 7, 8, 9, 10, 11]
BASE = 'c5184df5e161c72cfa389249a8b052efe1b87cf6'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, required=True,
                        help='complete jobs directory, including full frozen snapshots')
    args = parser.parse_args()
    evidence = args.evidence_root.resolve(strict=True)
    bundle_root = ROOT/'benchmarks/occt'
    bundle = validate_bundle(bundle_root)
    catalog = read(bundle_root/'catalog.json')
    old = json.loads(subprocess.check_output(['git', 'show', BASE+':benchmarks/occt/catalog.json'], cwd=ROOT))
    for key in ['issues', 'groups', 'evaluation_suites']:
        present = {(x['id'], x['version']): x for x in catalog[key]}
        assert all(present[(x['id'], x['version'])] == x for x in old[key])
    source_lock = {x['source_id']: x for x in read(bundle_root/'sources.lock.json')['sources']}
    old_lock = json.loads(subprocess.check_output(['git', 'show', BASE+':benchmarks/occt/sources.lock.json'], cwd=ROOT))
    assert all(source_lock[x['source_id']] == x for x in old_lock['sources'])
    groups = {key[0]: group for key, group in bundle['groups'].items()
              if key[0].startswith('occt-single20-')}
    assert len(groups) == 20
    old_numbers = {''.join(c for c in item['id'] if c.isdigit()) for item in old['issues']}
    all_rows = []
    replay_for = {}
    for number in REPLAYS:
        label = f'frozen-replay-{number:02}'
        receipt = read(evidence/label/'receipt.json')
        for row in receipt['checkpoints']:
            assert row['group_id'] in groups
            replay_for[row['group_id']] = label
            all_rows.append(dict(row, evidence_job=label))
    assert len(all_rows) == 160
    outcomes = Counter()
    tasks = []
    negative_total = 0
    for group_id, group in sorted(groups.items()):
        assert group['kind'] == 'single' and len(group['members']) == 1
        member = group['members'][0]
        issue_id = member['issue_id']
        if 'github' not in issue_id:
            assert ''.join(c for c in issue_id if c.isdigit()) not in old_numbers
        public = json.dumps(public_task(bundle, group), ensure_ascii=False)
        for private_marker in ['evaluation/cases/', 'reference.patch', 'negative_']:
            assert private_marker not in public
        provenance_dir = bundle_root/'evaluation/provenance/single20'/issue_id
        provenance = read(provenance_dir/'source.json')
        qualification = provenance.get('qualification', provenance.get('geometry_evidence'))
        task_rows = [row for row in all_rows if row['group_id'] == group_id]
        assert len(task_rows) == 8
        label = replay_for[group_id]
        source = source_lock[group['source_id']]
        summary = {'issue_id': issue_id, 'issue_version': member['issue_version'],
                   'title': group['title'], 'budget': group['budget'],
                   'group_id': group_id, 'suite': group['evaluation_suite'],
                   'source_id': group['source_id'], 'baseline_commit': source['commit'],
                   'baseline_tree_sha256': source['materialized_tree_sha256'],
                   'source_kind': provenance['source_kind'], 'frozen_replay': label,
                   'reference_commit': qualification['f']['source_commit'],
                   'reference_tree_sha256': qualification['f']['source_tree_sha256'],
                   'upstream_url': ('https://github.com/Open-Cascade-SAS/OCCT/issues/1543'
                                    if 'github' in issue_id else
                                    'https://occt3d.com/dev/tickets/'+issue_id.removeprefix('occt-').zfill(7)+'/'),
                   'verdict': 'PASS', 'checkpoints': [], 'snapshots': {}}
        summary['evidence_file'] = 'evidence.json'
        summary['result_path_namespace'] = 'tar archive member path'
        for role in ['b', 'f']:
            run = evidence/label/group_id/role
            snapshot = run/'benchmark-snapshot'
            frozen = verify_snapshot(snapshot)
            verification = read(run/'verification.json')
            assert verification['source_unchanged'] and verification['snapshot_unchanged']
            assert verification['shared_public_build_exit_code'] == 0
            suite = read(snapshot/'suite.json')
            assert Counter(c['category'] for c in suite['checkpoints']) == {
                'original': 1, 'neighborhood': 2, 'regression': 1}
            summary['snapshots'][role] = frozen['snapshot_sha256']
            # Compare every declared geometric asset with the executed frozen copy.
            assets = set(suite.get('support_files', []))
            assets.update(c['case'] for c in suite['checkpoints'])
            for relative in assets:
                executed = snapshot/'supervisor/cases/bundle'/relative
                assert digest(executed) == digest(bundle_root/relative), relative
            for row in [x for x in task_rows if x['role'] == role]:
                assert row['source_commit'] == qualification[role]['source_commit']
                assert row['source_tree_sha256'] == qualification[role]['source_tree_sha256']
                assert row['snapshot_sha256'] == frozen['snapshot_sha256']
                status = row['oracle']['status']
                assert status in {'geometry_pass', 'geometry_fail'}
                if role == 'f' or row['category'] == 'regression':
                    assert status == 'geometry_pass'
                if role == 'b' and row['category'] == 'original':
                    assert status == 'geometry_fail'
                outcomes[(role, row['category'], status)] += 1
                summary['checkpoints'].append({
                    'role': role, 'id': row['checkpoint_id'], 'category': row['category'],
                    'status': status, 'process_return_code': row['process_return_code'],
                    'result_path': f'jobs/{label}/{group_id}/{role}/{row["checkpoint_id"]}/result.json',
                    'runtime_binaries_sha256': row['runtime_binaries_sha256'],
                })
        negative_job = qualification['f']['label']
        direct = read(evidence/negative_job/'receipt.json')
        negatives = {name: result for name, result in direct['results'].items()
                     if name.startswith('negative_')}
        assert len(negatives) >= 3
        assert all(value['status'] == 'geometry_fail' for value in negatives.values())
        negative_total += len(negatives)
        summary['negative_controls'] = {'job': negative_job, 'rejected': sorted(negatives)}
        if issue_id in {'occt-24418', 'occt-25111', 'occt-26243', 'occt-26796', 'occt-26910'}:
            summary['supplementary_input_legality'] = []
            for role in ['b', 'f']:
                audit_job = f'm{issue_id.removeprefix("occt-")}-{role}-input-legality-01'
                audit = read(evidence/audit_job/'receipt.json')
                assert audit['source_commit'] == qualification[role]['source_commit']
                assert audit['results']['input_legality']['status'] == 'geometry_pass'
                summary['supplementary_input_legality'].append(audit_job)
        summary['full_snapshots_reverified'] = True
        save(provenance_dir/'qualification.json', summary)
        tasks.append(summary)
    matrix = {'repository_baseline': BASE, 'new_tasks': len(tasks),
              'frozen_checks': len(all_rows), 'reference_negative_controls_rejected': negative_total,
              'outcomes': [{'role': role, 'category': category, 'status': status, 'count': count}
                           for (role, category, status), count in sorted(outcomes.items())],
              'historical_catalog_entries_unchanged': True,
              'historical_source_locks_unchanged': True,
              'evidence_archive': 'evidence/occt-single20-evidence-20261103.tar.gz',
              'result_path_namespace': 'tar archive member path',
              'model_evaluation_runs': 0, 'tasks': tasks}
    save(RESEARCH/'qualification-matrix.json', matrix)
    mapping_keys = ['issue_id', 'issue_version', 'title', 'group_id', 'suite', 'budget',
                    'source_id', 'baseline_commit', 'baseline_tree_sha256', 'source_kind',
                    'reference_commit', 'reference_tree_sha256', 'upstream_url']
    save(RESEARCH/'registered-tasks.json', [{key: task[key] for key in mapping_keys} for task in tasks])
    print(json.dumps({key: matrix[key] for key in ['new_tasks', 'frozen_checks',
                                                'reference_negative_controls_rejected', 'outcomes']}))


if __name__ == '__main__':
    main()
