#!/usr/bin/env python3
"""Checkpoint-locked adapter for the OCCT single-v3 DRAW runner contract."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path, PurePosixPath

MARKER_RE=re.compile(r'^BENCH_ASSERT_(PASS|FAIL)\s+(\S+)\b.*\bkind=(expression|numeric)\b',re.M)
SUMMARY_RE=re.compile(r'^BENCH_ORACLE_OK assertions=(\d+) numeric_assertions=(\d+)\s*$',re.M)
DONE_RE=re.compile(r'^TEST_DONE assertions=(\d+) numeric_assertions=(\d+)\s*$',re.M)

def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def asset_root()->Path:
    control=Path(__file__).resolve().parents[1]
    return control/'private'/'evaluator_assets'/'occt_single_v4'

def load_lock()->dict:
    root=asset_root(); path=root/'dispatch_lock.json'
    if path.is_symlink() or not path.is_file(): raise ValueError('single-v3 dispatch lock is missing')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version')!=1 or value.get('routing_contract')!='occt-single-v4-explicit-checkpoint-v1':
        raise ValueError('unsupported single-v3 dispatch lock')
    payload={key:item for key,item in value.items() if key!='lock_sha256'}
    digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    if digest!=value.get('lock_sha256'):
        raise ValueError('single-v3 dispatch lock hash mismatch')
    return value

def route_for(case_file:Path, lock:dict)->tuple[str,dict]:
    control=Path(__file__).resolve().parents[1]
    case_root=Path(os.environ.get('BENCH_FROZEN_CASE_ROOT', str(control/'cases'/'bundle'))).resolve(strict=True)
    case=case_file.resolve(strict=True)
    if not case.is_file() or not case.is_relative_to(case_root):
        raise ValueError('case path is outside the frozen bundle')
    relative=case.relative_to(case_root).as_posix()
    route=lock.get('checkpoint_routes',{}).get(relative)
    if route is None: raise ValueError('unknown checkpoint case route')
    if _sha(case)!=route.get('case_sha256'): raise ValueError('checkpoint case hash mismatch')
    return relative,route

def validate_base_result(base:dict, route:dict)->dict:
    """Require the exact locked assertion IDs plus framework summary/error checks."""
    stdout=str(base.get('stdout_tail','')); stderr=str(base.get('stderr_tail','')); joined=stdout+'\n'+stderr
    events=MARKER_RE.findall(joined)
    expected=route.get('expected_assertion_ids',[])
    ids=[event[1] for event in events]
    summary=list(SUMMARY_RE.finditer(joined)); done=list(DONE_RE.finditer(joined))
    sentinel=sum(1 for line in joined.splitlines() if line=='__BENCH_ORACLE_COMPLETE__')
    missing=sorted(set(expected)-set(ids)); unexpected=sorted(set(ids)-set(expected))
    duplicates=sorted(item for item in set(ids) if ids.count(item)!=1)
    summary_pair=bool(len(summary)==1 and len(done)==1 and summary[0].groups()==done[0].groups()
                      and int(summary[0].group(1))==len(expected)
                      and int(summary[0].group(2))==sum(1 for _,_,kind in events if kind=='numeric'))
    contract_valid=(sentinel==1 and summary_pair and len(events)==len(expected)
                    and not missing and not unexpected and not duplicates)
    assertions_pass=all(status=='PASS' for status,_id,_kind in events)
    base_clean=(base.get('return_code')==0 and not base.get('timed_out')
                and not base.get('tcl_error_detected') and not base.get('occt_error_detected'))
    structural=contract_valid and assertions_pass
    passed=contract_valid and assertions_pass and base_clean and bool(base.get('passed'))
    expected_errors=route.get('expected_failure_lines',[])
    expected_error_seen=any(signature and signature in joined for signature in expected_errors)
    if passed: status='geometry_pass'
    elif (contract_valid and base.get('return_code')==0 and not base.get('timed_out')
          and not base.get('tcl_error_detected') and base.get('occt_error_detected') and expected_error_seen):
        status='geometry_fail'
    elif base.get('timed_out'): status='timeout_unmeasured'
    elif base.get('tcl_error_detected'): status='runner_error'
    elif base.get('occt_error_detected'): status='runtime_error'
    elif not structural: status='oracle_incomplete'
    else: status='runner_error'
    return {'passed':passed,'status':status,'checkpoint_id':route.get('checkpoint_id'),
            'category':route.get('category'),'expected_assertion_ids':expected,
            'observed_assertion_events':[{'status':s,'id':i,'kind':k} for s,i,k in events],
            'missing_assertions':missing,'unexpected_assertions':unexpected,'duplicate_assertions':duplicates,
            'completion_sentinel_count':sentinel,'summary_pair_valid':summary_pair,
            'expected_geometry_failure_signature_seen':expected_error_seen,
            'base_runner':base}

def _reject(reason:str, *, status='runner_error')->int:
    print(json.dumps({'protocol':'occt_single_v4_draw_case_v1','passed':False,'test_done_marker':False,
                      'return_code':1,'timed_out':False,'status':status,'error':reason},ensure_ascii=False))
    return 1

def main()->int:
    parser=argparse.ArgumentParser()
    for name in ('build-dir','resource-dir','case-dir'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--script',default='reproduce.tcl')
    parser.add_argument('--timeout-seconds',type=int,required=True)
    parser.add_argument('--cpu-limit-seconds',type=int,required=True)
    parser.add_argument('--address-space-gib',type=int,default=4)
    args=parser.parse_args()
    try:
        lock=load_lock()
        case_file=Path(args.case_dir)/args.script
        relative,route=route_for(case_file,lock)
        base_runner=asset_root()/'draw_case_v1_base.py'
        if base_runner.is_symlink() or not base_runner.is_file() or _sha(base_runner)!=lock.get('base_runner_sha256'):
            raise ValueError('locked framework draw_case_v1 base runner is missing or changed')
        command=[sys.executable,str(base_runner),'--build-dir',args.build_dir,'--resource-dir',args.resource_dir,
                 '--case-dir',args.case_dir,'--script',args.script,
                 '--timeout-seconds',str(args.timeout_seconds),'--cpu-limit-seconds',str(args.cpu_limit_seconds),
                 '--address-space-gib',str(args.address_space_gib)]
        proc=subprocess.run(command,cwd=Path(args.case_dir),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            text=True,timeout=args.timeout_seconds+8,check=False)
        try: base=json.loads(proc.stdout)
        except json.JSONDecodeError as exc: raise ValueError('framework draw_case_v1 returned invalid JSON') from exc
        checked=validate_base_result(base,route)
        checked.update({'protocol':'occt_single_v4_draw_case_v1','return_code':0 if checked['passed'] else 1,
                        'test_done_marker':bool(checked['passed']),'timed_out':bool(base.get('timed_out')),
                        'case_relative_path':relative,'case_sha256':route['case_sha256'],
                        'adapter_sha256':_sha(Path(__file__).resolve()),'lock_sha256':lock['lock_sha256'],
                        'adapter_process_return_code':proc.returncode})
        print(json.dumps(checked,ensure_ascii=False))
        return 0 if checked['passed'] else 1
    except subprocess.TimeoutExpired:
        return _reject('framework DRAW runner adapter timed out',status='timeout_unmeasured')
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
        return _reject(str(exc))

if __name__=='__main__': raise SystemExit(main())
