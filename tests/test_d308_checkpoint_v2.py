import json
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.runtime.occt_adapter import _normalize
from backend.suite_driver import checkpoint_status
from backend.checkpoints import normalize_checkpoints
from backend.catalog import validate_bundle

ROOT=Path(__file__).resolve().parents[1]

class D308CheckpointV2Tests(unittest.TestCase):
    def test_old_suite_is_retained_and_only_d308_changes(self):
        path=ROOT/'benchmarks/occt/evaluation/suites/new/occt-27310-27773-27252'
        old=json.loads((path/'1.json').read_text());new=json.loads((path/'2.json').read_text())
        a={cp['id']:cp for cp in old['checkpoints']};b={cp['id']:cp for cp in new['checkpoints']}
        self.assertEqual(set(a),set(b));self.assertEqual([k for k in a if a[k]!=b[k]],['M27310_2_d308'])
        cp=b['M27310_2_d308'];self.assertTrue(cp['runner_options']['pending_requirements'])
        script=(ROOT/'benchmarks/occt'/cp['case']).read_text()
        self.assertIn('scored=0',script);self.assertNotIn('checkreal TolReached',script)
        self.assertIn('surface_residual',script);self.assertIn('pcurve_mapping',script)
        self.assertNotIn('$reported <=',script);self.assertNotIn('$reported >',script.replace('$reported >=',''))

    def test_inconclusive_is_not_failed_or_passed_in_checkpoint_summary(self):
        raw={'status':'inconclusive','passed':False,'return_code':1,'pending_requirements':['coverage']}
        r=_normalize(raw,1,{'checkpoint_id':'d308','category':'original'})
        self.assertEqual(r['status'],'inconclusive');self.assertFalse(r['passed'])
        self.assertEqual(checkpoint_status({'passed':False,'result':r}),'inconclusive')
        s={'id':'s','version':'1','checkpoints':[{'id':'d308','case':'c.tcl','category':'original','visibility':'public','required':True}]}
        v=normalize_checkpoints(s,{'checkpoints':[{'id':'d308','status':'inconclusive','passed':False,'result':r}]})
        self.assertEqual(v['category_summary']['original']['inconclusive'],1)
        self.assertEqual(v['category_summary']['original']['failed'],0)
        self.assertFalse(v['technical_passed'])

    def test_lower_reported_tolerance_cannot_trigger_a_geometry_failure(self):
        from backend.runtime.assertion_oracle import validate_base_result,apply_pending_requirements
        route={'checkpoint_id':'d308','expected_assertion_ids':['measured']}
        for value in (1e-12,1e-7,6.923096538209009e-6,1e-4):
            text=f'D308_REPORTED_TOLERANCE={value}\nBENCH_ASSERT_PASS measured actual_residual=1e-8 kind=numeric\n__BENCH_ORACLE_COMPLETE__\nBENCH_ORACLE_OK assertions=1 numeric_assertions=1\nTEST_DONE assertions=1 numeric_assertions=1\n'
            raw=validate_base_result({'stdout_tail':text,'return_code':0,'passed':True},route)
            self.assertTrue(raw['passed'])
            guarded=apply_pending_requirements(raw,dict(route,pending_requirements=['coverage']))
            self.assertEqual(guarded['status'],'inconclusive')
            self.assertFalse(guarded['passed'])

    def test_explicit_geometric_failure_is_not_hidden_by_pending_coverage(self):
        raw={'status':'geometry_fail','passed':False,'return_code':1,'pending_requirements':['coverage']}
        r=_normalize(raw,1,{'checkpoint_id':'d308','category':'original'})
        self.assertEqual(checkpoint_status({'passed':False,'result':r}),'failed')


class InconclusiveRunStatusTests(unittest.TestCase):
    def test_failed_rule_takes_priority_over_unresolved_coverage(self):
        from backend.checkpoints import evaluation_run_status
        r={'passed':False,'tests':[{'status':'passed','passed':True},{'status':'inconclusive','passed':False}]}
        self.assertEqual(evaluation_run_status(r,1),'inconclusive')
        r['tests'].append({'status':'failed','passed':False})
        self.assertEqual(evaluation_run_status(r,1),'failed')
        r['tests'].pop();r['failure_stage']='submission'
        self.assertEqual(evaluation_run_status(r,1),'failed')

    def test_execution_error_is_not_a_confirmed_geometry_failure(self):
        from backend.checkpoints import evaluation_run_status
        self.assertEqual(evaluation_run_status({'tests':[{'status':'error','passed':False}]},1),'inconclusive')
        self.assertEqual(evaluation_run_status({'failure_stage':'infrastructure','tests':[]},2),'inconclusive')
