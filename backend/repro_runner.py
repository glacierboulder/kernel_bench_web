"""Agent-visible bounded command runner. No dependencies or network access."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time


def run(argv, wall=18, cpu=15, memory_mib=4096):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(memory_mib*1024**2,)*2)
        resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+1))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    started=time.monotonic()
    with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
        proc=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
        timed_out=False
        try:
            try:code=proc.wait(timeout=wall)
            except subprocess.TimeoutExpired:timed_out=True;code=None
        finally:
            # Clean the whole group even when its leader has already exited.
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait()
        def tail(f):
            f.seek(0,2);size=f.tell();f.seek(max(0,size-32768));return f.read().decode(errors='replace')
        return {'command':argv,'return_code':proc.returncode,'timed_out':timed_out,
                'wall_seconds':wall,'cpu_seconds':cpu,'address_space_mib':memory_mib,
                'elapsed_seconds':round(time.monotonic()-started,3),'stdout_tail':tail(out),'stderr_tail':tail(err)}


def main():
    p=argparse.ArgumentParser(description='Run a reproduction/debugger with local limits and process-group cleanup.')
    p.add_argument('--wall',type=int,default=18)
    p.add_argument('--cpu',type=int,default=15)
    p.add_argument('--memory-mib',type=int,default=4096)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();argv=a.command
    if argv and argv[0]=='--':argv=argv[1:]
    if not argv or not 1<=a.wall<=120 or not 1<=a.cpu<=60 or not 64<=a.memory_mib<=4096:p.error('command required; wall 1..120s, CPU 1..60s, address space 64..4096 MiB')
    result=run(argv,a.wall,a.cpu,a.memory_mib);print(json.dumps(result,ensure_ascii=False))
    return 0 if result['return_code']==0 and not result['timed_out'] else 1

if __name__=='__main__':raise SystemExit(main())
