"""Add an independently locked worker without disturbing the legacy worker."""
import argparse
import fcntl
import json
import os
import re
import time
from . import worker
from .app import DATA,get_run,rows
from .records import save
from .plan1a import finalize
from .dsh_config import cumulative_request_limit


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker-id',required=True)
    p.add_argument('--cpus',required=True,help='Two disjoint allowed logical CPUs, e.g. 2,3')
    p.add_argument('--request-limit',type=int)
    p.add_argument('--once',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',a.worker_id):p.error('invalid worker id')
    cpus={int(x) for x in a.cpus.split(',')}
    if len(cpus)!=2 or not cpus<=os.sched_getaffinity(0):p.error('exactly two allowed CPUs required')
    directory=DATA/'workers';directory.mkdir(exist_ok=True)
    with (directory/(a.worker_id+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        os.sched_setaffinity(0,cpus)
        def heartbeat(status,run_id=None):
            target=directory/(a.worker_id+'.json')
            temporary=target.with_suffix('.'+str(os.getpid())+'.tmp')
            temporary.write_text(json.dumps({'worker_id':a.worker_id,'pid':os.getpid(),'status':status,'run_id':run_id,'cpus':sorted(cpus),'at':time.time()}))
            temporary.replace(target)
        # Only this process gets a different heartbeat implementation.
        worker.heartbeat=heartbeat
        request_limit=cumulative_request_limit(a.request_limit)
        print(json.dumps({'worker_id':a.worker_id,'pid':os.getpid(),'cpus':sorted(cpus),'default_request_limit':request_limit}),flush=True)
        last_finalize=0
        try:
            while True:
                heartbeat('idle')
                item=worker.claim() # Existing SQLite BEGIN IMMEDIATE claim is process-safe.
                if item:
                    item.update(worker_id=a.worker_id,worker_cpus=sorted(cpus));save(item)
                    worker.run_task(item,request_limit)
                if item or time.monotonic()-last_finalize>10:
                    for study in rows('experiments'):
                        try:finalize(study['id'],lambda: (heartbeat('combination') or False))
                        except Exception as e:print('FINALIZE_ERROR='+type(e).__name__+': '+str(e),flush=True)
                    last_finalize=time.monotonic()
                if a.once:break
                time.sleep(2)
        finally:heartbeat('stopped')

if __name__=='__main__':main()
