#!/usr/bin/env python3
"""Run a supplied public DRAW script; this tool exposes no hidden oracle."""
from __future__ import annotations

import argparse
import json
import os
import resource
import shlex
import signal
import subprocess
import tempfile
import time
from pathlib import Path


def _limits(cpu_seconds: int, memory_gib: int):
    def apply():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 2))
        memory = memory_gib * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    return apply


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", default="reproduce.tcl")
    parser.add_argument("--log", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cpu-limit-seconds", type=int, default=160)
    parser.add_argument("--address-space-gib", type=int, default=4)
    args = parser.parse_args()

    required = os.environ.get("BENCH_REQUIRED_CONDA_ENV", "").strip()
    active = os.environ.get("CONDA_DEFAULT_ENV")
    prefix = Path(os.environ.get("CONDA_PREFIX", ""))
    verified_prefix = prefix.is_dir() and (prefix / "conda-meta").is_dir()
    if required and active != required:
        raise SystemExit(f"requires conda environment {required!r}; active={active!r}")
    if not required and not verified_prefix:
        raise SystemExit("must execute in a verified Conda environment")
    build, resource_dir, case_dir = args.build_dir.resolve(), args.resource_dir.resolve(), args.case_dir.resolve()
    script = (case_dir / args.script).resolve()
    binary = build / "lin64" / "clang" / "bin" / "DRAWEXE"
    plugin_dir = build / "lin64" / "clang" / "lib"
    bootstrap = build / "custom_clang_64.sh"
    env_script = build / "env.sh"
    for path in (script, binary, plugin_dir / "libTKTopTest.so", bootstrap, env_script):
        if not path.is_file() or (path == script and not path.is_relative_to(case_dir)):
            raise SystemExit(f"required public DRAW input/runtime file is missing or unsafe: {path}")
    resource_root = next((path for path in (resource_dir, resource_dir / "src", resource_dir.parent / "src")
                          if (path / "DrawResources").is_dir()), None)
    if resource_root is None:
        raise SystemExit(f"DrawResources missing below {resource_dir}")
    command = (
        "source " + shlex.quote(str(bootstrap)) + " '' 64 && source " + shlex.quote(str(env_script)) +
        " && export CSF_OCCTResourcePath=" + shlex.quote(str(resource_root)) +
        " CSF_OCCTLibPath=" + shlex.quote(str(plugin_dir)) +
        " CSF_OCCTBinPath=" + shlex.quote(str(binary.parent)) +
        " DRAWHOME=" + shlex.quote(str(resource_root / "DrawResources")) +
        " CSF_DrawPluginDefaults=" + shlex.quote(str(resource_root / "DrawResources")) +
        " && exec " + shlex.quote(str(binary)) + " -b -f " + shlex.quote(str(script))
    )
    env = os.environ.copy()
    env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    env.pop("DISPLAY", None)
    log = args.log.resolve() if args.log else Path(tempfile.mkdtemp(prefix="bf_g3_public_draw_")) / "draw.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    try:
        with log.open("wb") as output:
            process = subprocess.Popen(["bash", "-lc", command], cwd=case_dir, env=env,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True,
                                       preexec_fn=_limits(args.cpu_limit_seconds, args.address_space_gib))
            try:
                draw_rc = process.wait(timeout=args.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                draw_rc = process.wait()
            output.write(f"\nBF_DRAW_RC={'timeout' if timed_out else draw_rc}\n".encode())
    except OSError as exc:
        draw_rc = None
        diagnostic = f"{type(exc).__name__}: {exc}"
    else:
        diagnostic = None
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    marker = "TEST_DONE" in text
    return_code = 3 if timed_out else 2 if draw_rc is None else 0 if draw_rc == 0 and marker else 1
    record = {"tool_id": "bf-group3-public-draw-runner-v1", "command": ["bash", "-lc", command],
              "draw_process_return_code": draw_rc, "return_code": return_code,
              "test_done_marker": marker, "timed_out": timed_out,
              "duration_seconds": round(time.monotonic() - started, 3),
              "case_script": str(script), "log_path": str(log), "log_bytes": log.stat().st_size if log.is_file() else 0,
              "diagnostic": diagnostic,
              "limitation": "The public runner only reports process completion and the public TEST_DONE marker; it does not evaluate hidden geometry predicates."}
    print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
