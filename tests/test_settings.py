import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_paths_follow_cli_environment_file_and_default_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps({
                "paths": {"benchmark_root": "file-bench", "data_dir": "file-data"},
                "runtime": {"host": "127.0.0.1", "port": 8123},
            }), encoding="utf-8")

            with patch.dict(os.environ, {
                "BENCH_CONFIG": str(config),
                "BENCHMARK_ROOT": "env-bench",
                "BENCH_PROTO_ROOT": "compat-bench",
                "BENCH_DATA_DIR": "env-data",
            }, clear=True):
                cli = load_settings(overrides={"benchmark_root": "cli-bench", "data_dir": "cli-data"})
                self.assertEqual(cli.benchmark_root, (root / "cli-bench").resolve())
                self.assertEqual(cli.data_dir, (root / "cli-data").resolve())
                env = load_settings()
                self.assertEqual(env.benchmark_root, (root / "env-bench").resolve())
                self.assertEqual(env.data_dir, (root / "env-data").resolve())

            with patch.dict(os.environ, {"BENCH_CONFIG": str(config)}, clear=True):
                file_settings = load_settings()
                self.assertEqual(file_settings.benchmark_root, (root / "file-bench").resolve())
                self.assertEqual(file_settings.data_dir, (root / "file-data").resolve())
                self.assertEqual(file_settings.port, 8123)

                default = load_settings(overrides={"benchmark_root": "default-bench", "data_dir": "default-data"})
                self.assertEqual(default.benchmark_root, (root / "default-bench").resolve())
                self.assertEqual(default.data_dir, (root / "default-data").resolve())

    def test_legacy_catalog_alias_is_lower_priority_than_primary_variable(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {
                "BENCH_CONFIG": str(config),
                "BENCH_PROTO_ROOT": "compat-bench",
            }, clear=True):
                self.assertEqual(load_settings().benchmark_root, (Path(directory) / "compat-bench").resolve())
            with patch.dict(os.environ, {
                "BENCH_CONFIG": str(config),
                "BENCH_PROTO_ROOT": "compat-bench",
                "BENCHMARK_ROOT": "primary-bench",
            }, clear=True):
                self.assertEqual(load_settings().benchmark_root, (Path(directory) / "primary-bench").resolve())

    def test_gateway_must_remain_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"runtime": {"gateway_host": "192.0.2.2"}}), encoding="utf-8")
            with patch.dict(os.environ, {"BENCH_CONFIG": str(config)}, clear=True):
                with self.assertRaisesRegex(ValueError, "loopback"):
                    load_settings()


if __name__ == "__main__":
    unittest.main()
