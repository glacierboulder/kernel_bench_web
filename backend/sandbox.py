"""Outer bubblewrap boundary: explicit mounts, no host home, no network."""
import os
import json
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
from .settings import SETTINGS

CONDA = SETTINGS.python_prefix
PYTHON = str(SETTINGS.python)
TOOLCHAIN_ROOT = SETTINGS.conda.parent.parent if SETTINGS.conda else CONDA


def command(workspace, *, mounts=(), env=None, cwd='/workspace'):
    workspace = Path(workspace).resolve()
    for name in ['tmp', 'home']:
        (workspace / name).mkdir(parents=True, exist_ok=True)
    env_binary=shutil.which('env')
    bwrap=SETTINGS.config.get('tools',{}).get('bubblewrap') or shutil.which('bwrap')
    if not env_binary or not bwrap:
        raise RuntimeError('isolated execution requires env and bubblewrap on PATH or in config')
    args = [env_binary, '-i', bwrap, '--unshare-all', '--die-with-parent', '--new-session',
            '--cap-drop', 'ALL']
    for path in ['/usr', '/bin', '/lib', '/lib64']:
        if Path(path).exists():
            args += ['--ro-bind', path, path]
    args += ['--ro-bind', str(TOOLCHAIN_ROOT), str(TOOLCHAIN_ROOT), '--proc', '/proc', '--dev', '/dev',
             '--bind', str(workspace / 'tmp'), '$BENCH_TMP_DIR', '--tmpfs', '/run', '--dir', '/etc',
             '--bind', str(workspace / 'home'), '/home/agent',
             '--bind', str(Path(workspace).resolve()), '/workspace']
    for source, dest, writable in mounts:
        args += ['--bind' if writable else '--ro-bind', str(Path(source).resolve()), dest]
    variables = {'HOME': '/home/agent', 'USER': 'agent', 'LOGNAME': 'agent',
                 'PATH': str(SETTINGS.python.parent) + ':/usr/local/bin:/usr/bin:/bin',
                 'LANG': 'C.UTF-8', 'TMPDIR': '/workspace$BENCH_TMP_DIR', 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2',
                 'CONDA_PREFIX': str(CONDA), 'PYTHONNOUSERSITE': '1',
                 'NODE_OPTIONS': '--max-old-space-size=1024'}
    variables.update(env or {})
    for key, value in variables.items():
        args += ['--setenv', key, str(value)]
    return args + ['--remount-ro', '/', '--chdir', cwd]


def limits():
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1805))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (512, 512))
    resource.setrlimit(resource.RLIMIT_AS, (32 * 1024**3,) * 2)


def stop(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


def descendants(root):
    found = {root}
    facts = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            # comm may contain spaces or ')'; the trailing fields are authoritative.
            fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            facts.append((int(p.name), int(fields[1])))
        except (OSError, ValueError, IndexError):
            continue
    while True:
        added = {pid for pid, parent in facts if parent in found} - found
        if not added:
            break
        found.update(added)
    return found


def monitor(proc, timeout, cancel=lambda: False, disk_root=None, *, guard_reproductions=False):
    deadline = time.monotonic() + timeout
    last_disk = 0
    from .repro_guard import ReproGuard
    guard=ReproGuard(disk_root) if guard_reproductions and disk_root else None
    try:
        while proc.poll() is None:
            if cancel():
                raise RuntimeError('cancelled')
            if time.monotonic() >= deadline:
                raise TimeoutError('wall clock budget exceeded')
            processes = descendants(proc.pid)
            if guard:guard.check(processes)
            rss = 0
            for pid in processes:
                try:
                    rss += int(Path(f'/proc/{pid}/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                except (OSError, ValueError, IndexError):
                    pass
            if len(processes) > 128 or rss > 12 * 1024**3:
                reason='process_count' if len(processes)>128 else 'rss_sum'
                evidence={'reason':reason,'process_count':len(processes),'rss_sum_bytes':rss,
                          'process_limit':128,'rss_sum_limit_bytes':12*1024**3,
                          'rss_accounting':'sum of per-process RSS; shared pages may be counted repeatedly',
                          'at_unix':time.time(),'processes':[]}
                for pid in sorted(processes):
                    try:
                        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
                        evidence['processes'].append({'pid':pid,'ppid':int(fields[1]),'state':fields[0],
                            'comm':Path(f'/proc/{pid}/comm').read_text().strip(),
                            'rss_bytes':int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')})
                    except (OSError,ValueError,IndexError):pass
                if disk_root:
                    try:(Path(disk_root).parent/('resource-limit-'+Path(disk_root).name+'.json')).write_text(json.dumps(evidence,indent=2))
                    except OSError:pass
                raise RuntimeError(f'resource budget exceeded: {reason}; process_count={len(processes)}/128; rss_sum_bytes={rss}/{12*1024**3}')
            if disk_root and time.monotonic() - last_disk > 20:
                total = 0
                for parent, dirs, files in os.walk(disk_root, followlinks=False):
                    for name in files:
                        try:
                            total += (Path(parent) / name).lstat().st_size
                        except OSError:
                            pass
                if total > 6 * 1024**3:
                    raise RuntimeError('workspace disk budget exceeded')
                last_disk = time.monotonic()
            time.sleep(.5)
        return proc.returncode
    finally:
        stop(proc)
