"""Known assertion diagnostics must reach the same oracle for every role."""
import importlib.util
from pathlib import Path
import unittest

PATH = (Path(__file__).resolve().parents[1] / 'benchmarks/occt/evaluation/cases/'
        'evaluator_assets/five_group_originals/g2/run_eval.py')
spec = importlib.util.spec_from_file_location('g2_oracle_diagnostics', PATH)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def log(tolerance='1.0327861243812073e-07', error=None, case='M27310_2_d308'):
    if error is None:
        expected = '6.9230965382090094e-006' if case.endswith('d308') else '1.0e-7'
        error = f'Error: TolReached = {tolerance} is not equal to expected {expected}'
    return '\n'.join(['DRAW is running in batch mode', f'BF_HARNESS_CASE={case}',
                      error, 'BF_VAR_NbCurv=2', f'BF_VAR_Toler={tolerance}',
                      'BF_SOURCE_RC=0', 'BF_HARNESS_COMPLETED=1', 'BF_DRAW_RC=0'])


class OracleDiagnosticsTests(unittest.TestCase):
    def test_known_assertion_reaches_unchanged_predicate_for_all_roles(self):
        for role in ('B', 'F', 'agent'):
            with self.subTest(role=role):
                result = oracle.validate_draw_text('M27310_2_d308', role, log())
                self.assertEqual(result['status'], 'geometry_fail')
                self.assertEqual(result['detail']['observed_curve_count'], 2)
                self.assertEqual(result['detail']['expected_tolerance'], 6.9230965382090094e-6)
                self.assertEqual(result['detail']['official_relative_tolerance'], 0.1)

    def test_matching_reference_still_passes(self):
        text = log('6.9230965382090094e-6', error='')
        self.assertEqual(oracle.validate_draw_text('M27310_2_d308', 'agent', text)['status'], 'geometry_pass')

    def test_first_case_known_assertion_also_scores(self):
        result = oracle.validate_draw_text('M27310_1', 'agent', log('2.0e-7', case='M27310_1'))
        self.assertEqual(result['status'], 'geometry_fail')

    def test_unknown_wrong_reference_runtime_and_incomplete_logs_rejected(self):
        for text in (log(error='Error: unrelated failure'),
                     log(error='Error: TolReached = 1e-7 is not equal to expected 1.0e-7'),
                     log(error='invalid command name "bopcurves"'),
                     log().replace('BF_VAR_Toler=', 'MISSING_Toler='),
                     log().replace('BF_HARNESS_COMPLETED=1', '')):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    oracle.validate_draw_text('M27310_2_d308', 'agent', text)
