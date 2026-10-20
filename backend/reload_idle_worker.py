"""Reload an identified worker only after proving it has no active task."""
import argparse
import json
import os
from pathlib import Path
import signal
import shlex
import subprocess
import time
from .app import DATA,ROOT,db
from .settings import SETTINGS

p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--session',required=True);p.add_argument('--worker-id',required=True);p.add_argument('--cpus',default='2,3');a=p.parse_args()
if not a.worker_id.replace('_','').replace('-','').replace('.','').isalnum():
    raise SystemExit('Invalid worker id')
try:
    cpus=[int(x) for x in a.cpus.split(',')]
except ValueError as error:
    raise SystemExit('CPUs must be comma-separated integers') from error
if not cpus or len(set(cpus))!=len(cpus) or any(x<0 or x>= (os.cpu_count() or 1) for x in cpus):
    raise SystemExit('Invalid or duplicate CPU selection')
path=DATA/'worker-status.json' if a.worker_id=='legacy' else DATA/'workers'/(a.worker_id+'.json')
while True:
    h=json.loads(path.read_text())
    if h['pid']!=a.pid:raise SystemExit('Worker identity changed; no action')
    ready=False
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        h=json.loads(path.read_text())
        active=c.execute("SELECT 1 FROM runs WHERE json_extract(payload,'$.status') IN ('preparing','running','collecting','evaluating') AND (json_extract(payload,'$.worker_id')=? OR json_extract(payload,'$.status')='preparing') LIMIT 1",(a.worker_id,)).fetchone()
        if h['pid']==a.pid and h['status']=='idle' and not active:
            cmdline=Path('/proc')/str(a.pid)/'cmdline'
            if b'backend.' not in cmdline.read_bytes():raise SystemExit('Unexpected worker process')
            os.kill(a.pid,signal.SIGTERM)
            ready=True
    if ready:break
    time.sleep(1)
module=['backend.worker','--request-limit','500'] if a.worker_id=='legacy' else ['backend.parallel_worker','--worker-id',a.worker_id,'--cpus',','.join(map(str,cpus)),'--request-limit','500']
launch=[str(SETTINGS.python),'-m',*module]
if SETTINGS.conda and SETTINGS.conda_env:
    launch=[str(SETTINGS.conda),'run','--no-capture-output','-n',SETTINGS.conda_env,'python','-m',*module]
log=DATA/f'{a.worker_id}-reloaded.log'
# Arguments are supplied by a trusted local operator, never an HTTP client.
command='exec '+shlex.join(launch)+' > '+shlex.quote(str(log))+' 2>&1'
subprocess.run(['tmux','respawn-pane','-k','-t',a.session+':0.0','-c',str(ROOT),command],check=True)
print('Reloaded idle worker '+a.worker_id,flush=True)
