"""Offline evaluator setup from a frozen task and a versioned trusted suite."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .catalog import resolve_relative, validate_bundle
from .checkpoints import get_suite, normalize_checkpoints
from .freeze import normalize_suite_case_material
from .proto_config import BENCHMARK_ROOT, PROTO
from .sandbox import command, limits, monitor, PYTHON
from .settings import SETTINGS
from .toolchain import environment as toolchain_environment


LEGACY_FOLDERS={"single":"task_single","group":"task_group","active":"task_active",
                "visible3":"task_group_visible3","visible4":"task_group_visible4",
                "visible5":"task_group_visible5","visible5all":"task_group_visible5all"}


def _suite_for_group(group_id: str | None, task_kind: str, suite_ref: dict | None):
    bundle=validate_bundle(BENCHMARK_ROOT)
    if suite_ref:
        suite=get_suite(BENCHMARK_ROOT,suite_ref["id"],suite_ref["version"])
        if group_id and group_id not in suite.get("group_ids",[]):
            raise ValueError("evaluation suite is not compatible with this task group")
        return bundle,suite
    catalog=json.loads((BENCHMARK_ROOT/"catalog.json").read_text(encoding="utf-8"))
    candidates=[]
    for entry in catalog["evaluation_suites"]:
        value=json.loads((BENCHMARK_ROOT/entry["path"]).read_text(encoding="utf-8"))
        if value.get("legacy_task_kind")==task_kind and (not group_id or group_id in value.get("group_ids",[])):
            candidates.append(value)
    if len(candidates)==1:
        return bundle,candidates[0]
    return bundle,None


def _toolchain_id(bundle: dict, source_id: str | None) -> str:
    if source_id and source_id in bundle["sources"]:
        return bundle["sources"][source_id]["toolchain"]
    if len(bundle["sources"])==1:
        return next(iter(bundle["sources"].values()))["toolchain"]
    raise ValueError("evaluation must name an unambiguous locked source/toolchain")


def _copy_public_cases(bundle: dict, suites: list[dict], frozen_task: Path | None, control: Path,
                       dispatch_override: dict | None = None) -> None:
    catalog=(json.loads((bundle["root"]/"catalog.json").read_text(encoding="utf-8"))
             if bundle is not None else {"issues":[]})
    dispatch_path=(bundle["root"]/"evaluation"/"provenance"/"legacy-dispatch.json" if bundle is not None else None)
    dispatch=dispatch_override or (json.loads(dispatch_path.read_text(encoding="utf-8"))["groups"] if dispatch_path else {})
    folders=set()
    for suite in suites:
        for group_id in suite.get("group_ids",[]):
            item=dispatch.get(group_id)
            if item:
                folders.add(item["legacy_task_folder"])
        task_kind=suite.get("legacy_task_kind")
        folders.add(LEGACY_FOLDERS.get(task_kind,"task_single"))
        # The old group/active evaluators also call issue 544 through task_single.
        if task_kind in {"group","active"}:
            folders.add("task_single")

    issue_entries={(item["id"],item["version"]):item for item in catalog["issues"]}
    wanted={checkpoint.get("issue_id") for suite in suites for checkpoint in suite.get("checkpoints",[])
            if checkpoint.get("visibility")=="public" and checkpoint.get("issue_id")}
    frozen_visible=frozen_task/"visible" if frozen_task and (frozen_task/"visible").is_dir() else None
    for folder in folders:
        visible=control/"tasks"/folder/"visible"
        visible.mkdir(parents=True,exist_ok=True)
        if frozen_visible:
            for item in frozen_visible.iterdir():
                if item.is_symlink() or not item.is_dir():
                    continue
                target=visible/item.name
                if not target.exists():
                    shutil.copytree(item,target)
        for issue_id in wanted:
            number=issue_id.removeprefix("occt-")
            issue_dir=visible/f"issue_{number}"
            if issue_dir.is_dir() and any(issue_dir.iterdir()):
                continue
            if frozen_visible:
                raise ValueError(f"frozen task is missing public evaluation input for {issue_id}")
            reference=issue_entries.get((issue_id,"1"))
            if not reference:
                raise ValueError(f"public evaluation input is not catalogued: {issue_id}")
            manifest_path=bundle["root"]/reference["path"]
            issue=json.loads(manifest_path.read_text(encoding="utf-8"))
            issue_root=manifest_path.parent
            issue_dir.mkdir(parents=True,exist_ok=True)
            for material in issue["public_materials"]:
                source=(issue_root/material).resolve(strict=True)
                if not source.is_relative_to(issue_root.resolve()):
                    raise ValueError("public input path escapes its issue directory")
                shutil.copy2(source,issue_dir/source.name)


def _prepare_control(root: Path, frozen_task: Path | None, suites: list[dict],
                     task_kind: str, source_id: str | None, snapshot_root: Path | None = None):
    control=root/"evaluation-control"
    control.mkdir(parents=True)
    private=control/"private"
    evaluator=private/"evaluators";evaluator.mkdir(parents=True)
    (private/"common_base_source").mkdir(mode=0o555)
    case_root=BENCHMARK_ROOT/"evaluation"/"cases"
    supervisor=Path(snapshot_root)/"supervisor" if snapshot_root else case_root
    source_id=source_id or (suites[0].get("source_ids",[None])[0] if suites else None)
    manifest_suite_runtime=False
    if snapshot_root:
        evaluator_root=supervisor/"legacy"
    else:
        evaluator_directory="evaluation/cases/legacy"
        if source_id:
            bundle=validate_bundle(BENCHMARK_ROOT)
            source=bundle["sources"].get(source_id)
            if source is None:
                raise ValueError(f"task references an unknown source: {source_id}")
            toolchain=json.loads(resolve_relative(
                BENCHMARK_ROOT,f"toolchains/{source['toolchain']}.json").read_text(encoding="utf-8"))
            evaluator_directory=toolchain.get("evaluator_directory",evaluator_directory)
            manifest_suite_runtime=bool(toolchain.get("evaluator_directory"))
        evaluator_root=resolve_relative(BENCHMARK_ROOT,evaluator_directory)
    migrated=evaluator_root/"run_eval.py"
    original=(root/"frozen-evaluator.py" if (root/"frozen-evaluator.py").is_file()
              else migrated if migrated.is_file()
              else PROTO/"private"/"evaluators"/"run_eval.py")
    if not original.is_file():
        raise RuntimeError("trusted OCCT evaluator material is unavailable")
    # No user path is injected. The evaluator takes source/toolchain paths from
    # the supervisor's explicit mounts and BENCH_* toolchain environment.
    shutil.copy2(original,evaluator/"run_eval.py")
    runner=(root/"frozen-runner.py" if (root/"frozen-runner.py").is_file()
            else evaluator_root/"scripts"/"run_draw_case.py"
            if (evaluator_root/"scripts"/"run_draw_case.py").is_file()
            else PROTO/"scripts"/"run_draw_case.py")
    scripts=control/"scripts";scripts.mkdir()
    if not runner.is_file():
        raise RuntimeError("trusted DRAW case runner is unavailable")
    shutil.copy2(runner,scripts/"run_draw_case.py")

    if suites:
        if snapshot_root:
            driver=Path(snapshot_root)/"supervisor"/"suite_driver.py"
            case_source=Path(snapshot_root)/"supervisor"/"cases"/"bundle"
            if not driver.is_file() or not case_source.is_dir():
                raise RuntimeError("frozen manifest runner or suite case materials are unavailable")
            shutil.copy2(driver,control/"suite_driver.py")
            shutil.copytree(case_source,control/"cases"/"bundle",dirs_exist_ok=True)
            (control/"suite.json").write_text(json.dumps(suites[0],ensure_ascii=False),encoding="utf-8")
        elif manifest_suite_runtime:
            if len(suites)!=1:
                raise ValueError("a manifest evaluator must select exactly one evaluation suite")
            bundle=validate_bundle(BENCHMARK_ROOT)
            catalog=json.loads((BENCHMARK_ROOT/"catalog.json").read_text(encoding="utf-8"))
            suite_case_root=control/"cases"/"bundle"
            normalized,_=normalize_suite_case_material(bundle,catalog,suites[0],suite_case_root)
            shutil.copy2(Path(__file__).with_name("suite_driver.py"),control/"suite_driver.py")
            (control/"suite.json").write_text(json.dumps(normalized,ensure_ascii=False),encoding="utf-8")
        else:
            _copy_public_cases(validate_bundle(BENCHMARK_ROOT),suites,frozen_task,control)
    elif frozen_task and (frozen_task/"visible").is_dir():
        target=control/"tasks"/LEGACY_FOLDERS.get(task_kind,"task_single")/"visible"
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(frozen_task/"visible",target,dirs_exist_ok=True)

    for name in ("evaluator_tests","evaluator_assets"):
        source=supervisor/name if snapshot_root else case_root/name
        if source.is_dir():
            shutil.copytree(source,private/name,dirs_exist_ok=True)
    if not snapshot_root and len(suites)==1:
        from .occt_runtime import install as install_occt_runtime
        selected=json.loads((control/'suite.json').read_text()) if (control/'suite.json').is_file() else suites[0]
        install_occt_runtime(BENCHMARK_ROOT,selected,control,
            assets_root=private/'evaluator_assets',case_root=control/'cases/bundle',
            build_target=evaluator/'run_eval.py',draw_target=scripts/'run_draw_case.py')
    source_dir=(frozen_task/"repo" if frozen_task and (frozen_task/"repo").is_dir()
                else SETTINGS.cache_dir/"sources"/str(source_id)/"source")
    if not source_dir.is_dir():
        raise RuntimeError(f"locked source cache is unavailable for {source_id}")
    if any(item["case"]=="regression_analytic_boxes" for suite in suites for item in suite.get("checkpoints",[])):
        regression=Path(__file__).resolve().parents[1]/"config"/"regressions"
        if regression.is_dir():
            shutil.copytree(regression,control/"tasks"/"regressions"/"visible",dirs_exist_ok=True)
    return control,source_dir


def _combine_suites(raw: dict, suites: list[dict]) -> dict:
    normalized=[]
    for suite in suites:
        normalized.append(normalize_checkpoints(suite,raw))
    checkpoints=[row for result in normalized for row in result["checkpoints"]]
    summary={}
    for category in ("original","neighborhood","regression"):
        rows=[row for row in checkpoints if row["category"]==category]
        summary[category]={"declared":len(rows),
            "executed":sum(row["status"] not in {"not_run","skipped"} for row in rows),
            **{status:sum(row["status"]==status for row in rows)
               for status in ("passed","failed","timeout","error","not_run","skipped")},
            "state":"未配置" if not rows else "configured"}
    passed=bool(checkpoints) and all(not row["required"] or row["status"]=="passed" for row in checkpoints)
    raw["evaluation_suites"]=[{"id":suite["id"],"version":suite["version"]} for suite in suites]
    raw["checkpoints"]=checkpoints
    raw["category_summary"]=summary
    raw["technical_passed"]=passed
    raw["passed"]=bool(raw.get("passed")) and passed
    return raw


def evaluate_task(root, cancel=lambda: False, frozen_task=None, task_kind='single', *,
                  suites=None, baseline=False, source_id=None, group_id=None,
                  suite_ref=None, suite_snapshot=None, snapshot_root=None,
                  allow_missing_report=False,allow_empty_findings=False):
    root=Path(root)
    selected_kinds=suites or [task_kind]
    if snapshot_root and suite_snapshot is not None:
        bundle=None;suite=suite_snapshot
    else:
        bundle,suite=_suite_for_group(group_id,task_kind,suite_ref) if len(selected_kinds)==1 else (validate_bundle(BENCHMARK_ROOT),None)
    suite_values=[]
    if suite:
        suite_values=[suite]
    else:
        if bundle is None:
            raise ValueError("suite lookup requires a frozen suite manifest")
        catalog=json.loads((bundle["root"]/"catalog.json").read_text(encoding="utf-8"))
        for kind in selected_kinds:
            found=[json.loads((bundle["root"]/entry["path"]).read_text(encoding="utf-8"))
                   for entry in catalog["evaluation_suites"]
                   if json.loads((bundle["root"]/entry["path"]).read_text(encoding="utf-8")).get("legacy_task_kind")==kind]
            if len(found)==1:
                suite_values.append(found[0])

    evaluation=root/"evaluation-workspace";evaluation.mkdir()
    submission=evaluation/"submission";submission.mkdir()
    for name in ("patch.diff","report.md"):
        path=root/name
        if path.is_file() and not path.is_symlink():
            shutil.copy2(path,submission/name)
    suite_for_cases=[suite] if suite else suite_values
    snapshot_path=Path(snapshot_root) if snapshot_root else None
    control,source_dir=_prepare_control(root,Path(frozen_task) if frozen_task else None,
                                        suite_for_cases,
                                        task_kind,source_id,snapshot_path)
    mounts=[(control,"/evaluation",False),(source_dir,"/evaluation/private/common_base_source",False)]
    profile_path=(snapshot_path/"toolchain.json") if snapshot_path else None
    selected_source_id=source_id or (suite_for_cases[0]["source_ids"][0] if suite_for_cases else None)
    profile_id=(json.loads(profile_path.read_text(encoding="utf-8"))["id"] if profile_path else _toolchain_id(bundle,selected_source_id))
    manifest_suite_runtime=bool(profile_path and json.loads(profile_path.read_text(encoding="utf-8")).get("evaluator_directory"))
    if not profile_path and selected_source_id:
        live_source=bundle["sources"][selected_source_id]
        live_profile=json.loads(resolve_relative(
            BENCHMARK_ROOT,f"toolchains/{live_source['toolchain']}.json").read_text(encoding="utf-8"))
        manifest_suite_runtime=bool(live_profile.get("evaluator_directory"))
    tool_env=toolchain_environment(profile_id,profile_path=profile_path)
    if suite_values and snapshot_path:
        if len(suite_values)!=1:
            raise ValueError("a frozen task must select exactly one evaluation suite")
        args=(command(evaluation,mounts=mounts,env=tool_env)+
              [PYTHON,"/evaluation/suite_driver.py","--suite","/evaluation/suite.json",
               "--case-root","/evaluation/cases/bundle","--patch","/workspace/submission/patch.diff",
               "--report","/workspace/submission/report.md"])
        if allow_missing_report:
            args.append("--allow-missing-report")
    elif suite_values and manifest_suite_runtime:
        if len(suite_values)!=1:
            raise ValueError("a manifest evaluator must select exactly one evaluation suite")
        args=(command(evaluation,mounts=mounts,env=tool_env)+
              [PYTHON,"/evaluation/suite_driver.py","--suite","/evaluation/suite.json",
               "--case-root","/evaluation/cases/bundle","--patch","/workspace/submission/patch.diff",
               "--report","/workspace/submission/report.md"])
        if allow_missing_report:
            args.append("--allow-missing-report")
    elif baseline or (root/"plan1a-protocol.json").is_file() or len(selected_kinds)>1:
        regression=Path(__file__).resolve().parents[1]/"config"/"regressions"
        if regression.is_dir():
            (control/"tasks"/"regressions"/"visible").mkdir(parents=True,exist_ok=True)
            shutil.copytree(regression,control/"tasks"/"regressions"/"visible",dirs_exist_ok=True)
        driver=root/"frozen-driver.py" if (root/"frozen-driver.py").is_file() else Path(__file__).with_name("eval_driver.py")
        shutil.copy2(driver,control/"driver.py")
        args=command(evaluation,mounts=mounts,env=tool_env)+[PYTHON,"/evaluation/driver.py","--suites",*selected_kinds]
        if baseline:
            args.append("--baseline")
    else:
        if task_kind not in LEGACY_FOLDERS:
            raise ValueError(f"unsupported trusted evaluator suite kind: {task_kind}")
        args=(command(evaluation,mounts=mounts,env=tool_env)+
              [PYTHON,"/evaluation/private/evaluators/run_eval.py","--task",task_kind,
               "--patch","/workspace/submission/patch.diff","--report","/workspace/submission/report.md"])
        if allow_missing_report:
            args.append("--allow-missing-report")
        if allow_empty_findings:
            args.append("--allow-empty-findings")
        findings=root/"findings.jsonl"
        if task_kind=="active" and findings.is_file():
            shutil.copy2(findings,submission/"findings.jsonl")
            args.extend(["--findings","/workspace/submission/findings.jsonl"])
    with (root/"evaluation.raw.json").open("w") as output, (root/"evaluation-stderr.log").open("w") as err:
        proc=subprocess.Popen(args,stdout=output,stderr=err,start_new_session=True,preexec_fn=limits)
        code=monitor(proc,2400,cancel,evaluation)
    try:
        result=json.loads((root/"evaluation.raw.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Evaluator failed before JSON output: "+(root/"evaluation-stderr.log").read_text()[-2000:]) from exc
    if suite_values:
        result=_combine_suites(result,suite_values)
    result.setdefault("limitations",["This prototype does not run the complete upstream test suite."])
    (root/"evaluation.internal.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return code,result


def evaluate_single(root, cancel=lambda: False, frozen_task=None, task_kind='single', **kwargs):
    """Backward-compatible entrypoint used by existing workers."""
    return evaluate_task(root,cancel,frozen_task,task_kind,**kwargs)
