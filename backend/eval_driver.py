"""Trusted sandbox entrypoint. Build once; run only selected suites and regressions."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--suites', nargs='+', required=True, choices=['single','visible3','visible4','visible5','visible5all'])
    p.add_argument('--baseline', action='store_true')
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location('original','/evaluation/private/evaluators/run_eval.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    out={'protocol':'plan1a-eval-v1','suites':a.suites,'baseline':a.baseline,'tests':[], 'limitations':['Visible checks plus analytic box Boolean regression; not the full upstream suite.','Termination checks do not establish full geometric correctness.']}
    started=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='plan1a-') as tmp:
            source=Path(tmp)/'source';shutil.copytree(m.SOURCE,source)
            if not a.baseline:
                report=Path('/workspace/submission/report.md')
                out['report']={'provided':report.is_file() and report.stat().st_size>0}
                if not out['report']['provided']: raise ValueError('report missing or empty')
                out['patch_bytes']=m.apply_patch(source,'/workspace/submission/patch.diff')
            build=Path(tmp)/'build';out['build']=m.configure_and_build(source,build)
            if not out['build'].get('build') or out['build']['build']['return_code']!=0:
                out['failure_stage']='build'
            else:
                for suite in a.suites:
                    if suite in ('single','visible3'):
                        m.run_issue_544(source,build,out['tests'],'task_group_visible3' if suite=='visible3' else 'task_single')
                    if suite=='visible3':
                        m.run_issue_506(source,build,out['tests'],'task_group_visible3',visible=True)
                        m.run_issue_847(source,build,out['tests'])
                    if suite=='visible4':m.run_issue_690_693_172(source,build,out['tests'])
                    if suite=='visible5':m.run_issue_370_872_1452(source,build,out['tests'])
                    if suite=='visible5all':
                        m.run_issue_690_693_172(source,build,out['tests'],'task_group_visible5all')
                        m.run_issue_370_1452(source,build,out['tests'],'task_group_visible5all')
                m.run_cpp_visible(source,build,'regressions','analytic_boxes',out['tests'],'regression_analytic_boxes',
                    ['-lTKBO','-lTKPrim','-lTKTopAlgo','-lTKBRep','-lTKGeomBase','-lTKG3d','-lTKMath','-lTKernel'],timeout=18)
    except (ValueError,OSError) as e:
        out['failure_stage']='submission' if isinstance(e,ValueError) else 'infrastructure'
        out['error']=str(e)
    out['elapsed_seconds']=round(time.monotonic()-started,3)
    out['passed']=bool(out['tests']) and all(x['passed'] for x in out['tests']) and not out.get('failure_stage')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
