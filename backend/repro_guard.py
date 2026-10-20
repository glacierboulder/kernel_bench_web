"""Host fallback for native executables built inside an agent workspace."""
import json
import os
from pathlib import Path
import resource
import signal
import time

class ReproGuard:
    def __init__(self,workspace):
        self.workspace=Path(workspace).resolve();self.seen={}
        self.audit=self.workspace.parent/'repro-resource-events.jsonl'

    def check(self,pids):
        for pid in pids:
            try:
                exe=os.readlink(f'/proc/{pid}/exe')
                # Build tools and the DSH/Python runtime live outside /workspace.
                if not (exe.startswith(str(self.workspace)+'/') or exe.startswith('/workspace/')):continue
                fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
                key=(pid,fields[19]);born=self.seen.setdefault(key,time.monotonic())
                rss=int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
                # Kernel limits also constrain allocations between monitor samples.
                for kind,cap in [(resource.RLIMIT_AS,4*1024**3),(resource.RLIMIT_CPU,60)]:
                    soft,hard=resource.prlimit(pid,kind)
                    bound=cap if hard==resource.RLIM_INFINITY else min(hard,cap)
                    resource.prlimit(pid,kind,(bound if soft==resource.RLIM_INFINITY else min(soft,bound),bound))
                reason='rss' if rss>3*1024**3 else 'wall' if time.monotonic()-born>120 else None
                if reason:
                    # Never kill the DSH's shared group: target only this subtree.
                    from .sandbox import descendants
                    targets=descendants(pid)
                    for child in targets:
                        try:os.kill(child,signal.SIGKILL)
                        except ProcessLookupError:pass
                    event={'pid':pid,'executable':exe,'reason':reason,'rss_bytes':rss,'rss_limit_bytes':3*1024**3,'wall_limit_seconds':120,'at_unix':time.time()}
                    fd=os.open(self.audit,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
                    with os.fdopen(fd,'a') as f:f.write(json.dumps(event)+'\n')
            except (OSError,ValueError,IndexError):continue
