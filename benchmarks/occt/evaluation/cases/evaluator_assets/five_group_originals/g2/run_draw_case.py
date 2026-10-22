#!/usr/bin/env python3
"""Trusted headless DRAW runner; the oracle parser sees this run's captured stdout."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import resource
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _limit_child(cpu: int, memory_gib: int) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 2))
    resource.setrlimit(resource.RLIMIT_AS, (memory_gib * 1024**3, memory_gib * 1024**3))


def _helper():
    path = Path(__file__).resolve().parent / "run_eval.py"
    spec = importlib.util.spec_from_file_location("bf_group2_run_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load locked oracle helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _input_files(case_dir: Path) -> list[dict[str, str]]:
    result = []
    root = case_dir / "inputs"
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                result.append({"path": str(path.relative_to(case_dir).as_posix()), "sha256": digest(path)})
    public_inputs = case_dir / "inputs"
    return result


def _case_id(script: Path) -> str:
    match = re.search(r"^# BF_CASE_ID: ([A-Za-z0-9_.-]+)$", script.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise ValueError("staged harness has no stable case ID")
    return match.group(1)


def run(role: str, build_dir: Path, resource_dir: Path, case_dir: Path, script_name: str,
        log_path: Path, timeout: int, cpu_limit: int, memory_gib: int,
        source_commit: str | None = None, materialized_tree: str | None = None,
        build_record: Path | None = None, artifact_verification: Path | None = None) -> dict:
    required_conda_env = os.environ.get("BENCH_REQUIRED_CONDA_ENV", "").strip()
    active_conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    conda_prefix = Path(os.environ.get("CONDA_PREFIX", ""))
    verified_conda_prefix = conda_prefix.is_dir() and (conda_prefix / "conda-meta").is_dir()
    if required_conda_env and active_conda_env != required_conda_env:
        raise RuntimeError(
            f"runner requires conda environment {required_conda_env!r}; "
            f"active environment is {active_conda_env!r}"
        )
    if not required_conda_env and not verified_conda_prefix:
        raise RuntimeError("runner must execute in a verified Conda environment")
    build_dir, resource_dir, case_dir = build_dir.resolve(), resource_dir.resolve(), case_dir.resolve()
    script = (case_dir / script_name).resolve()
    if not script.is_file() or not script.is_relative_to(case_dir):
        raise RuntimeError("case script is missing or escapes case directory")
    case_id = _case_id(script)
    binary = build_dir / "lin64" / "gcc" / "bin" / "DRAWEXE"
    if not binary.is_file():
        if build_dir.name == "DRAWEXE" and build_dir.is_file():
            binary = build_dir
            build_dir = binary.parent.parent.parent
        else:
            raise RuntimeError(f"verified GCC DRAWEXE missing under build directory: {binary}")
    env_script = build_dir / "env.sh"
    if not env_script.is_file():
        raise RuntimeError(f"build environment script missing: {env_script}")
    resource_candidates = [resource_dir, resource_dir / "src", resource_dir.parent / "src"]
    resource_root = next((path for path in resource_candidates if (path / "DrawResources").is_dir()), None)
    if resource_root is None:
        raise RuntimeError(f"OCCT DrawResources missing under supplied resource location: {resource_dir}")

    command = (
        "export CSF_OCCTResourcePath=" + shlex.quote(str(resource_root)) + " && source " +
        shlex.quote(str(env_script)) + " && export CSF_OCCTResourcePath=" + shlex.quote(str(resource_root)) +
        " CSF_OCCTLibPath=" + shlex.quote(str(binary.parent.parent / "lib")) +
        " CSF_OCCTBinPath=" + shlex.quote(str(binary.parent)) +
        " DRAWHOME=" + shlex.quote(str(resource_root / "DrawResources")) +
        " CSF_DrawPluginDefaults=" + shlex.quote(str(resource_root / "DrawResources")) +
        " && exec " + shlex.quote(str(binary)) + " -b -f " + shlex.quote(str(script))
    )
    env = os.environ.copy()
    env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    env.pop("DISPLAY", None)
    log_path = log_path.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    timed_out = False
    raw = b""
    proc_rc = None
    with log_path.open("wb") as output:
        try:
            proc = subprocess.Popen(["bash", "-lc", command], cwd=case_dir, env=env,
                                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                                    preexec_fn=lambda: _limit_child(cpu_limit, memory_gib))
            try:
                proc_rc = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                proc_rc = proc.wait()
        except OSError as exc:
            elapsed = round(time.monotonic() - start, 3)
            result = {"status": "not_run", "oracle_ran": False, "error": str(exc),
                      "timed_out": False, "process_return_code": None, "duration_seconds": elapsed}
            return _record(role, case_id, build_dir, resource_root, script, binary, env_script,
                           log_path, result, source_commit, materialized_tree, build_record,
                           artifact_verification, required_conda_env, command)
    elapsed = round(time.monotonic() - start, 3)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    with log_path.open("ab") as output:
        output.write(f"\nBF_DRAW_RC={proc_rc if proc_rc is not None else 'timeout'}\n".encode())
    if timed_out:
        result = {"status": "timeout", "oracle_ran": False, "timed_out": True,
                  "process_return_code": None, "signal": signal.SIGKILL,
                  "duration_seconds": elapsed}
    elif proc_rc != 0:
        result = {"status": "runtime_error", "oracle_ran": False, "timed_out": False,
                  "process_return_code": proc_rc, "signal": -proc_rc if proc_rc < 0 else None,
                  "duration_seconds": elapsed, "diagnostic": "DRAW process did not return zero"}
    else:
        text += f"\nBF_DRAW_RC={proc_rc}"
        try:
            verdict = _helper().validate_draw_text(case_id, role, text)
            result = {"status": "completed", "oracle_ran": True, "timed_out": False,
                      "process_return_code": 0, "signal": None, "duration_seconds": elapsed,
                      "tcl_source_return_code": re.findall(r"^BF_SOURCE_RC=(\d+)$", text, re.M),
                      "test_done_marker": verdict["status"] == "geometry_pass",
                      "oracle": verdict}
        except Exception as exc:
            result = {"status": "runtime_error", "oracle_ran": False, "timed_out": False,
                      "process_return_code": 0, "signal": None, "duration_seconds": elapsed,
                      "diagnostic": f"oracle not evaluated: {type(exc).__name__}: {exc}"}
    return _record(role, case_id, build_dir, resource_root, script, binary, env_script,
                   log_path, result, source_commit, materialized_tree, build_record,
                   artifact_verification, required_conda_env, command,
                   timeout=timeout, cpu_limit=cpu_limit,
                   memory_gib=memory_gib)


def _record(role, case_id, build_dir, resource_root, script, binary, env_script,
            log_path, result, source_commit, materialized_tree, build_record,
            artifact_verification, required_conda_env, command,
            timeout=180, cpu_limit=160, memory_gib=4):
    case_dir = script.parent
    record = {
        "schema_version": "bf-group2-staged-run-v1", "role": role, "case_id": case_id,
        "source_commit": source_commit, "materialized_tree_sha256": materialized_tree,
        "build": {"status": "passed" if binary.is_file() and env_script.is_file() else "not_run",
                  "return_code": 0 if binary.is_file() and env_script.is_file() else None,
                  "drawexe_path": str(binary), "drawexe_sha256": digest(binary) if binary.is_file() else None,
                  "env_script_path": str(env_script), "env_script_sha256": digest(env_script) if env_script.is_file() else None,
                  "build_record_path": str(build_record) if build_record else None,
                  "build_record_sha256": digest(build_record) if build_record and build_record.is_file() else None,
                  "artifact_verification_path": str(artifact_verification) if artifact_verification else None,
                  "artifact_verification_sha256": digest(artifact_verification) if artifact_verification and artifact_verification.is_file() else None,
                  "compiler": "GCC 9.4.0", "optimization": "-O0 -DNDEBUG", "jobs": int(os.environ.get("BENCH_COMPILER_JOBS", "2")),
                  "targets": ["DRAWEXE", "TKTopTest"]},
        "execution": result, "runner_id": "bf-group2-gcc9-tcl-physical-oracle-v1",
        "runner_sha256": digest(Path(__file__).resolve()), "runner_process_exit_mapping": {
            "0": "completed", "1": "completed", "2": "runtime_error", "3": "timeout"},
        "harness_path": str(script), "harness_sha256": digest(script),
        "case_input_files": _input_files(case_dir), "official_test_or_hidden_oracle_files": [],
        "drawexe_path": str(binary), "drawexe_sha256": digest(binary),
        "environment_adaptations": {"LIBGL_ALWAYS_SOFTWARE": "1", "DISPLAY": "unset",
                                    "resource_root": str(resource_root), "env_script": str(env_script),
                                    "required_conda_env": required_conda_env},
        "command": ["bash", "-lc", command], "cwd": str(case_dir),
        "timeout_seconds": timeout, "cpu_limit_seconds": cpu_limit,
        "address_space_limit_gib": memory_gib, "duration_seconds": result.get("duration_seconds"),
        "process_return_code": 0 if result["status"] == "completed" and result.get("test_done_marker") else
                               1 if result["status"] == "completed" else
                               3 if result["status"] == "timeout" else 2,
        "draw_process_return_code": result.get("process_return_code"),
        "log_path": str(log_path), "log_sha256": digest(log_path) if log_path.is_file() else None,
        "oracle": result.get("oracle", {"status": "not_run", "checks": []}),
        "expected_outcome": "pass" if result.get("test_done_marker") else
                            "geometry_fail" if result.get("oracle", {}).get("status") == "geometry_fail" else "not_run",
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", default="reproduce.tcl")
    parser.add_argument("--role", choices=("B", "F", "agent"), default="agent")
    parser.add_argument("--log", type=Path, required=False, default=Path("run_draw_case.log"))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cpu-limit-seconds", type=int, default=160)
    parser.add_argument("--address-space-gib", type=int, default=4)
    parser.add_argument("--source-commit")
    parser.add_argument("--materialized-tree")
    parser.add_argument("--build-record", type=Path)
    parser.add_argument("--artifact-verification", type=Path)
    args = parser.parse_args()
    try:
        record = run(args.role, args.build_dir, args.resource_dir, args.case_dir, args.script,
                     args.log, args.timeout_seconds, args.cpu_limit_seconds, args.address_space_gib,
                     args.source_commit, args.materialized_tree, args.build_record,
                     args.artifact_verification)
    except Exception as exc:
        record = {"schema_version": "bf-group2-staged-run-v1", "execution": {
            "status": "not_run", "oracle_ran": False, "diagnostic": f"{type(exc).__name__}: {exc}"},
            "oracle": {"status": "not_run", "checks": []}, "process_return_code": 2,
            "test_done_marker": False,
            "required_conda_env": os.environ.get("BENCH_REQUIRED_CONDA_ENV") or None,
            "active_conda_env": os.environ.get("CONDA_DEFAULT_ENV")}
    print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
    return int(record.get("process_return_code", 2))


if __name__ == "__main__":
    raise SystemExit(main())
