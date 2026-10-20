#!/usr/bin/env python3
"""Suite-aware adapter preserving the five source/evaluator boundaries."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys

def _asset_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "evaluator_assets"
        lock = candidate / "five_group_execution" / "dispatch_lock.json"
        if lock.is_file() and not lock.is_symlink():
            return candidate
    raise RuntimeError("five-group evaluator assets are unavailable")

def _lock() -> dict:
    root = _asset_root()
    path = root / "five_group_execution" / "dispatch_lock.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or value.get("routing_contract") != "occt-five-group-explicit-checkpoint-v2":
        raise RuntimeError("unsupported five-group evaluator dispatch lock")
    return value

def _safe_asset(relative: str) -> Path:
    rel = PurePosixPath(relative)
    if rel.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in rel.parts):
        raise RuntimeError("unsafe evaluator asset path")
    root = _asset_root().resolve()
    path = root.joinpath(*rel.parts).resolve(strict=True)
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        raise RuntimeError("evaluator asset path escapes the locked bundle")
    return path

def _load(route: dict):
    path = _safe_asset(route["path"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != route["sha256"]:
        raise RuntimeError(f"locked evaluator helper hash mismatch: {path.name}")
    name = "occt_five_group_" + digest[:16]
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("cannot load locked evaluator helper")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module

def _selected_route() -> tuple[dict, dict]:
    lock = _lock()
    try:
        index = sys.argv.index("--suite")
        suite_path = Path(sys.argv[index + 1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError("suite driver must pass its frozen --suite manifest") from exc
    if suite_path.is_symlink() or not suite_path.is_file():
        raise RuntimeError("selected suite manifest is missing or symlinked")
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    identity = f'{suite.get("id")}@{suite.get("version")}'
    route = lock["suite_routes"].get(identity)
    if route is None or route["group_id"] not in suite.get("group_ids", []):
        raise RuntimeError(f"unregistered five-group suite route: {identity}")
    return lock, route

def apply_patch(source, patch_arg):
    lock, route = _selected_route()
    return _load(lock["helper_routes"][route["origin"]]).apply_patch(source, patch_arg)

def configure_and_build(source, build):
    lock, route = _selected_route()
    return _load(lock["helper_routes"][route["origin"]]).configure_and_build(source, build)

def validate_draw_text(*args, **kwargs):
    lock = _lock()
    return _load(lock["g3_geometry_oracle"]).validate_draw_text(*args, **kwargs)

__all__ = ["apply_patch", "configure_and_build", "validate_draw_text"]
