#!/usr/bin/env python3
"""Case-path router to the original bundle-local DRAW runner for each group."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

def _asset_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        for candidate in (parent / "private" / "evaluator_assets",
                          parent / "evaluator_assets"):
            lock = candidate / "five_group_execution" / "dispatch_lock.json"
            if lock.is_file() and not lock.is_symlink():
                return candidate
    raise RuntimeError("five-group DRAW runner assets are unavailable")

def _lock() -> dict:
    value = json.loads((_asset_root() / "five_group_execution" / "dispatch_lock.json").read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or value.get("routing_contract") != "occt-five-group-explicit-checkpoint-v2":
        raise RuntimeError("unsupported five-group DRAW dispatch lock")
    return value

def _checkpoint_ref(case_dir: str, script: str) -> str:
    if not script or Path(script).name != script or "\\" in script:
        raise RuntimeError("framework DRAW runner passed an unsafe checkpoint script name")
    parts = PurePosixPath(case_dir).parts
    bundle_positions = [index for index, part in enumerate(parts) if part == "bundle"]
    if len(bundle_positions) != 1:
        raise RuntimeError("frozen case directory must contain exactly one bundle root")
    suffix = parts[bundle_positions[0] + 1:]
    if not suffix:
        raise RuntimeError("frozen case directory does not identify a checkpoint parent")
    return PurePosixPath(*suffix, script).as_posix()

def _option_value(argv: list[str], name: str) -> str:
    try:
        return argv[argv.index(name) + 1]
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"framework DRAW runner did not pass {name}") from exc

def _runner_for_case(case_dir: str, script: str) -> tuple[str, Path]:
    lock = _lock()
    case_ref = _checkpoint_ref(case_dir, script)
    route = lock["checkpoint_routes"].get(case_ref)
    if route is None:
        raise RuntimeError(f"unregistered DRAW checkpoint route: {case_ref}")
    origin = route["origin"]
    route = lock["runner_routes"][origin]
    rel = PurePosixPath(route["path"])
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise RuntimeError("unsafe original DRAW runner path")
    root = _asset_root().resolve()
    runner = root.joinpath(*rel.parts).resolve(strict=True)
    if not runner.is_relative_to(root) or runner.is_symlink() or not runner.is_file():
        raise RuntimeError("original DRAW runner escapes the merged bundle")
    if hashlib.sha256(runner.read_bytes()).hexdigest() != route["sha256"]:
        raise RuntimeError(f"locked original DRAW runner hash mismatch: {runner.name}")
    return origin, runner

def _command_for_case(argv: list[str]) -> list[str]:
    case_dir = _option_value(argv, "--case-dir")
    script = _option_value(argv, "--script")
    origin, runner = _runner_for_case(case_dir, script)
    forwarded = list(argv)
    if origin == "g3" and "--role" not in forwarded:
        forwarded.extend(["--role", "agent"])
    return [sys.executable, str(runner), *forwarded]

def main() -> int:
    if any(item in {"-h", "--help"} for item in sys.argv[1:]):
        print("usage: run_draw_case.py --build-dir DIR --resource-dir DIR --case-dir DIR --script FILE [runner options]")
        return 0
    try:
        command = _command_for_case(sys.argv[1:])
        return subprocess.run(command, check=False).returncode
    except Exception as exc:
        print(f"five-group DRAW adapter error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
