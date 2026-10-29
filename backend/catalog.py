"""Reader and validator for versioned benchmark bundles.

Only public issue material is returned by ``public_task``. Evaluation suite
details stay supervisor-side and are never embedded in the public task record.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath
from typing import Any


ALLOWED_GROUP_KINDS = {"single", "group", "active"}
ALLOWED_EXECUTION_MODES = {"joint", "independent"}
ALLOWED_CHECK_CATEGORIES = {"original", "neighborhood", "regression"}
ALLOWED_VISIBILITY = {"public", "hidden"}
TRUSTED_RUNNERS = {"draw_case_v1", "cpp_case_v1"}
TRUSTED_ORACLES = {"draw_test_done_v1", "stdout_contains_v1"}
TRUSTED_CPP_LIBRARIES = {
    "TKBO", "TKPrim", "TKTopAlgo", "TKBRep", "TKGeomBase", "TKG3d", "TKG2d",
    "TKMath", "TKernel", "TKGeomAlgo", "TKShHealing", "TKOffset",
}
TRUSTED_TASK_KINDS = {"single", "group", "active", "visible3", "visible4", "visible5", "visible5all"}
PUBLIC_BANNED_FIELDS = {"private", "hidden_issue", "evaluator_path", "secret", "api_key"}


class CatalogError(ValueError):
    pass


def _read_json(path: Path, *, maximum: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise CatalogError(f"invalid or oversized JSON manifest: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot parse manifest {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"manifest must be an object: {path.name}")
    return value


def resolve_relative(root: Path, value: str, *, must_exist: bool = True) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CatalogError("manifest paths must be nonempty POSIX relative paths")
    rel = PurePosixPath(value)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise CatalogError(f"unsafe relative path: {value}")
    target = root.joinpath(*rel.parts)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise CatalogError(f"symlink is not allowed in benchmark materials: {value}")
    try:
        resolved = target.resolve(strict=must_exist)
        if not resolved.is_relative_to(root.resolve()):
            raise CatalogError(f"path escapes benchmark root: {value}")
    except OSError as exc:
        raise CatalogError(f"missing benchmark material: {value}") from exc
    return resolved


def _key_ref(item: dict[str, Any], label: str) -> tuple[str, str]:
    identity, version = item.get("id"), item.get("version")
    if not isinstance(identity, str) or not identity.strip() or not isinstance(version, str) or not version.strip():
        raise CatalogError(f"invalid {label} identity/version")
    return identity, version


def _fields(value: dict[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing:
        raise CatalogError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise CatalogError(f"{label} contains unknown fields: {', '.join(sorted(extra))}")


def _check_public_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in PUBLIC_BANNED_FIELDS:
                raise CatalogError(f"public issue manifest contains blocked field: {key}")
            _check_public_fields(child)
    elif isinstance(value, list):
        for child in value:
            _check_public_fields(child)


def _read_index(root: Path, name: str, label: str) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    catalog = _read_json(root / name)
    _fields(catalog,{"schema_version","id","title","issues","groups","evaluation_suites"},
            {"schema_version","id","title","issues","groups","evaluation_suites"},"catalog.json")
    values = catalog.get(label)
    if catalog.get("schema_version") != 1 or not isinstance(values, list):
        raise CatalogError(f"catalog.json must define a schema_version 1 {label} list")
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for item in values:
        if not isinstance(item, dict):
            raise CatalogError(f"invalid {label} catalog entry")
        _fields(item,{"id","version","path"},{"id","version","path"},f"{label} catalog reference")
        key = _key_ref(item, label)
        if key in indexed:
            raise CatalogError(f"duplicate {label} reference: {key[0]}@{key[1]}")
        indexed[key] = item
    return values, indexed


def validate_bundle(bundle_root: Path | str) -> dict[str, Any]:
    root = Path(bundle_root).expanduser().resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise CatalogError("benchmark root must be a regular directory")
    sources_lock = _read_json(root / "sources.lock.json")
    _fields(sources_lock,{"schema_version","algorithm","exclusions","sources"},
            {"schema_version","algorithm","exclusions","sources"},"sources.lock.json")
    source_items = sources_lock.get("sources")
    if (sources_lock.get("schema_version") != 1 or
            sources_lock.get("algorithm") != "agent-bench-tree-sha256-v1" or
            not isinstance(source_items, list)):
        raise CatalogError("sources.lock.json must define schema_version 1 and sources")
    sources: dict[str, dict[str, Any]] = {}
    for source in source_items:
        if not isinstance(source, dict):
            raise CatalogError("source lock entries must be objects")
        _fields(source,{"source_id","upstream_url","commit","materialized_tree_sha256","verification_status","provenance","toolchain"},
                {"source_id","upstream_url","commit","materialized_tree_sha256","verification_status","provenance","toolchain"},"source lock entry")
        identity = source.get("source_id")
        commit = source.get("commit")
        tree_hash = source.get("materialized_tree_sha256")
        if not isinstance(identity, str) or identity in sources:
            raise CatalogError("source_id must be unique")
        if not isinstance(source.get("upstream_url"),str) or not source["upstream_url"].startswith("https://"):
            raise CatalogError(f"source {identity} must use a documented HTTPS upstream URL")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise CatalogError(f"source {identity} must pin a full 40-digit commit")
        if not isinstance(tree_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", tree_hash):
            raise CatalogError(f"source {identity} must pin a SHA256 tree hash")
        if source.get("verification_status") not in {"verified_git", "unverified_export_without_git_metadata"}:
            raise CatalogError(f"source {identity} must state its verification status")
        resolve_relative(root,source.get("provenance"))
        toolchain_id=source.get("toolchain")
        if not isinstance(toolchain_id,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",toolchain_id):
            raise CatalogError(f"source {identity} has an unsafe toolchain reference")
        toolchain=_read_json(resolve_relative(root,f"toolchains/{toolchain_id}.json"))
        required_toolchain={"schema_version","id","title","platforms","executables","compiler_output_directory",
                            "tools_directory","compiler_jobs_max","tcl_version","tcl_paths"}
        allowed_toolchain=required_toolchain|{"evaluator_directory","optimization_flags"}
        if (not required_toolchain.issubset(toolchain) or not set(toolchain).issubset(allowed_toolchain) or
                toolchain.get("schema_version")!=1 or
                toolchain.get("id")!=toolchain_id or not isinstance(toolchain.get("title"),str) or
                not isinstance(toolchain.get("platforms"),list) or not toolchain["platforms"] or
                any(not isinstance(item,str) for item in toolchain["platforms"]) or
                not isinstance(toolchain.get("compiler_output_directory"),str) or
                not re.fullmatch(r"[A-Za-z0-9_.-]+",toolchain["compiler_output_directory"]) or
                not isinstance(toolchain.get("tcl_version"),str) or not isinstance(toolchain.get("tcl_paths"),str)):
            raise CatalogError(f"source {identity} has an incompatible toolchain profile")
        if 'optimization_flags' in toolchain and toolchain['optimization_flags'] not in {
                '-O0 -DNDEBUG','-O1 -DNDEBUG','-O2 -DNDEBUG','-O3 -DNDEBUG'}:
            raise CatalogError('unsupported toolchain optimization flags')
        executables=toolchain.get("executables")
        tools_dir=toolchain.get("tools_directory")
        jobs=toolchain.get("compiler_jobs_max")
        if (not isinstance(executables,dict) or set(executables)!={"cmake","c_compiler","cxx_compiler"} or
                any(not isinstance(value,str) or not value or "\n" in value for value in executables.values()) or
                not isinstance(tools_dir,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",tools_dir) or
                not isinstance(jobs,int) or not 1<=jobs<=2):
            raise CatalogError(f"source {identity} has an invalid toolchain profile")
        evaluator_directory=toolchain.get("evaluator_directory")
        if evaluator_directory is not None:
            if not isinstance(evaluator_directory,str):
                raise CatalogError(f"source {identity} has an invalid evaluator directory")
            evaluator_root=resolve_relative(root,evaluator_directory)
            if not evaluator_root.is_dir():
                raise CatalogError(f"source {identity} evaluator directory is missing")
            for relative in ("run_eval.py","scripts/run_draw_case.py"):
                runner=resolve_relative(root,f"{evaluator_directory}/{relative}")
                if not runner.is_file():
                    raise CatalogError(f"source {identity} evaluator runner is missing: {relative}")
        sources[identity] = source

    issue_entries, issue_index = _read_index(root, "catalog.json", "issues")
    group_entries, group_index = _read_index(root, "catalog.json", "groups")
    suite_entries, suite_index = _read_index(root, "catalog.json", "evaluation_suites")
    group_versions: dict[str, str] = {}
    for item in group_entries:
        identity, version = _key_ref(item, "group")
        previous = group_versions.get(identity)
        if previous is not None:
            raise CatalogError(
                f"group id {identity} has multiple versions ({previous}, {version}); "
                "group updates require a new group id"
            )
        group_versions[identity] = version
    issue_manifests: dict[tuple[str, str], dict[str, Any]] = {}
    for key, entry in issue_index.items():
        manifest = _read_json(resolve_relative(root, entry.get("path")))
        _fields(manifest,{"schema_version","id","version","title","source_id","statement","public_materials"},
                {"schema_version","id","version","title","source_id","statement","public_materials"},"issue manifest")
        if _key_ref(manifest, "issue") != key or manifest.get("schema_version") != 1:
            raise CatalogError(f"issue index/manifest mismatch for {key[0]}@{key[1]}")
        source_id = manifest.get("source_id")
        if source_id not in sources:
            raise CatalogError(f"issue {key[0]} references unknown source {source_id}")
        statement = resolve_relative((root / entry["path"]).parent, manifest.get("statement"))
        if statement.stat().st_size > 256 * 1024:
            raise CatalogError(f"statement is too large for issue {key[0]}")
        materials = manifest.get("public_materials")
        if not isinstance(materials, list) or not materials or len(set(materials))!=len(materials):
            raise CatalogError(f"issue {key[0]} must list its public materials")
        basenames=[]
        for material in materials:
            path = resolve_relative((root / entry["path"]).parent, material)
            if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
                raise CatalogError(f"invalid public material for issue {key[0]}")
            basenames.append(path.name)
        if len(set(basenames))!=len(basenames):
            raise CatalogError(f"issue {key[0]} has public materials with colliding filenames")
        _check_public_fields(manifest)
        issue_manifests[key] = manifest

    suite_manifests: dict[tuple[str, str], dict[str, Any]] = {}
    for key, entry in suite_index.items():
        manifest = _read_json(resolve_relative(root, entry.get("path")))
        _fields(manifest,{"schema_version","id","version","title","source_ids","group_ids","checkpoints"},
                {"schema_version","id","version","title","source_ids","group_ids","legacy_task_kind","checkpoints","support_files"},"suite manifest")
        if _key_ref(manifest, "suite") != key or manifest.get("schema_version") != 1:
            raise CatalogError(f"suite index/manifest mismatch for {key[0]}@{key[1]}")
        support_files = manifest.get("support_files", [])
        if (not isinstance(support_files, list) or any(not isinstance(value, str) for value in support_files)
                or len(set(support_files)) != len(support_files)):
            raise CatalogError(f"suite {key[0]} support_files must be unique relative file paths")
        for value in support_files:
            if not resolve_relative(root, value).is_file():
                raise CatalogError(f"suite {key[0]} support file is not a regular file: {value}")
        if not isinstance(manifest.get("source_ids"), list) or not manifest["source_ids"]:
            raise CatalogError(f"suite {key[0]} must list compatible source ids")
        if any(source_id not in sources for source_id in manifest["source_ids"]):
            raise CatalogError(f"suite {key[0]} references an unknown source")
        if manifest.get("legacy_task_kind") is not None and manifest.get("legacy_task_kind") not in TRUSTED_TASK_KINDS:
            raise CatalogError(f"suite {key[0]} references an unregistered legacy suite kind")
        groups = manifest.get("group_ids")
        if not isinstance(groups,list) or len(set(groups)) != len(groups):
            raise CatalogError(f"suite {key[0]} must declare unique compatible groups")
        checkpoints = manifest.get("checkpoints")
        if not isinstance(checkpoints, list) or not checkpoints:
            raise CatalogError(f"suite {key[0]} must declare checkpoints")
        checkpoint_ids: set[str] = set()
        for checkpoint in checkpoints:
            if not isinstance(checkpoint, dict):
                raise CatalogError(f"suite {key[0]} has an invalid checkpoint")
            _fields(checkpoint,{"id","category","visibility","runner","case","oracle","timeout_seconds","required"},
                    {"id","issue_id","category","visibility","runner","case","oracle","timeout_seconds","required","runner_options"},"checkpoint")
            identity = checkpoint.get("id")
            if not isinstance(identity, str) or not identity.strip() or identity in checkpoint_ids:
                raise CatalogError(f"suite {key[0]} checkpoint ids must be unique")
            checkpoint_ids.add(identity)
            if checkpoint.get("category") not in ALLOWED_CHECK_CATEGORIES:
                raise CatalogError(f"invalid checkpoint category in suite {key[0]}")
            if checkpoint.get("visibility") not in ALLOWED_VISIBILITY:
                raise CatalogError(f"invalid checkpoint visibility in suite {key[0]}")
            if checkpoint.get("runner") not in TRUSTED_RUNNERS or checkpoint.get("oracle") not in TRUSTED_ORACLES:
                raise CatalogError(f"unregistered runner/oracle in suite {key[0]}")
            try:
                case_path=resolve_relative(root,checkpoint.get("case"))
            except (TypeError,CatalogError) as exc:
                raise CatalogError(f"checkpoint {identity} has an invalid case path") from exc
            if not case_path.is_file():
                raise CatalogError(f"checkpoint {identity} case must reference a regular file")
            options=checkpoint.get("runner_options",{})
            if not isinstance(options,dict):
                raise CatalogError(f"checkpoint {identity} runner_options must be an object")
            case_timeout=options.get("case_timeout_seconds",checkpoint["timeout_seconds"])
            if not isinstance(case_timeout,int) or not 1<=case_timeout<=checkpoint["timeout_seconds"]:
                raise CatalogError(f"checkpoint {identity} has an invalid runner timeout")
            if checkpoint["runner"] == "draw_case_v1":
                if "script" in options:
                    raise CatalogError(
                        f"checkpoint {identity} cannot set runner_options.script; "
                        "case is the only DRAW script path"
                    )
                _fields(options,set(),{"case_timeout_seconds","expected_assertion_ids","expected_failure_lines"},"DRAW runner options")
                assertion_ids=options.get('expected_assertion_ids')
                if assertion_ids is not None and (not isinstance(assertion_ids,list) or not assertion_ids or
                        any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+',x) for x in assertion_ids) or
                        len(set(assertion_ids))!=len(assertion_ids)):
                    raise CatalogError('expected_assertion_ids must be unique nonempty assertion names')
                failure_lines=options.get('expected_failure_lines',[])
                if not isinstance(failure_lines,list) or any(not isinstance(x,str) or not x.strip() or '\n' in x for x in failure_lines):
                    raise CatalogError('expected_failure_lines must contain nonempty single-line signatures')
                if failure_lines and not assertion_ids:
                    raise CatalogError('failure signatures require an assertion contract')
                if case_path.suffix.lower() not in {".tcl"}:
                    raise CatalogError(f"checkpoint {identity} DRAW case must be a Tcl script")
            else:
                _fields(options,set(),{"libraries","inputs","stdout_contains","case_timeout_seconds"},"C++ runner options")
                libraries=options.get("libraries",[])
                inputs=options.get("inputs",[])
                if (not isinstance(libraries,list) or not libraries or
                        any(not isinstance(x,str) or x not in TRUSTED_CPP_LIBRARIES for x in libraries)):
                    raise CatalogError(f"checkpoint {identity} uses an unregistered C++ library")
                if (not isinstance(inputs,list) or any(not isinstance(x,str) for x in inputs)):
                    raise CatalogError(f"checkpoint {identity} has invalid C++ input paths")
                markers=options.get("stdout_contains",["TEST_DONE"])
                if not isinstance(markers,list) or not markers or any(not isinstance(x,str) or not x or len(x)>500 for x in markers):
                    raise CatalogError(f"checkpoint {identity} has invalid output oracle markers")
                if case_path.suffix.lower() not in {".cpp",".cc",".cxx"}:
                    raise CatalogError(f"checkpoint {identity} C++ case must reference a source file")
                for input_path in inputs:
                    referenced=resolve_relative(root,input_path)
                    if not referenced.is_file():
                        raise CatalogError(f"checkpoint {identity} input must reference a regular file")
            if checkpoint["oracle"] == "draw_test_done_v1" and checkpoint["runner"] != "draw_case_v1":
                raise CatalogError(f"checkpoint {identity} has an incompatible runner/oracle pair")
            if checkpoint["oracle"] == "stdout_contains_v1" and checkpoint["runner"] != "cpp_case_v1":
                raise CatalogError(f"checkpoint {identity} has an incompatible runner/oracle pair")
            if not isinstance(checkpoint.get("required"), bool):
                raise CatalogError(f"checkpoint {identity} must declare required")
            timeout = checkpoint.get("timeout_seconds")
            if not isinstance(timeout, int) or not 1 <= timeout <= 3600:
                raise CatalogError(f"checkpoint {identity} has invalid timeout")
            issue_id = checkpoint.get("issue_id")
            issue_sources={issue["source_id"] for (known_id,_),issue in issue_manifests.items() if known_id==issue_id}
            if issue_id is not None and (not issue_sources or not issue_sources.intersection(manifest["source_ids"])):
                raise CatalogError(f"checkpoint {identity} references unknown issue {issue_id}")
        suite_manifests[key] = manifest

    group_manifests: dict[tuple[str, str], dict[str, Any]] = {}
    for key, entry in group_index.items():
        manifest = _read_json(resolve_relative(root, entry.get("path")))
        _fields(manifest,{"schema_version","id","version","title","kind","source_id","execution_mode","members","budget","required_outputs","evaluation_suite"},
                {"schema_version","id","version","title","kind","source_id","execution_mode","members","budget","required_outputs","evaluation_suite","has_hidden_checks"},"group manifest")
        if _key_ref(manifest, "group") != key or manifest.get("schema_version") != 1:
            raise CatalogError(f"group index/manifest mismatch for {key[0]}@{key[1]}")
        source_id = manifest.get("source_id")
        if source_id not in sources:
            raise CatalogError(f"group {key[0]} references unknown source")
        if manifest.get("kind") not in ALLOWED_GROUP_KINDS or manifest.get("execution_mode") not in ALLOWED_EXECUTION_MODES:
            raise CatalogError(f"invalid group kind or execution mode: {key[0]}")
        members = manifest.get("members")
        if not isinstance(members, list) or not members:
            raise CatalogError(f"group {key[0]} requires at least one member")
        if manifest.get("kind")=="single" and len(members)!=1:
            raise CatalogError(f"single task {key[0]} must contain exactly one issue")
        seen: set[tuple[str, str]] = set()
        for member in members:
            if not isinstance(member, dict):
                raise CatalogError(f"invalid member in group {key[0]}")
            _fields(member,{"issue_id","issue_version"},{"issue_id","issue_version"},"group member")
            member_key = (member.get("issue_id"), member.get("issue_version"))
            if member_key in seen:
                raise CatalogError(f"duplicate issue member in group {key[0]}")
            seen.add(member_key)
            issue = issue_manifests.get(member_key)
            if issue is None or issue.get("source_id") != source_id:
                raise CatalogError(f"bad issue reference or mixed baseline in group {key[0]}")
        budget = manifest.get("budget")
        if not isinstance(budget, dict) or budget.get("scope") != "group":
            raise CatalogError(f"group {key[0]} must declare a group-scoped budget")
        seconds = budget.get("wall_seconds")
        if not isinstance(seconds, int) or not 1 <= seconds <= 7 * 24 * 3600:
            raise CatalogError(f"group {key[0]} has an invalid wall-clock budget")
        outputs = manifest.get("required_outputs")
        if (not isinstance(outputs, list) or not outputs or len(set(outputs))!=len(outputs) or
                any(x not in {"patch.diff","report.md","findings.jsonl"} for x in outputs)):
            raise CatalogError(f"group {key[0]} must declare required outputs")
        if manifest.get("kind")=="active" and "findings.jsonl" not in outputs:
            raise CatalogError(f"active task {key[0]} must declare findings.jsonl")
        suite_ref = manifest.get("evaluation_suite")
        if not isinstance(suite_ref,dict):
            raise CatalogError(f"group {key[0]} must select an evaluation suite")
        _fields(suite_ref,{"id","version"},{"id","version"},"evaluation suite reference")
        suite_key = (suite_ref.get("id"), suite_ref.get("version"))
        suite = suite_manifests.get(suite_key)
        if suite is None or source_id not in suite.get("source_ids", []):
            raise CatalogError(f"group {key[0]} references an incompatible evaluation suite")
        if key[0] not in suite.get("group_ids", []):
            raise CatalogError(f"suite {suite_key[0]} does not declare compatibility with group {key[0]}")
        has_hidden=any(item.get("visibility")=="hidden" for item in suite.get("checkpoints",[]))
        if "has_hidden_checks" in manifest and manifest["has_hidden_checks"] is not has_hidden:
            raise CatalogError(f"group {key[0]} has_hidden_checks disagrees with its evaluation suite")
        if manifest.get("execution_mode") == "joint" and len({issue_manifests[m]["source_id"] for m in seen}) != 1:
            raise CatalogError(f"joint group {key[0]} mixes source baselines")
        public_issue_ids={item[0] for item in seen}
        for checkpoint in suite.get("checkpoints",[]):
            issue_id=checkpoint.get("issue_id")
            if checkpoint.get("visibility")=="public" and issue_id is not None and issue_id not in public_issue_ids:
                raise CatalogError(f"suite {suite_key[0]} has a public checkpoint outside compatible group {key[0]}")
        group_manifests[key] = manifest

    known_group_ids={key[0] for key in group_manifests}
    for (suite_id,_),suite in suite_manifests.items():
        if any(group_id not in known_group_ids for group_id in suite["group_ids"]):
            raise CatalogError(f"suite {suite_id} references an unknown group")

    return {"root": root, "sources": sources, "issues": issue_manifests,
            "groups": group_manifests, "suites": suite_manifests,
            "counts": {"issues": len(issue_entries), "groups": len(group_entries),
                       "evaluation_suites": len(suite_entries)}}


def public_task(bundle: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    """Convert one validated group manifest to the older public API shape."""
    source = bundle["sources"][group["source_id"]]
    issue_cards = []
    for member in group["members"]:
        issue = bundle["issues"][(member["issue_id"], member["issue_version"])]
        statement_path = resolve_relative((bundle["root"] / next(
            entry["path"] for entry in _read_json(bundle["root"] / "catalog.json")["issues"]
            if entry["id"] == member["issue_id"] and entry["version"] == member["issue_version"]
        )).parent, issue["statement"])
        body = statement_path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = issue.get("title") or (title_match.group(1).strip() if title_match else member["issue_id"])
        clean_body = re.sub(r"(?is)\s*Upstream relation:.*$", "", body).strip()
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", clean_body) if part.strip()]
        summary = next((re.sub(r"\s+", " ", part).strip() for part in paragraphs
                        if not part.startswith("#") and not part.startswith("```")), "")
        number = member["issue_id"].removeprefix("occt-") if member["issue_id"].startswith("occt-") else None
        issue_cards.append({"id": member["issue_id"], "version": member["issue_version"],
                            "title": title, "visibility": "public", "number": number,
                            "summary": summary, "body": clean_body})
    seconds = group["budget"]["wall_seconds"]
    required = [Path(name).stem if Path(name).suffix else name for name in group["required_outputs"]]
    suite = group["evaluation_suite"]
    catalog=_read_json(bundle["root"] / "catalog.json")
    referenced=[]
    group_ref=next(item for item in catalog["groups"] if (item["id"],item["version"])==(group["id"],group["version"]))
    suite_ref=next(item for item in catalog["evaluation_suites"] if (item["id"],item["version"])==(suite["id"],suite["version"]))
    referenced.extend([resolve_relative(bundle["root"],group_ref["path"]),resolve_relative(bundle["root"],suite_ref["path"])])
    for member in group["members"]:
        issue_ref=next(item for item in catalog["issues"] if (item["id"],item["version"])==(member["issue_id"],member["issue_version"]))
        issue_path=resolve_relative(bundle["root"],issue_ref["path"])
        issue=bundle["issues"][(member["issue_id"],member["issue_version"])]
        referenced.extend([issue_path,resolve_relative(issue_path.parent,issue["statement"])])
        referenced.extend(resolve_relative(issue_path.parent,material) for material in issue["public_materials"])
    toolchain_path=resolve_relative(bundle["root"],f"toolchains/{source['toolchain']}.json")
    referenced.append(toolchain_path)
    content=hashlib.sha256()
    for path in sorted(set(referenced),key=lambda item:item.relative_to(bundle["root"]).as_posix()):
        relative=path.relative_to(bundle["root"]).as_posix()
        content.update(relative.encode("utf-8")+b"\0"+hashlib.sha256(path.read_bytes()).digest())
    source_bytes=json.dumps(source,ensure_ascii=False,sort_keys=True).encode("utf-8")
    content.update(b"source-lock-entry\0"+hashlib.sha256(source_bytes).digest())
    return {"id": group["id"], "version": group["version"], "title": group["title"],
            "kind": group["kind"], "source_id": group["source_id"],
            "base_commit": source["commit"], "issues": issue_cards,
            "budget": {"scope": "group", "wall_seconds": seconds,
                       "wall_clock_minutes": math.ceil(seconds / 60)},
            "has_hidden_checks": any(item.get("visibility")=="hidden" for item in bundle["suites"][(suite["id"],suite["version"])].get("checkpoints",[])),
            "execution_mode": group["execution_mode"], "required_output": required,
            "evaluation_suite": dict(suite), "tags": ["OCCT", "共享题库"],
            "description": "题目与评测版本由清单固定；检查详情保留在监督端。",
            "source_hash": content.hexdigest(),
            "discovery_quality_scored": False}


def import_public_tasks(bundle_root: Path | str):
    """Validate and register public groups. Imports do not access evaluator cases."""
    from .register import register

    bundle = validate_bundle(bundle_root)
    catalog = _read_json(bundle["root"] / "catalog.json")
    imported = 0
    for entry in catalog["groups"]:
        group = bundle["groups"][(entry["id"], entry["version"])]
        register(public_task(bundle, group))
        imported += 1
    return imported, bundle["counts"]


def main() -> None:
    import argparse
    parser=argparse.ArgumentParser(description="Read-only benchmark catalog validation")
    parser.add_argument("--root",type=Path,help="bundle root; defaults to configured BENCHMARK_ROOT")
    parser.add_argument("--json",action="store_true",help="print a JSON summary")
    args=parser.parse_args()
    if args.root is None:
        from .settings import SETTINGS
        root=SETTINGS.benchmark_root
    else:
        root=args.root
    bundle=validate_bundle(root)
    result={"ok":True,"root":str(bundle["root"]),**bundle["counts"],
            "sources":{key:{"commit":value["commit"],"verification_status":value["verification_status"]}
                       for key,value in bundle["sources"].items()}}
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else
          f"Valid catalog: issues={result['issues']}, groups={result['groups']}, suites={result['evaluation_suites']}")


if __name__=="__main__":
    main()
