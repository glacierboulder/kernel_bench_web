#!/usr/bin/env python3
"""One frozen adapter for OCCT build dispatch and checkpoint execution.

The supervisor provides an explicit writable case root. Geometry engines remain
hash-locked assets; they do not choose paths, limits or checkpoint identities.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

PROTOCOL='occt-checkpoint-v1'

def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def _assets():
    for parent in Path(__file__).resolve().parents:
        for root in (parent/'evaluator_assets',parent/'private/evaluator_assets'):
            if (root/'unified_runtime/contract.json').is_file(): return root
    raise ValueError('frozen OCCT runtime contract is missing')

def _safe(root,relative):
    rel=PurePosixPath(relative)
    if not relative or rel.is_absolute() or '\\' in relative or any(p in {'.','..'} for p in rel.parts):
        raise ValueError('unsafe runtime asset path')
    p=root.joinpath(*rel.parts)
    if p.is_symlink(): raise ValueError('runtime symlink is not permitted')
    p=p.resolve(strict=True)
    if not p.is_relative_to(root.resolve()) or not p.is_file(): raise ValueError('runtime asset escapes its root')
    return p

def _contract():
    c=json.loads((_assets()/'unified_runtime/contract.json').read_text())
    if c.get('schema_version')!=1: raise ValueError('unsupported OCCT runtime contract')
    return c

def _asset(route):
    path=_safe(_assets(),route['path'])
    if _sha(path)!=route['sha256']: raise ValueError('locked OCCT runtime asset hash mismatch: '+route['path'])
    return path

def _load(route):
    p=_asset(route);name='occt_asset_'+route['sha256'][:16]
    spec=importlib.util.spec_from_file_location(name,p)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def _build_helper():
    c=_contract()
    try:suite=Path(sys.argv[sys.argv.index('--suite')+1])
    except (ValueError,IndexError) as exc:raise ValueError('frozen --suite is required for build dispatch') from exc
    s=json.loads(suite.read_text())
    if f"{s['id']}@{s['version']}"!=c['suite'] or c['group_id'] not in s['group_ids']:
        raise ValueError('build suite differs from runtime contract')
    jobs=int(os.environ.get('BENCH_COMPILER_JOBS','2'))
    if not 1<=jobs<=2: raise ValueError('compiler jobs must be 1 or 2')
    return _load(c['build_helper'])

def apply_patch(source,patch_arg):return _build_helper().apply_patch(source,patch_arg)
def configure_and_build(source,build):return _build_helper().configure_and_build(source,build)

def validate_draw_text(*args,**kwargs):
    return _load(_contract()['geometry_helper']).validate_draw_text(*args,**kwargs)

def _route(case_file,c):
    explicit=os.environ.get('BENCH_FROZEN_CASE_ROOT')
    if not explicit: raise ValueError('supervisor must supply BENCH_FROZEN_CASE_ROOT')
    root=Path(explicit).resolve(strict=True);case=case_file.resolve(strict=True)
    if not case.is_file() or not case.is_relative_to(root):raise ValueError('case path is outside the frozen bundle')
    relative=case.relative_to(root).as_posix()
    matches=[r for r in c['checkpoints'].values() if r['case']==relative]
    if len(matches)!=1:raise ValueError('case has no unique checkpoint route')
    route=matches[0]
    if _sha(case)!=route['case_sha256']:raise ValueError('checkpoint case hash mismatch')
    return route

def _normalize(raw,process_code,route):
    # Preserve raw evidence and the original verdict. Never treat return code 0
    # or mere process completion as a successful geometric oracle.
    staged=raw.get('schema_version') in {'bf-group2-staged-run-v1','bf-group3-staged-run-v1'}
    oracle_status=raw.get('oracle',{}).get('status') if staged else raw.get('status')
    code=raw.get('process_return_code') if staged else raw.get('return_code')
    timeout=bool(raw.get('timed_out')) or oracle_status in {'timeout','timeout_unmeasured'} or (staged and code==3)
    passed=(process_code==0 and not timeout and
            (oracle_status=='geometry_pass' if staged else raw.get('passed',raw.get('test_done_marker',False)) is True and code==0))
    if oracle_status in {'geometry_pass','geometry_fail'}:
        ran=True;status=oracle_status if not passed else 'geometry_pass'
        if status=='geometry_pass' and not passed:status='runner_error';ran=False
    elif timeout:ran=False;status='timeout'
    elif raw.get('error') or oracle_status in {'runner_error','oracle_incomplete','runtime_error','not_run'}:
        ran=False;status=oracle_status or 'runner_error'
    elif staged:
        ran=False;status='not_run'
    else:
        # Legacy strict runners explicitly return passed/test_done_marker only
        # after validating their oracle. Their failure diagnostics remain raw.
        ran=passed or (raw.get('oracle_summary_found') is True and not raw.get('tcl_error_detected'))
        status='geometry_pass' if passed else 'geometry_fail' if ran else 'oracle_incomplete'
    return {'protocol':PROTOCOL,'checkpoint_id':route['checkpoint_id'],'category':route['category'],
            'passed':passed,'status':status,'oracle_ran':ran,'return_code':0 if passed else 1,
            'test_done_marker':passed,'timed_out':timeout,'runner_process_return_code':process_code,
            'elapsed_seconds':raw.get('elapsed_seconds',raw.get('duration_seconds')),'raw_result':raw}

def main():
    p=argparse.ArgumentParser()
    for n in ('build-dir','resource-dir','case-dir'):p.add_argument('--'+n,required=True)
    p.add_argument('--script',default='reproduce.tcl')
    p.add_argument('--timeout-seconds',type=int,required=True);p.add_argument('--cpu-limit-seconds',type=int,required=True)
    p.add_argument('--address-space-gib',type=int,default=4)
    a=p.parse_args()
    try:
        if not 1<=a.timeout_seconds<=3600 or not 1<=a.cpu_limit_seconds<=3600 or not 1<=a.address_space_gib<=32:
            raise ValueError('runtime limits out of range')
        c=_contract();r=_route(Path(a.case_dir)/a.script,c);engine=r['engine'];runner=_asset(engine)
        argv=[sys.executable,str(runner),*sys.argv[1:]]
        if engine.get('role'):argv+=['--role',engine['role']]
        # Original g3 oracle locates a compatible run_eval.py near its assets;
        # preserve that helper in the engine subtree (never this dispatcher).
        env=os.environ.copy()
        toolchain=env.get('BENCH_TOOLCHAIN_NAME','clang')
        lib=Path(a.build_dir).resolve()/'lin64'/toolchain/'lib'
        # Legacy env.sh scripts can derive incorrect paths from CASROOT. Keep
        # the selected build's libraries explicit before their bootstrap runs.
        env['LD_LIBRARY_PATH']=os.pathsep.join(x for x in (str(lib),env.get('BENCH_EXTRA_LIBRARY_PATH',''),env.get('LD_LIBRARY_PATH','')) if x)
        env['CSF_OCCTLibPath']=str(lib)
        resources=Path(a.resource_dir).resolve()
        if not (resources/'DrawResources').is_dir(): resources=resources/'src'
        env['DRAWDEFAULT']=str(resources/'DrawResources/DrawDefault')
        env['DRAWHOME']=str(resources/'DrawResources')
        env['CSF_DrawPluginDefaults']=str(resources/'DrawResources')
        env['CSF_OCCTResourcePath']=str(resources)
        proc=subprocess.run(argv,cwd=a.case_dir,env=env,text=True,capture_output=True,timeout=a.timeout_seconds+8)
        raw=json.loads(proc.stdout)
        if engine['kind']=='assertions':
            path=_assets()/'unified_runtime/assertion_oracle.py'
            spec=importlib.util.spec_from_file_location('occt_assertion_oracle',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            raw=module.validate_base_result(raw,r)
            raw['status']=module.completed_failure_status(raw)
            raw['return_code']=0 if raw['passed'] else 1
        out=_normalize(raw,proc.returncode,r)
        out.update(case_sha256=r['case_sha256'],adapter_sha256=_sha(Path(__file__)))
    except subprocess.TimeoutExpired:
        out={'protocol':PROTOCOL,'passed':False,'status':'timeout','oracle_ran':False,'return_code':1,'test_done_marker':False,'timed_out':True}
    except (OSError,ValueError,KeyError,ImportError) as exc:
        out={'protocol':PROTOCOL,'passed':False,'status':'runner_error','oracle_ran':False,'return_code':1,'test_done_marker':False,'timed_out':False,'error':str(exc)}
    print(json.dumps(out,ensure_ascii=False))
    return 0 if out['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
