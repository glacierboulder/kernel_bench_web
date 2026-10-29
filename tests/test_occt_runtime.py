import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.runtime import occt_adapter as adapter
from backend.occt_runtime import enabled, install
from backend.suite_driver import checkpoint_status

ROOT=Path(__file__).resolve().parents[1]

class UnifiedOcctRuntimeTests(unittest.TestCase):
    def test_registry_covers_fifteen_suites_and_113_checkpoints(self):
        value=json.loads((ROOT/'benchmarks/occt/evaluation/runtime.json').read_text())
        self.assertEqual(len(value['suites']),15)
        self.assertEqual(sum(len(c['checkpoints']) for c in value['suites'].values()),113)
        for c in value['suites'].values():
            for key,r in c['checkpoints'].items():
                self.assertEqual(key,r['checkpoint_id'])
                self.assertEqual(len(r['case_sha256']),64)

    def test_explicit_writable_root_allows_relocation_and_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cases=root/'different/location';cases.mkdir(parents=True)
            file=cases/'case.tcl';file.write_text('puts TEST_DONE\n')
            route={'case':'case.tcl','case_sha256':adapter._sha(file)}
            contract={'checkpoints':{'cp':route}}
            with patch.dict(os.environ,{'BENCH_FROZEN_CASE_ROOT':str(cases)}):
                self.assertEqual(adapter._route(file,contract),route)
                outside=root/'outside.tcl';outside.write_text('puts TEST_DONE\n')
                with self.assertRaisesRegex(ValueError,'outside'):adapter._route(outside,contract)
                file.write_text('tampered\n')
                with self.assertRaisesRegex(ValueError,'hash'):adapter._route(file,contract)
            with patch.dict(os.environ,{},clear=True):
                with self.assertRaisesRegex(ValueError,'supervisor'):adapter._route(file,contract)

    def test_asset_traversal_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'one.py';p.write_text('')
            (root/'link.py').symlink_to(p)
            for relative in ('../one.py','/one.py','link.py'):
                with self.subTest(relative=relative),self.assertRaises(ValueError):adapter._safe(root,relative)

    def test_process_success_without_oracle_is_not_pass(self):
        route={'checkpoint_id':'cp','category':'original'}
        raw={'return_code':0,'test_done_marker':False}
        out=adapter._normalize(raw,0,route)
        self.assertFalse(out['passed']);self.assertFalse(out['oracle_ran'])
        self.assertEqual(checkpoint_status({'passed':False,'result':out}),'error')

    def test_geometry_failure_and_infrastructure_have_different_statuses(self):
        route={'checkpoint_id':'cp','category':'original'}
        for status,expected in [('geometry_pass','passed'),('geometry_fail','failed'),('not_run','not_run')]:
            raw={'schema_version':'bf-group2-staged-run-v1','process_return_code':0 if status=='geometry_pass' else 1,'oracle':{'status':status}}
            out=adapter._normalize(raw,0 if status=='geometry_pass' else 1,route)
            self.assertEqual(checkpoint_status({'passed':out['passed'],'result':out}),expected)
        out=adapter._normalize({'error':'missing library'},1,route)
        self.assertEqual(checkpoint_status({'passed':False,'result':out}),'error')

    def test_build_rejects_incompatible_suite_and_excess_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'suite.json';p.write_text(json.dumps({'id':'s','version':'1','group_ids':['g']}))
            c={'suite':'s@1','group_id':'g','build_helper':{}}
            with patch.object(adapter,'_contract',return_value=c),patch.object(adapter,'_load',return_value='helper'),patch.object(adapter.sys,'argv',['driver','--suite',str(p)]):
                with patch.dict(os.environ,{'BENCH_COMPILER_JOBS':'2'}):self.assertEqual(adapter._build_helper(),'helper')
                with patch.dict(os.environ,{'BENCH_COMPILER_JOBS':'3'}):
                    with self.assertRaises(ValueError):adapter._build_helper()
                c['suite']='wrong@1'
                with self.assertRaises(ValueError):adapter._build_helper()

    def test_v4_oracle_contract_not_weakened(self):
        spec=importlib.util.spec_from_file_location('old_v4',ROOT/'benchmarks/occt/tools/occt-v4-clang10-o3/run_draw_case.py')
        original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
        from backend.runtime.assertion_oracle import validate_base_result
        route={'checkpoint_id':'one','category':'original','expected_assertion_ids':['a']}
        text='BENCH_ASSERT_PASS a value kind=numeric\n__BENCH_ORACLE_COMPLETE__\nBENCH_ORACLE_OK assertions=1 numeric_assertions=1\nTEST_DONE assertions=1 numeric_assertions=1\n'
        for stdout in (text,text.replace('PASS','FAIL'),text.replace('a value','wrong value'),text+text,''):
            base={'stdout_tail':stdout,'return_code':0,'passed':True}
            self.assertEqual(validate_base_result(base,route),original.validate_base_result(base,route))


class DataOnlyAuthoringTests(unittest.TestCase):
    def test_new_suite_generates_contract_without_runtime_registration(self):
        from backend.occt_runtime import configuration
        from backend.catalog import validate_bundle
        from backend.freeze import normalize_suite_case_material
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            case=root/'case.tcl';case.write_text('puts TEST_DONE\n')
            (root/'toolchains').mkdir();(root/'sources.lock.json').write_text(json.dumps({'sources':[{'source_id':'s','toolchain':'tool'}]}))
            (root/'toolchains/tool.json').write_text(json.dumps({'compiler_output_directory':'clang','optimization_flags':'-O3 -DNDEBUG'}))
            suite={'id':'new-data-only','version':'1','source_ids':['s'],'group_ids':['g'],
                   'checkpoints':[{'id':'one','category':'original','runner':'draw_case_v1','case':'case.tcl',
                                   'runner_options':{'expected_assertion_ids':['volume','valid']}}]}
            c=configuration(root,suite)
            self.assertTrue(c['standard_build']);self.assertEqual(c['public_build_profile']['optimization_flags'],'-O3 -DNDEBUG')
            self.assertEqual(c['checkpoints']['one']['expected_assertion_ids'],['volume','valid'])
            supervisor=root/'supervisor';(supervisor/'legacy/scripts').mkdir(parents=True)
            config=install(root,suite,supervisor,case_root=root)
            self.assertEqual(config,c)
            self.assertTrue((supervisor/'evaluator_assets/unified_runtime/public_build.py').is_file())
            self.assertEqual((supervisor/'legacy/run_eval.py').read_bytes(),(supervisor/'legacy/scripts/run_draw_case.py').read_bytes())
            self.assertFalse((root/'evaluation/runtime.json').exists())

if __name__=='__main__':unittest.main()
