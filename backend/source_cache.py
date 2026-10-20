"""Per-user immutable source cache; prepares only an explicitly selected commit."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from contextlib import contextmanager

from .settings import SETTINGS


EXCLUDED_NAMES = {".git", "__pycache__", "CMakeFiles", "build"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _excluded(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return bool(set(parts) & EXCLUDED_NAMES) or Path(relative).suffix in EXCLUDED_SUFFIXES


def tree_sha256(root: Path | str) -> str:
    """Hash sorted relative paths, file type, executable bit and file/link data."""
    root = Path(root).resolve(strict=True)
    digest = hashlib.sha256()
    paths = sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix().encode("utf-8"))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if _excluded(relative):
            continue
        info = path.lstat()
        mode = info.st_mode
        if stat.S_ISDIR(mode):
            continue
        if stat.S_ISLNK(mode):
            target = os.readlink(path)
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root):
                raise ValueError(f"source symlink escapes the tree: {relative}")
            kind, data = b"L", target.encode("utf-8")
        elif stat.S_ISREG(mode):
            kind, data = b"F", path.read_bytes()
        else:
            raise ValueError(f"unsupported file type in source tree: {relative}")
        executable = b"1" if mode & 0o111 else b"0"
        digest.update(relative.encode("utf-8") + b"\0" + kind + b"\0" + executable + b"\0" +
                      str(len(data)).encode("ascii") + b"\0" + data + b"\0")
    return digest.hexdigest()


def _safe_extract_git_archive(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    with tarfile.open(archive, "r:") as bundle:
        for item in bundle:
            relative = PurePosixPath(item.name)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError(f"unsafe path in Git archive: {item.name}")
            target = destination.joinpath(*relative.parts)
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.issym():
                link = PurePosixPath(item.linkname)
                if link.is_absolute():
                    raise ValueError(f"absolute symlink in Git archive: {item.name}")
                resolved = (target.parent / item.linkname).resolve()
                if not resolved.is_relative_to(destination.resolve()):
                    raise ValueError(f"escaping symlink in Git archive: {item.name}")
                target.symlink_to(item.linkname)
                continue
            if not item.isfile():
                raise ValueError(f"unsupported entry in Git archive: {item.name}")
            stream = bundle.extractfile(item)
            if stream is None:
                raise ValueError(f"unreadable Git archive entry: {item.name}")
            with stream, target.open("wb") as output:
                shutil.copyfileobj(stream, output)
            target.chmod(item.mode & 0o777)


def _copy_source_tree(source: Path, destination: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped = set()
        for name in names:
            full = Path(directory) / name
            rel = full.relative_to(source).as_posix()
            if name in EXCLUDED_NAMES or full.suffix in EXCLUDED_SUFFIXES:
                skipped.add(name)
        return skipped

    shutil.copytree(source, destination, symlinks=True, ignore=ignore)
    tree_sha256(destination)  # rejects links that leave the copied tree


@contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        except ImportError:
            pass
        yield


def _source_entry(source_id: str) -> dict:
    lock = json.loads((SETTINGS.benchmark_root / "sources.lock.json").read_text(encoding="utf-8"))
    for item in lock.get("sources", []):
        if item.get("source_id") == source_id:
            return item
    raise ValueError(f"unknown source_id: {source_id}")


def _git_top_level(source: Path) -> str | None:
    git=_git_binary()
    if not git:
        return None
    try:
        result = subprocess.run([git, "-C", str(source), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _git_binary() -> str | None:
    configured=os.environ.get("BENCH_GIT") or SETTINGS.config.get("tools",{}).get("git") or "git"
    if os.sep in str(configured):
        candidate=Path(str(configured)).expanduser()
        if not candidate.is_absolute():candidate=SETTINGS.config_file.parent/candidate
        return str(candidate.resolve()) if candidate.is_file() else None
    return shutil.which(str(configured))


def prepare_source(source_id: str, from_dir: Path | str, *, allow_unverified: bool = False) -> dict:
    """Import from a local Git checkout or a provenance-labeled plain export.

    No clone/fetch or network access occurs. Existing cache entries are never
    overwritten, and published source files are read-only.
    """
    entry = _source_entry(source_id)
    commit = entry["commit"]
    expected = entry["materialized_tree_sha256"]
    origin = Path(from_dir).expanduser().resolve(strict=True)
    if origin.is_symlink() or not origin.is_dir():
        raise ValueError("source import must name a regular directory")
    git_root = _git_top_level(origin)
    git_archive = False
    if git_root:
        git=_git_binary()
        if not git:
            raise ValueError("configured Git executable is unavailable")
        available = subprocess.run([git, "-C", str(origin), "cat-file", "-e", f"{commit}^{{commit}}"],
                                   capture_output=True, check=False, timeout=20)
        if available.returncode != 0:
            raise ValueError(f"locked commit {commit} is not present in this local Git repository")
        git_archive = True
    if not git_root and not allow_unverified:
        raise ValueError("source has no Git metadata; pass --allow-unverified to import it explicitly")

    cache_root = SETTINGS.cache_dir / "sources"
    target = cache_root / source_id
    lock_path = cache_root / ".locks" / f"{source_id}.lock"
    with _exclusive_lock(lock_path):
        if target.exists():
            metadata_path = target / "source.json"
            source_path = target / "source"
            if target.is_symlink() or not metadata_path.is_file() or not source_path.is_dir():
                raise ValueError("existing source cache entry is incomplete; refusing to overwrite")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            actual = tree_sha256(source_path)
            if actual != expected or metadata.get("tree_sha256") != actual:
                raise ValueError("existing source cache hash does not match sources.lock.json")
            return {**metadata, "cache_path": str(source_path), "reused": True}

        cache_root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{source_id}-", dir=cache_root))
        try:
            source_path = temporary / "source"
            if git_archive:
                archive = temporary / "source.tar"
                subprocess.run([_git_binary(), "-C", str(origin), "archive", "--format=tar",
                                f"--output={archive}", commit], check=True, timeout=180)
                _safe_extract_git_archive(archive, source_path)
                archive.unlink()
            else:
                _copy_source_tree(origin, source_path)
            actual = tree_sha256(source_path)
            if actual != expected:
                raise ValueError(f"source tree hash mismatch: expected {expected}, got {actual}")
            for path in sorted(source_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if path.is_symlink():
                    continue
                if path.is_dir():
                    path.chmod(0o555)
                else:
                    path.chmod(path.stat().st_mode & ~0o222)
            source_path.chmod(0o555)
            metadata = {"source_id": source_id, "commit": commit, "tree_sha256": actual,
                        "verification_status": "verified_git" if git_archive else "unverified_export_without_git_metadata",
                        "source_origin_kind": "git_archive" if git_archive else "unverified_local_export"}
            (temporary / "source.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, target)
            return {**metadata, "cache_path": str(target / "source"), "reused": False}
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare one pinned source from a local checkout/export")
    parser.add_argument("source_id")
    parser.add_argument("--from-dir", type=Path, required=True)
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare_source(args.source_id, args.from_dir,
                                    allow_unverified=args.allow_unverified), indent=2))


if __name__ == "__main__":
    main()
