"""Verify every common-runtime suite through fresh freeze and control setup."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.catalog import public_task,validate_bundle
from backend.evaluator import _prepare_control
from backend.freeze import freeze_catalog_task,verify_snapshot
from backend.settings import SETTINGS
from backend.occt_runtime import enabled,RUNTIME

bundle=validate_bundle(SETTINGS.benchmark_root)
selected=[g for g in bundle['groups'].values() if enabled(bundle['root'],bundle['suites'][(g['evaluation_suite']['id'],g['evaluation_suite']['version'])])]
if not selected:raise ValueError('no common-runtime groups registered')
results=[]
for group in selected:
    with tempfile.TemporaryDirectory(prefix='occt-freeze-') as directory:
        run=Path(directory);manifest=freeze_catalog_task(public_task(bundle,group),run)
        snapshot=run/'benchmark-snapshot';verify_snapshot(snapshot)
        suite=json.loads((snapshot/'suite.json').read_text())
        control,source=_prepare_control(run,None,[suite],group['kind'],group['source_id'],snapshot)
        adapter_path=control/'scripts/run_draw_case.py'
        assert adapter_path.read_bytes()==(RUNTIME/'occt_adapter.py').read_bytes()
        assert adapter_path.read_bytes()==(control/'private/evaluators/run_eval.py').read_bytes()
        for name in ('run_draw_case.py','public_build.py','build.sh'):
            expected={'run_draw_case.py':'public_draw.py','public_build.py':'public_build.py','build.sh':'build.sh'}[name]
            assert (snapshot/'tools'/name).read_bytes()==(RUNTIME/expected).read_bytes()
        assert not (snapshot/'tools/contract.json').exists()
        spec=importlib.util.spec_from_file_location('frozen_common_adapter',adapter_path)
        adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
        contract=adapter._contract();cases=control/'cases/bundle'
        previous=os.environ.get('BENCH_FROZEN_CASE_ROOT')
        os.environ['BENCH_FROZEN_CASE_ROOT']=str(cases)
        try:
            for cp in suite['checkpoints']:
                route=adapter._route(cases/cp['case'],contract)
                assert route['checkpoint_id']==cp['id']
                adapter._asset(route['engine'])
        finally:
            if previous is None:os.environ.pop('BENCH_FROZEN_CASE_ROOT',None)
            else:os.environ['BENCH_FROZEN_CASE_ROOT']=previous
        # The direct setup path must use the same implementation too.
        direct=run/'direct';direct.mkdir()
        raw_suite=bundle['suites'][(suite['id'],suite['version'])]
        dc,_=_prepare_control(direct,None,[raw_suite],group['kind'],group['source_id'])
        assert (dc/'scripts/run_draw_case.py').read_bytes()==adapter_path.read_bytes()
        row={'group_id':group['id'],'suite_id':suite['id'],'checkpoints':len(suite['checkpoints']),
             'snapshot_sha256':manifest['snapshot_sha256'],'adapter_sha256':hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
             'frozen_and_direct_controls_match':True,'public_tools_unified':True}
        results.append(row);print(json.dumps(row),flush=True)
print(json.dumps({'groups':len(results),'dispatcher_routes_validated':sum(r['checkpoints'] for r in results),
                  'unique_adapter_hashes':len({r['adapter_sha256'] for r in results}),'builds_run':0,'paid_model_calls':0}),flush=True)
