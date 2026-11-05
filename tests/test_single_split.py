"""Inventory, oracle preservation and frozen routing for deduplicated single tasks."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from backend.catalog import public_task, validate_bundle
from backend.freeze import normalize_suite_case_material
from backend.occt_runtime import configuration, install
from backend.runtime.occt_adapter import _route
from backend.worker import _load_task_specs
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'benchmarks/occt'


class SingleSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=validate_bundle(BUNDLE)
        cls.catalog=json.loads((BUNDLE/'catalog.json').read_text())
        cls.provenance=json.loads((BUNDLE/'evaluation/provenance/single-split-20261105.json').read_text())
        cls.rows=[row for row in cls.provenance['selections'] if 'task_id' in row]

    def test_layout_and_unique_issue_selection(self):
        self.assertFalse((BUNDLE/'groups/new').exists())
        singles=[e for e in self.catalog['groups'] if e['path'].startswith('groups/single/')]
        multiples=[e for e in self.catalog['groups'] if e['path'].startswith('groups/multiple/')]
        self.assertEqual(len(singles),42)
        self.assertEqual(len(multiples),5)
        members=[self.bundle['groups'][(e['id'],e['version'])]['members'] for e in singles]
        self.assertTrue(all(len(m)==1 for m in members))
        self.assertEqual(len({m[0]['issue_id'] for m in members}),42)
        expected={'30082':'2','30202':'2','33541':'2','31602':'2','32850':'1',
                  '21494':'1','29807':'1','31835':'1','27310':'1','27773':'1','27252':'1','27780':'1'}
        self.assertEqual({r['issue_id'].split('-')[-1]:r['issue_version'] for r in self.rows},expected)
        for e in multiples:
            self.assertEqual(len(self.bundle['groups'][(e['id'],e['version'])]['members']),3)

    def test_single_suites_preserve_exact_parent_issue_contract(self):
        total=0
        for row in self.rows:
            with self.subTest(issue=row['issue_id']):
                group=self.bundle['groups'][(row['task_id'],'1')]
                parent=self.bundle['groups'][(row['parent_group_id'],'1')]
                suite=self.bundle['suites'][(row['suite_id'],'1')]
                original=self.bundle['suites'][(row['parent_suite']['id'],row['parent_suite']['version'])]
                self.assertEqual(group['source_id'],parent['source_id'])
                self.assertEqual(suite['checkpoints'],[cp for cp in original['checkpoints'] if cp['issue_id']==row['issue_id']])
                self.assertEqual(suite.get('support_files'),original.get('support_files'))
                categories=[cp['category'] for cp in suite['checkpoints']]
                self.assertIn('original',categories)
                self.assertGreaterEqual(categories.count('neighborhood'),2)
                self.assertIn('regression',categories)
                self.assertEqual(len(public_task(self.bundle,group)['issues']),1)
                total+=len(suite['checkpoints'])
                # Keep helper, engine, hashes, pending requirements and path aliases intact.
                config=deepcopy(configuration(BUNDLE,suite))
                old=configuration(BUNDLE,original)
                self.assertEqual(config['build_helper'],old['build_helper'])
                for key,route in config['checkpoints'].items():
                    self.assertEqual(route,old['checkpoints'][key])
                if row['issue_id']=='occt-27310':
                    cp=next(cp for cp in suite['checkpoints'] if cp['id']=='M27310_2_d308')
                    self.assertTrue(cp['runner_options']['pending_requirements'])
        self.assertEqual(total,59)

    def test_all_split_suites_install_and_route_frozen_material(self):
        for row in self.rows:
            with self.subTest(issue=row['issue_id']),tempfile.TemporaryDirectory() as directory:
                supervisor=Path(directory)
                assets=supervisor/'evaluator_assets'
                shutil.copytree(BUNDLE/'evaluation/cases/evaluator_assets',assets)
                (supervisor/'legacy/scripts').mkdir(parents=True)
                cases=supervisor/'cases/bundle'
                suite=self.bundle['suites'][(row['suite_id'],'1')]
                frozen,_=normalize_suite_case_material(self.bundle,self.catalog,suite,cases)
                config=install(BUNDLE,frozen,supervisor)
                self.assertEqual(set(config['checkpoints']),{cp['id'] for cp in suite['checkpoints']})
                with patch.dict('os.environ',{'BENCH_FROZEN_CASE_ROOT':str(cases)}):
                    for cp in frozen['checkpoints']:
                        route=_route(cases/cp['case'],config)
                        self.assertEqual(route['checkpoint_id'],cp['id'])

    def test_worker_resolves_split_tasks_without_legacy_dispatch(self):
        with patch('backend.worker.BENCHMARK_ROOT',BUNDLE):
            specs=_load_task_specs()
        for row in self.rows:
            self.assertEqual(specs[row['task_id']]['suite_id'],row['suite_id'])
            self.assertIsNone(specs[row['task_id']]['legacy_version'])


if __name__=='__main__':
    unittest.main()
