#!/usr/bin/env python3
"""Run one case-mapped G3 DRAW harness against a local frozen Clang 10 build."""
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
import time
from pathlib import Path

GROUP = "occt-bf-group-b2613378-27780-27252-21494-v1"
EXIT_MAP = {"0": "completed", "1": "completed", "2": "runtime_error", "3": "timeout"}
EXPECTED = {
    "B": {
        "commit": "2613378e60ff5e517b2bf73699184d0c6f636bb8",
        "tree": "43c6421991ea0372ec0f7622aa8daea5676a7b7e",
        "materialized": "5ead8e62e4d72f801f43d8bd81dda610925dd2b9704ff51aaebe755def165104",
        "drawexe": "73746f35b3a10c0aac595a6aa16b69e2387227bdb33fb27bf1062dad6827e57a",
        "tktoptest": "8a0157a9461e5990fb74da8544d020721bf4b6d94bd2cfb38863a6afc1d1c9a7",
    },
    "F": {
        "commit": "870ae593c3c060fe822e20bd2f1acfdd3fcbd449",
        "tree": "75920cb58780f31d7063633b98095dfb69821abe",
        "materialized": "8f57dd653c66586b33e5cdd60dbae743b921c07c860358904dfa99f45ebf9857",
        "drawexe": "bc9406526b1c4c2a032c3f332f8bf8a1ba7d22614cdeaa5a09df870bb3dbd779",
        "tktoptest": "a739973fb0b475d84d7c668fd94031e887cb3dee56cfd7c42d80f5e5c927475b",
    },
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _limit_child(cpu_seconds: int, memory_gib: int) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 2))
    memory = memory_gib * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))


