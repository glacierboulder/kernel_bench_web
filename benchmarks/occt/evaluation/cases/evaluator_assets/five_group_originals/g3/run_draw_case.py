#!/usr/bin/env python3
"""Framework CLI adapter pinned to the G3 case-mapped geometry runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GROUP = "occt-bf-group-b2613378-27780-27252-21494-v1"
CORE_SHA256 = "36c057a5eeb849d3db60ee64bbf5930663c00bb6fc0d8249f09313c156f8b72e"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runner_paths() -> tuple[Path, Path]:
    here = Path(__file__).resolve()
    # In the worker image the copied adapter is /evaluation/scripts/... and
    # private assets live under /evaluation/private/.... Also support the
    # exact local _prepare_control tree (control/scripts + control/private)
    # used by integration probes and direct offline replay.
    for parent in here.parents:
        runtime_assets = parent / "private" / "evaluator_assets" / GROUP
        runtime_helper = parent / "private" / "evaluators" / "run_eval.py"
        if runtime_assets.is_dir() and runtime_helper.is_file():
            return runtime_assets / "run_draw_case_core.py", runtime_helper
    for parent in here.parents:
        asset = parent / "evaluator_assets" / GROUP
        helper_candidates = (parent / "legacy" / "run_eval.py", asset / "run_eval.py")
        helper = next((item for item in helper_candidates if item.is_file()), None)
        core = asset / "run_draw_case_core.py"
        if core.is_file() and helper is not None:
            return core, helper
    raise RuntimeError("frozen G3 geometry core/helper are unavailable")


def _artifact_info(requested: str, build: Path) -> tuple[str | None, dict[str, str]]:
    binary = build / "lin64" / "clang" / "bin" / "DRAWEXE"
    plugin = build / "lin64" / "clang" / "lib" / "libTKTopTest.so"
    actual = {"drawexe_sha256": sha(binary) if binary.is_file() else "",
              "tktoptest_sha256": sha(plugin) if plugin.is_file() else ""}
    # The artifact hashes are recorded as provenance only. Agent mode always
    # remains agent-attributed: a patch can change a dependent geometry library
    # while DRAWEXE and TKTopTest retain their calibration bytes.
    return (requested if requested in {"B", "F"} else None), actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", default="reproduce.tcl")
    parser.add_argument("--role", choices=("B", "F", "agent"), default="agent")
    parser.add_argument("--log", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--oracle-helper", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--materialized-tree")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--cpu-limit-seconds", type=int, default=160)
    parser.add_argument("--address-space-gib", type=int, default=4)
    args = parser.parse_args()

    try:
        required = os.environ.get("BENCH_REQUIRED_CONDA_ENV", "").strip()
        active = os.environ.get("CONDA_DEFAULT_ENV")
        prefix = Path(os.environ.get("CONDA_PREFIX", ""))
        verified_prefix = prefix.is_dir() and (prefix / "conda-meta").is_dir()
        if required and active != required:
            raise RuntimeError(f"requires conda environment {required!r}; active={active!r}")
        if not required and not verified_prefix:
            raise RuntimeError("must execute in a verified Conda environment")
        build, resource_dir, case_dir = args.build_dir.resolve(), args.resource_dir.resolve(), args.case_dir.resolve()
        core, default_helper = _runner_paths()
        core_hash = sha(core)
        if core_hash != CORE_SHA256:
            raise RuntimeError(f"locked G3 geometry core hash mismatch: {core_hash}")
        helper = args.oracle_helper.resolve() if args.oracle_helper else default_helper.resolve()
        if not helper.is_file():
            raise RuntimeError(f"frozen G3 geometry helper is missing: {helper}")
        calibration_identity, actual = _artifact_info(args.role, build)
        log = args.log.resolve() if args.log else Path(tempfile.mkdtemp(prefix="bf_group3_draw_")) / "draw.log"
        command = [sys.executable, str(core), "--build-dir", str(build),
                   "--resource-dir", str(resource_dir), "--case-dir", str(case_dir),
                   "--script", args.script, "--role", args.role,
                   "--log", str(log), "--oracle-helper", str(helper),
                   "--timeout-seconds", str(args.timeout_seconds),
                   "--cpu-limit-seconds", str(args.cpu_limit_seconds),
                   "--address-space-gib", str(args.address_space_gib)]
        if args.record:
            # The wrapper writes the augmented record after it has parsed the
            # core result; avoid writing an intermediate file at the same path.
            pass
        if args.source_commit:
            command += ["--source-commit", args.source_commit]
        if args.materialized_tree:
            command += ["--materialized-tree", args.materialized_tree]
        if args.evidence_dir:
            command += ["--evidence-dir", str(args.evidence_dir.resolve())]
        process = subprocess.run(command, cwd=case_dir, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        try:
            record = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"geometry core did not return JSON: {process.stdout[-3000:]}") from exc
        execution = record.get("execution", {})
        oracle = record.get("oracle", {})
        geometry_status = oracle.get("status", "not_run")
        test_done = execution.get("status") == "completed" and execution.get("oracle_ran") is True and geometry_status == "geometry_pass"
        return_code = 0 if test_done else 1 if execution.get("status") == "completed" else 3 if execution.get("status") == "timeout" else 2
        record.update({
            "requested_role": args.role,
            "role": args.role,
            "calibration_identity": calibration_identity,
            "actual_artifact_hashes": actual,
            "geometry_core_path": str(core),
            "geometry_core_sha256": core_hash,
            "framework_runner_path": str(Path(__file__).resolve()),
            "framework_runner_sha256": sha(Path(__file__).resolve()),
            "test_done_marker": test_done,
            "return_code": return_code,
            "timed_out": execution.get("status") == "timeout",
            "process_return_code": return_code,
        })
        if args.record:
            record_path = args.record.resolve()
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                   encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
        return return_code
    except Exception as exc:
        record = {"requested_role": args.role, "role": args.role,
                  "execution": {"status": "not_run", "oracle_ran": False},
                  "oracle": {"status": "not_run", "checks": []},
                  "test_done_marker": False, "return_code": 2,
                  "timed_out": False, "process_return_code": 2,
                  "diagnostic": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
