"""Read-only deployment and benchmark readiness report; never installs tools."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

from .catalog import CatalogError, validate_bundle
from .settings import SETTINGS


def _binary(config_key: str, env_name: str, fallback: str | None = None) -> str | None:
    tools = SETTINGS.config.get("tools", {})
    configured = os.environ.get(env_name) or tools.get(config_key)
    if not configured:
        configured = fallback
    if not configured:
        return None
    candidate = str(Path(configured).expanduser()) if "/" in str(configured) else shutil.which(str(configured))
    return candidate if candidate and Path(candidate).is_file() else None


def _version(binary: str | None) -> str | None:
    if not binary:
        return None
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True,
                                timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0][:160] if result.returncode == 0 and output else None


def _source_report(bundle: dict) -> list[dict]:
    from .source_cache import tree_sha256

    reports=[]
    for source_id, locked in bundle["sources"].items():
        cache=SETTINGS.cache_dir/"sources"/source_id
        metadata_file=cache/"source.json"
        source_dir=cache/"source"
        item={"source_id":source_id,"commit":locked["commit"],
              "lock_status":locked["verification_status"],"cached":source_dir.is_dir(),
              "verified":False,"status":"not_prepared"}
        if source_dir.is_dir() and metadata_file.is_file() and not metadata_file.is_symlink():
            try:
                metadata=json.loads(metadata_file.read_text(encoding="utf-8"))
                actual=tree_sha256(source_dir)
                item.update(cached_tree_sha256=actual,
                            metadata_commit_matches=metadata.get("commit")==locked["commit"],
                            metadata_hash_matches=metadata.get("tree_sha256")==actual,
                            expected_hash_matches=actual==locked["materialized_tree_sha256"],
                            verification_status=metadata.get("verification_status"),
                            cache_path=str(source_dir))
                item["verified"]=(item["metadata_commit_matches"] and item["metadata_hash_matches"]
                                   and item["expected_hash_matches"]
                                   and metadata.get("verification_status")=="verified_git")
                item["status"]="verified" if item["verified"] else "unverified_or_hash_mismatch"
            except (OSError, ValueError, json.JSONDecodeError) as error:
                item.update(status="invalid_cache",error=type(error).__name__)
        reports.append(item)
    return reports


def report() -> dict:
    checks={}
    try:
        bundle=validate_bundle(SETTINGS.benchmark_root)
        checks["catalog"]={"ok":True,"counts":bundle["counts"]}
        sources=_source_report(bundle)
    except (CatalogError,OSError,ValueError) as error:
        bundle=None;sources=[]
        checks["catalog"]={"ok":False,"error":str(error)}
    package_versions={}
    for package in ("fastapi","pydantic","uvicorn"):
        try:package_versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:package_versions[package]=None
    checks["python_packages"]={"versions":package_versions,
        "ok":all(package_versions.values()) and package_versions["pydantic"].split(".",1)[0]=="2"}
    binaries={name:_binary(config,env,default) for name,config,env,default in [
        ("git","git","BENCH_GIT","git"),("node","node","BENCH_NODE","node"),
        ("bubblewrap","bubblewrap","BENCH_BWRAP","bwrap"),("cmake","cmake","BENCH_CMAKE","cmake"),
        ("c_compiler","c_compiler","BENCH_CC",None),("cxx_compiler","cxx_compiler","BENCH_CXX",None),
        ("codex_cli","codex_cli","BENCH_CODEX",None)]}
    checks["system_tools"]={name:{"path":path,"version":_version(path)} for name,path in binaries.items()}
    runtime_dir=Path(__file__).resolve().parents[1]/"runtime"/"dsh"
    dsh_manifest=runtime_dir/"package-lock.json"
    dsh_cli=runtime_dir/"node_modules"/"@deepseek-ai"/"dsh"/"lib"/"bin.js"
    node_path=Path(binaries["node"]) if binaries["node"] else None
    conda_root=SETTINGS.conda.parent.parent if SETTINGS.conda else SETTINGS.python_prefix
    node_visible=bool(node_path and (node_path.is_relative_to(Path("/usr")) or node_path.is_relative_to(conda_root)))
    dsh_ready=bool(node_visible and dsh_manifest.is_file() and dsh_cli.is_file())
    checks["system_tools"]["node"]["visible_in_sandbox_mounts"]=node_visible
    linux=platform.system()=="Linux"
    bubblewrap_present=bool(linux and binaries["bubblewrap"])
    sandbox_probe={"attempted":False,"ok":False,"reason":"Linux bubblewrap is unavailable"}
    if bubblewrap_present:
        sandbox_probe["attempted"]=True
        try:
            from .preflight import verify
            sandbox_probe.update(ok=True,checks=verify())
        except Exception as error:
            sandbox_probe.update(ok=False,reason=type(error).__name__)
    verified_source=bool(sources and all(item["verified"] for item in sources))
    checks["runtime_paths"]={"benchmark_root":str(SETTINGS.benchmark_root),
        "data_dir":str(SETTINGS.data_dir),"cache_dir":str(SETTINGS.cache_dir),
        "work_dir":str(SETTINGS.work_dir),"data_dir_exists":SETTINGS.data_dir.is_dir(),
        "data_dir_writable":SETTINGS.data_dir.is_dir() and os.access(SETTINGS.data_dir,os.W_OK),
        "cache_dir_exists":SETTINGS.cache_dir.is_dir(),"work_dir_exists":SETTINGS.work_dir.is_dir()}
    checks["platform"]={"system":platform.system(),"machine":platform.machine(),
                         "linux_execution_supported":linux,"bubblewrap_present":bubblewrap_present,
                         "sandbox_probe":sandbox_probe}
    codex_version=SETTINGS.config.get("tools",{}).get("codex_version")
    codex_declared=bool(binaries["codex_cli"] and codex_version)
    checks["agents"]={"dsh_cli_ready":dsh_ready,
        "dsh_credentials_available":bool(os.environ.get("DEEPSEEK_API_KEY")),
        "codex_cli":binaries["codex_cli"],"codex_version_declared":codex_version,
        "codex_live_enabled":False,
        "codex_reason":"Codex live remains disabled until this CLI version and credential isolation are validated."}
    checks["source_cache"]=sources
    toolchains={}
    if bundle:
        from .toolchain import available
        for source_id,locked in bundle["sources"].items():
            profile_path=SETTINGS.benchmark_root/"toolchains"/(locked["toolchain"]+".json")
            try:
                profile=json.loads(profile_path.read_text(encoding="utf-8"))
                toolchains[locked["toolchain"]]=available(profile)
            except (OSError,ValueError,json.JSONDecodeError) as error:
                toolchains[locked["toolchain"]]={"available":False,"error":type(error).__name__}
    checks["toolchains"]=toolchains
    toolchain_ready=bool(toolchains) and all(
        all(toolchains[name].get(key,{}).get("available") and toolchains[name].get(key,{}).get("visible_in_sandbox_mounts")
            for key in ("cmake","c_compiler","cxx_compiler"))
        and toolchains[name].get("tcl_configured") for name in toolchains)
    checks["readiness"]={"catalog_read":bool(bundle),
        "web_service":bool(checks["python_packages"]["ok"]),
        "linux_execution_prerequisites":bool(bundle and sandbox_probe["ok"] and verified_source
                                             and binaries["git"] and toolchain_ready),
        "dsh_runtime":dsh_ready,
        "codex_live":False,
        "codex_configuration_complete":codex_declared}
    return {"schema_version":1,"read_only":True,"checks":checks}


def main() -> None:
    import argparse
    parser=argparse.ArgumentParser(description="Read-only environment and benchmark readiness checks")
    parser.add_argument("--json",action="store_true",help="print machine-readable JSON")
    args=parser.parse_args();value=report()
    print(json.dumps(value,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
