"""Copy an old data directory without deleting or rewriting its original."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


TRANSIENT_NAMES = {"worker-status.json", "plan1b-worker-status.json"}


def _walk(root: Path):
    for directory, subdirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in list(subdirs):
            path = base / name
            if path.is_symlink():
                raise ValueError(f"migration refuses symlink: {path.relative_to(root)}")
        for name in files:
            path = base / name
            if path.is_symlink():
                raise ValueError(f"migration refuses symlink: {path.relative_to(root)}")
            yield path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _database_backup(source: Path, target: Path) -> None:
    source_db = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
    target_db = sqlite3.connect(target, timeout=30)
    try:
        source_db.backup(target_db, pages=256, sleep=0.05)
        result = target_db.execute("PRAGMA quick_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"SQLite quick_check failed for {source.name}: {result}")
    finally:
        target_db.close()
        source_db.close()
    shutil.copystat(source, target, follow_symlinks=False)


def migrate(source_dir: Path | str, target_dir: Path | str, *, execute: bool = False,
            quiesced: bool = False) -> dict:
    source = Path(source_dir).expanduser().resolve(strict=True)
    target = Path(target_dir).expanduser().resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("source and target data directories must be separate")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("target must be absent or an empty directory")
    files = list(_walk(source))
    total = sum(path.stat().st_size for path in files if not path.name.endswith(("-wal", "-shm")))
    databases = [path for path in files if path.suffix in {".sqlite3", ".db"}]
    if not execute:
        return {"source": str(source), "target": str(target), "files": len(files),
                "bytes": total, "sqlite_databases": len(databases), "dry_run": True}
    if not quiesced:
        raise ValueError("copy requires --quiesced after the service and workers have stopped")
    target.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(target.parent).free
    if free < total:
        raise OSError(f"insufficient free space: need {total} bytes, have {free}")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-migration-", dir=target.parent))
    copied = 0
    try:
        for item in files:
            relative = item.relative_to(source)
            if item.name.endswith(("-wal", "-shm")):
                # SQLite's backup API below captures committed WAL state.
                continue
            if item.name in TRANSIENT_NAMES or item.name.endswith(".lock"):
                continue
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if item.suffix in {".sqlite3", ".db"}:
                _database_backup(item, destination)
            else:
                shutil.copy2(item, destination)
                if _sha256(item) != _sha256(destination):
                    raise RuntimeError(f"file hash mismatch: {relative}")
            copied += 1
        manifest = {"schema_version": 1, "source": str(source), "copied_files": copied,
                    "source_bytes": total, "sqlite_backup_api": True,
                    "original_preserved": True, "created_at_unix": int(__import__("time").time())}
        (stage / "migration-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(stage, target)
        return {**manifest, "target": str(target), "dry_run": False}
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy legacy benchmark data, preserving the original")
    parser.add_argument("--from", dest="source", type=Path, required=True)
    parser.add_argument("--to", dest="target", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="perform the copy; default is a read-only size report")
    parser.add_argument("--quiesced", action="store_true", help="confirm that the app and all workers are stopped")
    args = parser.parse_args()
    print(json.dumps(migrate(args.source, args.target, execute=args.execute,
                             quiesced=args.quiesced), indent=2))


if __name__ == "__main__":
    main()
