#!/usr/bin/env python3
"""Thin G3 suite-driver API wrapper around the frozen geometry oracle."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

GROUP = "occt-bf-group-b2613378-27780-27252-21494-v1"
EXPECTED_GEOMETRY_ORACLE_SHA256 = "d1a64053733de910040e56b9f075cbfb3be25f98ba75867bfc48a4ec690a13a3"
EXPECTED_BUILD_HELPER_SHA256 = "2de3ee65be27c29534e3fe3fec76a1165758acf41f9551cecd8248ae517de72c"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _find_asset(name: str) -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parent / name]
    candidates.extend(parent / "evaluator_assets" / GROUP / name for parent in here.parents)
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            return candidate.resolve()
    raise RuntimeError(f"frozen G3 private evaluator asset is missing: {name}")


def _load(name: str, module_name: str):
    path = _find_asset(name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load G3 evaluator module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


_GEOMETRY, GEOMETRY_ORACLE_PATH = _load("geometry_oracle.py", "bf_g3_frozen_geometry_oracle")
_BUILD, BUILD_HELPER_PATH = _load("build_helper.py", "bf_g3_frozen_build_helper")
GEOMETRY_ORACLE_SHA256 = _sha256(GEOMETRY_ORACLE_PATH)
BUILD_HELPER_SHA256 = _sha256(BUILD_HELPER_PATH)
if GEOMETRY_ORACLE_SHA256 != EXPECTED_GEOMETRY_ORACLE_SHA256:
    raise RuntimeError(f"G3 geometry oracle hash mismatch: {GEOMETRY_ORACLE_SHA256}")
if BUILD_HELPER_SHA256 != EXPECTED_BUILD_HELPER_SHA256:
    raise RuntimeError(f"G3 build helper hash mismatch: {BUILD_HELPER_SHA256}")

# Preserve the exact case-mapped geometry predicate callable and add only the
# suite driver's required local patch/build API.
validate_draw_text = _GEOMETRY.validate_draw_text
apply_patch = _BUILD.apply_patch
configure_and_build = _BUILD.configure_and_build


def build_overlay_path() -> Path:
    """Resolve and verify the G3 compatibility overlay without building."""
    return _BUILD._overlay()

__all__ = ["validate_draw_text", "apply_patch", "configure_and_build",
           "GEOMETRY_ORACLE_PATH", "GEOMETRY_ORACLE_SHA256",
           "BUILD_HELPER_PATH", "BUILD_HELPER_SHA256", "build_overlay_path"]
