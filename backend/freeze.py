"""Freeze catalog inputs at queue time for an isolated run."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from pathlib import PurePosixPath

from .catalog import validate_bundle, resolve_relative, public_task
from .settings import SETTINGS


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _copy_tree(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"freeze source is not a regular directory: {source.name}")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError(f"freeze source contains a symlink: {source.name}")
    shutil.copytree(source, target, symlinks=True)


def _copy_writable_tree(source: Path, target: Path) -> None:
    _copy_tree(source, target)
    for path in target.rglob("*"):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        if path.is_dir():
            path.chmod(mode | 0o700)
        else:
            path.chmod(mode | 0o600)
    target.chmod(target.stat().st_mode | 0o700)


def _issue_case_reference(value: str, issue_refs_by_directory: dict[str, dict], bundle: dict):
    """Resolve an issue case through its catalog path, never its directory name."""
    parts = PurePosixPath(value).parts
    if len(parts) < 4 or parts[0] != "issues":
        raise ValueError(f"suite issue case path is malformed: {value}")
    directory = PurePosixPath(*parts[:3]).as_posix()
    issue_ref = issue_refs_by_directory.get(directory)
    if issue_ref is None:
        raise ValueError(f"suite case does not match a catalogued issue path: {value}")
    issue_key = (issue_ref["id"], issue_ref["version"])
    issue = bundle["issues"].get(issue_key)
    if issue is None:
        raise ValueError(f"suite case references an unknown issue: {issue_key[0]}@{issue_key[1]}")
    return issue_ref, issue, parts[3:]


def _evaluator_issue_case(value: str, issue_ref: dict, remainder: tuple[str, ...]) -> str:
    return PurePosixPath("issues", issue_ref["id"], issue_ref["version"], *remainder).as_posix()


def normalize_suite_case_material(bundle: dict, catalog: dict, suite: dict,
                                  case_root: Path | str) -> tuple[dict, list[dict]]:
    """Copy suite cases and map catalog paths onto stable issue identities.

    Catalog directory names are presentation paths. Frozen evaluator paths use
    the issue identity recorded in catalog.json, so renaming an issue directory
    cannot silently break a case path or a downstream dispatcher key.
    """
    case_root = Path(case_root)
    frozen_suite = deepcopy(suite)
    issue_refs_by_directory = {
        PurePosixPath(item["path"]).parent.as_posix(): item for item in catalog["issues"]
    }
    aliases = []
    for checkpoint in frozen_suite["checkpoints"]:
        values = [("case", checkpoint["case"])]
        values.extend(("input", value) for value in checkpoint.get("runner_options", {}).get("inputs", []))
        normalized_inputs = []
        for role, catalog_value in values:
            source_path = resolve_relative(bundle["root"], catalog_value)
            evaluator_value = catalog_value
            if catalog_value.startswith("issues/"):
                issue_ref, issue, remainder = _issue_case_reference(
                    catalog_value, issue_refs_by_directory, bundle)
                evaluator_value = _evaluator_issue_case(catalog_value, issue_ref, remainder)
                if evaluator_value != catalog_value:
                    aliases.append({"checkpoint_id": checkpoint["id"], "role": role,
                                    "catalog_case": catalog_value,
                                    "evaluator_case": evaluator_value,
                                    "issue_id": issue_ref["id"],
                                    "issue_version": issue_ref["version"]})
                issue_root = resolve_relative(bundle["root"], issue_ref["path"]).parent
                for material in issue["public_materials"]:
                    public_path = resolve_relative(issue_root, material)
                    public_target = (case_root / "issues" / issue_ref["id"] /
                                     issue_ref["version"] / material)
                    public_target.parent.mkdir(parents=True, exist_ok=True)
                    if public_target.is_symlink():
                        raise ValueError(f"frozen evaluator case is a symlink: {public_target.name}")
                    if not public_target.exists():
                        shutil.copy2(public_path, public_target)
            else:
                target = case_root / PurePosixPath(evaluator_value)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    raise ValueError(f"frozen evaluator case is a symlink: {target.name}")
                if not target.exists():
                    shutil.copy2(source_path, target)
            if role == "case":
                checkpoint["case"] = evaluator_value
            else:
                normalized_inputs.append(evaluator_value)
        if normalized_inputs:
            checkpoint.setdefault("runner_options", {})["inputs"] = normalized_inputs
    return frozen_suite, aliases


def freeze_catalog_task(task: dict, run_root: Path | str, *, suite_override: dict | None = None) -> dict:
    """Snapshot public task inputs and trusted evaluation materials.

    Source code itself stays in the immutable per-user cache until the worker
    materializes a private writable copy. No network access or model call occurs.
    """
    if task.get("version") == "proto-1" or not task.get("source_id"):
        return {"kind": "legacy", "frozen": False}
    bundle = validate_bundle(SETTINGS.benchmark_root)
    key = (task.get("id"), task.get("version"))
    group = bundle["groups"].get(key)
    if group is None:
        raise ValueError("queued catalog task does not match a validated group/version")
    expected_task=public_task(bundle,group)
    frozen_fields=("id","version","title","kind","source_id","base_commit","issues","budget",
                   "has_hidden_checks","execution_mode","required_output","evaluation_suite","source_hash")
    if any(task.get(field)!=expected_task.get(field) for field in frozen_fields):
        raise ValueError("queued task public material or catalog version differs from the frozen catalog")
    source = bundle["sources"][group["source_id"]]
    cache = SETTINGS.cache_dir / "sources" / group["source_id"]
    metadata_path, source_path = cache / "source.json", cache / "source"
    if metadata_path.is_symlink() or not metadata_path.is_file() or source_path.is_symlink() or not source_path.is_dir():
        raise ValueError(f"verified source cache is not prepared for {group['source_id']}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    from .source_cache import tree_sha256
    source_hash = tree_sha256(source_path)
    if (metadata.get("verification_status") != "verified_git" or
            metadata.get("commit") != source["commit"] or
            metadata.get("tree_sha256") != source_hash or
            source_hash != source["materialized_tree_sha256"]):
        raise ValueError("source cache failed its locked Git commit/tree verification")

    catalog_path = bundle["root"] / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    group_ref = next(item for item in catalog["groups"] if (item["id"], item["version"]) == key)
    suite_ref = suite_override or group["evaluation_suite"]
    suite_value=bundle["suites"].get((suite_ref.get("id"),suite_ref.get("version")))
    if (suite_value is None or group["source_id"] not in suite_value.get("source_ids",[]) or
            group["id"] not in suite_value.get("group_ids",[])):
        raise ValueError("selected evaluation suite is incompatible with the frozen task group")
    suite_entry = next(item for item in catalog["evaluation_suites"]
                       if (item["id"], item["version"]) == (suite_ref["id"], suite_ref["version"]))
    root = Path(run_root)
    snapshot = root / "benchmark-snapshot"
    if snapshot.exists():
        raise FileExistsError("benchmark snapshot already exists")
    snapshot.mkdir(parents=True, mode=0o700)
    _write_json(snapshot / "catalog.json", catalog)
    _write_json(snapshot / "group.json", group)
    frozen_suite = deepcopy(suite_value)
    _write_json(snapshot / "source-lock.json", source)
    toolchain_value=json.loads(resolve_relative(bundle["root"], f"toolchains/{source['toolchain']}.json").read_text(encoding="utf-8"))
    _write_json(snapshot / "toolchain.json", toolchain_value)
    dispatch=bundle["root"]/"evaluation"/"provenance"/"legacy-dispatch.json"
    if dispatch.is_file() and not dispatch.is_symlink():
        shutil.copy2(dispatch,snapshot/"legacy-dispatch.json")

    visible = snapshot / "visible"
    for member in group["members"]:
        issue_key = (member["issue_id"], member["issue_version"])
        issue = bundle["issues"][issue_key]
        issue_ref = next(item for item in catalog["issues"]
                         if (item["id"], item["version"]) == issue_key)
        issue_root = resolve_relative(bundle["root"], issue_ref["path"]).parent
        issue_dir = visible / f"issue_{member['issue_id'].removeprefix('occt-')}"
        issue_dir.mkdir(parents=True)
        statement = resolve_relative(issue_root, issue["statement"])
        shutil.copy2(statement, issue_dir / "statement.md")
        _write_json(issue_dir / "issue.json", issue)
        for material in issue["public_materials"]:
            source_file = resolve_relative(issue_root, material)
            shutil.copy2(source_file, issue_dir / source_file.name)

    for item in ("build.sh", "run_draw_case.py"):
        src = bundle["root"] / "tools" / toolchain_value.get("tools_directory",source["toolchain"]) / item
        if src.is_symlink() or not src.is_file():
            raise ValueError(f"locked task tool is missing: {item}")
        target = snapshot / "tools" / item
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(src, target)

    supervisor = snapshot / "supervisor"
    cases = bundle["root"] / "evaluation" / "cases"
    evaluator_directory = toolchain_value.get("evaluator_directory", "evaluation/cases/legacy")
    evaluator_root = resolve_relative(bundle["root"], evaluator_directory)
    evaluator_files = {
        "legacy/run_eval.py": evaluator_root / "run_eval.py",
        "legacy/scripts/run_draw_case.py": evaluator_root / "scripts" / "run_draw_case.py",
    }
    for target_name, src in evaluator_files.items():
        if src.is_symlink() or not src.is_file():
            raise ValueError(f"trusted evaluation runner is missing: {src.name}")
        dst = supervisor / target_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for name in ("evaluator_tests", "evaluator_assets"):
        src = cases / name
        if not src.exists():
            continue
        if src.is_symlink():
            raise ValueError(f"trusted evaluation material is a symlink: {name}")
        dst = supervisor / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            _copy_tree(src, dst)
        else:
            shutil.copy2(src, dst)
    (supervisor/"suite_driver.py").parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(__file__).with_name("suite_driver.py"),supervisor/"suite_driver.py")

    case_root=supervisor/"cases"/"bundle"
    frozen_suite, case_path_aliases = normalize_suite_case_material(bundle, catalog, suite_value, case_root)

    _write_json(snapshot / "suite.json", frozen_suite)

    content_hash = hashlib.sha256()
    for path in sorted(snapshot.rglob("*"), key=lambda item: item.relative_to(snapshot).as_posix()):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(snapshot).as_posix()
            content_hash.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    manifest = {"schema_version": 1, "task_id": group["id"], "task_version": group["version"],
                "source_id": group["source_id"], "source_commit": source["commit"],
                "source_tree_sha256": source_hash,
                "suite_id": suite_ref["id"], "suite_version": suite_ref["version"],
                "toolchain_id": source["toolchain"], "catalog_hash": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                "group_manifest_path": group_ref["path"], "suite_manifest_path": suite_entry["path"],
                "case_path_aliases": case_path_aliases,
                "snapshot_sha256": content_hash.hexdigest(), "frozen": True}
    _write_json(snapshot / "snapshot.json", manifest)
    return manifest


def materialize_source(snapshot_root: Path | str, destination: Path | str) -> Path:
    """Copy the pinned cache tree into a writable task repo and recheck it."""
    snapshot = Path(snapshot_root)
    manifest = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))
    cached = SETTINGS.cache_dir / "sources" / manifest["source_id"] / "source"
    from .source_cache import tree_sha256
    if tree_sha256(cached) != manifest["source_tree_sha256"]:
        raise ValueError("locked source cache changed after task was queued")
    target = Path(destination)
    _copy_writable_tree(cached, target)
    if tree_sha256(target) != manifest["source_tree_sha256"]:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError("materialized source tree differs from the locked baseline")
    return target


def verify_snapshot(snapshot_root: Path | str) -> dict:
    snapshot=Path(snapshot_root)
    manifest_path=snapshot/"snapshot.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("frozen benchmark snapshot manifest is missing")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    digest=hashlib.sha256()
    for path in sorted(snapshot.rglob("*"), key=lambda item: item.relative_to(snapshot).as_posix()):
        if path == manifest_path:
            continue
        if path.is_symlink():
            raise ValueError("frozen benchmark snapshot contains a symlink")
        if path.is_file():
            relative=path.relative_to(snapshot).as_posix()
            digest.update(relative.encode("utf-8")+b"\0"+hashlib.sha256(path.read_bytes()).digest())
    if digest.hexdigest()!=manifest.get("snapshot_sha256"):
        raise ValueError("frozen benchmark snapshot changed after queueing")
    return manifest
