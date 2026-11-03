"""Reconstruct a locked single-issue baseline from local upstream Git objects.

The command exports the exact natural commit. For a curator-derived baseline,
it applies the recorded inverse patch and restores the recorded commit object.
It performs no network access and publishes only a fully verified new directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRAMEWORK_ROOT))

from backend.source_cache import (  # noqa: E402
    _exclusive_lock,
    _safe_extract_git_archive,
    tree_sha256,
)


def git(repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repository), "-c", "core.autocrlf=false", *arguments],
        input=data,
    )


def reconstruct(bundle: Path, source_id: str, upstream: Path, destination: Path) -> dict:
    entries = json.loads((bundle / "sources.lock.json").read_text())["sources"]
    entry = next((item for item in entries if item["source_id"] == source_id), None)
    if entry is None or not source_id.startswith("occt-single20-"):
        raise ValueError("select a registered occt-single20 source identity")
    provenance_path = (bundle / entry["provenance"]).resolve(strict=True)
    if not provenance_path.is_relative_to(bundle):
        raise ValueError("source provenance escapes the benchmark bundle")
    provenance = json.loads(provenance_path.read_text())
    origin = provenance.get("origin_commit", entry["commit"])
    derived = origin != entry["commit"]
    origin_tree = git(upstream, "rev-parse", origin + "^{tree}").decode().strip()
    origin_object = git(upstream, "cat-file", "commit", origin)
    patch_path = provenance_path.parent / "inverse-source.patch"
    commit_path = provenance_path.parent / "derived-commit.txt"
    if derived and (not patch_path.is_file() or not commit_path.is_file()):
        raise ValueError("derived baseline requires its inverse patch and exact commit object")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_lock(destination.parent / ("." + destination.name + ".prepare.lock")):
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("destination already exists")
        with tempfile.TemporaryDirectory(prefix=".single20-", dir=destination.parent) as folder:
            temporary = Path(folder)
            archive = temporary / "source.tar"
            git(upstream, "archive", "--format=tar", "--output=" + str(archive), origin)
            source = temporary / "source"
            _safe_extract_git_archive(archive, source)
            actual_origin_hash = tree_sha256(source)
            expected_origin_hash = provenance.get(
                "origin_tree_sha256", entry["materialized_tree_sha256"]
            )
            if actual_origin_hash != expected_origin_hash:
                raise ValueError("upstream export differs from the recorded origin tree")
            subprocess.run(["git", "init", "--quiet", str(source)], check=True)
            git(source, "add", "--all", "--force")
            if git(source, "write-tree").decode().strip() != origin_tree:
                raise ValueError("exported file bytes or modes differ from the upstream Git tree")
            stored_origin = git(source, "hash-object", "-t", "commit", "-w", "--stdin",
                                data=origin_object).decode().strip()
            if stored_origin != origin:
                raise ValueError("upstream commit object identity mismatch")
            (source / ".git/shallow").write_text(origin + "\n")
            git(source, "update-ref", "HEAD", origin)
            patch_hash = None
            if derived:
                patch_hash = hashlib.sha256(patch_path.read_bytes()).hexdigest()
                git(source, "apply", "--reverse", "--ignore-space-change", "--check",
                    str(patch_path))
                git(source, "apply", "--reverse", "--ignore-space-change", str(patch_path))
                git(source, "add", "--all", "--force")
                actual_tree = git(source, "write-tree").decode().strip()
                commit_object = commit_path.read_bytes()
                headers = commit_object.split(b"\n\n", 1)[0].decode().splitlines()
                if "tree " + actual_tree not in headers or "parent " + origin not in headers:
                    raise ValueError("derived commit does not bind this tree and natural origin")
                stored = git(source, "hash-object", "-t", "commit", "-w", "--stdin",
                             data=commit_object).decode().strip()
                if stored != entry["commit"]:
                    raise ValueError("derived commit differs from sources.lock.json")
                git(source, "update-ref", "HEAD", stored)
            final_hash = tree_sha256(source)
            if final_hash != entry["materialized_tree_sha256"]:
                raise ValueError("reconstructed source differs from the locked materialized tree")
            git(source, "diff", "--exit-code", entry["commit"])
            if destination.exists() or destination.is_symlink():
                raise FileExistsError("destination appeared during preparation")
            os.rename(source, destination)
    return {
        "source_id": source_id,
        "commit": entry["commit"],
        "materialized_tree_sha256": final_hash,
        "origin_commit": origin,
        "inverse_patch_sha256": patch_hash,
        "destination": str(destination),
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_id")
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, default=FRAMEWORK_ROOT / "benchmarks/occt")
    args = parser.parse_args()
    result = reconstruct(
        args.bundle.resolve(strict=True), args.source_id,
        args.upstream_repo.resolve(strict=True), args.destination.absolute(),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
