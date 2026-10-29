#!/usr/bin/env python3
"""Run one bounded DRAW case and return a machine-readable oracle result."""
from __future__ import annotations

import argparse
import json
import os
import re
import resource
import signal
import subprocess
import sys
import hashlib
import tempfile
import time
from pathlib import Path


SUMMARY_RE = re.compile(r"^BENCH_ORACLE_OK assertions=(\d+) numeric_assertions=(\d+)\s*$", re.M)
DONE_RE = re.compile(r"^TEST_DONE assertions=(\d+) numeric_assertions=(\d+)\s*$", re.M)
OCCT_ERROR_RE = re.compile(r"^\s*(?:Error\b|An exception was caught\b|\*\* Exception\b)", re.M | re.I)


def limit_child(cpu_seconds: int, address_space_bytes: int) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 2))
    resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))


def tail(handle, limit: int = 32768) -> str:
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    handle.seek(max(0, size - limit))
    return handle.read(limit).decode("utf-8", errors="replace")


def scan_failures(handle) -> bool:
    """Inspect the whole bounded log, including diagnostics preceding its tail."""
    handle.seek(0)
    for raw_line in handle:
        line = raw_line.decode("utf-8", errors="replace")
        if (OCCT_ERROR_RE.search(line) or "BENCH_TCL_ERROR:" in line
                or "BENCH_ORACLE_FAILED" in line or line.startswith("BENCH_ASSERT_FAIL")):
            return True
    return False


def diagnostic_lines(*handles) -> list[str]:
    """Preserve full-log OCCT diagnostics for failure attribution."""
    found=[]
    for handle in handles:
        handle.seek(0)
        for raw in handle:
            line=raw.decode('utf-8',errors='replace').strip()
            if OCCT_ERROR_RE.search(line): found.append(line)
    return found


def resolve_resource_dirs(resource_arg: Path) -> tuple[Path, Path]:
    """Return (OCCT resource root, DrawResources plugin directory)."""
    candidate = resource_arg.expanduser().resolve()
    roots: list[Path] = []
    if candidate.is_dir():
        roots.append(candidate)
        if candidate.name == "DrawResources":
            roots.insert(0, candidate)
    else:
        source_root = candidate.parent if candidate.name in {"resources", "DrawResources"} else candidate
        roots.extend((source_root / "resources", source_root / "src" / "DrawResources"))

    seen: set[Path] = set()
    for root in roots:
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)
        if root.name == "DrawResources":
            if root.is_dir():
                return root, root
        plugin_dir = root / "DrawResources"
        if plugin_dir.is_dir():
            return root, plugin_dir.resolve()
    raise FileNotFoundError(
        f"DRAW resources not found from {candidate}; expected source/resources or source/src/DrawResources"
    )


def find_draw(build_dir: Path, toolchain_name: str) -> tuple[Path, Path]:
    pairs = (
        (build_dir / "lin64" / toolchain_name / "bin", build_dir / "lin64" / toolchain_name / "lib"),
        (build_dir / "lin64" / "clang" / "bin", build_dir / "lin64" / "clang" / "lib"),
        (build_dir / "lin64" / "gcc" / "bin", build_dir / "lin64" / "gcc" / "lib"),
        (build_dir / "ADDITIONAL" / "lin64" / toolchain_name / "bin",
         build_dir / "ADDITIONAL" / "lin64" / toolchain_name / "lib"),
        (build_dir / "ADDITIONAL" / "lin64" / "clang" / "bin",
         build_dir / "ADDITIONAL" / "lin64" / "clang" / "lib"),
        (build_dir / "out" / "bin", build_dir / "out" / "lib"),
        (build_dir / "bin", build_dir / "lib"),
    )
    for binary_dir, library_dir in pairs:
        # OCCT 8.x versions the executable (for example DRAWEXE-8.0.0).
        binaries = [binary_dir / "DRAWEXE", *sorted(binary_dir.glob("DRAWEXE-*"))]
        binary = next((item for item in binaries if item.is_file()), None)
        if binary is not None and library_dir.is_dir():
            return binary.resolve(), library_dir.resolve()
    expected = [str(binary_dir / "DRAWEXE[-*]") for binary_dir, _ in pairs]
    raise FileNotFoundError("DRAWEXE or matching library directory not found; checked " + ", ".join(expected))


def tcl_quote(value: str) -> str:
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("case script path contains an unsupported control character")
    escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
               .replace("$", "\\$").replace("[", "\\[").replace("]", "\\]"))
    return '"' + escaped + '"'


