#!/usr/bin/env python3
"""Private oracle parser and future GCC 9.4/O0/j1 build helper for group 2.

Geometry verdicts are computed from the exact stdout bytes captured from the
current DRAW invocation. This module never reads calibration result booleans.
"""
from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

GROUP = "occt-bf-group-b55-27310-27773-27252-oracle-v2"
XLOCALE_SHA256 = "0cfbf755395add5d865f01722849120cbd0dccb0774755f2af369950dbcb779f"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
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
    """Keep the existing required, non-empty patch.diff submission contract."""
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
    candidate = Path(__file__).resolve().parent / "toolchain_overlay"
    header = candidate / "xlocale.h"
    if not header.is_file() or sha256(header) != XLOCALE_SHA256:
        raise RuntimeError("locked xlocale compatibility overlay is missing or changed")
    return candidate


def configure_and_build(source: Path, build: Path) -> dict:
    """Future local helper; this task does not invoke it or rebuild OCCT."""
    source, build = Path(source).resolve(), Path(build).resolve()
    cmake = os.environ.get("BENCH_CMAKE", "cmake")
    cc, cxx = os.environ.get("BENCH_CC", "gcc"), os.environ.get("BENCH_CXX", "g++")
    jobs = os.environ.get("BENCH_COMPILER_JOBS", "2")
    if jobs not in {"1", "2"}:
        return {"configure": None, "build": None, "failure": "BENCH_COMPILER_JOBS must be 1 or 2"}
    overlay = _overlay()
    args = [cmake, "-S", str(source), "-B", str(build), "-G", "Unix Makefiles",
            "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_LIBRARY_TYPE=Shared",
            "-DINSTALL_SAMPLES=OFF", "-DINSTALL_TEST_CASES=OFF", "-DBUILD_DOC_Overview=OFF",
            "-DBUILD_ADDITIONAL_TOOLKITS=DRAWEXE;TKTopTest",
            "-DBUILD_MODULE_ApplicationFramework=OFF", "-DBUILD_MODULE_DataExchange=OFF",
            "-DBUILD_MODULE_Draw=OFF", "-DBUILD_MODULE_FoundationClasses=OFF",
            "-DBUILD_MODULE_ModelingAlgorithms=OFF", "-DBUILD_MODULE_ModelingData=OFF",
            "-DBUILD_MODULE_Visualization=ON", "-DUSE_TK=ON", "-DUSE_FREETYPE=ON",
            f"-DCMAKE_C_COMPILER={cc}", f"-DCMAKE_CXX_COMPILER={cxx}",
            "-DCMAKE_C_FLAGS_RELEASE=-O0 -DNDEBUG", "-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG",
            f"-DCMAKE_CXX_FLAGS=-I{overlay}"]
    for variable, env_name in (("3RDPARTY_TCL_DIR", "BENCH_TCL_DIR"),
                               ("3RDPARTY_TCL_INCLUDE_DIR", "BENCH_TCL_INCLUDE_DIR"),
                               ("3RDPARTY_TCL_LIBRARY", "BENCH_TCL_LIBRARY"),
                               ("3RDPARTY_TCL_LIBRARY_DIR", "BENCH_TCL_LIBRARY_DIR"),
                               ("3RDPARTY_TK_DIR", "BENCH_TK_DIR"),
                               ("3RDPARTY_TK_INCLUDE_DIR", "BENCH_TK_INCLUDE_DIR"),
                               ("3RDPARTY_TK_LIBRARY", "BENCH_TK_LIBRARY"),
                               ("3RDPARTY_TK_LIBRARY_DIR", "BENCH_TK_LIBRARY_DIR")):
        if os.environ.get(env_name):
            args.append(f"-D{variable}={os.environ[env_name]}")
    configured = run(args, source, 2400)
    if configured["return_code"] != 0:
        return {"configure": configured, "build": None}
    built = run([cmake, "--build", str(build), "--target", "DRAWEXE", "TKTopTest",
                 "--parallel", jobs], source, 3600)
    return {"configure": configured, "build": built}


