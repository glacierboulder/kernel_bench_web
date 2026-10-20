"""Collect structured per-issue claims without treating claims as evaluation."""
import json
from pathlib import Path
import zipfile
from .submission import source_files

FIELDS=('issue_id','root_cause','evidence','changed_files','validation','limitations')

def collect(run,root,key=''):
    root=Path(root);workspace=root/'agent-workspace';p=workspace/'issue-reports.json'
    errors=[];reports=[]
    if p.is_symlink() or not p.is_file() or p.stat().st_size>1024**2:
        errors.append('issue-reports.json missing, symlink, or too large')
    else:
        try:
            reports=json.loads(p.read_text())
            if not isinstance(reports,list):raise ValueError('expected a list')
            expected={i['id'] for i in run['task']['issues']}
            if len(reports)!=len(expected) or {r.get('issue_id') for r in reports if isinstance(r,dict)}!=expected:
                errors.append('issue membership must match the fixed task exactly')
            for report in reports:
                if not isinstance(report,dict) or any(f not in report for f in FIELDS):
                    errors.append('missing report fields');continue
                if not isinstance(report['root_cause'],str) or not report['root_cause'].strip():errors.append('root_cause must state evidence or uncertainty')
                for f in ('evidence','changed_files','validation','limitations'):
                    if not isinstance(report[f],list):errors.append(f+' must be a list')
                if not report['evidence'] or not report['validation']:errors.append('evidence and validation cannot be empty')
                for name in report['changed_files']:
                    if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:errors.append('unsafe changed file path')
        except (ValueError,TypeError,AttributeError) as e:
            reports=[];errors.append(str(e))
    tests=workspace/'new-tests';files=[]
    if tests.exists() or tests.is_symlink():
        try:
            entries=source_files(tests)
            if sum(p.stat().st_size for p in entries.values())>5*1024**2:raise ValueError('new tests exceed 5 MiB')
            with zipfile.ZipFile(root/'new-tests.zip','w',zipfile.ZIP_DEFLATED) as z:
                for name,p in sorted(entries.items()):z.writestr(name,p.read_bytes().replace(key.encode(),b'[REDACTED]') if key else p.read_bytes());files.append(name)
        except ValueError as e:errors.append(str(e))
    result={'protocol':'issue-reports-v1','passed':not errors,'errors':errors,'reports':reports,'new_tests':files,
            'new_test_execution':'not automatically executed; requires independent evaluator admission',
            'claims_are_scores':False}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    (root/'issue-reports.json').write_text(text.replace(key,'[REDACTED]') if key else text)
    return json.loads((root/'issue-reports.json').read_text())
