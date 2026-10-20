"""Aggregate legacy and independent workers without overwriting their heartbeats."""
import json
import time
from pathlib import Path


def status(data, verified_override=None, *, explicit_launch=False):
    data=Path(data);workers=[]
    for path in [data/'worker-status.json',*sorted((data/'workers').glob('*.json'))]:
        try:
            h=json.loads(path.read_text())
            fresh=0<=time.time()-h['at']<30 and h['status'] in ('idle','busy','combination')
            if fresh:workers.append({**h,'worker_id':h.get('worker_id','legacy')})
        except (OSError,ValueError,KeyError,TypeError):continue
    verified=(data/'live-verified.json').is_file() if verified_override is None else bool(verified_override)
    return {'enabled':bool(workers and (verified or explicit_launch)),
            'verified':verified,'explicit_launch':bool(explicit_launch),
            'worker_online':bool(workers),'worker_status':'busy' if any(w['status']!='idle' for w in workers) else 'idle' if workers else 'offline',
            'worker_count':len(workers),'workers':workers}
