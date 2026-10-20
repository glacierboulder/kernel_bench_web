import os
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.settings import SETTINGS
from backend.toolchain import environment


class ToolchainEnvironmentTests(unittest.TestCase):
    def test_default_compiler_jobs_are_capped_by_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)/"toolchain.json"
            profile.write_text(json.dumps({
                "schema_version":1,
                "id":"fixture-capped",
                "compiler_jobs_max":1,
                "compiler_output_directory":"fixture",
                "executables":{"cmake":"cmake","c_compiler":"cc","cxx_compiler":"c++"},
            }),encoding="utf-8")
            settings=replace(SETTINGS,config={"sandbox":{"compiler_jobs":2}},conda=None)
            with patch("backend.toolchain.SETTINGS",settings),patch.dict(os.environ):
                os.environ.pop("BENCH_COMPILER_JOBS",None)
                result=environment("fixture-capped",profile_path=profile)
            self.assertEqual(result["BENCH_COMPILER_JOBS"],"1")

    def test_explicit_compiler_jobs_above_profile_cap_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)/"toolchain.json"
            profile.write_text(json.dumps({
                "schema_version":1,
                "id":"fixture-capped",
                "compiler_jobs_max":1,
                "compiler_output_directory":"fixture",
                "executables":{"cmake":"cmake","c_compiler":"cc","cxx_compiler":"c++"},
            }),encoding="utf-8")
            settings=replace(SETTINGS,config={},conda=None)
            with patch("backend.toolchain.SETTINGS",settings),patch.dict(os.environ,{"BENCH_COMPILER_JOBS":"2"}):
                with self.assertRaisesRegex(ValueError,"toolchain maximum of 1"):
                    environment("fixture-capped",profile_path=profile)

    def test_conda_environment_is_exported_only_from_verified_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix=Path(directory)/"benchmark-env"
            (prefix/"conda-meta").mkdir(parents=True)
            profile=prefix.parent/"toolchain.json"
            profile.write_text(json.dumps({
                "schema_version":1,
                "id":"fixture-conda",
                "compiler_jobs_max":2,
                "compiler_output_directory":"fixture",
                "executables":{"cmake":"cmake","c_compiler":"cc","cxx_compiler":"c++"},
            }),encoding="utf-8")
            settings=replace(SETTINGS,config={},conda=None,conda_env=None,python_prefix=prefix)
            with patch("backend.toolchain.SETTINGS",settings),patch.dict(os.environ):
                os.environ.pop("BENCH_REQUIRED_CONDA_ENV",None)
                result=environment("fixture-conda",profile_path=profile)
            self.assertEqual(result["CONDA_DEFAULT_ENV"],"benchmark-env")
            self.assertEqual(result["BENCH_REQUIRED_CONDA_ENV"],"benchmark-env")

    def test_inconsistent_explicit_required_conda_environment_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix=Path(directory)/"benchmark-env"
            (prefix/"conda-meta").mkdir(parents=True)
            profile=prefix.parent/"toolchain.json"
            profile.write_text(json.dumps({
                "schema_version":1,
                "id":"fixture-conda",
                "compiler_jobs_max":2,
                "compiler_output_directory":"fixture",
                "executables":{"cmake":"cmake","c_compiler":"cc","cxx_compiler":"c++"},
            }),encoding="utf-8")
            settings=replace(SETTINGS,config={},conda=None,conda_env=None,python_prefix=prefix)
            with patch("backend.toolchain.SETTINGS",settings),patch.dict(
                os.environ,{"BENCH_REQUIRED_CONDA_ENV":"other-env"}
            ):
                with self.assertRaisesRegex(ValueError,"must match the configured Conda environment"):
                    environment("fixture-conda",profile_path=profile)

    def test_absolute_executable_symlink_is_resolved_for_sandbox_mounts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            actual=root/"compiler-real"
            actual.write_text("#!/bin/sh\nexit 0\n",encoding="utf-8")
            actual.chmod(0o755)
            alias=root/"compiler-alias"
            alias.symlink_to(actual)
            profile=root/"toolchain.json"
            profile.write_text(json.dumps({
                "schema_version":1,
                "id":"fixture",
                "compiler_jobs_max":2,
                "compiler_output_directory":"fixture",
                "executables":{"cmake":"cmake","c_compiler":"cc",
                               "cxx_compiler":str(alias)},
            }),encoding="utf-8")
            with patch("backend.toolchain.SETTINGS",replace(SETTINGS,config={},conda=None)):
                result=environment("fixture",profile_path=profile)
            self.assertEqual(result["BENCH_CXX"],str(actual.resolve()))
            self.assertEqual(result["BENCH_CMAKE"],"cmake")
            self.assertEqual(result["BENCH_CC"],"cc")


if __name__=="__main__":
    unittest.main()
