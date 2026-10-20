"""Small operator status view without dumping reasoning, keys, or full tool output."""
import json
import sys
from .app import DATA, get_run

if __name__ == '__main__':
    run=get_run(sys.argv[1])
    calls=[]
    steps=[]
    for event in run['events']:
        try:
            payload=json.loads(event['message'])
        except (ValueError,TypeError):
            continue
        if payload.get('type')=='tool_call':
            argument=payload.get('input',{})
            calls.append({'tool':payload.get('tool'),'action':str(argument.get('description') or argument.get('command') or argument)[:220]})
        if payload.get('type')=='status' and payload.get('phase')=='step_end':
            steps.append(payload.get('step'))
    workspace=DATA/'runs'/run['id']/'agent-workspace'
    print(json.dumps({'id':run['id'],'status':run['status'],'session_id':run.get('session_id'),
                      'steps':steps[-1] if steps else 0,'events':len(run['events']),
                      'last_tools':calls[-4:],'compiled_objects':sum(1 for _ in (workspace/'build').rglob('*.o')),
                      'error':run.get('error'),'elapsed_seconds':run.get('elapsed_seconds'),
                      'checks':run.get('checks')},ensure_ascii=False,indent=2))
