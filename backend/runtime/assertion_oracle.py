"""V4 assertion semantics, extracted without changing geometric predicates."""
import re

MARKER_RE=re.compile(r'^BENCH_ASSERT_(PASS|FAIL)\s+(\S+)\b.*\bkind=(expression|numeric)\b',re.M)
SUMMARY_RE=re.compile(r'^BENCH_ORACLE_OK assertions=(\d+) numeric_assertions=(\d+)\s*$',re.M)
DONE_RE=re.compile(r'^TEST_DONE assertions=(\d+) numeric_assertions=(\d+)\s*$',re.M)

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

