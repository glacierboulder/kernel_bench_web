"""Candidate release gates and output-parser controls; no OCCT build is implied."""
from pathlib import Path
import ast
import json
import re
import unittest

from backend.runtime.assertion_oracle import validate_base_result, apply_pending_requirements

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'benchmarks/occt'


class CandidateContractTests(unittest.TestCase):
    def test_candidates_do_not_change_active_catalog_or_sources(self):
        registration = json.loads((BUNDLE / 'evaluation/provenance/authoring-20261110/candidate-registration.json').read_text(encoding='utf-8'))
        catalog = json.loads((BUNDLE / 'catalog.json').read_text(encoding='utf-8'))
        locks = json.loads((BUNDLE / 'sources.lock.json').read_text(encoding='utf-8'))
        self.assertEqual(registration['status'], 'candidate_only_not_registered')
        for key in ('issues', 'groups', 'evaluation_suites'):
            self.assertFalse({x['id'] for x in registration[key]} & {x['id'] for x in catalog[key]})
        self.assertFalse({x['source_id'] for x in registration['sources']} & {x['source_id'] for x in locks['sources']})

    def test_public_manifest_has_no_missing_or_unlisted_material(self):
        for number in (23933, 23981, 23985, 23998, 25337, 24220, 29038, 30198):
            root = BUNDLE / f'issues/occt-{number}/1'
            issue = json.loads((root / 'issue.json').read_text(encoding='utf-8'))
            actual = {p.relative_to(root).as_posix() for p in (root / 'public').rglob('*') if p.is_file()}
            self.assertEqual(set(issue['public_materials']), actual, number)
            suite = json.loads((BUNDLE / f'evaluation/suites/single/occt-{number}/1.json').read_text(encoding='utf-8'))
            for checkpoint in suite['checkpoints']:
                blocked = apply_pending_requirements({'passed': True, 'status': 'geometry_pass'}, checkpoint['runner_options'])
                self.assertFalse(blocked['passed'], number)
                self.assertEqual(blocked['status'], 'inconclusive')

    def test_actual_output_parser_rejects_errors_despite_pass_markers(self):
        # Load only the actual pure parser: importing its Linux resource-control
        # module on Windows would misrepresent what was tested here.
        parser_file = ROOT / 'backend/runtime/public_draw.py'
        tree = ast.parse(parser_file.read_text(encoding='utf-8'))
        nodes = [n for n in tree.body if
                 (isinstance(n, ast.FunctionDef) and n.name == 'evaluate_output') or
                 (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                  ('SUMMARY_RE', 'DONE_RE', 'OCCT_ERROR_RE') for t in n.targets))]
        scope = {'re': re}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(parser_file), 'exec'), scope)
        good = ('BENCH_ASSERT_PASS geometry kind=numeric\n'
                'BENCH_ORACLE_OK assertions=1 numeric_assertions=1\n'
                'TEST_DONE assertions=1 numeric_assertions=1\n'
                '__BENCH_ORACLE_COMPLETE__\n')
        route = {'expected_assertion_ids': ['geometry']}
        def verdict(text):
            return validate_base_result(scope['evaluate_output'](0, False, text, ''), route)
        self.assertTrue(verdict(good)['passed'])
        for broken in (good + 'Error: independent OCCT operation failed\n',
                       good.replace('__BENCH_ORACLE_COMPLETE__', ''),
                       good + 'BENCH_ASSERT_PASS geometry kind=numeric\n',
                       good.replace('PASS geometry', 'PASS another_id')):
            self.assertFalse(verdict(broken)['passed'])


if __name__ == '__main__':
    unittest.main()
