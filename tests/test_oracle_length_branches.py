"""Exercise the actual benchmark scripts' length-oracle branches via Tcl."""
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
ISSUE=ROOT/'benchmarks/occt/issues/occt-30703/1'
class LengthOracleBranches(unittest.TestCase):
 def branch(self,path,description,body):
  text=path.read_text();tail=text[text.index('set v4_res_description'):]
  script=f'proc whatis {{args}} {{return {{{description}}}}}\nproc length {{args}} {{{body}}}\n'+tail
  p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
  self.assertEqual(p.stderr,'');return p.stdout
 def test_all_length_payloads_cover_success_and_failure(self):
  files=sorted(ISSUE.glob('*payload.tcl'));self.assertEqual(len(files),3)
  for path in files:
   expected='31.41592653589793' if path.name.startswith('regression') else '22.9782037'
   for desc,body,pass_expected in [('res is a 3D curve',f'return {{The length res is {expected}}}',True),('res is a','error must_not_measure',False),('res is a 3D curve','return {The length res is 1}',False),('res is a 3D curve','error measurement_failed',False),('res is a 3D curve','return malformed',False)]:
    with self.subTest(file=path.name,description=desc,body=body):
     out=self.branch(path,desc,body)
     self.assertEqual(out.count('__BENCH_ASSERT_PASS__ curve_length')+out.count('__BENCH_ASSERT_FAIL__ curve_length'),1)
     self.assertIn('__BENCH_ASSERT_PASS__ curve_length' if pass_expected else '__BENCH_ASSERT_FAIL__ curve_length',out)
if __name__=='__main__':unittest.main()
