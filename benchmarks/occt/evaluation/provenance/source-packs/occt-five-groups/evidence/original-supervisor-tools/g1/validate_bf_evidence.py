#!/usr/bin/env python3
"""Validate private natural-history B/F evidence identities and records.

This tool verifies hashes and recorded outcomes. It does not run OCCT, replay an
oracle, or decide whether a runner/oracle is trustworthy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


HASH_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
EXCLUDED_NAMES = {".git", "__pycache__", "CMakeFiles", "build"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
CATEGORIES = {"original", "neighborhood", "regression"}


class ValidationError(Exception):
    """Evidence is incomplete, inconsistent, or fails the declared matrix."""


def _fail(message: str) -> None:
    raise ValidationError(message)


def _is_hex_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_RE.fullmatch(value) is not None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _need_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _need_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{label} must be an array")
    return value


def _need_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")
    return value


def _need_sha256(value: Any, label: str) -> str:
    if not _is_hex_hash(value):
        _fail(f"{label} must be a lowercase 64-character SHA-256")
    return value


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read {label} JSON at {path}: {exc}")
    return _need_dict(value, label)


def _safe_artifact(base: Path, raw_path: Any, label: str) -> tuple[Path, str]:
    """Resolve a non-symlink sidecar-relative regular file."""
    raw = _need_text(raw_path, f"{label}.path")
    if "\\" in raw:
        _fail(f"{label}.path must use relative POSIX separators")
    parts = raw.split("/")
    if raw.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        _fail(f"{label}.path must stay inside the sidecar and contain no dot segments")
    cursor = base
    for part in parts:
        cursor = cursor / part
        try:
            mode = cursor.lstat().st_mode
        except OSError as exc:
            _fail(f"missing {label} file {raw}: {exc}")
        if stat.S_ISLNK(mode):
            _fail(f"{label}.path must not traverse symlinks: {raw}")
    if not stat.S_ISREG(cursor.lstat().st_mode):
        _fail(f"{label}.path is not a regular file: {raw}")
    return cursor, raw


def _verify_file_hash(base: Path, item: Any, label: str) -> tuple[str, Path]:
    entry = _need_dict(item, label)
    path, relative = _safe_artifact(base, entry.get("path"), label)
    expected = _need_sha256(entry.get("sha256"), f"{label}.sha256")
    actual = _sha256_file(path)
    if actual != expected:
        _fail(f"{label} SHA-256 mismatch for {relative}: expected {expected}, got {actual}")
    return actual, path


def _is_excluded(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return bool(set(parts) & EXCLUDED_NAMES) or Path(relative).suffix in EXCLUDED_SUFFIXES


def tree_sha256(root: Path | str) -> str:
    """Match agent_bench_web's agent-bench-tree-sha256-v1 source hash."""
    root = Path(root).resolve(strict=True)
    digest = hashlib.sha256()
    paths = sorted(
        root.rglob("*"),
        key=lambda path: path.relative_to(root).as_posix().encode("utf-8"),
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if _is_excluded(relative):
            continue
        info = path.lstat()
        mode = info.st_mode
        if stat.S_ISDIR(mode):
            continue
        if stat.S_ISLNK(mode):
            target = os.readlink(path)
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                _fail(f"source symlink escapes archived tree: {relative}")
            kind, data = b"L", target.encode("utf-8")
            size = len(data)
        elif stat.S_ISREG(mode):
            kind, data = b"F", None
            size = info.st_size
        else:
            _fail(f"unsupported source file type in archived tree: {relative}")
        executable = b"1" if mode & 0o111 else b"0"
        digest.update(
            relative.encode("utf-8") + b"\0" + kind + b"\0" + executable + b"\0"
            + str(size).encode("ascii") + b"\0"
        )
        if kind == b"L":
            digest.update(data)
        else:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def _safe_extract_archive(archive: Path, destination: Path) -> None:
    destination.mkdir()
    with tarfile.open(archive, "r:") as bundle:
        for item in bundle:
            relative = PurePosixPath(item.name)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                _fail(f"unsafe path in Git archive: {item.name}")
            target = destination.joinpath(*relative.parts)
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.issym():
                if PurePosixPath(item.linkname).is_absolute():
                    _fail(f"absolute symlink in Git archive: {item.name}")
                resolved = (target.parent / item.linkname).resolve()
                try:
                    resolved.relative_to(destination.resolve())
                except ValueError:
                    _fail(f"escaping symlink in Git archive: {item.name}")
                target.symlink_to(item.linkname)
                continue
            if not item.isfile():
                _fail(f"unsupported entry in Git archive: {item.name}")
            stream = bundle.extractfile(item)
            if stream is None:
                _fail(f"unreadable entry in Git archive: {item.name}")
            with stream, target.open("wb") as output:
                shutil.copyfileobj(stream, output)
            target.chmod(item.mode & 0o777)


def _git(repo: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        _fail(f"cannot execute git: {exc}")
    if result.returncode and not allow_failure:
        detail = result.stderr.strip() or result.stdout.strip()
        _fail(f"git {' '.join(args)} failed in {repo}: {detail}")
    return result


def _repo_path(base: Path, raw: Any, label: str) -> Path:
    value = _need_text(raw, f"{label}.repository")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        _fail(f"cannot resolve {label}.repository {value}: {exc}")
    if not resolved.is_dir():
        _fail(f"{label}.repository is not a directory: {resolved}")
    return resolved


def _materialized_git_tree_sha256(repo: Path, commit: str) -> str:
    """Hash exactly the Git archive source tree used by the shared source cache."""
    with tempfile.TemporaryDirectory(prefix="bf-evidence-archive-") as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / "source.tar"
        exported = temporary_path / "source"
        try:
            with archive.open("wb") as stream:
                result = subprocess.run(
                    ["git", "-C", str(repo), "archive", "--format=tar", commit],
                    check=False,
                    stdout=stream,
                    stderr=subprocess.PIPE,
                    text=False,
                )
        except OSError as exc:
            _fail(f"cannot create read-only Git archive for {commit}: {exc}")
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            _fail(f"git archive failed for {commit}: {detail}")
        try:
            _safe_extract_archive(archive, exported)
            return tree_sha256(exported)
        except (OSError, tarfile.TarError) as exc:
            _fail(f"cannot verify archived source tree for {commit}: {exc}")


def _verify_sources(base: Path, manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    sources = _need_dict(manifest.get("sources"), "sources")
    if set(sources) != {"B", "F"}:
        _fail("sources must contain exactly B and F")
    identities: dict[str, dict[str, str]] = {}
    repositories: dict[str, Path] = {}
    repository_tops: dict[str, Path] = {}
    for role in ("B", "F"):
        source = _need_dict(sources[role], f"sources.{role}")
        repo = _repo_path(base, source.get("repository"), f"sources.{role}")
        commit = _need_text(source.get("commit"), f"sources.{role}.commit").lower()
        git_tree = _need_text(source.get("git_tree"), f"sources.{role}.git_tree").lower()
        materialized = _need_sha256(
            source.get("materialized_tree_sha256"), f"sources.{role}.materialized_tree_sha256"
        )
        if not GIT_OBJECT_RE.fullmatch(commit):
            _fail(f"sources.{role}.commit must be a full Git object ID")
        if not GIT_OBJECT_RE.fullmatch(git_tree):
            _fail(f"sources.{role}.git_tree must be a full Git object ID")
        actual_commit = _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").stdout.strip().lower()
        if actual_commit != commit:
            _fail(f"sources.{role}.commit does not resolve to the declared full commit")
        actual_tree = _git(repo, "rev-parse", "--verify", f"{commit}^{{tree}}").stdout.strip().lower()
        if actual_tree != git_tree:
            _fail(f"sources.{role} Git tree mismatch: expected {git_tree}, got {actual_tree}")
        actual_materialized = _materialized_git_tree_sha256(repo, commit)
        if actual_materialized != materialized:
            _fail(
                f"sources.{role} materialized source tree mismatch: expected {materialized}, "
                f"got {actual_materialized}"
            )
        top = Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
        repositories[role] = repo
        repository_tops[role] = top
        identities[role] = {
            "commit": commit,
            "git_tree": git_tree,
            "materialized_tree_sha256": materialized,
        }
    if repository_tops["B"] != repository_tops["F"]:
        _fail("B and F must be verified from the same Git repository")
    if identities["B"]["commit"] == identities["F"]["commit"]:
        _fail("B and F must be different commits; F must be a strict descendant")
    ancestry = _git(
        repositories["F"],
        "merge-base",
        "--is-ancestor",
        identities["B"]["commit"],
        identities["F"]["commit"],
        allow_failure=True,
    )
    if ancestry.returncode != 0:
        _fail("B commit is not an ancestor of F commit")
    return identities


def _canonical_inputs_sha256(inputs: list[dict[str, str]]) -> str:
    normalized = sorted(inputs, key=lambda item: item["path"].encode("utf-8"))
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _process_exit_mapping(value: Any, label: str) -> dict[str, str]:
    mapping = _need_dict(value, label)
    if not mapping:
        _fail(f"{label} must explicitly map at least one process return code")
    normalized: dict[str, str] = {}
    for raw_code, raw_state in mapping.items():
        if not isinstance(raw_code, str):
            _fail(f"{label} keys must be decimal process return-code strings")
        try:
            code = int(raw_code)
        except ValueError:
            _fail(f"{label} has invalid process return code {raw_code!r}")
        if str(code) != raw_code:
            _fail(f"{label} process return codes must use canonical decimal spelling")
        state = _need_text(raw_state, f"{label}[{raw_code}]")
        if state not in {"completed", "runtime_error", "timeout"}:
            _fail(f"{label}[{raw_code}] must map to completed, runtime_error, or timeout")
        normalized[raw_code] = state
    return dict(sorted(normalized.items(), key=lambda item: int(item[0])))


def _verify_members_and_cases(
    base: Path, manifest: dict[str, Any], mode: str
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], str]:
    raw_members = _need_list(manifest.get("members"), "members")
    if not raw_members:
        _fail("members must not be empty")
    members: dict[str, dict[str, Any]] = {}
    issue_keys: set[tuple[str, str]] = set()
    for index, raw in enumerate(raw_members):
        member = _need_dict(raw, f"members[{index}]")
        canonical_id = _need_text(member.get("canonical_id"), f"members[{index}].canonical_id")
        issue_id = _need_text(member.get("issue_id"), f"members[{index}].issue_id")
        issue_version = _need_text(member.get("issue_version"), f"members[{index}].issue_version")
        if canonical_id in members:
            _fail(f"duplicate canonical member: {canonical_id}")
        issue_key = (issue_id, issue_version)
        if issue_key in issue_keys:
            _fail(f"duplicate issue_id/issue_version member: {issue_id}/{issue_version}")
        members[canonical_id] = {
            "canonical_id": canonical_id,
            "issue_id": issue_id,
            "issue_version": issue_version,
        }
        issue_keys.add(issue_key)
    if mode == "formal" and not 3 <= len(members) <= 5:
        _fail("formal mode requires 3-5 distinct canonical members")

    build_config = _need_dict(manifest.get("build_config"), "build_config")
    _need_text(build_config.get("id"), "build_config.id")
    config_hash, _ = _verify_file_hash(base, build_config, "build_config")
    cases: dict[str, dict[str, Any]] = {}
    runner_specs: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {}
    for index, raw in enumerate(_need_list(manifest.get("cases"), "cases")):
        case = _need_dict(raw, f"cases[{index}]")
        case_id = _need_text(case.get("case_id"), f"cases[{index}].case_id")
        if case_id in cases:
            _fail(f"duplicate case_id: {case_id}")
        canonical_id = _need_text(case.get("canonical_id"), f"cases[{index}].canonical_id")
        if canonical_id not in members:
            _fail(f"case {case_id} references unknown canonical member {canonical_id}")
        member = members[canonical_id]
        issue_id = _need_text(case.get("issue_id"), f"cases[{index}].issue_id")
        issue_version = _need_text(case.get("issue_version"), f"cases[{index}].issue_version")
        if issue_id != member["issue_id"] or issue_version != member["issue_version"]:
            _fail(f"case {case_id} issue mapping differs from canonical member {canonical_id}")
        category = _need_text(case.get("category"), f"cases[{index}].category")
        if category not in CATEGORIES:
            _fail(f"case {case_id} has unsupported category {category}")
        visibility = _need_text(case.get("visibility"), f"cases[{index}].visibility")
        expected_visibility = "public" if category == "original" else "hidden"
        if visibility != expected_visibility:
            _fail(f"case {case_id} {category} visibility must be {expected_visibility}")
        if mode == "candidate_originals" and category != "original":
            _fail("candidate_originals mode may contain only original cases")

        input_entries: list[dict[str, str]] = []
        input_seen: set[str] = set()
        for input_index, raw_input in enumerate(_need_list(case.get("inputs"), f"case {case_id}.inputs")):
            input_item = _need_dict(raw_input, f"case {case_id}.inputs[{input_index}]")
            path, relative = _safe_artifact(base, input_item.get("path"), f"case {case_id} input")
            expected = _need_sha256(input_item.get("sha256"), f"case {case_id} input.sha256")
            actual = _sha256_file(path)
            if actual != expected:
                _fail(f"case {case_id} input SHA-256 mismatch for {relative}: expected {expected}, got {actual}")
            if relative in input_seen:
                _fail(f"case {case_id} repeats input path {relative}")
            input_seen.add(relative)
            input_entries.append({"path": relative, "sha256": actual})
        if not input_entries:
            _fail(f"case {case_id} must have at least one hashed input")
        inputs_hash = _canonical_inputs_sha256(input_entries)

        oracle = _need_dict(case.get("oracle"), f"case {case_id}.oracle")
        oracle_id = _need_text(oracle.get("id"), f"case {case_id}.oracle.id")
        oracle_hash, _ = _verify_file_hash(base, oracle, f"case {case_id} oracle")
        check_ids = [_need_text(item, f"case {case_id}.oracle.check_ids[]") for item in _need_list(
            oracle.get("check_ids"), f"case {case_id}.oracle.check_ids"
        )]
        if not check_ids or len(set(check_ids)) != len(check_ids):
            _fail(f"case {case_id} oracle.check_ids must be non-empty and unique")

        runner = _need_dict(case.get("runner"), f"case {case_id}.runner")
        runner_id = _need_text(runner.get("id"), f"case {case_id}.runner.id")
        runner_hash, _ = _verify_file_hash(base, runner, f"case {case_id} runner")
        exit_mapping = _process_exit_mapping(
            runner.get("process_exit_mapping"), f"case {case_id}.runner.process_exit_mapping"
        )
        mapping_key = tuple(exit_mapping.items())
        prior_spec = runner_specs.get(runner_id)
        current_spec = (runner_hash, mapping_key)
        if prior_spec is not None and prior_spec != current_spec:
            _fail(f"runner {runner_id} has inconsistent hash or process-exit mapping across cases")
        runner_specs[runner_id] = current_spec
        cases[case_id] = {
            "case_id": case_id,
            "canonical_id": canonical_id,
            "issue_id": issue_id,
            "issue_version": issue_version,
            "category": category,
            "visibility": visibility,
            "inputs_sha256": inputs_hash,
            "oracle_id": oracle_id,
            "oracle_sha256": oracle_hash,
            "check_ids": check_ids,
            "runner_id": runner_id,
            "runner_sha256": runner_hash,
            "runner_process_exit_mapping": exit_mapping,
        }

    if not cases:
        _fail("cases must not be empty")
    for canonical_id in members:
        member_cases = [case for case in cases.values() if case["canonical_id"] == canonical_id]
        categories = {case["category"] for case in member_cases}
        required = {"original"} if mode == "candidate_originals" else CATEGORIES
        missing = sorted(required - categories)
        if missing:
            _fail(f"member {canonical_id} is missing required case categories: {', '.join(missing)}")
    return members, cases, config_hash


def _expected_run_keys(cases: dict[str, dict[str, Any]], mode: str) -> set[tuple[str, str]]:
    expected: set[tuple[str, str]] = set()
    for case_id, case in cases.items():
        category = case["category"]
        if category == "original" or category == "regression":
            expected.add(("B", case_id))
            expected.add(("F", case_id))
        elif category == "neighborhood":
            if mode != "formal":
                _fail("neighborhood cases require formal mode")
            expected.add(("F", case_id))
    return expected


def _verify_execution_record(
    record: dict[str, Any],
    run: dict[str, Any],
    case: dict[str, Any],
    source: dict[str, str],
    config_hash: str,
    log_hash: str,
) -> str:
    expected_fields = {
        "format_version": 1,
        "source": run["source"],
        "case_id": case["case_id"],
        "canonical_id": case["canonical_id"],
        "issue_id": case["issue_id"],
        "issue_version": case["issue_version"],
        "category": case["category"],
        "source_commit": source["commit"],
        "source_tree_sha256": source["materialized_tree_sha256"],
        "inputs_sha256": case["inputs_sha256"],
        "oracle_sha256": case["oracle_sha256"],
        "runner_sha256": case["runner_sha256"],
        "runner_process_exit_mapping": case["runner_process_exit_mapping"],
        "build_config_sha256": config_hash,
        "log_sha256": log_hash,
    }
    for key, expected in expected_fields.items():
        if record.get(key) != expected:
            _fail(f"execution record {case['case_id']} {key} mismatch")

    execution = _need_dict(record.get("execution"), f"execution record {case['case_id']}.execution")
    execution_status = _need_text(
        execution.get("status"), f"execution record {case['case_id']}.execution.status"
    )
    if execution_status not in {"completed", "not_run", "timeout", "runtime_error"}:
        _fail(f"{case['case_id']} has unsupported execution status {execution_status}")
    oracle_ran = execution.get("oracle_ran")
    if not isinstance(oracle_ran, bool):
        _fail(f"{case['case_id']} execution.oracle_ran must be boolean")
    process_return_code = execution.get("process_return_code")
    if process_return_code is not None and (
        not isinstance(process_return_code, int) or isinstance(process_return_code, bool)
    ):
        _fail(f"{case['case_id']} execution.process_return_code must be an integer or null")
    signal = execution.get("signal")
    if signal is not None and (
        not isinstance(signal, int) or isinstance(signal, bool) or signal <= 0
    ):
        _fail(f"{case['case_id']} execution.signal must be a positive integer or null")
    timeout_seconds = execution.get("timeout_seconds")
    if timeout_seconds is not None and (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        _fail(f"{case['case_id']} execution.timeout_seconds must be positive or null")

    exit_mapping = case["runner_process_exit_mapping"]
    if process_return_code is not None:
        mapped_status = exit_mapping.get(str(process_return_code))
        if mapped_status != execution_status:
            _fail(
                f"{case['case_id']} process return code {process_return_code} is not mapped by the locked runner "
                f"to execution status {execution_status}"
            )
        if process_return_code < 0 and (
            execution_status == "completed" or signal != -process_return_code
        ):
            _fail(f"{case['case_id']} signal-terminated process cannot be a completed geometry run")
    if execution_status == "completed":
        if process_return_code is None:
            _fail(f"{case['case_id']} completed execution requires process_return_code")
        if signal is not None or timeout_seconds is not None:
            _fail(f"{case['case_id']} completed execution cannot have signal or timeout metadata")
        if oracle_ran is not True:
            _fail(f"{case['case_id']} completed execution requires oracle_ran=true")
    else:
        if oracle_ran is not False:
            _fail(f"{case['case_id']} incomplete execution requires oracle_ran=false")
        if execution_status == "not_run" and (
            process_return_code is not None or signal is not None or timeout_seconds is not None
        ):
            _fail(f"{case['case_id']} not_run execution cannot have process, signal, or timeout results")
        if execution_status == "timeout" and timeout_seconds is None:
            _fail(f"{case['case_id']} timeout execution requires timeout_seconds")
        if execution_status == "runtime_error" and process_return_code is None and signal is None:
            _fail(f"{case['case_id']} runtime_error requires a process return code or signal")
        if execution_status != "timeout" and timeout_seconds is not None:
            _fail(f"{case['case_id']} timeout_seconds is only valid for timeout execution")
        oracle = _need_dict(record.get("oracle"), f"execution record {case['case_id']}.oracle")
        if oracle.get("status") != "not_run" or oracle.get("checks") != []:
            _fail(f"{case['case_id']} incomplete execution cannot claim a geometry oracle result")
        _fail(f"{case['case_id']} execution status {execution_status} cannot count as a geometric result")

    build = _need_dict(record.get("build"), f"execution record {case['case_id']}.build")
    oracle = _need_dict(record.get("oracle"), f"execution record {case['case_id']}.oracle")
    oracle_status = _need_text(oracle.get("status"), f"execution record {case['case_id']}.oracle.status")
    build_status = build.get("status")
    return_code = build.get("return_code")
    if build_status != "passed" or not isinstance(return_code, int) or isinstance(return_code, bool) or return_code != 0:
        if oracle_status == "geometry_fail":
            _fail(f"{case['case_id']} build failure cannot count as geometric failure")
        _fail(f"{case['case_id']} has no successful build; geometry outcome is unusable")

    checks = _need_list(oracle.get("checks"), f"execution record {case['case_id']}.oracle.checks")
    check_results: dict[str, bool] = {}
    for index, raw_check in enumerate(checks):
        check = _need_dict(raw_check, f"execution record {case['case_id']}.oracle.checks[{index}]")
        check_id = _need_text(check.get("id"), f"execution record {case['case_id']} check.id")
        passed = check.get("passed")
        if not isinstance(passed, bool):
            _fail(f"execution record {case['case_id']} check {check_id} passed must be boolean")
        if check_id in check_results:
            _fail(f"execution record {case['case_id']} repeats oracle check {check_id}")
        check_results[check_id] = passed
    if set(check_results) != set(case["check_ids"]):
        _fail(f"execution record {case['case_id']} oracle check IDs differ from the locked oracle")
    derived_status = "geometry_pass" if all(check_results.values()) else "geometry_fail"
    if oracle_status != derived_status:
        _fail(f"execution record {case['case_id']} oracle status disagrees with its check results")
    if oracle_status not in {"geometry_pass", "geometry_fail"}:
        _fail(f"{case['case_id']} outcome is not a reproduced geometric pass/fail")
    return oracle_status


def _verify_runs(
    base: Path,
    manifest: dict[str, Any],
    mode: str,
    members: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, str]],
    config_hash: str,
) -> tuple[int, set[tuple[str, str, tuple[tuple[str, str], ...]]]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    run_entries = _need_list(manifest.get("runs"), "runs")
    for index, raw in enumerate(run_entries):
        run = _need_dict(raw, f"runs[{index}]")
        source_role = _need_text(run.get("source"), f"runs[{index}].source")
        if source_role not in {"B", "F"}:
            _fail(f"runs[{index}].source must be B or F")
        case_id = _need_text(run.get("case_id"), f"runs[{index}].case_id")
        if case_id not in cases:
            _fail(f"run references unknown case_id {case_id}")
        key = (source_role, case_id)
        if key in records:
            _fail(f"duplicate run record for {source_role}/{case_id}")
        records[key] = run

    expected_keys = _expected_run_keys(cases, mode)
    actual_keys = set(records)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing:
        _fail("missing required run records: " + ", ".join(f"{source}/{case_id}" for source, case_id in missing))
    if extra:
        _fail("unexpected run records: " + ", ".join(f"{source}/{case_id}" for source, case_id in extra))

    outcomes: dict[tuple[str, str], str] = {}
    used_runners: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
    for (source_role, case_id), run in records.items():
        case = cases[case_id]
        source = sources[source_role]
        expected_run_fields = {
            "source_commit": source["commit"],
            "source_tree_sha256": source["materialized_tree_sha256"],
            "inputs_sha256": case["inputs_sha256"],
            "oracle_sha256": case["oracle_sha256"],
            "runner_sha256": case["runner_sha256"],
            "runner_process_exit_mapping": case["runner_process_exit_mapping"],
            "build_config_sha256": config_hash,
        }
        for field, expected in expected_run_fields.items():
            if run.get(field) != expected:
                _fail(f"run {source_role}/{case_id} {field} differs from the verified identity")

        log_hash, _ = _verify_file_hash(base, run.get("log"), f"run {source_role}/{case_id} log")
        record_hash, record_path = _verify_file_hash(
            base,
            run.get("execution_record"),
            f"run {source_role}/{case_id} execution_record",
        )
        execution_record = _load_json(record_path, f"run {source_role}/{case_id} execution record")
        outcome = _verify_execution_record(
            execution_record, run, case, source, config_hash, log_hash
        )
        outcomes[(source_role, case_id)] = outcome
        used_runners.add((
            case["runner_id"],
            case["runner_sha256"],
            tuple(case["runner_process_exit_mapping"].items()),
        ))

    # The matrix outcome rules are deliberately separate from identity checking.
    for case_id, case in cases.items():
        category = case["category"]
        if category == "original":
            if outcomes[("B", case_id)] != "geometry_fail":
                _fail(f"B original defect was not reproduced geometrically: {case_id}")
            if outcomes[("F", case_id)] != "geometry_pass":
                _fail(f"F original did not pass: {case_id}")
        elif category == "neighborhood":
            if outcomes[("F", case_id)] != "geometry_pass":
                _fail(f"F neighborhood case did not pass: {case_id}")
        elif category == "regression":
            if outcomes[("B", case_id)] != "geometry_pass":
                _fail(f"B regression case did not pass: {case_id}")
            if outcomes[("F", case_id)] != "geometry_pass":
                _fail(f"F regression case did not pass: {case_id}")
    return len(records), used_runners


def _verify_acceptance_lock(
    manifest_path: Path,
    acceptance_path: Path | None,
    mode: str,
    used_runners: set[tuple[str, str, tuple[tuple[str, str], ...]]],
) -> bool:
    if acceptance_path is None:
        if mode == "formal":
            _fail("formal mode requires --acceptance-manifest to lock the sidecar and trusted runners")
        return False
    try:
        acceptance_path = acceptance_path.resolve(strict=True)
    except OSError as exc:
        _fail(f"cannot resolve acceptance manifest: {exc}")
    acceptance = _load_json(acceptance_path, "acceptance manifest")
    lock = _need_dict(acceptance.get("bf_evidence"), "acceptance manifest.bf_evidence")
    lock_path, lock_relative = _safe_artifact(
        acceptance_path.parent, lock.get("path"), "acceptance manifest bf_evidence"
    )
    if lock_path.resolve() != manifest_path.resolve():
        _fail(f"acceptance manifest bf_evidence.path ({lock_relative}) is not the validated sidecar")
    expected_sidecar_hash = _need_sha256(lock.get("sha256"), "acceptance manifest bf_evidence.sha256")
    actual_sidecar_hash = _sha256_file(manifest_path)
    if actual_sidecar_hash != expected_sidecar_hash:
        _fail("acceptance manifest sidecar SHA-256 mismatch")

    raw_trusted = _need_list(lock.get("trusted_runners"), "acceptance manifest bf_evidence.trusted_runners")
    trusted: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {}
    for index, raw in enumerate(raw_trusted):
        item = _need_dict(raw, f"trusted_runners[{index}]")
        runner_id = _need_text(item.get("id"), f"trusted_runners[{index}].id")
        runner_hash = _need_sha256(item.get("sha256"), f"trusted_runners[{index}].sha256")
        mapping = _process_exit_mapping(
            item.get("process_exit_mapping"), f"trusted_runners[{index}].process_exit_mapping"
        )
        trusted_spec = (runner_hash, tuple(mapping.items()))
        if runner_id in trusted and trusted[runner_id] != trusted_spec:
            _fail(f"acceptance manifest has conflicting identity or exit mapping for runner {runner_id}")
        trusted[runner_id] = trusted_spec
    for runner_id, runner_hash, mapping in used_runners:
        if trusted.get(runner_id) != (runner_hash, mapping):
            _fail(f"trusted runner lock missing or mismatched for {runner_id}, including process-exit mapping")
    return True


def validate(manifest_path: Path, acceptance_path: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = _load_json(manifest_path, "B/F evidence manifest")
    if manifest.get("example_only") is True:
        _fail("example_only manifest cannot be validated as evidence")
    version = manifest.get("format_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        _fail("format_version must be integer 1")
    mode = _need_text(manifest.get("mode"), "mode")
    if mode not in {"candidate_originals", "formal"}:
        _fail("mode must be candidate_originals or formal")
    candidate_id = _need_text(manifest.get("candidate_id"), "candidate_id")
    members, cases, config_hash = _verify_members_and_cases(
        manifest_path.parent, manifest, mode
    )
    source_identities = _verify_sources(manifest_path.parent, manifest)
    run_count, used_runners = _verify_runs(
        manifest_path.parent,
        manifest,
        mode,
        members,
        cases,
        source_identities,
        config_hash,
    )
    lock_verified = _verify_acceptance_lock(
        manifest_path, acceptance_path, mode, used_runners
    )
    report: dict[str, Any] = {
        "valid": True,
        "candidate_id": candidate_id,
        "mode": mode,
        "evidence_validation_passed": True,
        "member_count": len(members),
        "case_count": len(cases),
        "run_count": run_count,
        "B_commit": source_identities["B"]["commit"],
        "B_git_tree": source_identities["B"]["git_tree"],
        "B_materialized_tree_sha256": source_identities["B"]["materialized_tree_sha256"],
        "F_commit": source_identities["F"]["commit"],
        "F_git_tree": source_identities["F"]["git_tree"],
        "F_materialized_tree_sha256": source_identities["F"]["materialized_tree_sha256"],
        "B_is_strict_ancestor_of_F": True,
        "acceptance_lock_verified": lock_verified,
        "geometry_replayed": False,
        "oracle_authenticity_proven": False,
    }
    if mode == "candidate_originals":
        report.update({
            "candidate_original_matrix_valid": True,
            "formal_matrix_complete": False,
            "formal_acceptance": False,
        })
    else:
        report.update({
            "candidate_original_matrix_valid": True,
            "formal_matrix_complete": True,
            "formal_acceptance": "requires_human_review",
        })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="private B/F evidence sidecar JSON")
    parser.add_argument(
        "--acceptance-manifest",
        type=Path,
        help="delivery acceptance JSON that locks this sidecar and trusted runner hashes",
    )
    args = parser.parse_args(argv)
    try:
        report = validate(args.manifest, args.acceptance_manifest)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (ValidationError, OSError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
