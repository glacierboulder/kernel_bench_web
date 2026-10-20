"""Read-only availability preflight for every profile referenced by OCCT tasks."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog import validate_bundle
from backend.settings import SETTINGS
from backend.toolchain import available, environment


bundle = validate_bundle(SETTINGS.benchmark_root)
source_ids = {group["source_id"] for group in bundle["groups"].values()}
toolchain_ids = sorted({bundle["sources"][source_id]["toolchain"] for source_id in source_ids})
records = []
for toolchain_id in toolchain_ids:
    path = SETTINGS.benchmark_root / "toolchains" / f"{toolchain_id}.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    ready = available(profile)
    assert all(ready[name]["available"] and ready[name]["visible_in_sandbox_mounts"]
               for name in ("cmake", "c_compiler", "cxx_compiler")), (toolchain_id, ready)
    resolved = environment(toolchain_id, profile_path=path)
    jobs = int(resolved["BENCH_COMPILER_JOBS"])
    assert 1 <= jobs <= min(2, int(profile.get("compiler_jobs_max", 2))), (toolchain_id, jobs)
    include = Path(resolved["BENCH_TCL_INCLUDE_DIR"])
    library = Path(resolved["BENCH_TCL_LIBRARY"])
    assert (include / "tcl.h").is_file() and library.is_file(), (toolchain_id, include, library)
    tcl_version = subprocess.run(
        ["tclsh"], input="puts [info patchlevel]\n", capture_output=True,
        text=True, check=True, timeout=5,
    ).stdout.strip()
    assert re.fullmatch(r"8\.6(?:\.\d+)?", tcl_version), (toolchain_id, tcl_version)
    tools = SETTINGS.benchmark_root / "tools" / profile["tools_directory"]
    for name in ("build.sh", "run_draw_case.py"):
        candidate = tools / name
        assert candidate.is_file() and candidate.stat().st_mode & 0o111, candidate
    ninja = shutil.which("ninja")
    ninja_version = None
    if ninja:
        ninja_version = subprocess.run([ninja, "--version"], capture_output=True,
                                       text=True, check=True, timeout=5).stdout.strip()
    records.append({
        "toolchain_id": toolchain_id,
        "max_compiler_jobs": ready["compiler_jobs_max"],
        "resolved_compiler_jobs": jobs,
        "executables": {name: ready[name]["path"] for name in ("cmake", "c_compiler", "cxx_compiler")},
        "tcl_version": tcl_version,
        "tcl_include": str(include),
        "tcl_library": str(library),
        "tools_directory": tools.relative_to(SETTINGS.benchmark_root).as_posix(),
        "tools_executable": True,
        "ninja_version": ninja_version,
        "build_invoked": False,
    })

print(json.dumps({"profiles_checked": len(records), "preflight": records}, ensure_ascii=False))
