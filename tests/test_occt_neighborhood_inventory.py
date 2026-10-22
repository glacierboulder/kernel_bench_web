"""The in-place extension preserves old checks and caps actual scenarios."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'benchmarks/occt'


class NeighborhoodInventoryTests(unittest.TestCase):
    def test_preserved_checks_hashes_dependencies_and_scenario_cap(self):
        ledger = json.loads((ROOT / 'evaluation/provenance/neighborhood-v2-coverage.json').read_text())
        totals = {}
        self.assertEqual(len(ledger['groups']), 5)
        self.assertEqual(sum(row['old_checkpoint_count'] for row in ledger['groups']), 49)
        for row in ledger['groups']:
            path = ROOT / row['suite_path']
            suite = json.loads(path.read_text())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['suite_sha256_after'])
            old = suite['checkpoints'][:row['old_checkpoint_count']]
            digest = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(digest, row['original_checkpoint_list_sha256'])
            for checkpoint in old:
                if checkpoint['category'] == 'neighborhood':
                    issue = re.search(r'(\d+)$', checkpoint['issue_id']).group(1)
                    totals[issue] = totals.get(issue, 0) + (2 if issue in {'30082', '33541'} else 1)
            appended = suite['checkpoints'][len(old):]
            self.assertEqual(appended, [case['checkpoint'] for case in row['checkpoints']])
            self.assertGreater(len(appended), 0)
            old_issues = {cp['issue_id'] for cp in old if cp.get('issue_id')}
            self.assertEqual({cp['issue_id'] for cp in appended}, old_issues)
            for case in row['checkpoints']:
                self.assertEqual(case['scenario_count'], len(case['scenarios']))
                issue = re.search(r'(\d+)$', case['checkpoint']['issue_id']).group(1)
                totals[issue] = totals.get(issue, 0) + case['scenario_count']
                self.assertTrue(case['checkpoint']['required'])
                for dependency in case.get('support_files', []):
                    self.assertIn(dependency, suite['support_files'])
                    self.assertTrue((ROOT / dependency).is_file())
        self.assertEqual(totals, ledger['issue_scenario_totals'])
        self.assertTrue(all(0 < count <= 15 for count in totals.values()))
