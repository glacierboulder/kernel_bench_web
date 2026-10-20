#!/usr/bin/env python3
"""Build and run one isolated OCCT prototype evaluator."""
import argparse
import fnmatch
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("BENCH_EVALUATION_SOURCE", str(ROOT / "private" / "common_base_source")))
TOOLCHAIN_NAME = os.environ.get("BENCH_TOOLCHAIN_NAME", "clang")


def conda(*args):
    # This runner already runs inside the configured evaluation environment.
    values=list(map(str,args))
    if values and values[0]=="cmake":
        values[0]=os.environ.get("BENCH_CMAKE","cmake")
    return values


def run(command, cwd, timeout, input_data=None):
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=input_data is None,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    return {
        "command": [str(part) for part in command],
        "return_code": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output_tail": output[-12000:],
    }


def apply_patch(source, patch_arg):
    if patch_arg == "-":
        patch_data = sys.stdin.buffer.read()
    else:
        patch_path = Path(patch_arg).expanduser().resolve()
        if not patch_path.is_file():
            raise ValueError(f"patch file does not exist: {patch_path}")
        if patch_path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("patch exceeds 20 MiB prototype limit")
        patch_data = patch_path.read_bytes()
    if not patch_data:
        raise ValueError("empty patch")

    check = run(["git", "apply", "--check", "--whitespace=nowarn", "-"], source, 60, patch_data)
    if check["return_code"] != 0:
        raise ValueError("patch check failed: " + check["output_tail"][-3000:])
    applied = run(["git", "apply", "--whitespace=nowarn", "-"], source, 60, patch_data)
    if applied["return_code"] != 0:
        raise ValueError("patch apply failed: " + applied["output_tail"][-3000:])
    return len(patch_data)


def configure_and_build(source, build):
    c_compiler = os.environ.get("BENCH_CC", "clang-10")
    cxx_compiler = os.environ.get("BENCH_CXX", "clang++-10")
    try:
        compiler_jobs = min(2, max(1, int(os.environ.get("BENCH_COMPILER_JOBS", "2"))))
    except ValueError as exc:
        raise ValueError("BENCH_COMPILER_JOBS must be 1 or 2") from exc
    args = [
        "cmake", "-S", str(source), "-B", str(build),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_C_FLAGS_RELEASE=-O1 -DNDEBUG",
        "-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG",
        f"-DCMAKE_C_COMPILER={c_compiler}",
        f"-DCMAKE_CXX_COMPILER={cxx_compiler}",
        "-DBUILD_LIBRARY_TYPE=Shared",
        "-DBUILD_ADDITIONAL_TOOLKITS=TKTopTest;DRAWEXE",
        "-DBUILD_MODULE_ApplicationFramework=OFF",
        "-DBUILD_MODULE_DataExchange=OFF",
        "-DBUILD_MODULE_Draw=OFF",
        "-DBUILD_MODULE_FoundationClasses=OFF",
        "-DBUILD_MODULE_ModelingAlgorithms=OFF",
        "-DBUILD_MODULE_ModelingData=OFF",
        "-DBUILD_MODULE_Visualization=OFF",
        "-DUSE_FREETYPE=OFF", "-DUSE_TK=OFF",
    ]
    for variable, environment in (("3RDPARTY_TCL_DIR","BENCH_TCL_DIR"),
                                  ("3RDPARTY_TCL_INCLUDE_DIR","BENCH_TCL_INCLUDE_DIR"),
                                  ("3RDPARTY_TCL_LIBRARY","BENCH_TCL_LIBRARY"),
                                  ("3RDPARTY_TCL_LIBRARY_DIR","BENCH_TCL_LIBRARY_DIR")):
        value=os.environ.get(environment)
        if value:
            args.append(f"-D{variable}={value}")
    configured = run(conda(*args), ROOT, 2400)
    if configured["return_code"] != 0:
        return {"configure": configured, "build": None}
    built = run(conda("cmake", "--build", str(build), "--target", "DRAWEXE", "TKTopTest", "--parallel", str(compiler_jobs)), ROOT, 3600)
    return {"configure": configured, "build": built}


def run_draw_issue(source, build, task_folder, issue_folder, result, test_name):
    case = ROOT / "tasks" / task_folder / "visible" / issue_folder
    runner = ROOT / "scripts" / "run_draw_case.py"
    draw = run(conda("python", str(runner), "--build-dir", str(build), "--resource-dir", str(source / "resources"), "--case-dir", str(case), "--timeout-seconds", "18", "--cpu-limit-seconds", "15"), ROOT, 30)
    detail = draw["output_tail"]
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        payload = None
    passed = bool(payload and payload.get("return_code") == 0 and payload.get("test_done_marker") and not payload.get("timed_out"))
    result.append({"test": test_name, "passed": passed, "result": payload or detail})


def run_issue_544(source, build, result, task_folder="task_single"):
    run_draw_issue(source, build, task_folder, "issue_544", result, "visible_issue_544")


