"""Run an explicitly selected immutable suite against an existing patch offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
from pathlib import Path

from .app import DATA,get_run
from .catalog import public_task,validate_bundle
from .checkpoints import get_suite
from .evaluator import evaluate_task
from .freeze import freeze_catalog_task,materialize_source
from .public_results import public_evaluation
from .settings import SETTINGS
from .study import evaluation_record,put


def _source_for_run(run: dict, bundle: dict, source_run: Path | None = None) -> tuple[str,str]:
    source_id=run.get("task",{}).get("source_id")
    provenance=run.get("provenance") or {}
    tree_hash=provenance.get("source_tree_sha256_locked")
    proof="run_provenance.source_tree_sha256_locked"
    if not tree_hash and source_run:
        snapshot=source_run/"benchmark-snapshot"/"snapshot.json"
        if snapshot.is_file() and not snapshot.is_symlink():
            value=json.loads(snapshot.read_text(encoding="utf-8"))
            tree_hash=value.get("source_tree_sha256")
            proof="run_benchmark_snapshot.snapshot.json"
    if source_id in bundle["sources"]:
        expected=bundle["sources"][source_id]["materialized_tree_sha256"]
        if not tree_hash or tree_hash!=expected:
            raise ValueError("original run has no verified baseline tree hash matching its locked source; commit identity alone is insufficient")
        return source_id,proof
    if not tree_hash:
        raise ValueError("original run has no source_id or verified baseline tree hash; refusing commit-only inference")
    matches=[identity for identity,item in bundle["sources"].items()
             if item["materialized_tree_sha256"]==tree_hash]
    if len(matches)!=1:
        raise ValueError("cannot uniquely match the original run's frozen source tree to a locked source")
    return matches[0],proof


def _select_group(bundle: dict, suite: dict, source_id: str, preferred_id: str | None):
    if source_id not in suite.get("source_ids",[]):
        raise ValueError("target evaluation suite is incompatible with the selected source_id")
    candidates=[(key,group) for key,group in bundle["groups"].items()
                if key[0] in suite.get("group_ids",[]) and group["source_id"]==source_id]
    if preferred_id:
        candidates=[item for item in candidates if item[0][0]==preferred_id]
    if not candidates:
        raise ValueError("target suite has no compatible task group for the selected source")
    return sorted(candidates,key=lambda item:(item[0][0],item[0][1]))[0][1]


def reevaluate(*, suite_id: str, suite_version: str, run_id: str | None = None,
               patch_path: Path | str | None = None, source_id: str | None = None) -> dict:
    if bool(run_id)==bool(patch_path):
        raise ValueError("provide exactly one of run_id or patch_path")
    if patch_path and not source_id:
        raise ValueError("patch-file reevaluation requires an explicit source_id")
    bundle=validate_bundle(SETTINGS.benchmark_root)
    suite=get_suite(SETTINGS.benchmark_root,suite_id,suite_version)
    original=None
    baseline_proof=None
    if run_id:
        original=get_run(run_id)
        if original.get("mode")!="live" or original.get("status") in {"queued","preparing","running","collecting","evaluating"}:
            raise ValueError("run-id reevaluation requires an ended live run")
        source_run=DATA/"runs"/run_id
        source_id,baseline_proof=_source_for_run(original,bundle,source_run)
        preferred_id=original["task"]["id"]
        patch_source=source_run/"patch.diff"
        if patch_source.is_symlink() or not patch_source.is_file():
            raise ValueError("original run has no regular patch.diff")
        base_commit=original["task"].get("base_commit")
        if base_commit and bundle["sources"][source_id]["commit"]!=base_commit:
            raise ValueError("original run base commit differs from its locked source")
        report_source=source_run/"report.md"
    else:
        preferred_id=None
        patch_source=Path(patch_path).expanduser().resolve(strict=True)
        if patch_source.is_symlink() or not patch_source.is_file() or patch_source.stat().st_size>20*1024**2:
            raise ValueError("patch must be a regular file no larger than 20 MiB")
        report_source=None
    if source_id not in bundle["sources"]:
        raise ValueError("unknown source_id")
    group=_select_group(bundle,suite,source_id,preferred_id)
    if original:
        original_members={item["id"] for item in original["task"].get("issues",[])}
        target_members={item["issue_id"] for item in group["members"]}
        if not original_members.issubset(target_members):
            raise ValueError("selected target group does not include every original run issue")

    identity=secrets.token_hex(8)
    root=DATA/"reevaluations"/identity
    root.mkdir(parents=True,mode=0o700)
    task=public_task(bundle,group)
    snapshot_manifest=freeze_catalog_task(task,root,suite_override={"id":suite_id,"version":suite_version})
    frozen=root/"frozen-task";frozen.mkdir(mode=0o700)
    materialize_source(root/"benchmark-snapshot",frozen/"repo")
    shutil.copytree(root/"benchmark-snapshot"/"visible",frozen/"visible")
    shutil.copytree(root/"benchmark-snapshot"/"tools",frozen/"tools")
    shutil.copy2(patch_source,root/"patch.diff")
    if report_source and report_source.is_file() and not report_source.is_symlink():
        shutil.copy2(report_source,root/"report.md")
    suite_snapshot=json.loads((root/"benchmark-snapshot"/"suite.json").read_text(encoding="utf-8"))
    code,result=evaluate_task(root,frozen_task=frozen,task_kind=suite_snapshot.get("legacy_task_kind","single"),
        source_id=source_id,group_id=group["id"],
        suite_ref={"id":suite_id,"version":suite_version},suite_snapshot=suite_snapshot,
        snapshot_root=root/"benchmark-snapshot",allow_missing_report=not (root/"report.md").is_file())
    record=evaluation_record(run_id,result,code,"reevaluation",root)
    record["reevaluation"]={"source_id":source_id,"source_commit":snapshot_manifest["source_commit"],
        "source_tree_sha256":snapshot_manifest["source_tree_sha256"],"suite_id":suite_id,
        "suite_version":suite_version,"patch_sha256":hashlib.sha256((root/"patch.diff").read_bytes()).hexdigest(),
        "report_provided":(root/"report.md").is_file(),"snapshot_sha256":snapshot_manifest["snapshot_sha256"],
        "model_called":False,"baseline_verification":baseline_proof or "explicit_source_id_for_patch"}
    put("evaluations",record,False)
    return {**record,"result":public_evaluation(result,original)}


def main() -> None:
    parser=argparse.ArgumentParser(description="Offline reevaluation against an explicitly selected suite version")
    subject=parser.add_mutually_exclusive_group(required=True)
    subject.add_argument("--run-id")
    subject.add_argument("--patch",type=Path)
    parser.add_argument("--source-id",help="required with --patch; inferred and checked for --run-id")
    parser.add_argument("--suite-id",required=True)
    parser.add_argument("--suite-version",required=True)
    args=parser.parse_args()
    result=reevaluate(suite_id=args.suite_id,suite_version=args.suite_version,
        run_id=args.run_id,patch_path=args.patch,source_id=args.source_id)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
