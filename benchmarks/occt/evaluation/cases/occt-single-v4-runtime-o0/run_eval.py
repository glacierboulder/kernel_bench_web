#!/usr/bin/env python3
"""Trusted source-patch and OCCT build helpers for the intersection suite."""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


VERSION_MACRO_RE = re.compile(r"^\s*#define\s+OCC_VERSION_(MAJOR|MINOR)\s+(\d+)", re.M)
MAX_PATCH_BYTES = 20 * 1024 * 1024


def run(command, cwd: Path, timeout: int, input_data: bytes | None = None) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen(
        [str(part) for part in command], cwd=cwd,
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        output, _ = proc.communicate(input=input_data, timeout=timeout)
        output = output.decode("utf-8", errors="replace")
        return {
            "command": [str(part) for part in command],
            "return_code": proc.returncode,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output_tail": output[-12000:],
        }
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        output, _ = proc.communicate()
        output = output.decode("utf-8", errors="replace")
        return {
            "command": [str(part) for part in command],
            "return_code": None,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output_tail": str(output)[-12000:],
        }


def apply_patch(source: Path, patch_arg: str) -> int:
    """Apply a bounded unified diff only after git's whitespace-aware dry run."""
    source = Path(source).resolve(strict=True)
    if patch_arg == "-":
        patch_data = sys.stdin.buffer.read(MAX_PATCH_BYTES + 1)
    else:
        patch_path = Path(patch_arg).expanduser().resolve()
        if not patch_path.is_file():
            raise ValueError(f"patch file does not exist: {patch_path}")
        if patch_path.stat().st_size > MAX_PATCH_BYTES:
            raise ValueError("patch exceeds 20 MiB limit")
        with patch_path.open("rb") as patch_file:
            patch_data = patch_file.read(MAX_PATCH_BYTES + 1)
    if not patch_data:
        raise ValueError("empty patch")
    if len(patch_data) > MAX_PATCH_BYTES:
        raise ValueError("patch exceeds 20 MiB limit")

    check = run(
        ["git", "apply", "--check", "--whitespace=nowarn", "-"],
        source,
        60,
        patch_data,
    )
    if check["return_code"] != 0:
        raise ValueError("patch check failed: " + check["output_tail"][-3000:])
    applied = run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        source,
        60,
        patch_data,
    )
    if applied["return_code"] != 0:
        raise ValueError("patch apply failed: " + applied["output_tail"][-3000:])
    return len(patch_data)