def parse_samples(text: str, case_id: str) -> dict[int, list[tuple[float, float, float]]]:
    if "BF_TCL_SAMPLING_COMPLETE=1" not in text:
        raise ValueError(f"sampling incomplete: {case_id}")
    raw: dict[int, list[tuple[int, tuple[float, float, float]]]] = {}
    pattern = re.compile(r"^BF_CURVE_(\d+)_SAMPLE_(\d+)=([^,]+),([^,]+),([^\s]+)$", re.M)
    for match in pattern.finditer(text):
        point = tuple(float(match.group(i)) for i in (3, 4, 5))
        if not all(math.isfinite(value) for value in point):
            raise ValueError(f"nonfinite sample: {case_id}")
        raw.setdefault(int(match.group(1)), []).append((int(match.group(2)), point))
    curves = {}
    for curve_id, values in raw.items():
        values.sort(key=lambda item: item[0])
        if [index for index, _ in values] != list(range(17)):
            raise ValueError(f"incomplete or duplicate samples: {case_id}/curve{curve_id}")
        curves[curve_id] = [point for _, point in values]
    count = re.search(r"^BF_CURVE_COUNT=(\d+)$", text, re.M)
    if count is None or int(count.group(1)) != len(curves):
        raise ValueError(f"curve count/sample mismatch: {case_id}")
    return curves


def parse_vertices(text: str) -> list[tuple[float, float, float]]:
    block = text.split("BF_VERTEX_COORDS_BEGIN", 1)
    if len(block) != 2 or "BF_VERTEX_COORDS_END" not in block[1]:
        raise ValueError("missing vertex coordinate block")
    content = block[1].split("BF_VERTEX_COORDS_END", 1)[0]
    return [tuple(float(match.group(i)) for i in (1, 2, 3)) for match in re.finditer(
        r"^result_\d+ \(x,y,z\) : ([^\s]+) ([^\s]+) ([^\s]+)$", content, re.M)]


def dist(a, b) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _common_draw_checks(text: str, case_id: str, role: str) -> None:
    if "DRAW is running in batch mode" not in text:
        raise ValueError("DRAW did not start")
    if text.count(f"BF_HARNESS_CASE={case_id}") != 1 or "BF_HARNESS_COMPLETED=1" not in text:
        raise ValueError("staged harness completion marker missing or duplicated")
    if text.count("BF_DRAW_RC=0") != 1 or not text.rstrip().endswith("BF_DRAW_RC=0"):
        raise ValueError("DRAW process did not complete with exactly one final zero-return marker")
    source_rc = re.findall(r"^BF_SOURCE_RC=(\d+)$", text, re.M)
    if len(source_rc) != 1:
        raise ValueError("missing or duplicate Tcl source result")
    expected_empty_curve_error = (
        case_id == "M27252" and role == "B" and
        'BF_SOURCE_ERROR=can\'t read "NbCurv": no such variable' in text
    )
    if case_id == "M27252" and role == "B":
        # Only the reviewed empty-BOP result is a geometry failure. Missing input,
        # malformed result text, any other Tcl failure, or another diagnostic
        # remains runtime_error.
        if (source_rc != ["1"] or "BF_SOURCE_ERROR=can't read \"NbCurv\": no such variable" not in text or
                "has no 3d curves" not in text or "has no 3d points" not in text):
            raise ValueError("M27252 B did not match the exact reviewed no-3D-curve adapter signature")
    elif source_rc != ["0"]:
        raise ValueError("Tcl source command failed")
    fatal = re.compile(r"(?:DRAW\s+function\s+failed|invalid command name|unknown command|wrong # args|"
                       r"can't read|couldn't (?:open|read|load)|no such file or directory|"
                       r"BF_ORACLE_EVAL_ERROR=|Standard_[A-Za-z0-9_]+Exception|while executing|"
                       r"invoked from within)", re.I)
    allow = []
    if role == "B" and case_id == "M27310_1":
        allow = [re.compile(r"^Error: Number of curves is bad!$"),
                 re.compile(r"^Error: TolReached = [-+0-9.eE]+ is not equal to expected 1\.0e-7$")]
    elif role == "B" and case_id == "M27310_2_d308":
        allow = [re.compile(r"^Error: TolReached = [-+0-9.eE]+ is not equal to expected 6\.9230965382090094e-006$")]
    elif role == "B" and case_id == "M27773":
        allow = [re.compile(r'^Error\s*:\s*is WRONG because number of VERTEX entities in shape "result" is 0$')]
    for line in text.splitlines():
        if expected_empty_curve_error and line == 'BF_SOURCE_ERROR=can\'t read "NbCurv": no such variable':
            continue
        if fatal.search(line):
            raise ValueError(f"Draw/Tcl runtime diagnostic: {line[:200]}")
        if re.match(r"^\s*Error\s*:", line, re.I) and not any(pattern.match(line.strip()) for pattern in allow):
            raise ValueError(f"unrecognized Error diagnostic: {line[:200]}")