def resolve_tcl_init() -> Path | None:
    """Locate the deployment's real Tcl standard library; never emulate it."""
    candidates=[]
    explicit=os.environ.get('BENCH_TCL_INIT')
    if explicit: candidates.append(Path(explicit))
    for key,suffix in (('BENCH_TCL_LIBRARY_DIR','tcl8.6/init.tcl'),
                       ('BENCH_TCL_DIR','lib/tcl8.6/init.tcl'),
                       ('TCL_LIBRARY','init.tcl')):
        if os.environ.get(key): candidates.append(Path(os.environ[key])/suffix)
    candidates.extend((Path(sys.prefix)/'lib/tcl8.6/init.tcl',
                       Path(sys.prefix).parent.parent/'lib/tcl8.6/init.tcl'))
    return next((p.resolve() for p in candidates if p.is_file()),None)


def tcl_bootstrap(tcl_init: Path | None) -> str:
    # Tcl_CreateInterp alone lacks the script-defined math functions used by
    # ordinary Tcl 8.6 expressions. Only initialize interpreters missing them.
    body=("error {Tcl standard library is unavailable; configure BENCH_TCL_LIBRARY_DIR}" if tcl_init is None else
          "set ::tcl_library " + tcl_quote(str(tcl_init.parent)) + "\nsource " + tcl_quote(str(tcl_init)))
    return ("if {![llength [info commands ::tcl::mathfunc::max]] || "
            "![llength [info commands ::tcl::mathfunc::min]]} {\n"+body+"\n}\n")


def write_wrapper(script: Path, wrapper: Path, tcl_init: Path | None = None) -> None:
    quoted = tcl_quote(str(script))
    wrapper.write_text(
        "set ::bench_runner_script " + quoted + "\n"
        "set ::bench_runner_code [catch {\n" + tcl_bootstrap(tcl_init) + "source $::bench_runner_script\n} "
        "::bench_runner_message ::bench_runner_options]\n"
        "if {$::bench_runner_code != 0} {\n"
        "  puts stderr \"BENCH_TCL_ERROR: $::bench_runner_message\"\n"
        "  if {[dict exists $::bench_runner_options -errorinfo]} {\n"
        "    puts stderr [dict get $::bench_runner_options -errorinfo]\n"
        "  }\n"
        "  exit 1\n"
        "}\n",
        encoding="utf-8",
    )


