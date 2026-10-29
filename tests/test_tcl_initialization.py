import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from backend.runtime.public_draw import tcl_bootstrap, write_wrapper
from backend.runtime.assertion_oracle import completed_failure_status

class TclInitializationTests(unittest.TestCase):
    def test_real_standard_library_restores_missing_math_functions(self):
        executable=shutil.which('tclsh')
        if not executable:self.skipTest('Tcl shell unavailable')
        query=subprocess.run([executable],input='puts [info library]\n',text=True,capture_output=True,check=True)
        init=Path(query.stdout.strip())/'init.tcl'
        script='rename ::tcl::mathfunc::max {}\nrename ::tcl::mathfunc::min {}\n'+tcl_bootstrap(init)+'''
puts [expr {max(-3,2.5,2)}]
puts [expr {min(-3,2.5,2)}]
puts [catch {expr {max()}}]
puts [catch {expr {max("invalid",2)}}]
'''
        proc=subprocess.run([executable],input=script,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0);self.assertEqual(proc.stderr,'')
        self.assertEqual(proc.stdout.splitlines(),['2.5','-3','1','1'])

    def test_missing_library_does_not_emulate_or_skip_test_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper=Path(directory)/'wrapper.tcl'
            write_wrapper(Path(directory)/'case.tcl',wrapper)
            text=wrapper.read_text();self.assertIn('Tcl standard library is unavailable',text)
            self.assertLess(text.index('Tcl standard library is unavailable'),text.index('source $::bench_runner_script'))
            self.assertIn('exit 1',text)

    def test_completed_shape_property_failure_is_geometry_failure(self):
        r={'status':'runtime_error','summary_pair_valid':True,'completion_sentinel_count':1,
           'base_runner':{'return_code':0,'stdout_tail':'Error : The volume of result shape is 4188.79, expected 3945.6'},
           'observed_assertion_events':[{'status':'PASS'}]}
        self.assertEqual(completed_failure_status(r),'geometry_fail')
        r['base_runner']['stdout_tail']='Error: cannot load required library'
        self.assertEqual(completed_failure_status(r),'runtime_error')
        r['base_runner']['tcl_error_detected']=True
        r['observed_assertion_events']=[{'status':'FAIL'}]
        self.assertEqual(completed_failure_status(r),'runtime_error')