def _case_id(script: Path) -> str:
    match = re.search(r"^# BF_CASE_ID: ([A-Za-z0-9_.-]+)$", script.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise ValueError("harness has no stable BF_CASE_ID")
    return match.group(1)


def _helper(path_arg: Path | None):
    if path_arg is None:
        # Both the staging tree and the framework's supervisor snapshot carry
        # evaluator assets as a sibling of legacy/.
        parent_asset = Path(__file__).resolve().parents[1] / "run_eval.py"
        group_asset = Path(__file__).resolve().parents[2] / "evaluator_assets" / GROUP / "run_eval.py"
        asset = parent_asset if parent_asset.is_file() else group_asset
    else:
        asset = path_arg.resolve()
    spec = importlib.util.spec_from_file_location("g3_case_mapped_oracle", asset)
    if spec is None or spec.loader is None or not asset.is_file():
        raise RuntimeError(f"cannot load case-mapped G3 geometry oracle: {asset}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inputs_hash(items: list[dict]) -> str:
    normalized = sorted(({"path": item["path"], "sha256": item["sha256"]} for item in items),
                        key=lambda item: item["path"].encode("utf-8"))
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sidecar_context(evidence_dir: Path, role: str, case_id: str, runner_path: Path):
    evidence_dir = evidence_dir.resolve()
    manifest_path = evidence_dir / "bf_evidence.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["case_id"] == case_id)
    runner_spec = case["runner"]
    locked_runner = evidence_dir / runner_spec["path"]
    if sha(runner_path.resolve()) != runner_spec["sha256"] or sha(locked_runner) != runner_spec["sha256"]:
        raise RuntimeError("trusted runner hash does not match the sidecar runner lock")
    input_items = case["inputs"]
    for item in input_items:
        if sha(evidence_dir / item["path"]) != item["sha256"]:
            raise RuntimeError(f"sidecar input changed: {item['path']}")
    source = manifest["sources"][role]
    if source["commit"] != EXPECTED[role]["commit"]:
        raise RuntimeError(f"{role} source commit differs from frozen G3 identity")
    build_config = manifest["build_config"]
    config_hash = sha(evidence_dir / build_config["path"])
    if config_hash != build_config["sha256"]:
        raise RuntimeError("sidecar build configuration hash mismatch")
    return manifest, case, source, input_items, _inputs_hash(input_items), config_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--role", choices=("B", "F", "agent"), required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--oracle-helper", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--materialized-tree")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cpu-limit-seconds", type=int, default=160)
    parser.add_argument("--address-space-gib", type=int, default=4)
    args = parser.parse_args()

    required_env = os.environ.get("BENCH_REQUIRED_CONDA_ENV", "").strip()
    active_env = os.environ.get("CONDA_DEFAULT_ENV")
    prefix = Path(os.environ.get("CONDA_PREFIX", ""))
    verified_prefix = prefix.is_dir() and (prefix / "conda-meta").is_dir()
    if required_env and active_env != required_env:
        raise SystemExit(f"run in conda environment {required_env!r}; current environment is {active_env!r}")
    if not required_env and not verified_prefix:
        raise SystemExit("run inside a verified Conda environment")
    build = args.build_dir.resolve()
    resource_dir = args.resource_dir.resolve()
    case_dir = args.case_dir.resolve()
    script = (case_dir / args.script).resolve()
    if not script.is_file() or not script.is_relative_to(case_dir):
        raise SystemExit("harness is missing or escapes the supplied case directory")
    case_id = _case_id(script)
    binary = build / "lin64" / "clang" / "bin" / "DRAWEXE"
    plugin = build / "lin64" / "clang" / "lib" / "libTKTopTest.so"
    bootstrap = build / "custom_clang_64.sh"
    env_script = build / "env.sh"
    for path in (binary, plugin, bootstrap, env_script):
        if not path.is_file():
            raise SystemExit(f"required local runtime file is missing: {path}")
    resource_root = next((path for path in (resource_dir, resource_dir / "src", resource_dir.parent / "src")
                          if (path / "DrawResources").is_dir()), None)
    if resource_root is None:
        raise SystemExit(f"DrawResources missing below supplied resource path: {resource_dir}")

    actual = {"drawexe": sha(binary), "tktoptest": sha(plugin)}
    if args.role in EXPECTED:
        expected = EXPECTED[args.role]
        if actual != {"drawexe": expected["drawexe"], "tktoptest": expected["tktoptest"]}:
            raise SystemExit(f"{args.role} B/F runtime artifact hash mismatch: {actual}")
        if args.source_commit and args.source_commit != expected["commit"]:
            raise SystemExit(f"{args.role} source commit does not match frozen G3 identity")
        if args.materialized_tree and args.materialized_tree != expected["materialized"]:
            raise SystemExit(f"{args.role} materialized source tree does not match frozen G3 identity")
    sidecar = None
    if args.evidence_dir:
        if args.role not in EXPECTED:
            raise SystemExit("sidecar execution records support only B/F roles")
        sidecar = _sidecar_context(args.evidence_dir, args.role, case_id, Path(__file__))
        _, case_spec, source, input_items, inputs_hash, config_hash = sidecar
        if args.source_commit and args.source_commit != source["commit"]:
            raise SystemExit("requested commit disagrees with sidecar identity")
        if args.materialized_tree and args.materialized_tree != source["materialized_tree_sha256"]:
            raise SystemExit("requested materialized tree disagrees with sidecar identity")
        if case_spec["runner"]["id"] != "bf-group3-clang10-case-mapped-v1":
            raise SystemExit("sidecar references an unexpected trusted runner ID")

    command = (
        "source " + shlex.quote(str(bootstrap)) + " '' 64 && source " +
        shlex.quote(str(env_script)) + " && export CSF_OCCTResourcePath=" +
        shlex.quote(str(resource_root)) + " CSF_OCCTLibPath=" +
        shlex.quote(str(plugin.parent)) + " CSF_OCCTBinPath=" +
        shlex.quote(str(binary.parent)) + " DRAWHOME=" +
        shlex.quote(str(resource_root / "DrawResources")) +
        " CSF_DrawPluginDefaults=" + shlex.quote(str(resource_root / "DrawResources")) +
        " && exec " + shlex.quote(str(binary)) + " -b -f " + shlex.quote(str(script))
    )
    env = os.environ.copy()
    env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    env.pop("DISPLAY", None)
    args.log = args.log.resolve()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    draw_rc = None
    with args.log.open("wb") as output:
        proc = subprocess.Popen(["bash", "-lc", command], cwd=case_dir, env=env,
                                stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                                preexec_fn=lambda: _limit_child(args.cpu_limit_seconds, args.address_space_gib))
        try:
            draw_rc = proc.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            draw_rc = proc.wait()
        output.write(f"\nBF_DRAW_RC={'timeout' if timed_out else draw_rc}\n".encode())
    elapsed = round(time.monotonic() - started, 3)
    text = args.log.read_text(encoding="utf-8", errors="replace")
    signal_number = -draw_rc if isinstance(draw_rc, int) and draw_rc < 0 else None
    verdict = {"status": "not_run", "checks": []}
    if timed_out:
        runner_rc, status, oracle_ran = 3, "timeout", False
    elif draw_rc != 0:
        runner_rc, status, oracle_ran = 2, "runtime_error", False
    else:
        try:
            verdict = _helper(args.oracle_helper).validate_draw_text(case_id, args.role, text, draw_rc)
            status, oracle_ran = "completed", True
            runner_rc = 0 if verdict["status"] == "geometry_pass" else 1
        except Exception as exc:
            status, oracle_ran, runner_rc = "runtime_error", False, 2
            verdict = {"status": "not_run", "checks": [],
                       "diagnostic": f"{type(exc).__name__}: {exc}"}

    log_hash = sha(args.log)
    record = {
        "schema_version": "bf-group3-staged-run-v1",
        "role": args.role,
        "case_id": case_id,
        "runner_id": "bf-group3-clang10-case-mapped-v1",
        "runner_sha256": sha(Path(__file__).resolve()),
        "runner_process_exit_mapping": EXIT_MAP,
        "command": ["bash", "-lc", command],
        "cwd": str(case_dir),
        "harness_path": str(script),
        "harness_sha256": sha(script),
        "drawexe_sha256": actual["drawexe"],
        "tktoptest_sha256": actual["tktoptest"],
        "log_path": str(args.log),
        "log_sha256": log_hash,
        "duration_seconds": elapsed,
        "draw_process_return_code": None if timed_out else draw_rc,
        "process_return_code": runner_rc,
        "execution": {
            "status": status, "oracle_ran": oracle_ran, "process_return_code": runner_rc,
            "signal": signal.SIGKILL if timed_out else signal_number,
            "timeout_seconds": args.timeout_seconds if timed_out else None,
            "raw_tcl_source_return_codes": re.findall(r"^BF_SOURCE_RC=(\d+)$", text, re.M),
        },
        "oracle": verdict,
        "build": {"status": "passed", "return_code": 0,
                  "drawexe_sha256": actual["drawexe"], "tktoptest_sha256": actual["tktoptest"],
                  "compiler": "Clang 10", "optimization": "-O0 -DNDEBUG", "jobs": int(os.environ.get("BENCH_COMPILER_JOBS", "2")),
                  "targets": ["DRAWEXE", "TKTopTest"]},
        "environment_adaptations": {"LIBGL_ALWAYS_SOFTWARE": "1", "DISPLAY": "unset",
                                    "resource_root": str(resource_root),
                                    "required_conda_env": required_env},
    }
    if sidecar:
        manifest, case_spec, source, input_items, inputs_hash, config_hash = sidecar
        record.update({
            "format_version": 1,
            "source": args.role,
            "canonical_id": case_spec["canonical_id"],
            "issue_id": case_spec["issue_id"],
            "issue_version": case_spec["issue_version"],
            "category": case_spec["category"],
            "source_commit": source["commit"],
            "source_tree_sha256": source["materialized_tree_sha256"],
            "inputs_sha256": inputs_hash,
            "oracle_sha256": case_spec["oracle"]["sha256"],
            "build_config_sha256": config_hash,
            "input_file_hashes": input_items,
        })
    if args.record:
        args.record = args.record.resolve()
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
    return runner_rc


if __name__ == "__main__":
    raise SystemExit(main())
