"""Public API projections that remove hidden evaluator evidence and host paths."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .settings import SETTINGS

DATA=SETTINGS.data_dir


def _visibility(run: dict | None) -> dict[str, str]:
    if not run:
        return {}
    snapshot=DATA/"runs"/run.get("id","")/"benchmark-snapshot"/"suite.json"
    suite=None
    try:
        if snapshot.is_file() and not snapshot.is_symlink():
            suite=json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError,ValueError,json.JSONDecodeError):
        suite=None
    if suite is None:
        reference=run.get("task",{}).get("evaluation_suite")
        if reference:
            try:
                catalog=json.loads((SETTINGS.benchmark_root/"catalog.json").read_text(encoding="utf-8"))
                entry=next(item for item in catalog["evaluation_suites"]
                           if item["id"]==reference["id"] and item["version"]==reference["version"])
                suite=json.loads((SETTINGS.benchmark_root/entry["path"]).read_text(encoding="utf-8"))
            except (OSError,ValueError,KeyError,StopIteration,json.JSONDecodeError):
                suite=None
    if not suite:
        return {}
    return {item["case"]:item["visibility"] for item in suite.get("checkpoints",[])}


def _hidden(name, visibility: dict[str,str]) -> bool:
    return visibility.get(name)=="hidden" or name.startswith(("hidden_","positive_control"))


def public_evaluation(value: dict | None, run: dict | None = None) -> dict | None:
    if not isinstance(value,dict):
        return value
    result=copy.deepcopy(value)
    visibility=_visibility(run)
    checkpoints=result.get("checkpoints")
    hidden_checkpoint_ids=set()
    if isinstance(checkpoints,list):
        public=[];hidden=[]
        for item in checkpoints:
            if not isinstance(item,dict):
                continue
            if item.get("visibility")=="hidden":
                if isinstance(item.get("id"),str):hidden_checkpoint_ids.add(item["id"])
                if isinstance(item.get("case"),str):hidden_checkpoint_ids.add(item["case"])
                hidden.append(item);continue
            public.append({key:item.get(key) for key in ("id","issue_id","category","status","required","elapsed_seconds") if key in item})
        if hidden:
            public.append({"id":"hidden-summary","issue_id":None,"name":"隐藏检查（详情不公开）",
                           "visibility":"hidden","category_summary":_status_counts(hidden)})
        result["checkpoints"]=public
    tests=result.get("tests")
    if isinstance(tests,list):
        public=[];hidden=[]
        for item in tests:
            if not isinstance(item,dict):
                continue
            name=str(item.get("test",""))
            if _hidden(name,visibility) or name in hidden_checkpoint_ids:
                hidden.append(item);continue
            public.append({"test":name,"passed":bool(item.get("passed")),
                           "status":"passed" if item.get("passed") else "failed"})
        result["tests"]=public
        if hidden:
            result["hidden_check_summary"]=_status_counts([
                {"status":"passed" if item.get("passed") else "failed"} for item in hidden])
    build=result.get("build")
    if isinstance(build,dict):
        result["build"]={phase:{"return_code":(build.get(phase) or {}).get("return_code")}
                         for phase in ("configure","build")}
    for key in ("error","patch_error","output_tail","command","path","private_path","evidence"):
        if key in result:
            result.pop(key,None)
    result.pop("hidden_tests",None)
    return result


def _status_counts(rows: list[dict]) -> dict:
    statuses=("passed","failed","timeout","error","not_run","skipped")
    return {"declared":len(rows),**{status:sum(item.get("status")==status for item in rows) for status in statuses}}


def public_run(run: dict) -> dict:
    result=copy.deepcopy(run)
    visibility=_visibility(run)
    checks=result.get("checks")
    if isinstance(checks,list):
        public=[];hidden=[]
        for item in checks:
            name=str(item.get("name",item.get("test","")))
            if item.get("visibility")=="hidden" or _hidden(name,visibility):
                hidden.append(item);continue
            public.append({key:item.get(key) for key in ("issue_id","name","status","category","elapsed_seconds") if key in item})
        if hidden:
            public.append({"issue_id":None,"name":"隐藏检查（详情不公开）","visibility":"hidden",
                           "category_summary":_status_counts(hidden)})
        result["checks"]=public
    result["evaluation"]=public_evaluation(result.get("evaluation"),run)
    for event in result.get("events",[]):
        if event.get("stage") in {"failed","error","timed_out"}:
            event["message"]="运行未成功；监督端保留诊断记录。"
    if result.get("error"):
        result["error"]="运行失败；监督端保留诊断记录。"
    return result


def public_evaluation_record(item: dict, runs_by_id: dict[str,dict] | None = None) -> dict:
    result=copy.deepcopy(item)
    run=(runs_by_id or {}).get(item.get("run_id"))
    if isinstance(result.get("result"),dict):
        result["result"]=public_evaluation(result["result"],run)
    visibility=_visibility(run)
    stages=result.get("stages")
    if isinstance(stages,list):
        public=[];hidden=[]
        checkpoint_ids=set()
        raw=item.get("result",{})
        for checkpoint in raw.get("checkpoints",[]) if isinstance(raw,dict) else []:
            if checkpoint.get("visibility")=="hidden":
                checkpoint_ids.update(x for x in (checkpoint.get("id"),checkpoint.get("case")) if isinstance(x,str))
        for stage in stages:
            name=str(stage.get("name",""))
            if _hidden(name,visibility) or name in checkpoint_ids:
                hidden.append(stage);continue
            public.append({key:stage.get(key) for key in ("name","status") if key in stage})
        if hidden:public.append({"name":"隐藏检查（详情不公开）","status":"summarized","count":len(hidden)})
        result["stages"]=public
    return result


def public_asset(item: dict) -> dict:
    result=copy.deepcopy(item)
    if isinstance(result.get("evaluation"),dict):
        result["evaluation"]=public_evaluation(result["evaluation"])
    return result