def occt_version(source: Path) -> tuple[int, int]:
    candidates = (
        source / "src" / "Standard" / "Standard_Version.hxx",
        source / "Standard" / "Standard_Version.hxx",
        source / "inc" / "Standard_Version.hxx",
    )
    for path in candidates:
        if not path.is_file():
            continue
        found = dict(VERSION_MACRO_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
        if "MAJOR" in found and "MINOR" in found:
            return int(found["MAJOR"]), int(found["MINOR"])
    raise ValueError("could not identify OCCT major/minor version from Standard_Version.hxx")


def _legacy_build_aliases(source: Path, build: Path, toolchain_name: str) -> dict:
    aliases = []
    alias_dir = build / "lin64" / toolchain_name
    for name in ("bin", "lib"):
        target = build / "out" / name
        if not target.is_dir():
            target = build / "lin64" / "gcc" / name
        link = alias_dir / name
        if target.is_dir() and not link.exists() and not link.is_symlink():
            alias_dir.mkdir(parents=True, exist_ok=True)
            link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
            aliases.append(str(link.relative_to(build)))

    legacy_headers = build / "inc" if (build / "inc").is_dir() else source / "inc"
    include_alias = build / "include" / "opencascade"
    if legacy_headers.is_dir() and not include_alias.exists() and not include_alias.is_symlink():
        include_alias.parent.mkdir(parents=True, exist_ok=True)
        include_alias.symlink_to(legacy_headers, target_is_directory=True)
        aliases.append(str(include_alias.relative_to(build)))
    return {"build_tree_aliases": aliases}


def _runtime_exists(build: Path, toolchain_name: str) -> bool:
    for binary_dir, library_dir in _runtime_layouts(build, toolchain_name):
        binaries = (binary_dir / "DRAWEXE", *binary_dir.glob("DRAWEXE-*"))
        if any(binary.is_file() for binary in binaries) and library_dir.is_dir():
            return True
    return False


def _runtime_layouts(build: Path, toolchain_name: str) -> tuple[tuple[Path, Path], ...]:
    return (
        (build / "lin64" / toolchain_name / "bin", build / "lin64" / toolchain_name / "lib"),
        (build / "lin64" / "clang" / "bin", build / "lin64" / "clang" / "lib"),
        (build / "lin64" / "gcc" / "bin", build / "lin64" / "gcc" / "lib"),
        (build / "ADDITIONAL" / "lin64" / toolchain_name / "bin",
         build / "ADDITIONAL" / "lin64" / toolchain_name / "lib"),
        (build / "ADDITIONAL" / "lin64" / "clang" / "bin",
         build / "ADDITIONAL" / "lin64" / "clang" / "lib"),
        (build / "out" / "bin", build / "out" / "lib"),
        (build / "bin", build / "lib"),
    )



def optimization_flags_for_profile(toolchain_name: str) -> str:
    profiles = {"clang-o3": "-O3 -DNDEBUG", "clang-o0": "-O0 -DNDEBUG"}
    try:
        return profiles[toolchain_name]
    except KeyError as exc:
        raise ValueError(f"unsupported locked compiler profile: {toolchain_name}") from exc

def configure_and_build(source: Path, build: Path) -> dict:
    """Configure DRAW/TKTopTest with version-appropriate toolkit options."""
    source = Path(source).resolve(strict=True)
    build = Path(build).resolve()
    if not (source / "CMakeLists.txt").is_file():
        raise ValueError(f"OCCT source CMakeLists.txt is missing: {source}")
    if build == source or build.is_relative_to(source):
        raise ValueError("build directory must be outside the locked source tree")

    major, minor = occt_version(source)
    if major == 6 and minor in (8, 9):
        toolkit_variable = "BUILD_TOOLKITS"
    elif major in (7, 8):
        toolkit_variable = "BUILD_ADDITIONAL_TOOLKITS"
    else:
        raise ValueError(f"unsupported OCCT version {major}.{minor}; expected 6.8, 6.9, 7.x, or 8.x")

    try:
        jobs = min(2, max(1, int(os.environ.get("BENCH_COMPILER_JOBS", "2"))))
    except ValueError as exc:
        raise ValueError("BENCH_COMPILER_JOBS must be 1 or 2") from exc
    if str(jobs) != os.environ.get("BENCH_COMPILER_JOBS", str(jobs)):
        # Reject values such as 0, 3, or malformed strings after the clamp.
        raise ValueError("BENCH_COMPILER_JOBS must be 1 or 2")

    cmake_bin = os.environ.get("BENCH_CMAKE", "cmake")
    compiler_c = os.environ.get("BENCH_CC", "clang-10")
    compiler_cxx = os.environ.get("BENCH_CXX", "clang++-10")
    toolchain_name = os.environ.get("BENCH_TOOLCHAIN_NAME", "clang")
    optimization_flags = optimization_flags_for_profile(toolchain_name)
    configure_command = [
        cmake_bin, "-S", str(source), "-B", str(build),
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_C_FLAGS_RELEASE={optimization_flags}",
        f"-DCMAKE_CXX_FLAGS_RELEASE={optimization_flags}",
        f"-DCMAKE_C_COMPILER={compiler_c}",
        f"-DCMAKE_CXX_COMPILER={compiler_cxx}",
    ]
    locale_header = source / "src" / "Standard" / "Standard_CLocaleSentry.hxx"
    compatibility = []
    if sys.platform.startswith("linux") and locale_header.is_file() and "#include <xlocale.h>" in locale_header.read_text():
        probe = subprocess.run([compiler_cxx, "-E", "-x", "c++", "-"],
                               input=b"#include <xlocale.h>\n", capture_output=True, timeout=30)
        if probe.returncode != 0:
            # glibc 2.26 moved the declarations into locale.h. Keep this
            # compatibility header in the disposable build, outside source.
            shim = build / "compat-include"
            shim.mkdir(parents=True, exist_ok=True)
            (shim / "xlocale.h").write_text("#pragma once\n#include <locale.h>\n")
            configure_command.append(f"-DCMAKE_CXX_FLAGS=-I{shim}")
            compatibility.append("build-only xlocale.h forwarding to locale.h")
    if toolkit_variable == "BUILD_TOOLKITS":
        configure_command.extend((
            "-DBUILD_TOOLKITS=TKTopTest;DRAWEXE",
            f"-DINSTALL_DIR={build / 'install'}",
        ))
    else:
        configure_command.extend((
            "-DBUILD_LIBRARY_TYPE=Shared",
            "-DBUILD_ADDITIONAL_TOOLKITS=TKTopTest;DRAWEXE",
            "-DBUILD_MODULE_ApplicationFramework=OFF",
            "-DBUILD_MODULE_DataExchange=OFF",
            "-DBUILD_MODULE_Draw=OFF",
            "-DBUILD_MODULE_FoundationClasses=OFF",
            "-DBUILD_MODULE_ModelingAlgorithms=OFF",
            "-DBUILD_MODULE_ModelingData=OFF",
            "-DBUILD_MODULE_Visualization=OFF",
            "-DUSE_FREETYPE=OFF",
            "-DUSE_TK=OFF",
        ))
    for variable, environment in (
        ("3RDPARTY_TCL_DIR", "BENCH_TCL_DIR"),
        ("3RDPARTY_TCL_INCLUDE_DIR", "BENCH_TCL_INCLUDE_DIR"),
        ("3RDPARTY_TCL_LIBRARY", "BENCH_TCL_LIBRARY"),
        ("3RDPARTY_TCL_LIBRARY_DIR", "BENCH_TCL_LIBRARY_DIR"),
    ):
        value = os.environ.get(environment)
        if value:
            configure_command.append(f"-D{variable}={value}")

    build.mkdir(parents=True, exist_ok=True)
    configure = run(configure_command, build.parent, 2400)
    output = {
        "occt_version": f"{major}.{minor}",
        "toolkit_cache_variable": toolkit_variable,
        "configure": configure,
        "build": None,
        "build_compatibility": compatibility,
    }
    if configure["return_code"] != 0:
        return output

    build_result = run(
        [cmake_bin, "--build", str(build), "--target", "DRAWEXE", "TKTopTest", "--parallel", str(jobs)],
        build.parent,
        3600,
    )
    output["build"] = build_result
    if build_result["return_code"] == 0:
        aliases = _legacy_build_aliases(source, build, toolchain_name)
        output.update(aliases)
        if not _runtime_exists(build, toolchain_name):
            build_result["return_code"] = 1
            build_result["runtime_layout_error"] = "DRAWEXE and its matching library directory were not found"
    return output
