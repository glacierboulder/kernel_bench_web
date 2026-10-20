"""Inert patch negative control: baseline must still fail #544, no model calls."""
import json
import secrets
from .app import DATA
from .evaluator import PROTO, evaluate_single

if __name__ == '__main__':
    root = DATA / 'offline-checks' / secrets.token_hex(6)
    root.mkdir(parents=True)
    name = 'src/FoundationClasses/TKernel/Standard/Standard.cxx'
    first = (PROTO / 'tasks/task_single/repo' / name).read_text().splitlines()[0]
    (root / 'patch.diff').write_text('--- a/'+name+'\n+++ b/'+name+'\n@@ -1 +1,2 @@\n+// Inert offline isolation control; does not repair the benchmark.\n '+first+'\n')
    (root / 'report.md').write_text('Offline negative control. No model, no bug fix, expected baseline failure.\n')
    print('OFFLINE_CONTROL='+str(root), flush=True)
    code, result = evaluate_single(root)
    summary = {'exit_code': code, 'passed': result.get('passed'), 'tests': result.get('tests', []),
               'build_ok': bool(result.get('build', {}).get('build') and result['build']['build']['return_code'] == 0)}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if not summary['build_ok'] or not summary['tests'] or summary['passed']:
        raise SystemExit('Offline negative control failed to establish the expected baseline behavior')
    (DATA/'offline-control.json').write_text(json.dumps(dict(root=str(root),**summary),indent=2))
