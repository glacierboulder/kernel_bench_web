"""Executable boundary assertions, run before any remote-model task."""
import json
from pathlib import Path
import subprocess
import tempfile
from .sandbox import TOOLCHAIN_ROOT, command, limits, PYTHON

CHECK = '''
import json, os, socket
from pathlib import Path
checks = {}
checks['agent_home_isolated'] = Path.home() == Path('/home/agent')
checks['agent_credentials_absent'] = not any((Path.home() / name).exists() for name in ('.ssh', '.codex', '.aws', '.config'))
checks['private_material_absent'] = not Path('/workspace/private').exists() and not Path('/workspace/evaluation').exists()
checks['no_host_credentials'] = not any(k in os.environ for k in ('DEEPSEEK_API_KEY','ANTHROPIC_API_KEY','ARK_API_KEY','SSH_AUTH_SOCK'))
checks['namespaced_proc'] = len([p for p in Path('/proc').iterdir() if p.name.isdigit()]) < 10
checks['toolchain_readonly'] = False
try:
    (Path(os.environ['BENCH_TOOLCHAIN_PREFIX']) / '.bench-write-probe').write_text('x')
except OSError:
    checks['toolchain_readonly'] = True
except KeyError:
    checks['toolchain_readonly'] = False
Path('/workspace/write-probe').write_text('ok')
checks['workspace_writable'] = True
checks['no_proxy_variables'] = not any(k.lower() in ('http_proxy','https_proxy','all_proxy') for k in os.environ)
for label, host, port in [('public_network_blocked','1.1.1.1',443)]:
    sock=socket.socket();sock.settimeout(.4)
    try:
        sock.connect((host,port));checks[label]=False
    except OSError:
        checks[label]=True
    finally:
        sock.close()
print(json.dumps(checks))
assert all(checks.values()), checks
'''

def verify():
    with tempfile.TemporaryDirectory(prefix='cadai-boundary-') as directory:
        sandbox_env = {'BENCH_TOOLCHAIN_PREFIX': str(TOOLCHAIN_ROOT)}
        result = subprocess.run(command(directory, env=sandbox_env) + [PYTHON, '-c', CHECK],
                                capture_output=True, text=True, timeout=20, preexec_fn=limits)
    if result.returncode:
        raise RuntimeError('sandbox preflight failed: ' + result.stderr[-2000:])
    return json.loads(result.stdout)

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
