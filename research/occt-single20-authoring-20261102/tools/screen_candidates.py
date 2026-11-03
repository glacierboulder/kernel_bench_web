"""Screen supplied candidate identities against the locked current catalog."""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    existing = {int(row['id'].rsplit('-', 1)[1]) for row in catalog['issues']}
    rows = []
    for path in sorted(args.input_root.glob('issues/*/candidate.json')):
        candidate = json.loads(path.read_text())
        number = int(candidate['unit_id'].split(':')[1])
        commit = candidate.get('selected_fix_commit')
        patch = next(args.input_root.glob('materials/**/' + commit + '.patch.gz'), None) if commit else None
        source_paths = []
        if patch:
            content = gzip.decompress(patch.read_bytes()).decode()
            source_paths = [name for name in re.findall(r'^diff --git a/(\S+)', content, re.M) if name.startswith('src/')]
        rows.append({
            'canonical_id': candidate['unit_id'],
            'title': next(iter(json.loads(candidate['source_titles'])), candidate['unit_id']),
            'duplicate_current_catalog_number': number in existing,
            'candidate_record_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'reference_commit_lead': commit or None,
            'reference_date': candidate.get('selected_fix_date') or None,
            'source_patch_paths': source_paths,
            'upstream_test_paths': json.loads(candidate['selected_test_paths']),
            'state': 'duplicate' if number in existing else 'source_fix_lead' if source_paths else 'needs_fix_or_baseline_evidence',
            'geometry_qualification': 'not_run',
        })
    output = {
        'repository_baseline': 'c5184df5e161c72cfa389249a8b052efe1b87cf6',
        'catalog_sha256': hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        'existing_canonical_issue_numbers': sorted(existing),
        'candidate_count': len(rows),
        'duplicate_count': sum(row['duplicate_current_catalog_number'] for row in rows),
        'candidates': rows,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print({key: output[key] for key in ['candidate_count', 'duplicate_count']})
    print('nonduplicate source-change leads', sum(row['state'] == 'source_fix_lead' for row in rows))


if __name__ == '__main__':
    main()