def _official_log(text: str) -> str:
    match = re.search(r"^BF_OFFICIAL_BOP_LOG_BEGIN\n(.*?)\nBF_OFFICIAL_BOP_LOG_END$", text, re.M | re.S)
    return match.group(1) if match else ""


def _variable(text: str, name: str) -> str | None:
    match = re.search(rf"^BF_VAR_{re.escape(name)}=(.*)$", text, re.M)
    return match.group(1).strip() if match else None


def _result(case_id: str, role: str, passed: bool, detail: dict) -> dict:
    return {"status": "geometry_pass" if passed else "geometry_fail",
            "checks": [{"id": "geometry_predicate", "passed": bool(passed)}], "detail": detail}


def _verify_original(case_id: str, role: str, text: str) -> dict:
    if case_id in {"M27310_1", "M27310_2_d308"}:
        expected_tol = 1e-7 if case_id == "M27310_1" else 6.9230965382090094e-6
        curves_raw = _variable(text, "NbCurv")
        tol_raw = _variable(text, "Toler")
        if curves_raw is None or tol_raw is None:
            raise ValueError("official M27310 variables were not produced")
        curves, tolerance = int(curves_raw), float(tol_raw)
        passed = curves == 2 and abs(tolerance - expected_tol) <= 0.1 * expected_tol
        return _result(case_id, role, passed, {"official_test": case_id, "observed_curve_count": curves,
            "observed_tolerance": tolerance, "expected_curve_count": 2,
            "expected_tolerance": expected_tol, "official_relative_tolerance": 0.1,
            "display_adapter": "pure_display_noop_v1"})
    if case_id == "M27773":
        coords = parse_vertices(text)
        if role == "B":
            if coords or 'number of VERTEX entities in shape "result" is 0' not in text:
                raise ValueError("M27773 B has neither the reviewed zero-vertex geometry result nor valid roots")
            return _result(case_id, role, False, {"observed_vertices": 0, "expected_vertices": 2,
                "official_predicate": "checknbshapes result -vertex 2"})
        # Official Tcl offsets the circle of radius 20 by 10, so the
        # checked section has radius 30 around x=1.
        expected_y = math.sqrt(30.0**2 - 1.0)
        expected = [(0.0, expected_y, 0.0), (0.0, -expected_y, 0.0)]
        if len(coords) != 2:
            raise ValueError("M27773 F did not produce exactly two vertices")
        error = min(max(dist(coords[0], expected[0]), dist(coords[1], expected[1])),
                    max(dist(coords[0], expected[1]), dist(coords[1], expected[0])))
        passed = error <= 1e-6 and "OK :  is GOOD because number of VERTEX entities" in text
        return _result(case_id, role, passed, {"observed_vertices": len(coords), "analytic_root_error": error,
                                               "expected_vertices": 2})
    if case_id == "M27252":
        log = _official_log(text)
        if role == "B":
            exact_empty = "has no 3d curves" in log and "has no 3d points" in log
            if not exact_empty:
                raise ValueError("M27252 B no-curve adapter did not find exact official BOP output")
            return _result(case_id, role, False, {"observed_curve_count": 0, "expected_curve_count": 1,
                "adapter": "m27252-empty-bopcurves-v1", "tolerance_status": "not_evaluated_no_3d_curves",
                "official_bop_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
                "tcl_source_return_code": 1})
        tolerance_match = re.search(r"Tolerance Reached=([-+0-9.eE]+)", log)
        curve_match = re.search(r"(\d+) curve\(s\) found", log)
        if not tolerance_match or not curve_match:
            raise ValueError("M27252 F official BOP log lacks curve/tolerance output")
        tolerance, curves = float(tolerance_match.group(1)), int(curve_match.group(1))
        passed = curves == 1 and tolerance <= 1e-7
        return _result(case_id, role, passed, {"observed_curve_count": curves,
            "observed_tolerance": tolerance, "expected_curve_count": 1, "maximum_tolerance": 1e-7,
            "display_adapter": "pure_display_noop_v1"})
    raise ValueError(f"unknown original case: {case_id}")