def evaluate_output(return_code, timed_out: bool, stdout: str, stderr: str) -> dict:
    joined = stdout + "\n" + stderr
    summary_matches = list(SUMMARY_RE.finditer(joined))
    done_matches = list(DONE_RE.finditer(joined))
    summary = summary_matches[-1] if summary_matches else None
    done = done_matches[-1] if done_matches else None
    tcl_error = "BENCH_TCL_ERROR:" in joined or "BENCH_ORACLE_FAILED" in joined
    # OCCT's CheckCommands procedures commonly print a failure and return
    # normally. A Tcl catch alone therefore cannot establish a passing oracle.
    diagnostic_error = bool(OCCT_ERROR_RE.search(joined))
    failed_assertions = len(re.findall(r"^BENCH_ASSERT_FAIL\b", joined, re.M))
    expected_oracle_error = bool(
        failed_assertions > 0 and "BENCH_ORACLE_FAILED" in joined
        and re.search(r"^BENCH_TCL_ERROR: one or more benchmark assertions failed\s*$", joined, re.M)
    )
    assertion_events = re.findall(r"^BENCH_ASSERT_(?:PASS|FAIL)\b.*?\bkind=(expression|numeric)\b", joined, re.M)
    assertions = int(summary.group(1)) if summary else len(assertion_events)
    numeric_assertions = int(summary.group(2)) if summary else sum(kind == "numeric" for kind in assertion_events)
    observed_numeric = sum(kind == "numeric" for kind in assertion_events)
    valid_oracle = bool(
        summary and done
        and summary.groups() == done.groups()
        and assertions > 0
        and 0 <= numeric_assertions <= assertions
        and len(assertion_events) == assertions
        and observed_numeric == numeric_assertions
        and failed_assertions == 0
    )
    passed = bool(return_code == 0 and not timed_out and not tcl_error and not diagnostic_error and valid_oracle)
    return {
        "protocol": "draw_case_oracle_v1", "oracle_scope": "public_script_only",
        "return_code": return_code,
        "timed_out": timed_out,
        "test_done_marker": passed,
        "passed": passed,
        "assertions": assertions,
        "numeric_assertions": numeric_assertions,
        "failed_assertions": failed_assertions,
        "tcl_error_detected": tcl_error,
        "expected_oracle_error": expected_oracle_error,
        "infrastructure_tcl_error": tcl_error and not expected_oracle_error,
        "occt_error_detected": diagnostic_error,
        "oracle_summary_found": bool(summary),
        "stdout_tail": stdout[-24000:],
        "stderr_tail": stderr[-12000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--script", default="reproduce.tcl")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--cpu-limit-seconds", type=int, default=25)
    parser.add_argument("--address-space-gib", type=int, default=4)
    args = parser.parse_args()

    result: dict = {"protocol": "draw_case_oracle_v1", "oracle_scope": "public_script_only", "passed": False, "test_done_marker": False}
    try:
        if not 1 <= args.timeout_seconds <= 3600:
            raise ValueError("timeout-seconds must be between 1 and 3600")
        if not 1 <= args.cpu_limit_seconds <= 3600:
            raise ValueError("cpu-limit-seconds must be between 1 and 3600")
        if not 1 <= args.address_space_gib <= 32:
            raise ValueError("address-space-gib must be between 1 and 32")

        build_dir = args.build_dir.expanduser().resolve(strict=True)
        case_dir = args.case_dir.expanduser().resolve(strict=True)
        if not case_dir.is_dir():
            raise ValueError("case-dir must be a directory")
        script = (case_dir / args.script).resolve(strict=True)
        if not script.is_file() or not script.is_relative_to(case_dir):
            raise ValueError("script must be a file contained in case-dir")
        resources, draw_resources = resolve_resource_dirs(args.resource_dir)
        toolchain_name = os.environ.get("BENCH_TOOLCHAIN_NAME", "clang")
        binary, library_dir = find_draw(build_dir, toolchain_name)

        env = os.environ.copy()
        extra_library_path = env.get("BENCH_EXTRA_LIBRARY_PATH", "")
        env.update({
            "CASROOT": str(resources.parent),
            "DRAWDEFAULT": str(draw_resources / "DrawDefault"),
            "CSF_OCCTResourcePath": str(resources),
            "CSF_OCCTLibPath": str(library_dir),
            "CSF_OCCTBinPath": str(binary.parent),
            "CSF_DrawPluginDefaults": str(draw_resources),
            "DRAWHOME": str(draw_resources),
            "CSF_TestDataPath": str(case_dir),
            "CSF_LANGUAGE": "us",
            "MMGT_CLEAR": "1",
            "LD_LIBRARY_PATH": os.pathsep.join(
                path for path in (str(library_dir), extra_library_path, env.get("LD_LIBRARY_PATH", "")) if path
            ),
        })

        with tempfile.TemporaryDirectory(prefix="occt-draw-case-") as temporary:
            wrapper = Path(temporary) / "run_case.tcl"
            tcl_init = resolve_tcl_init()
            write_wrapper(script, wrapper, tcl_init)
            result["tcl_standard_library"] = {"init_script":str(tcl_init) if tcl_init else None,
                "sha256":hashlib.sha256(tcl_init.read_bytes()).hexdigest() if tcl_init else None}
            with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
                started = time.monotonic()
                proc = subprocess.Popen(
                    [str(binary), "-b", "-f", str(wrapper)],
                    cwd=case_dir,
                    env=env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True,
                    preexec_fn=lambda: limit_child(
                        args.cpu_limit_seconds,
                        args.address_space_gib * 1024**3,
                    ),
                )
                timed_out = False
                try:
                    return_code = proc.wait(timeout=args.timeout_seconds)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(proc.pid, signal.SIGKILL)
                    return_code = proc.wait()
                elapsed = round(time.monotonic() - started, 3)
                full_log_failed = scan_failures(stdout_file) or scan_failures(stderr_file)
                errors = diagnostic_lines(stdout_file, stderr_file)
                stdout = tail(stdout_file)
                stderr = tail(stderr_file)
            result.update(evaluate_output(return_code, timed_out, stdout, stderr))
            result["diagnostic_lines"] = errors
            if full_log_failed:
                result.update(passed=False, test_done_marker=False, full_log_failure_detected=True)
            result.update({
                "script": str(script),
                "draw_executable": str(binary),
                "elapsed_seconds": elapsed,
            })
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
        result["tcl_error_detected"] = False

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
