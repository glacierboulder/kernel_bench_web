from pathlib import Path
import subprocess,re,unittest
ROOT=Path(__file__).resolve().parents[1]
class ConeBranches(unittest.TestCase):
 def test_each_order_emits_exactly_one_truthful_assertion(self):
  for path in sorted((ROOT/'benchmarks/occt/issues/occt-33244/1').glob('neighborhood_*.tcl')):
   for good1,good2 in [(True,True),(False,False),(True,False),(False,True)]:
    # isdraw output is determined per operand order, including rejected third curve.
    values={prefix+suffix: int(good and suffix!='_3') for prefix,good in [('ii',good1),('jj',good2)] for suffix in ['_1','_2','_3']}
    commands='proc pload {args} {}\nproc cone {args} {}\nproc intersect {args} {}\narray set present {'+' '.join(f'{k} {v}' for k,v in values.items())+'}\nproc isdraw {name} {global present;return $present($name)}\n'
    p=subprocess.run(['tclsh'],input=commands+path.read_text(),text=True,capture_output=True,check=True);self.assertEqual(p.stderr,'')
    events=re.findall(r'BENCH_ASSERT_(PASS|FAIL) (order_s[12]_s[12])',p.stdout)
    with self.subTest(path=path.name,good1=good1,good2=good2):
     self.assertEqual(events,[('PASS' if good1 else 'FAIL','order_s1_s2'),('PASS' if good2 else 'FAIL','order_s2_s1')])
if __name__=='__main__':unittest.main()