def run_issue_506(source, build, result, task_folder="task_group", visible=False):
    compiler_lib = build / "lin64" / TOOLCHAIN_NAME / "lib"
    binary = build / "lin64" / TOOLCHAIN_NAME / "bin" / "DRAWEXE"
    if visible:
        harness = ROOT / "tasks" / task_folder / "visible" / "issue_506" / "reproduce.cpp"
        inputs = ROOT / "tasks" / task_folder / "visible" / "issue_506"
    else:
        harness = ROOT / "private" / "evaluator_tests" / "issue_506_bndsort_repro.cpp"
        inputs = ROOT / "private" / "evaluator_assets" / "issue_506"
    work = build / "evaluator"
    work.mkdir(parents=True, exist_ok=True)
    executable = work / "issue_506_bndsort_repro"
    compile_args = conda(
        os.environ.get("BENCH_CXX", "clang++-10"), "-std=c++17",
        "-I", str(build / "include" / "opencascade"),
        "-L", str(compiler_lib), f"-Wl,-rpath,{compiler_lib}",
        str(harness), "-lTKTopAlgo", "-lTKBRep", "-lTKMath", "-lTKernel", "-lTKG3d", "-lTKGeomBase",
        "-o", str(executable),
    )
    compiled = run(compile_args, ROOT, 120)
    if compiled["return_code"] != 0:
        result.append({"test": "visible_issue_506_compile" if visible else "hidden_issue_506_compile", "passed": False, "result": compiled})
        return

    cases = (("visible_issue_506_hole0", "hole0.brep"), ("visible_issue_506_hole1", "hole1.brep")) if visible else (("positive_control_hole0", "hole0.brep"), ("hidden_issue_506_hole1", "hole1.brep"))
    for case_name, hole_name in cases:
        command = conda(str(executable), str(inputs / "brd.brep"), str(inputs / hole_name))

        def limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_CPU, (10, 12))
            resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

        try:
            tested = subprocess.run(command, cwd=inputs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15, preexec_fn=limits, check=False)
            output = tested.stdout[-5000:]
            passed = tested.returncode == 0 and "indices.Size(): 1" in output and "Index 0" in output
            detail = {"return_code": tested.returncode, "output_tail": output}
        except subprocess.TimeoutExpired as exc:
            passed = False
            detail = {"timed_out": True, "output_tail": str(exc.stdout or "")[-5000:]}
        result.append({"test": case_name, "passed": passed, "result": detail})


def run_issue_847(source, build, result):
    run_draw_issue(source, build, "task_group_visible3", "issue_847", result, "visible_issue_847")


def run_cpp_visible(source, build, task_folder, issue_folder, result, test_name, libraries,
                    arguments=(), timeout=18):
    """Compile and run a public C++ reproducer shipped with a visible task."""
    compiler_lib = build / "lin64" / TOOLCHAIN_NAME / "lib"
    harness = ROOT / "tasks" / task_folder / "visible" / issue_folder / "reproduce.cpp"
    inputs = harness.parent
    work = build / "evaluator"
    work.mkdir(parents=True, exist_ok=True)
    executable = work / (issue_folder + "_repro")
    compile_args = conda(
        os.environ.get("BENCH_CXX", "clang++-10"), "-std=c++17",
        "-I", str(build / "include" / "opencascade"),
        "-L", str(compiler_lib), f"-Wl,-rpath,{compiler_lib}",
        str(harness), *libraries, "-o", str(executable),
    )
    compiled = run(compile_args, ROOT, 120)
    if compiled["return_code"] != 0:
        result.append({"test": test_name + "_compile", "passed": False, "result": compiled})
        return

    def limits_for_case():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 14))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    command = [str(executable), *(str(inputs / argument) for argument in arguments)]
    try:
        tested = subprocess.run(command, cwd=inputs, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=timeout,
                                preexec_fn=limits_for_case, check=False)
        detail = {"return_code": tested.returncode, "output_tail": tested.stdout[-8000:]}
        passed = tested.returncode == 0 and "TEST_DONE" in tested.stdout
    except subprocess.TimeoutExpired as exc:
        detail = {"timed_out": True, "output_tail": str(exc.stdout or "")[-8000:]}
        passed = False
    result.append({"test": test_name, "passed": passed, "result": detail})


def run_issue_690_693_172(source, build, result, task_folder="task_group_visible4"):
    for issue in ("issue_690", "issue_693", "issue_172"):
        run_draw_issue(source, build, task_folder, issue, result, "visible_" + issue)


def run_issue_370_1452(source, build, result, task_folder="task_group_visible5"):
    run_cpp_visible(source, build, task_folder, "issue_370", result, "visible_issue_370",
                    ["-lTKGeomAlgo", "-lTKShHealing", "-lTKTopAlgo", "-lTKBRep",
                     "-lTKGeomBase", "-lTKG3d", "-lTKMath", "-lTKernel"], timeout=18)
    run_cpp_visible(source, build, task_folder, "issue_1452", result, "visible_issue_1452",
                    ["-lTKOffset", "-lTKTopAlgo", "-lTKBRep", "-lTKGeomBase", "-lTKG3d",
                     "-lTKG2d", "-lTKMath", "-lTKernel"])


