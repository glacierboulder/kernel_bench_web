import json
import subprocess
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.freeze import materialize_source
from backend.source_cache import prepare_source, tree_sha256
from backend.settings import SETTINGS


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def unlock_tree(root: Path) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        path.chmod(0o755 if path.is_dir() else 0o644)
    root.chmod(0o755)


class SourceCacheTests(unittest.TestCase):
    def test_selects_two_local_commits_reuses_and_publishes_atomically(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "--quiet")
        git(repo, "config", "user.email", "bench-test@example.invalid")
        git(repo, "config", "user.name", "Benchmark Test")

        material = repo / "sample.txt"
        material.write_text("first baseline\n", encoding="utf-8")
        git(repo, "add", "sample.txt")
        git(repo, "commit", "--quiet", "-m", "first")
        first_commit = git(repo, "rev-parse", "HEAD")
        first_hash = tree_sha256(repo)

        material.write_text("second baseline\n", encoding="utf-8")
        git(repo, "commit", "--quiet", "-am", "second")
        second_commit = git(repo, "rev-parse", "HEAD")
        second_hash = tree_sha256(repo)
        self.assertNotEqual(first_commit, second_commit)
        self.assertNotEqual(first_hash, second_hash)

        bundle = root / "bundle"
        bundle.mkdir()
        (bundle / "sources.lock.json").write_text(json.dumps({"sources": [
            {"source_id": "fixture-first", "commit": first_commit,
             "materialized_tree_sha256": first_hash},
            {"source_id": "fixture-second", "commit": second_commit,
             "materialized_tree_sha256": second_hash},
            {"source_id": "fixture-bad", "commit": second_commit,
             "materialized_tree_sha256": "0" * 64},
        ]}), encoding="utf-8")
        cache = root / "cache"
        self.addCleanup(unlock_tree, cache)
        fake_settings = replace(SETTINGS, benchmark_root=bundle, cache_dir=cache)

        with patch("backend.source_cache.SETTINGS", fake_settings), \
             patch("backend.freeze.SETTINGS", fake_settings):
            first = prepare_source("fixture-first", repo)
            self.assertEqual(first["commit"], first_commit)
            self.assertEqual((Path(first["cache_path"]) / "sample.txt").read_text(), "first baseline\n")
            reused = prepare_source("fixture-first", repo)
            self.assertTrue(reused["reused"])

            snapshot = root / "snapshot"
            snapshot.mkdir()
            (snapshot / "snapshot.json").write_text(json.dumps({
                "source_id": "fixture-first", "source_tree_sha256": first_hash,
            }), encoding="utf-8")
            run_one = materialize_source(snapshot, root / "run-one" / "repo")
            run_two = materialize_source(snapshot, root / "run-two" / "repo")
            (run_one / "sample.txt").write_text("agent edit\n", encoding="utf-8")
            self.assertEqual((run_two / "sample.txt").read_text(), "first baseline\n")
            self.assertEqual((Path(first["cache_path"]) / "sample.txt").read_text(), "first baseline\n")

            outcomes = []
            errors = []

            def prepare_second():
                try:
                    outcomes.append(prepare_source("fixture-second", repo))
                except Exception as error:  # surface thread failures in the test thread
                    errors.append(error)

            threads = [threading.Thread(target=prepare_second) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            self.assertEqual(len(outcomes), 2)
            self.assertEqual({item["reused"] for item in outcomes}, {False, True})
            self.assertEqual((Path(outcomes[0]["cache_path"]) / "sample.txt").read_text(), "second baseline\n")

            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                prepare_source("fixture-bad", repo)
            self.assertFalse((cache / "sources" / "fixture-bad").exists())
            self.assertFalse(list((cache / "sources").glob(".fixture-bad-*")))

if __name__ == "__main__":
    unittest.main()
