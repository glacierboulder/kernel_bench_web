"""Codex CLI adapter with bounded recovery and a supervisor-owned API proxy.

Live execution stays disabled by default and requires an exact CLI version,
explicit operator enablement, and verified worker-side credential isolation.
"""
from __future__ import annotations

import json
import os
import queue
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .codex_protocol import CodexStream
from .recovery import RecoveryBudget


class CredentialIsolationUnsupported(RuntimeError):
    pass


def _binary(config: dict | None = None) -> str | None:
    config = config or {}
    value = os.environ.get("BENCH_CODEX") or config.get("codex_cli")
    if not value:
        return None
    return str(Path(value).expanduser()) if os.sep in value else shutil.which(value)


class CodexAdapter:
    """Build argv without a shell and resume only an explicitly saved session."""
    adapter_id = "codex"
    live_enabled = False
    disabled_reason = "Codex live is disabled by default until isolation checks and explicit enablement."

    def __init__(self, config: dict | None = None):
        from .settings import SETTINGS
        self.config=dict(SETTINGS.config.get("tools",{}))
        self.config.update(SETTINGS.config.get("codex",{}))
        if config:
            self.config.update(config)
        self.binary = _binary(self.config)
        self.expected_version = self.config.get("codex_version")

    def probe(self) -> dict:
        if not self.binary:
            return {"available": False,"live_enabled":False,"version_matches":False,
                    "reason": "Codex CLI is not configured"}
        try:
            probe_env=dict(os.environ)
            probe_env.pop("OPENAI_API_KEY",None)
            probe_env.pop("DEEPSEEK_API_KEY",None)
            result = subprocess.run([self.binary, "--version"], capture_output=True,
                                    text=True, timeout=5, check=False,env=probe_env)
        except (OSError, subprocess.TimeoutExpired):
            return {"available": False,"live_enabled":False,"version_matches":False,
                    "reason": "Codex CLI version probe failed"}
        version = (result.stdout or result.stderr).strip().splitlines()
        version = version[0] if result.returncode == 0 and version else None
        exact = bool(version and self.expected_version and self.expected_version in version)
        key_available=bool(os.environ.get("OPENAI_API_KEY"))
        isolation_ready=(self.config.get("codex_isolation_verified") is True and
                         self.config.get("codex_live_enabled") is True and key_available and
                         isinstance(self.config.get("model"),str) and bool(self.config.get("model")))
        live=bool(exact and isolation_ready)
        return {"available": exact, "binary": self.binary, "version": version,
                "version_matches": exact, "credential_available":key_available,
                "live_enabled": live,
                "reason": ("Codex Responses proxy is configured" if live else
                           "Codex live is disabled until credential isolation is verified, explicitly enabled, and an API key is available"
                           if exact else "Configure and verify an exact Codex CLI version")}

    def argv(self, prompt: str, *, session_id: str | None = None,model:str|None=None,
             proxy_base_url:str|None=None,externally_sandboxed:bool=False) -> list[str]:
        if not self.binary:
            raise RuntimeError("Codex CLI is not configured")
        base = [self.binary, "exec"]
        if session_id is not None:
            if not session_id or session_id.lower() in {"last", "--last"}:
                raise ValueError("resume requires the recorded session UUID")
            import uuid
            try:
                session_id = str(uuid.UUID(session_id))
            except ValueError as exc:
                raise ValueError("resume requires a valid recorded session UUID") from exc
            base.extend(["resume", session_id])
        base.extend(["--json","--ignore-user-config","--ignore-rules","--skip-git-repo-check"])
        if externally_sandboxed:
            # Worker launches Codex inside a stronger bubblewrap boundary with
            # no host home, no network namespace route and a fixed API proxy.
            base.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            base.extend(["--sandbox","workspace-write"])
        if model:
            base.extend(["--model",model])
        if proxy_base_url:
            base.extend(["--config","model_provider=agent_bench_proxy"])
            config={
                "model_providers.agent_bench_proxy.name":'"Agent Bench fixed proxy"',
                "model_providers.agent_bench_proxy.base_url":json.dumps(proxy_base_url),
                "model_providers.agent_bench_proxy.wire_api":'"responses"',
                "model_providers.agent_bench_proxy.requires_openai_auth":"false",
                "model_providers.agent_bench_proxy.supports_websockets":"false",
                "model_providers.agent_bench_proxy.capabilities.external_web_access":"false",
                "model_providers.agent_bench_proxy.request_max_retries":"0",
                "model_providers.agent_bench_proxy.stream_max_retries":"0",
            }
            for key,value in config.items():
                base.extend(["--config",f"{key}={value}"])
        base.append("-")
        return base

    def environment(self, *, home: Path, session_home: Path) -> dict[str, str]:
        # This contains no user's real CODEX_HOME or API key. Authentication is
        # intentionally absent until the supervisor can isolate it from shells.
        return {"HOME": str(home), "CODEX_HOME": str(session_home),
                "PATH": "/usr/bin:/bin",
                "PYTHONNOUSERSITE": "1", "NO_COLOR": "1"}

    def start(self, prompt: str, *, workspace: Path, home: Path,
              session_home: Path, session_id: str | None = None,
              stdout=None, stderr=None,launcher_prefix:list[str]|None=None,
              binary_command:list[str]|None=None,model:str|None=None,
              proxy_base_url:str|None=None,externally_sandboxed:bool=False) -> subprocess.Popen:
        """Start one isolated CLI process; caller owns streaming and cancellation."""
        if not isinstance(prompt,str) or not prompt:
            raise ValueError("Codex task prompt must be nonempty text")
        if not self.binary:
            raise RuntimeError("Codex CLI is not configured")
        workspace=Path(workspace).resolve(strict=True)
        home=Path(home);session_home=Path(session_home)
        home.mkdir(parents=True,exist_ok=True,mode=0o700)
        session_home.mkdir(parents=True,exist_ok=True,mode=0o700)
        argv=self.argv(prompt,session_id=session_id,model=model,proxy_base_url=proxy_base_url,
                       externally_sandboxed=externally_sandboxed)
        if binary_command:
            argv=[*binary_command,*argv[1:]]
        if launcher_prefix:
            argv=[*launcher_prefix,*argv]
        process=subprocess.Popen(argv,cwd=workspace,env=self.environment(home=home,session_home=session_home),
                                 stdin=subprocess.PIPE,stdout=stdout or subprocess.PIPE,
                                 stderr=stderr or subprocess.PIPE,text=True,start_new_session=True)
        try:
            process.stdin.write(prompt)
            process.stdin.close()
        except BaseException:
            process.kill()
            process.wait()
            raise
        return process

    def run(self, prompt: str, *, workspace: Path, home: Path, session_home: Path,
            timeout_seconds: int, cancelled=lambda: False, on_event=lambda _event: None,
            session_id: str | None = None, request_limit: int | None = None,
            request_counter=None,launcher_prefix:list[str]|None=None,
            binary_command:list[str]|None=None,model:str|None=None,
            proxy_base_url:str|None=None,externally_sandboxed:bool=False) -> dict:
        """Run, parse, and conservatively resume one explicitly recorded session."""
        if not self.binary:
            raise RuntimeError("Codex CLI is not configured")
        if request_limit is not None and (request_limit<1 or not callable(request_counter)):
            raise ValueError("a cumulative request limit requires a trusted request counter")
        budget=RecoveryBudget(total_limit=2,tool_refusal_limit=1)
        attempts=[];first_status=None;current_prompt=prompt;current_session=session_id
        usage_total={"input_tokens":0,"cached_input_tokens":0,"output_tokens":0,"reasoning_output_tokens":0}
        usage_observed=False
        started=time.monotonic()

        def finish(value: dict) -> dict:
            value["recovery_budget"]={"limit":budget.total_limit,"used":budget.used_total,
                                      "remaining":budget.total_limit-budget.used_total,
                                      "tool_refusals_used":budget.used_tool_refusal}
            value["cumulative_request_limit"]=request_limit
            count=request_counter() if callable(request_counter) else None
            if request_limit is not None and (not isinstance(count,int) or count<0 or count>request_limit):
                raise RuntimeError("trusted Codex gateway returned an invalid cumulative request count")
            value["api_request_count"]=count
            return value

        while True:
            remaining=timeout_seconds-(time.monotonic()-started)
            if remaining<=0:
                return finish({"status":"timed_out","session_id":current_session,"attempts":attempts,
                        "first_status":first_status,"usage":usage_total if usage_observed else None})
            parser=CodexStream();lines=queue.Queue();sentinel=object()
            with tempfile.TemporaryFile(mode="w+b") as error_file:
                process=self.start(current_prompt,workspace=workspace,home=home,session_home=session_home,
                                   session_id=current_session,stderr=error_file,
                                   launcher_prefix=launcher_prefix,binary_command=binary_command,
                                   model=model,proxy_base_url=proxy_base_url,
                                   externally_sandboxed=externally_sandboxed)
                def read_output():
                    try:
                        for line in process.stdout:
                            lines.put(line)
                    finally:
                        lines.put(sentinel)
                reader=threading.Thread(target=read_output,daemon=True);reader.start()
                deadline=time.monotonic()+remaining;was_cancelled=False
                while time.monotonic()<deadline:
                    if cancelled():
                        was_cancelled=True
                        try: os.killpg(process.pid,signal.SIGTERM)
                        except ProcessLookupError: pass
                        break
                    try:
                        line=lines.get(timeout=0.1)
                    except queue.Empty:
                        if process.poll() is not None and not reader.is_alive():
                            break
                        continue
                    if line is sentinel:
                        break
                    event=parser.feed(line)
                    if event is not None:
                        try:
                            on_event(json.loads(line))
                        except (ValueError,TypeError):
                            pass
                if process.poll() is None:
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try: os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                return_code=process.wait()
                reader.join(timeout=5)
                if process.stdout:
                    process.stdout.close()
                parsed=parser.finish(return_code)
                if parsed.get("usage") is not None:
                    usage_observed=True
                    for key,value in parsed["usage"].items():
                        if key in usage_total: usage_total[key]+=value
                if parser.thread_id:
                    if current_session and parser.thread_id!=current_session:
                        parsed.update(status="failed",failure_type="invalid_or_changed_session_id",
                                      recovery_reason="invalid_or_changed_session_id")
                    else:
                        current_session=parser.thread_id
                error_file.seek(0,os.SEEK_END);size=error_file.tell()
                error_file.seek(max(0,size-4000));stderr_tail=error_file.read().decode("utf-8",errors="replace")
            if was_cancelled:
                return finish({"status":"cancelled","session_id":current_session,"attempts":attempts,
                        "first_status":first_status,"final":parsed,"stderr_tail":stderr_tail,
                        "usage":usage_total if usage_observed else None})
            if parsed["status"]=="completed":
                if first_status is None: first_status="completed"
                return finish({"status":"completed","session_id":current_session,"attempts":attempts,
                        "first_status":first_status,"final":parsed,"stderr_tail":stderr_tail,
                        "usage":usage_total if usage_observed else None})
            if first_status is None: first_status=parsed["status"]
            reason=parsed.get("recovery_reason") or "unknown_error"
            request_count=request_counter() if callable(request_counter) else None
            if request_limit is not None and (not isinstance(request_count,int) or request_count<0):
                raise RuntimeError("trusted Codex gateway returned an invalid cumulative request count")
            if request_limit is not None and request_count>=request_limit:
                decision={"action":"stop","reason":"cumulative_request_budget_exhausted"}
            else:
                decision=budget.decide(reason,process_exited=True,session_id=current_session,
                                       result_known=bool(parsed.get("completed") or parsed.get("failure_type")))
            attempts.append({"status":parsed["status"],"reason":reason,"decision":decision,
                             "stderr_tail":stderr_tail,"usage":parsed.get("usage")})
            if decision["action"]!="resume_session":
                return finish({"status":parsed["status"],"session_id":current_session,"attempts":attempts,
                        "first_status":first_status,"final":parsed,"stderr_tail":stderr_tail,
                        "usage":usage_total if usage_observed else None})
            current_session=decision["session_id"]
            current_prompt=("Continue permitted work in the same task and workspace. Do not repeat any action that was denied. "
                            "Keep the original task constraints and report honestly.")

    def run_isolated(self,prompt:str,*,workspace:Path,control:Path,gateway_dir:Path,
                     api_key:str,model:str,request_limit:int,max_output_tokens:int,
                     timeout_seconds:int,cancelled=lambda:False,on_event=lambda _event:None,
                     session_id:str|None=None,task_env:dict[str,str]|None=None)->dict:
        """Run Codex in the worker's outer bubblewrap boundary and fixed proxy."""
        from .codex_gateway import CodexGateway
        from .sandbox import PYTHON,command
        from .tool_paths import executable

        entry=Path(self.binary).expanduser().resolve(strict=True)
        if entry.suffix!=".js" or not entry.is_file():
            raise CredentialIsolationUnsupported("Codex installation must resolve to a reviewed Node.js entrypoint")
        package=entry.parent.parent
        node=executable("Node.js",env_name="BENCH_NODE",config_name="node",default="node")
        control=Path(control).resolve(strict=True)
        workspace=Path(workspace).resolve(strict=True)
        gateway_dir=Path(gateway_dir).resolve()
        gateway_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        socket_path=gateway_dir/"codex.sock"
        gateway=CodexGateway(socket_path,api_key,model,max_requests=request_limit,
                             max_output_tokens=max_output_tokens)
        gateway.start()
        session_home=workspace/"home"/".codex"
        session_home.mkdir(parents=True,exist_ok=True,mode=0o700)
        (control/"codex_runner.py").write_text(
            Path(__file__).with_name("codex_runner.py").read_text(encoding="utf-8"),encoding="utf-8")
        runner=[PYTHON,"/control/codex_runner.py","--socket","/gateway/codex.sock",
                "--port","18763","--"]
        mounts=[(control,"/control",False),(gateway_dir,"/gateway",False),
                (package,"/runtime/codex",False)]
        sandbox_env={"HOME":"/home/agent","CODEX_HOME":"/home/agent/.codex",
                     "PATH":str(Path(node).parent)+":"+str(Path(PYTHON).parent)+":/usr/local/bin:/usr/bin:/bin",
                     "PYTHONNOUSERSITE":"1","NO_COLOR":"1","PYTHONUNBUFFERED":"1"}
        allowed_tool_env={"BENCH_CMAKE","BENCH_CC","BENCH_CXX","BENCH_TOOLCHAIN_NAME",
                          "BENCH_COMPILER_JOBS","BENCH_TCL_DIR","BENCH_TCL_INCLUDE_DIR",
                          "BENCH_TCL_LIBRARY","BENCH_TCL_LIBRARY_DIR","BENCH_EXTRA_LIBRARY_PATH"}
        sandbox_env.update({key:value for key,value in (task_env or {}).items() if key in allowed_tool_env})
        launcher=command(workspace,mounts=mounts,env=sandbox_env)+runner
        codex_command=[node,"/runtime/codex/bin/codex.js"]
        try:
            result=self.run(prompt,workspace=workspace,home=workspace/"home",
                session_home=session_home,timeout_seconds=timeout_seconds,cancelled=cancelled,
                on_event=on_event,session_id=session_id,request_limit=request_limit,
                request_counter=gateway.request_count,launcher_prefix=launcher,
                binary_command=codex_command,model=model,
                proxy_base_url="http://127.0.0.1:18763/v1",externally_sandboxed=True)
            result["gateway_audit"]=list(gateway.audit)
            return result
        finally:
            gateway.close()


def codex_stream() -> CodexStream:
    return CodexStream()
