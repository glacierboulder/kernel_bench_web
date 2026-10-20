"""Resolve a benchmark toolchain profile into an explicit safe environment."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .settings import SETTINGS


def _value(env_name: str, config_name: str, profile_value=None):
    if os.environ.get(env_name):
        return os.environ[env_name]
    configured=SETTINGS.config.get("tools",{}).get(config_name)
    return configured or profile_value


def _configured_path(value):
    if value in (None, ""):
        return None
    path=Path(str(value)).expanduser()
    if not path.is_absolute():
        path=SETTINGS.config_file.parent/path
    return str(path.resolve())


def _configured_executable(value):
    if value in (None, ""):
        return None
    text=str(value)
    if os.path.isabs(text) or os.sep in text or (os.altsep and os.altsep in text):
        return _configured_path(text)
    return text


def environment(toolchain_id: str, *, profile_path: Path | None = None) -> dict[str,str]:
    profile_path=profile_path or SETTINGS.benchmark_root/"toolchains"/f"{toolchain_id}.json"
    profile_path=Path(profile_path)
    if profile_path.is_symlink() or not profile_path.is_file():
        raise ValueError(f"toolchain profile is unavailable: {toolchain_id}")
    profile=json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version")!=1 or profile.get("id")!=toolchain_id:
        raise ValueError("toolchain profile identity/schema mismatch")
    executable=profile.get("executables",{})
    cmake=_configured_executable(_value("BENCH_CMAKE","cmake",executable.get("cmake")))
    cc=_configured_executable(_value("BENCH_CC","c_compiler",executable.get("c_compiler")))
    cxx=_configured_executable(_value("BENCH_CXX","cxx_compiler",executable.get("cxx_compiler")))
    maximum_jobs=min(2,int(profile.get("compiler_jobs_max",2)))
    requested_jobs=os.environ.get("BENCH_COMPILER_JOBS")
    if requested_jobs is None:
        # The profile is a hard resource cap; lower a general default to it.
        # An explicit per-run override above the cap remains an error below.
        configured_jobs=int(SETTINGS.config.get("sandbox",{}).get("compiler_jobs",2))
        jobs=min(configured_jobs,maximum_jobs) if configured_jobs>=1 else configured_jobs
    else:
        jobs=int(requested_jobs)
    if not 1<=jobs<=maximum_jobs:
        raise ValueError(f"compiler job count must be between 1 and the toolchain maximum of {maximum_jobs}")
    env={"BENCH_CMAKE":str(cmake),"BENCH_CC":str(cc),"BENCH_CXX":str(cxx),
         "BENCH_TOOLCHAIN_NAME":str(profile.get("compiler_output_directory","clang")),
         "BENCH_COMPILER_JOBS":str(jobs)}
    conda_prefix=Path(SETTINGS.python_prefix).resolve()
    if conda_prefix.is_dir() and (conda_prefix/"conda-meta").is_dir():
        conda_name=SETTINGS.conda_env or conda_prefix.name
        required_name=os.environ.get("BENCH_REQUIRED_CONDA_ENV")
        if required_name and required_name!=conda_name:
            raise ValueError("BENCH_REQUIRED_CONDA_ENV must match the configured Conda environment")
        env["CONDA_DEFAULT_ENV"]=conda_name
        env["BENCH_REQUIRED_CONDA_ENV"]=conda_name
    for key,config_key in (("BENCH_TCL_DIR","tcl_dir"),
                           ("BENCH_TCL_INCLUDE_DIR","tcl_include_dir"),
                           ("BENCH_TCL_LIBRARY","tcl_library"),
                           ("BENCH_TCL_LIBRARY_DIR","tcl_library_dir"),
                           ("BENCH_EXTRA_LIBRARY_PATH","extra_library_path")):
        value=_value(key,config_key)
        if value:
            env[key]=_configured_path(value)
    if SETTINGS.conda:
        conda_root=SETTINGS.conda.parent.parent
        defaults={"BENCH_TCL_DIR":conda_root,
                  "BENCH_TCL_INCLUDE_DIR":conda_root/"include",
                  "BENCH_TCL_LIBRARY":conda_root/"lib"/"libtcl8.6.so",
                  "BENCH_TCL_LIBRARY_DIR":conda_root/"lib",
                  "BENCH_EXTRA_LIBRARY_PATH":conda_root/"lib"}
        for key,path in defaults.items():
            if key not in env and path.exists():
                env[key]=str(path)
    return env


def available(profile: dict) -> dict:
    found={}
    env_names={"cmake":"BENCH_CMAKE","c_compiler":"BENCH_CC","cxx_compiler":"BENCH_CXX"}
    for name,env_name in env_names.items():
        configured=_value(env_name,name,profile.get("executables",{}).get(name))
        path=_configured_path(configured) if configured and os.sep in str(configured) else shutil.which(str(configured)) if configured else None
        executable_path=Path(path).resolve() if path else None
        conda_root=SETTINGS.conda.parent.parent if SETTINGS.conda else SETTINGS.python_prefix
        visible=bool(executable_path and (executable_path.is_relative_to(Path("/usr")) or executable_path.is_relative_to(conda_root)))
        found[name]={"configured":configured,"path":path,
                     "available":bool(executable_path and executable_path.is_file() and os.access(executable_path,os.X_OK)),
                     "visible_in_sandbox_mounts":visible}
    found["compiler_jobs_max"]=min(2,int(profile.get("compiler_jobs_max",2)))
    found["tcl_version_required"]=profile.get("tcl_version")
    conda_root=SETTINGS.conda.parent.parent if SETTINGS.conda else SETTINGS.python_prefix
    tcl_library=_value("BENCH_TCL_LIBRARY","tcl_library") or (conda_root/"lib"/"libtcl8.6.so")
    tcl_include=_value("BENCH_TCL_INCLUDE_DIR","tcl_include_dir") or (conda_root/"include")
    found["tcl_library_path"]=_configured_path(tcl_library)
    found["tcl_include_path"]=_configured_path(tcl_include)
    found["tcl_configured"]=bool(tcl_library and Path(_configured_path(tcl_library)).is_file()
                                  and tcl_include and Path(_configured_path(tcl_include)).is_dir())
    return found
