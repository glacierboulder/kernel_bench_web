#!/usr/bin/env python3
"""Run one headless DRAW script with conservative resource limits."""
import argparse
import json
import os
import resource
import signal
import subprocess
import tempfile
import time
from pathlib import Path


def limit_child(cpu_seconds, address_space_bytes):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 2))
    resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))


def tail(path, limit=32768):
    path.seek(0, os.SEEK_END)
    size = path.tell()
    path.seek(max(0, size - limit))
    data = path.read(limit)
    return data.decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", default="reproduce.tcl")
    parser.add_argument("--timeout-seconds", type=int, default=18)
    parser.add_argument("--cpu-limit-seconds", type=int, default=15)
    parser.add_argument("--address-space-gib", type=int, default=4)
    args = parser.parse_args()

    build_dir = args.build_dir.resolve()
    resource_dir = args.resource_dir.resolve()
    case_dir = args.case_dir.resolve()
    script = (case_dir / args.script).resolve()
    toolchain_name = os.environ.get("BENCH_TOOLCHAIN_NAME", "clang")
    binary = build_dir / "lin64" / toolchain_name / "bin" / "DRAWEXE"
    library_dir = build_dir / "lin64" / toolchain_name / "lib"
    if not binary.is_file() or not script.is_file():
        raise SystemExit(f"missing DRAWEXE or script: {binary}, {script}")

    env = os.environ.copy()
    env.update({
        "CSF_OCCTResourcePath": str(resource_dir),
        "CSF_OCCTLibPath": str(library_dir),
        "CSF_OCCTBinPath": str(binary.parent),
        "CSF_DrawPluginDefaults": str(resource_dir / "DrawResources"),
        "DRAWHOME": str(resource_dir / "DrawResources"),
        "CSF_LANGUAGE": "us",
        "MMGT_CLEAR": "1",
        "LD_LIBRARY_PATH": os.pathsep.join(
            p for p in (str(library_dir), env.get("BENCH_EXTRA_LIBRARY_PATH", ""),
                        env.get("LD_LIBRARY_PATH", "")) if p
        ),
    })

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        started = time.monotonic()
        proc = subprocess.Popen(
            [str(binary), "-b", "-f", str(script)],
            cwd=case_dir,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
            preexec_fn=lambda: limit_child(args.cpu_limit_seconds, args.address_space_gib * 1024**3),
        )
        timed_out = False
        try:
            return_code = proc.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            return_code = proc.wait()
        elapsed = round(time.monotonic() - started, 3)
        stdout_tail = tail(stdout_file)
        stderr_tail = tail(stderr_file)
    result = {
        "script": str(script),
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": elapsed,
        "test_done_marker": "TEST_DONE" in stdout_tail,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
