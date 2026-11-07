"""All registered V4 routes must reject a missing named assertion."""
import json
from pathlib import Path
import unittest
from backend.runtime.assertion_oracle import validate_base_result
ROOT=Path(__file__).resolve().parents[1]
class CorpusContract(unittest.TestCase):
 def test_every_locked_route_detects_each_missing_assertion(self):
  lock=json.loads((ROOT/'benchmarks/occt/evaluation/cases/evaluator_assets/occt_single_v4/dispatch_lock.json').read_text())
  routes=lock['checkpoint_routes'];self.assertGreater(len(routes),0)
  for path,route in routes.items():
   ids=route['expected_assertion_ids'];self.assertGreater(len(ids),0)
   def result(kept):
    text='\n'.join([f'BENCH_ASSERT_PASS {key} measured kind=expression' for key in kept]+['__BENCH_ORACLE_COMPLETE__',f'BENCH_ORACLE_OK assertions={len(kept)} numeric_assertions=0',f'TEST_DONE assertions={len(kept)} numeric_assertions=0'])
    return validate_base_result(dict(stdout_tail=text,return_code=0,passed=True),route)
   with self.subTest(route=path):self.assertEqual(result(ids)['status'],'geometry_pass')
   for missing in ids:
    with self.subTest(route=path,missing=missing):
     r=result([key for key in ids if key!=missing]);self.assertFalse(r['passed']);self.assertIn(missing,r['missing_assertions'])
if __name__=='__main__':unittest.main()
