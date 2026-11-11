"""Read-only authoring contract audit; no model, database, source build or Linux sandbox."""
from pathlib import Path
import argparse,importlib.util,json,os,shutil,sys,tempfile

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from backend.catalog import validate_bundle,public_task
from backend.freeze import normalize_suite_case_material
from backend.occt_runtime import configuration,install
from backend.runtime.assertion_oracle import apply_pending_requirements

ISSUES=(23933,23981,23985,23998,25337,24220,29038,30198)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--root',type=Path,default=REPO/'benchmarks/occt')
 args=parser.parse_args();root=args.root
 active_counts=validate_bundle(root)['counts']
 registration=json.loads((root/'evaluation/provenance/authoring-20261110/candidate-registration.json').read_text(encoding='utf-8'))
 assert registration['status']=='candidate_only_not_registered'
 review_temp=tempfile.TemporaryDirectory(prefix='occt-candidate-review-')
 review_root=Path(review_temp.name)/'bundle'
 shutil.copytree(root,review_root)
 catalog_file=review_root/'catalog.json';candidate_catalog=json.loads(catalog_file.read_text(encoding='utf-8'))
 for key in ['issues','groups','evaluation_suites']:
  assert not set(x['id'] for x in registration[key]) & set(x['id'] for x in candidate_catalog[key])
  candidate_catalog[key].extend(registration[key])
 catalog_file.write_text(json.dumps(candidate_catalog,ensure_ascii=False),encoding='utf-8')
 locks=review_root/'sources.lock.json';value=json.loads(locks.read_text(encoding='utf-8'));value['sources'].extend(registration['sources']);locks.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
 root=review_root
 bundle=validate_bundle(root);catalog=json.loads((root/'catalog.json').read_text(encoding='utf-8'))
 rows=[]
 for number in ISSUES:
  group=bundle['groups'][(f'occt-single-{number}','1')]
  suite=bundle['suites'][(group['evaluation_suite']['id'],'1')]
  card=json.dumps(public_task(bundle,group),ensure_ascii=False)
  assert 'reference.patch' not in card and 'oracle_helpers' not in card
  assert len(suite['checkpoints'])==4
  assert sum(cp['category']=='neighborhood' for cp in suite['checkpoints'])==2
  with tempfile.TemporaryDirectory(prefix='authoring-contract-') as temp:
   work=Path(temp);cases=work/'cases/bundle'
   frozen,aliases=normalize_suite_case_material(bundle,catalog,suite,cases)
   contract=configuration(root,frozen,case_root=cases)
   assert contract and contract['standard_build']
   control=work/'control'
   (control/'scripts').mkdir(parents=True)
   (control/'private/evaluators').mkdir(parents=True)
   install(root,frozen,control,assets_root=control/'evaluator_assets',case_root=cases,
           build_target=control/'private/evaluators/run_eval.py',draw_target=control/'scripts/run_draw_case.py')
   spec=importlib.util.spec_from_file_location(f'authoring_adapter_{number}',control/'scripts/run_draw_case.py')
   adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
   frozen_contract=adapter._contract();previous=os.environ.get('BENCH_FROZEN_CASE_ROOT')
   os.environ['BENCH_FROZEN_CASE_ROOT']=str(cases)
   try:
    for cp in frozen['checkpoints']:
     route=adapter._route(cases/cp['case'],frozen_contract)
     assert route['expected_assertion_ids']==cp['runner_options']['expected_assertion_ids']
     adapter._asset(route['engine'])
     blocked=apply_pending_requirements({'passed':True,'status':'geometry_pass'},route)
     assert not blocked['passed'] and blocked['status']=='inconclusive'
    # An edited frozen test must be rejected before geometry dispatch.
    changed=cases/frozen['checkpoints'][0]['case']
    changed.write_bytes(changed.read_bytes()+b'\n# deliberate author audit tamper\n')
    try:adapter._route(changed,frozen_contract)
    except ValueError:pass
    else:raise AssertionError('tampered checkpoint was accepted')
   finally:
    if previous is None:os.environ.pop('BENCH_FROZEN_CASE_ROOT',None)
    else:os.environ['BENCH_FROZEN_CASE_ROOT']=previous
   # Emulate the actual public-workspace flattening, not the source-tree layout.
   issue=bundle['issues'][(f'occt-{number}','1')]
   issue_root=root/f'issues/occt-{number}/1';visible=work/'visible';visible.mkdir()
   for relative in issue['public_materials']:
    asset=issue_root/relative
    shutil.copyfile(asset,visible/asset.name)
    if relative!='public/reproduce.tcl':assert (cases/f'issues/occt-{number}/1'/relative).is_file()
   repro=(visible/'reproduce.tcl').read_text(encoding='utf-8')
   assert 'file isdirectory $inputs' in repro
   assert 'evaluation/cases' not in repro
   assert not any('reference.patch' in p.name or 'neighbor' in p.name for p in visible.iterdir())
   rows.append({'issue':number,'frozen_routes':4,'support_files':len(suite['support_files']),
                'tampered_case_rejected':True,'pending_blocks_formal_pass':True,
                'public_inputs_present_in_private_bundle':True,'public_material_flattening_checked':True})
 print(json.dumps({'ok':True,'tasks':len(rows),'routes':sum(x['frozen_routes'] for x in rows),
                   'builds_run':0,'model_calls':0,'linux_sandbox_runs':0,'registration_performed':False,'active_catalog_counts':active_counts,'candidate_review_counts':bundle['counts'],'results':rows},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
