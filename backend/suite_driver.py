"""Run a frozen versioned suite using registered, data-only runner contracts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import subprocess
import sys
import tempfile
import time


def _resolve(root: Path, value: str) -> Path:
    rel=PurePosixPath(value)
    if not value or rel.is_absolute() or "\\" in value or any(x in {"", ".", ".."} for x in rel.parts):
        raise ValueError("unsafe case material path")
    target=root.joinpath(*rel.parts).resolve(strict=True)
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError("case material is missing or escapes the frozen case root")
    return target


def _limits(cpu: int, memory_gib: int):
    def apply():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+2))
        resource.setrlimit(resource.RLIMIT_AS,(memory_gib*1024**3,memory_gib*1024**3))
    return apply


def _run(argv: list[str], *, cwd: Path, timeout: int, cpu: int, memory_gib: int, env=None, output_limit=12000) -> dict:
    started=time.monotonic()
    try:
        proc=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            text=True,timeout=timeout,check=False,env=env,
                            preexec_fn=_limits(cpu,memory_gib))
        output=proc.stdout[-output_limit:]
        return {"return_code":proc.returncode,"elapsed_seconds":round(time.monotonic()-started,3),
                "output_tail":output,"timed_out":False}
    except subprocess.TimeoutExpired as exc:
        value=exc.stdout or ""
        if isinstance(value,bytes): value=value.decode("utf-8",errors="replace")
        return {"return_code":None,"elapsed_seconds":round(time.monotonic()-started,3),
                "output_tail":str(value)[-12000:],"timed_out":True}


def _execute(checkpoint: dict, *, case_root: Path, build: Path, source: Path,
             work: Path, draw_runner: Path) -> dict:
    runner=checkpoint["runner"]
    options=checkpoint.get("runner_options",{})
    case=_resolve(case_root,checkpoint["case"])
    timeout=int(options.get("case_timeout_seconds",checkpoint["timeout_seconds"]))
    if runner=="draw_case_v1":
        resources = source / "src" if (source / "src" / "DrawResources").is_dir() else source / "resources"
        command=[sys.executable,str(draw_runner),"--build-dir",str(build),
                 "--resource-dir",str(resources),"--case-dir",str(case.parent),
                 "--script",case.name,
                 "--timeout-seconds",str(timeout),"--cpu-limit-seconds",str(max(1,timeout-3))]
        env = os.environ.copy()
        env["CASROOT"] = str(source)
        detail=_run(command,cwd=case.parent,timeout=timeout+12,cpu=timeout+5,memory_gib=4,env=env,output_limit=2*1024*1024)
        output=detail["output_tail"]
        try:
            payload=json.loads(output)
        except json.JSONDecodeError:
            payload=None
        if payload is not None:
            if payload.get("schema_version") in {"bf-group2-staged-run-v1", "bf-group3-staged-run-v1"}:
                # These locked runners report the geometry oracle verdict in
                # a staged record, rather than the legacy TEST_DONE envelope.
                payload = {"return_code": payload.get("process_return_code"),
                           "test_done_marker": payload.get("oracle", {}).get("status") == "geometry_pass",
                           "timed_out": payload.get("process_return_code") == 3,
                           "elapsed_seconds": payload.get("duration_seconds"),
                           "runner_record": payload}
            detail=payload
        passed=(detail.get("return_code")==0 and bool(detail.get("test_done_marker"))
                and not detail.get("timed_out"))
        return {"passed":passed,"result":detail}

    if runner!="cpp_case_v1":
        raise ValueError("runner is not registered")
    if case.stat().st_size>10*1024**2:
        raise ValueError("C++ case exceeds 10 MiB")
    libraries=options.get("libraries",[])
    inputs=[_resolve(case_root,item) for item in options.get("inputs",[])]
    compiler=os.environ.get("BENCH_CXX","clang++-10")
    library_dir=build/"lin64"/os.environ.get("BENCH_TOOLCHAIN_NAME","clang")/"lib"
    include_dir=build/"include"/"opencascade"
    executable=work/(str(checkpoint["id"])+".exe")
    compile_argv=[compiler,"-std=c++17","-I",str(include_dir),"-L",str(library_dir),
                  f"-Wl,-rpath,{library_dir}",str(case),*("-l"+name for name in libraries),
                  "-o",str(executable)]
    compiled=_run(compile_argv,cwd=work,timeout=120,cpu=110,memory_gib=4)
    if compiled["return_code"]!=0:
        return {"passed":False,"phase":"compile","result":compiled}
    tested=_run([str(executable),*(str(item) for item in inputs)],cwd=case.parent,
                timeout=timeout,cpu=max(2,timeout-3),memory_gib=2)
    markers=options.get("stdout_contains",["TEST_DONE"])
    passed=(tested["return_code"]==0 and not tested["timed_out"]
            and all(marker in tested["output_tail"] for marker in markers))
    return {"passed":passed,"compile":compiled,"result":tested}


def _writable_case_root(case_root: Path, work: Path, assets: Path) -> Path:
    target = work / "bundle"
    shutil.copytree(case_root, target)
    if assets.is_dir():
        shutil.copytree(assets, target / "evaluation" / "cases" / "evaluator_assets", dirs_exist_ok=True)
    return target


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--suite",required=True,type=Path)
    parser.add_argument("--case-root",required=True,type=Path)
    parser.add_argument("--patch",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--allow-missing-report",action="store_true")
    args=parser.parse_args()
    suite=json.loads(args.suite.read_text(encoding="utf-8"))
    out={"protocol":"manifest-suite-v1","suite":{"id":suite["id"],"version":suite["version"]},
         "tests":[],"checkpoints":[],"limitations":["Checks are only those declared in this frozen suite; this is not the full upstream test suite."]}
    started=time.monotonic()
    try:
        report=Path(args.report)
        if not report.is_file() or report.stat().st_size==0:
            if not args.allow_missing_report:
                raise ValueError("report missing or empty")
            out["report"]={"provided":False}
        else:
            out["report"]={"provided":True}
        source_snapshot=Path(os.environ.get("BENCH_EVALUATION_SOURCE","/evaluation/private/common_base_source"))
        with tempfile.TemporaryDirectory(prefix="manifest-suite-") as temporary:
            temp=Path(temporary);source=temp/"source";build=temp/"build";work=build/"evaluator"
            shutil.copytree(source_snapshot,source)
            import importlib.util
            evaluator=Path("/evaluation/private/evaluators/run_eval.py")
            spec=importlib.util.spec_from_file_location("trusted_legacy_helpers",evaluator)
            helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
            out["patch_bytes"]=helpers.apply_patch(source,args.patch)
            out["build"]=helpers.configure_and_build(source,build)
            if not out["build"].get("build") or out["build"]["build"].get("return_code")!=0:
                out["failure_stage"]="build"
                out["tests"]=[{"test":row["id"],"passed":False,
                    "result":{"status":"not_run","reason":"build failed"}} for row in suite["checkpoints"]]
            else:
                work.mkdir(parents=True,exist_ok=True)
                # Harnesses create images/logs beside their inputs. Preserve the
                # frozen materials and run an evaluator-only writable copy.
                # Hidden harnesses resolve their trusted Tcl helpers relative
                # to the original bundle layout, not the private Python loader.
                case_root = _writable_case_root(args.case_root, work, Path("/evaluation/private/evaluator_assets"))
                draw_runner=Path("/evaluation/scripts/run_draw_case.py")
                for checkpoint in suite["checkpoints"]:
                    try:
                        result=_execute(checkpoint,case_root=case_root,build=build,source=source,
                                        work=work,draw_runner=draw_runner)
                        status="passed" if result.get("passed") else "timeout" if result.get("result",{}).get("timed_out") else "failed"
                    except (OSError,ValueError,KeyError) as exc:
                        result={"passed":False,"reason":str(exc)};status="error"
                    row={"id":checkpoint["id"],"status":status,"passed":status=="passed",
                         "result":result,"category":checkpoint["category"],
                         "visibility":checkpoint["visibility"],"issue_id":checkpoint.get("issue_id"),
                         "elapsed_seconds":result.get("result",{}).get("elapsed_seconds")}
                    out["checkpoints"].append(row);out["tests"].append({"test":checkpoint["id"],**row})
    except ValueError as exc:
        out["failure_stage"]="submission";out["error"]=str(exc)
    except (OSError,json.JSONDecodeError,KeyError) as exc:
        out["failure_stage"]="infrastructure";out["error"]=str(exc)
    out["elapsed_seconds"]=round(time.monotonic()-started,3)
    out["passed"]=bool(out["tests"]) and all(item.get("passed") is True for item in out["tests"]) and not out.get("failure_stage")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