def _verify_hidden(case_id: str, role: str, text: str) -> dict:
    if case_id == "M27773_neighbor_offset_line" or case_id == "M27773_regression_circle_line":
        coords = parse_vertices(text)
        if len(coords) != 2:
            raise ValueError("M27773 hidden section did not yield two vertices")
        if case_id == "M27773_neighbor_offset_line":
            expected_y = math.sqrt(30.0**2 - (0.5 - 1.0)**2)
            expected, tolerance = [(0.5, expected_y, 0.0), (0.5, -expected_y, 0.0)], 1e-6
            offset = re.search(r"^BF_OFFSET_CVALUE0=([^,]+),([^,]+),([^\s]+)$", text, re.M)
            if not offset or tuple(float(offset.group(i)) for i in (1, 2, 3)) != (31.0, 0.0, 0.0):
                raise ValueError("offset curve identity does not match input definition")
        else:
            expected_y = math.sqrt(20.0**2 - 1.0)
            expected, tolerance = [(0.0, expected_y, 0.0), (0.0, -expected_y, 0.0)], 1e-6
        error = min(max(dist(coords[0], expected[0]), dist(coords[1], expected[1])),
                    max(dist(coords[0], expected[1]), dist(coords[1], expected[0])))
        return _result(case_id, role, error <= tolerance, {"observed_vertices": 2,
            "analytic_root_error": error, "expected_vertices": 2})

    if case_id in {"M27252_neighbor_translated_plane", "M27252_regression_cylinder_plane"}:
        curves = parse_samples(text, case_id)
        if set(curves) != {1}:
            raise ValueError("M27252 hidden oracle requires exactly one sampled curve")
        points = curves[1]
        if case_id == "M27252_neighbor_translated_plane":
            cx, cy, radius = -7.49999999999998, -7.49999999999996, 4.99999999999999
            nx, ny, nz = 0.0, -0.873177869039721, 0.487401691645866
            px, py, pz = 12.5, 12.5, 44.887384
            endpoints = ((-12.5, -7.5, 9.0574768), (-7.5, -12.5, 0.1))
            endpoint_tol, residual_tol = 3e-5, 2e-5
            radial = [abs(math.hypot(x-cx, y-cy)-radius) for x, y, z in points]
            plane = [abs(nx*(x-px)+ny*(y-py)+nz*(z-pz)) for x, y, z in points]
            gap = dist(points[0], points[-1])
            end_err = min(max(dist(points[0], endpoints[0]), dist(points[-1], endpoints[1])),
                          max(dist(points[0], endpoints[1]), dist(points[-1], endpoints[0])))
            wrong = [abs(nx*(x-px)+ny*(y-py)+nz*(z-(pz+0.2))) for x, y, z in points]
            passed = (end_err <= endpoint_tol and gap > 1 and max(radial) <= residual_tol and
                      max(plane) <= residual_tol and min(wrong) > 0.09)
            return _result(case_id, role, passed, {"curve_count": 1, "sample_count": len(points),
                "max_cylinder_radial_residual": max(radial), "max_plane_residual": max(plane),
                "endpoint_error": end_err, "wrong_plane_offset_min_residual": min(wrong)})
        gap = dist(points[0], points[-1])
        radial = [abs(math.hypot(x, y)-5.0) for x, y, z in points]
        plane = [abs(z) for x, y, z in points]
        wrong = [abs(math.hypot(x, y)-4.5) for x, y, z in points]
        passed = gap <= 1e-5 and max(radial) <= 1e-5 and max(plane) <= 1e-5 and min(wrong) > 0.49
        return _result(case_id, role, passed, {"curve_count": 1, "sample_count": len(points),
            "endpoint_gap": gap, "max_cylinder_radial_residual": max(radial),
            "max_plane_residual": max(plane), "wrong_radius_min_residual": min(wrong)})

    if case_id == "M27310_neighbor_finite_face":
        curves = parse_samples(text, case_id)
        if set(curves) != {1}:
            raise ValueError("finite-face neighborhood must produce exactly one curve")
        points = curves[1]
        cx, cy, z0 = -33.75046920776, 13.0, 38.50001144409
        rsmall, rlarge, umax = 2.0, 15.0000004768372, 1.04719822459855
        ends = []
        for u in (0.0, umax):
            x, y = cx+rsmall*math.sin(u), cy+rsmall*math.cos(u)
            z = z0-math.sqrt(rlarge*rlarge-(y-0.5)**2)
            ends.append((x, y, z))
        end_error = min(max(dist(points[0], ends[0]), dist(points[-1], ends[1])),
                        max(dist(points[0], ends[1]), dist(points[-1], ends[0])))
        small = [abs(math.hypot(x-cx,y-cy)-rsmall) for x,y,z in points]
        large = [abs(math.hypot(y-0.5,z-z0)-rlarge) for x,y,z in points]
        passed = end_error <= 0.01 and max(small) <= 0.01 and max(large) <= 0.01 and all(z <= z0+0.01 for x,y,z in points)
        return _result(case_id, role, passed, {"curve_count": 1, "sample_count": len(points),
            "endpoint_error": end_error, "max_small_cylinder_residual": max(small),
            "max_large_cylinder_residual": max(large), "branch": "lower_z"})

    if case_id == "M27310_regression_two_loops":
        module_path = Path(__file__).resolve().parent / "verify_m27310_endpoint_graph.py"
        spec = importlib.util.spec_from_file_location("m27310_endpoint_graph", module_path)
        if spec is None or spec.loader is None:
            raise ValueError("locked physical endpoint-graph verifier is missing")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        curves = module.parse_samples(text, role, case_id)
        geometry = module.verify_geometry(curves)
        return _result(case_id, role, True, {"physical_oracle": geometry,
            "curve_piece_count_is_metadata_only": True})
    raise ValueError(f"unknown hidden case: {case_id}")


def validate_draw_text(case_id: str, role: str, text: str) -> dict:
    """Validate process markers and case geometry on this invocation's raw log."""
    _common_draw_checks(text, case_id, role)
    if case_id in {"M27310_1", "M27310_2_d308", "M27773", "M27252"}:
        return _verify_original(case_id, role, text)
    return _verify_hidden(case_id, role, text)

