"""Normalize trusted evaluator output into versioned checkpoint result rows."""
from __future__ import annotations

import json
from pathlib import Path

from .catalog import CatalogError, validate_bundle


STATUSES = ("passed","failed","timeout","error","not_run","skipped")
CATEGORIES = ("original","neighborhood","regression")


def get_suite(bundle_root: Path | str, suite_id: str, version: str) -> dict:
    bundle=validate_bundle(bundle_root)
    catalog=json.loads((bundle["root"] / "catalog.json").read_text(encoding="utf-8"))
    entry=next((x for x in catalog["evaluation_suites"] if x["id"]==suite_id and x["version"]==version),None)
    if not entry:
        raise CatalogError(f"unknown evaluation suite {suite_id}@{version}")
    return json.loads((bundle["root"] / entry["path"]).read_text(encoding="utf-8"))


def normalize_checkpoints(suite: dict, raw_result: dict) -> dict:
    tests=raw_result.get("tests") if isinstance(raw_result.get("tests"),list) else []
    by_name={}
    for test in tests:
        if isinstance(test,dict) and isinstance(test.get("test"),str):
            by_name.setdefault(test["test"],[]).append(test)
    direct=raw_result.get("checkpoints") if isinstance(raw_result.get("checkpoints"),list) else []
    by_id={row.get("id"):row for row in direct if isinstance(row,dict) and isinstance(row.get("id"),str)}
    prior_stage_failure=raw_result.get("failure_stage") in {"submission","build","infrastructure"}
    checkpoints=[]
    for spec in suite.get("checkpoints",[]):
        matches=by_name.get(spec["case"],[])
        test=by_id.get(spec["id"])
        if test is None and matches:
            test=matches.pop(0)
        if test is None:
            status="not_run" if prior_stage_failure else "skipped" if not spec["required"] else "error"
            checkpoints.append({"id":spec["id"],"issue_id":spec.get("issue_id"),
                "case":spec["case"],
                "category":spec["category"],"visibility":spec["visibility"],
                "required":spec["required"],"status":status,
                "reason":"evaluation stopped before this checkpoint" if prior_stage_failure else "runner returned no matching checkpoint"})
            continue
        detail=test.get("result")
        timed_out=bool(isinstance(detail,dict) and (detail.get("timed_out") or detail.get("status")=="timeout"))
        explicit=test.get("status")
        status=explicit if explicit in STATUSES else "passed" if test.get("passed") is True else "timeout" if timed_out else "failed"
        elapsed=(test.get("elapsed_seconds") if isinstance(test.get("elapsed_seconds"),(int,float)) else None)
        if elapsed is None and isinstance(detail,dict):
            elapsed=detail.get("elapsed_seconds")
            if elapsed is None and isinstance(detail.get("result"),dict):
                elapsed=detail["result"].get("elapsed_seconds")
        checkpoints.append({"id":spec["id"],"issue_id":spec.get("issue_id"),
            "case":spec["case"],
            "category":spec["category"],"visibility":spec["visibility"],
            "required":spec["required"],"status":status,
            "elapsed_seconds":elapsed,"evidence":detail})
    breakdown={}
    for category in CATEGORIES:
        rows=[row for row in checkpoints if row["category"]==category]
        breakdown[category]={"declared":len(rows),
            "executed":sum(row["status"] not in {"not_run","skipped"} for row in rows),
            **{status:sum(row["status"]==status for row in rows) for status in STATUSES},
            "state":"未配置" if not rows else "configured"}
    complete=bool(checkpoints) and all(not row["required"] or row["status"]=="passed" for row in checkpoints)
    return {"suite_id":suite["id"],"suite_version":suite["version"],
            "checkpoints":checkpoints,"category_summary":breakdown,
            "technical_passed":complete}
