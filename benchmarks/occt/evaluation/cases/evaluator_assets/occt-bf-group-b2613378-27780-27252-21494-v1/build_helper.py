#!/usr/bin/env python3
"""G3 bundle-local Clang 10 / O0 build helper, adapted from reviewed G1 code.

The manifest suite driver calls ``apply_patch`` and ``configure_and_build``.
The public submission contract remains the framework's non-empty patch.diff
and report.md contract; this module only provides the controlled build helper.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

GROUP = "occt-bf-group-b2613378-27780-27252-21494-v1"
XLOCALE_SHA256 = "0cfbf755395add5d865f01722849120cbd0dccb0774755f2af369950dbcb779f"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(command: list[str], cwd: Path, timeout: int, input_data: bytes | None = None) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=cwd, input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout, check=False)
        output = proc.stdout.decode("utf-8", errors="replace")
        return {"command": [str(item) for item in command], "return_code": proc.returncode,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "output_tail": output[-12000:], "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or b""
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="replace")
        return {"command": [str(item) for item in command], "return_code": None,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "output_tail": raw.decode("utf-8", errors="replace")[-12000:],
                "timed_out": True}


def apply_patch(source: Path, patch_arg: str) -> int:
    """Apply the required non-empty agent patch to the isolated B source copy."""
    if patch_arg == "-":
        patch_data = sys.stdin.buffer.read()
    else:
        patch_path = Path(patch_arg).expanduser().resolve()
        if not patch_path.is_file():
            raise ValueError(f"patch file does not exist: {patch_path}")
        if patch_path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("patch exceeds 20 MiB limit")
        patch_data = patch_path.read_bytes()
    if not patch_data:
        raise ValueError("empty patch")
    checked = run(["git", "apply", "--check", "--whitespace=nowarn", "-"], source, 60, patch_data)
    if checked["return_code"] != 0:
        raise ValueError("patch check failed: " + checked["output_tail"][-3000:])
    applied = run(["git", "apply", "--whitespace=nowarn", "-"], source, 60, patch_data)
    if applied["return_code"] != 0:
        raise ValueError("patch apply failed: " + applied["output_tail"][-3000:])
    return len(patch_data)


def _overlay() -> Path:
    # The helper module is loaded from this group's private evaluator assets
    # in both the staged bundle and the prepared framework control tree.
    candidate = Path(__file__).resolve().parent / "toolchain_overlay"
    header = candidate / "xlocale.h"
    if not header.is_file() or sha256(header) != XLOCALE_SHA256:
        raise RuntimeError("locked xlocale compatibility overlay is missing or has changed")
    return candidate


def _tcl_values() -> dict[str, str]:
    prefix = Path(os.environ.get("CONDA_PREFIX", sys.prefix)).resolve()
    defaults = {
        "BENCH_TCL_DIR": prefix,
        "BENCH_TCL_INCLUDE_DIR": prefix / "include",
        "BENCH_TCL_LIBRARY": prefix / "lib" / "libtcl8.6.so",
        "BENCH_TCL_LIBRARY_DIR": prefix / "lib",
        "BENCH_TK_DIR": prefix,
        "BENCH_TK_INCLUDE_DIR": prefix / "include",
        "BENCH_TK_LIBRARY": prefix / "lib" / "libtk8.6.so",
        "BENCH_TK_LIBRARY_DIR": prefix / "lib",
    }
    result: dict[str, str] = {}
    for key, default in defaults.items():
        value = os.environ.get(key, str(default))
        if value:
            result[key] = str(Path(value).resolve())
    return result


def configure_and_build(source: Path, build: Path) -> dict:
    """Configure/build the frozen natural-source profile with one or two compiler jobs."""
    source = Path(source).resolve()
    build = Path(build).resolve()
    cmake = os.environ.get("BENCH_CMAKE", "cmake")
    cc = os.environ.get("BENCH_CC", "clang-10")
    cxx = os.environ.get("BENCH_CXX", "clang++-10")
    jobs = os.environ.get("BENCH_COMPILER_JOBS", "2")
    if jobs not in {"1", "2"}:
        return {"configure": None, "build": None, "failure": "BENCH_COMPILER_JOBS must be 1 or 2"}
    overlay = _overlay()
    cmake_args = [
        cmake, "-S", str(source), "-B", str(build),
        "-G", "Unix Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_LIBRARY_TYPE=Shared",
        "-DINSTALL_SAMPLES=OFF", "-DINSTALL_TEST_CASES=OFF", "-DBUILD_DOC_Overview=OFF",
        "-DBUILD_ADDITIONAL_TOOLKITS=DRAWEXE;TKTopTest",
        "-DBUILD_MODULE_ApplicationFramework=OFF", "-DBUILD_MODULE_DataExchange=OFF",
        "-DBUILD_MODULE_Draw=OFF", "-DBUILD_MODULE_FoundationClasses=OFF",
        "-DBUILD_MODULE_ModelingAlgorithms=OFF", "-DBUILD_MODULE_ModelingData=OFF",
        "-DBUILD_MODULE_Visualization=ON", "-DUSE_TK=ON", "-DUSE_FREETYPE=ON",
        f"-DCMAKE_C_COMPILER={cc}", f"-DCMAKE_CXX_COMPILER={cxx}",
        "-DCMAKE_C_FLAGS_RELEASE=-O0 -DNDEBUG", "-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG",
        f"-DCMAKE_CXX_FLAGS=-I{overlay}",
    ]
    for variable, key in (
        ("3RDPARTY_TCL_DIR", "BENCH_TCL_DIR"),
        ("3RDPARTY_TCL_INCLUDE_DIR", "BENCH_TCL_INCLUDE_DIR"),
        ("3RDPARTY_TCL_LIBRARY", "BENCH_TCL_LIBRARY"),
        ("3RDPARTY_TCL_LIBRARY_DIR", "BENCH_TCL_LIBRARY_DIR"),
        ("3RDPARTY_TK_DIR", "BENCH_TK_DIR"),
        ("3RDPARTY_TK_INCLUDE_DIR", "BENCH_TK_INCLUDE_DIR"),
        ("3RDPARTY_TK_LIBRARY", "BENCH_TK_LIBRARY"),
        ("3RDPARTY_TK_LIBRARY_DIR", "BENCH_TK_LIBRARY_DIR"),
    ):
        value = os.environ.get(key) or _tcl_values().get(key)
        if value:
            cmake_args.append(f"-D{variable}={value}")
    freetype = {
        "3RDPARTY_FREETYPE_INCLUDE_DIR_ft2build": os.environ.get("BENCH_FREETYPE_INCLUDE_FT2BUILD", "/usr/include/freetype2"),
        "3RDPARTY_FREETYPE_INCLUDE_DIR_freetype2": os.environ.get("BENCH_FREETYPE_INCLUDE_FREETYPE2", "/usr/include/freetype2"),
        "3RDPARTY_FREETYPE_LIBRARY": os.environ.get("BENCH_FREETYPE_LIBRARY", "/usr/lib/x86_64-linux-gnu/libfreetype.so"),
        "3RDPARTY_FREETYPE_LIBRARY_DIR": os.environ.get("BENCH_FREETYPE_LIBRARY_DIR", "/usr/lib/x86_64-linux-gnu"),
    }
    cmake_args.extend(f"-D{name}={value}" for name, value in freetype.items() if value)
    configured = run(cmake_args, source, 2400)
    if configured["return_code"] != 0:
        return {"configure": configured, "build": None}
    built = run([cmake, "--build", str(build), "--target", "DRAWEXE", "TKTopTest",
                 "--parallel", jobs], source, 3600)
    return {"configure": configured, "build": built}