def run_issue_370_872_1452(source, build, result, task_folder="task_group_visible5"):
    run_cpp_visible(source, build, task_folder, "issue_370", result, "visible_issue_370",
                    ["-lTKGeomAlgo", "-lTKShHealing", "-lTKTopAlgo", "-lTKBRep",
                     "-lTKGeomBase", "-lTKG3d", "-lTKMath", "-lTKernel"], timeout=18)
    run_cpp_visible(source, build, task_folder, "issue_872", result, "visible_issue_872",
                    ["-lTKTopAlgo", "-lTKBRep", "-lTKGeomBase", "-lTKG3d", "-lTKMath",
                     "-lTKernel"], arguments=("stretchError.brep",))
    run_cpp_visible(source, build, task_folder, "issue_1452", result, "visible_issue_1452",
                    ["-lTKOffset", "-lTKTopAlgo", "-lTKBRep", "-lTKGeomBase", "-lTKG3d",
                     "-lTKG2d", "-lTKMath", "-lTKernel"])


def validate_findings(findings_arg):
    if not findings_arg:
        return {"status": "not_provided", "valid_count": 0}
    path = Path(findings_arg).expanduser().resolve()
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return {"status": "invalid", "error": "findings file missing or larger than 2 MiB", "valid_count": 0}
    records = []
    root = path.parent.resolve()
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or not all(isinstance(record.get(key), str) and record[key].strip() for key in ("input", "repro", "observation")):
                raise ValueError(f"line {line_number}: expected nonempty input, repro, observation strings")
            for key in ("input", "repro"):
                target = (root / record[key]).resolve()
                if root not in target.parents or not target.is_file():
                    raise ValueError(f"line {line_number}: {key} must name an existing file inside {root}")
            records.append(record)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "invalid", "error": str(exc), "valid_count": len(records)}
    return {"status": "valid", "valid_count": len(records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("single", "group", "active", "visible3", "visible4", "visible5", "visible5all"), required=True)
    parser.add_argument("--patch", required=True, help="unified diff path, or - to read stdin")
    parser.add_argument("--report", required=True)
    parser.add_argument("--findings")
    parser.add_argument("--allow-missing-report", action="store_true")
    parser.add_argument("--allow-empty-findings", action="store_true")
    args = parser.parse_args()
    if args.task == "active" and not args.findings:
        raise SystemExit("task_active requires --findings FINDINGS_JSONL")

    started = time.monotonic()
    output = {"task": args.task, "tests": [], "limitations": ["This prototype does not run the complete upstream test suite.", "Issue 506 uses a small reproducer, not the upstream Google Test target."]}
    if args.task in ("visible3", "visible4", "visible5", "visible5all"):
        output["hidden_tests"] = False
    report = Path(args.report).expanduser().resolve()
    output["report"] = {"provided": report.is_file() and report.stat().st_size > 0, "path": str(report)}
    if not output["report"]["provided"] and not args.allow_missing_report:
        output["report"]["error"] = "report file missing or empty"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1
    if args.task == "active":
        output["findings"] = validate_findings(args.findings)
        if output["findings"]["status"] != "valid" or (output["findings"]["valid_count"] == 0 and not args.allow_empty_findings):
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1

    if not SOURCE.is_dir():
        raise SystemExit(f"private baseline source missing: {SOURCE}")
    with tempfile.TemporaryDirectory(prefix="occt-bench-eval-") as temporary:
        work = Path(temporary)
        source = work / "source"
        shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns(".git", "tests", "__pycache__"))
        try:
            output["patch_bytes"] = apply_patch(source, args.patch)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            output["patch_error"] = str(exc)
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 2

        build = work / "build"
        build_result = configure_and_build(source, build)
        output["build"] = build_result
        if not build_result.get("build") or build_result["build"]["return_code"] != 0:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
        if args.task in ("single", "group", "active"):
            run_issue_544(source, build, output["tests"], "task_single")
        elif args.task == "visible3":
            run_issue_544(source, build, output["tests"], "task_group_visible3")
        if args.task in ("group", "active"):
            run_issue_506(source, build, output["tests"])
        if args.task == "visible3":
            run_issue_506(source, build, output["tests"], "task_group_visible3", visible=True)
            run_issue_847(source, build, output["tests"])
        if args.task == "visible4":
            run_issue_690_693_172(source, build, output["tests"])
        if args.task == "visible5":
            run_issue_370_872_1452(source, build, output["tests"])
        if args.task == "visible5all":
            run_issue_690_693_172(source, build, output["tests"], "task_group_visible5all")
            run_issue_370_1452(source, build, output["tests"], "task_group_visible5all")

    output["elapsed_seconds"] = round(time.monotonic() - started, 3)
    output["passed"] = all(test["passed"] for test in output["tests"])
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
