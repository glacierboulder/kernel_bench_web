"""Per-deployment settings with CLI > environment > file > defaults precedence.

The module deliberately contains no credentials and performs no installation or
network activity. Paths from the JSON file are relative to that file.
"""
from __future__ import annotations

import json
import ipaddress
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
_UNSET = object()


def config_path() -> Path:
    value = os.environ.get("BENCH_CONFIG")
    if value:
        return Path(value).expanduser().resolve()
    return Path.home() / ".config" / "agent-bench-web" / "config.json"


def read_config(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f"invalid benchmark config file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("benchmark config must be a JSON object")
    return value


def choose(name: str, *, cli: Any = _UNSET, env: str | None = None,
           config: dict[str, Any] | None = None, section: str | None = None,
           default: Any = None) -> Any:
    """Resolve one option using the documented precedence."""
    if cli is not _UNSET and cli is not None:
        return cli
    if env and os.environ.get(env) not in (None, ""):
        return os.environ[env]
    config = config if config is not None else read_config()
    value: Any = config
    if section:
        value = value.get(section, {}) if isinstance(value, dict) else {}
    if isinstance(value, dict) and value.get(name) is not None:
        return value[name]
    return default


def _path(value: Any, default: Path, *, relative_to: Path | None = None) -> Path:
    if value in (None, ""):
        return default.expanduser().resolve()
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (relative_to or ROOT) / path
    return path.resolve()


def _executable_path(value: Any, default: Path, *, relative_to: Path) -> Path:
    if value in (None, ""):
        return default.expanduser().resolve()
    text=str(value)
    if os.sep not in text and not text.startswith("~"):
        located=shutil.which(text)
        if located:
            return Path(located).resolve()
    return _path(text,default,relative_to=relative_to)


@dataclass(frozen=True)
class Settings:
    config_file: Path
    config: dict[str, Any]
    benchmark_root: Path
    data_dir: Path
    cache_dir: Path
    work_dir: Path
    python: Path
    python_prefix: Path
    conda: Path | None
    conda_env: str | None
    host: str
    port: int
    gateway_host: str
    gateway_port: int


def load_settings(*, overrides: dict[str, Any] | None = None) -> Settings:
    """Load deployment settings. ``overrides`` represents CLI-level values."""
    overrides = overrides or {}
    cfg_path = config_path()
    cfg = read_config(cfg_path)
    relative_base = cfg_path.parent if cfg_path.is_file() else ROOT
    paths = cfg.get("paths", {})
    runtime = cfg.get("runtime", {})
    tools = cfg.get("tools", {})
    sandbox=cfg.get("sandbox",{})
    proxies=cfg.get("proxies",{})
    if not all(isinstance(x, dict) for x in (paths, runtime, tools,sandbox,proxies)):
        raise ValueError("paths, runtime, tools, sandbox, and proxies settings must be JSON objects")

    benchmark_value = choose("benchmark_root", cli=overrides.get("benchmark_root", _UNSET),
                             env="BENCHMARK_ROOT", config=cfg, section="paths",
                             default="benchmarks/occt")
    # The historical variable remains an explicit compatibility alias.
    if "benchmark_root" not in overrides and not os.environ.get("BENCHMARK_ROOT"):
        benchmark_value = os.environ.get("BENCH_PROTO_ROOT", benchmark_value)

    data_override = overrides.get("data_dir", _UNSET)
    data_value = choose("data_dir", cli=data_override, env="BENCH_DATA_DIR",
                        config=cfg, section="paths", default=None)
    legacy_db = ROOT / "data" / "bench.sqlite3"
    if data_value is None and legacy_db.is_file():
        # Preserve an ignored in-place deployment until its operator explicitly
        # migrates it. Fresh clones do not contain this file and use user data.
        data_value = str(legacy_db.parent)
    data_default = Path.home() / ".local" / "share" / "agent-bench-web" / "data"

    cache_value = choose("cache_dir", cli=overrides.get("cache_dir", _UNSET),
                         env="BENCH_CACHE_DIR", config=cfg, section="paths",
                         default=None)
    work_value = choose("work_dir", cli=overrides.get("work_dir", _UNSET),
                        env="BENCH_WORK_DIR", config=cfg, section="paths",
                        default=None)
    benchmark = _path(benchmark_value, ROOT / "benchmarks" / "occt", relative_to=relative_base)
    data = _path(data_value, data_default, relative_to=relative_base)
    cache = _path(cache_value, Path.home() / ".cache" / "agent-bench-web", relative_to=relative_base)
    work = _path(work_value, Path.home() / ".local" / "state" / "agent-bench-web" / "work", relative_to=relative_base)

    python_value = choose("python", cli=overrides.get("python", _UNSET),
                          env="BENCH_PYTHON", config=cfg, section="tools",
                          default=sys.executable)
    python = _executable_path(python_value, Path(sys.executable), relative_to=relative_base)
    prefix_value = choose("python_prefix", cli=overrides.get("python_prefix", _UNSET),
                          env="BENCH_PYTHON_PREFIX", config=cfg, section="tools",
                          default=sys.prefix)
    prefix = _path(prefix_value, Path(sys.prefix), relative_to=relative_base)
    conda_value = choose("conda", cli=overrides.get("conda", _UNSET), env="BENCH_CONDA",
                         config=cfg, section="tools", default=os.environ.get("CONDA_EXE"))
    conda = _executable_path(conda_value,Path(shutil.which("conda") or "conda"),relative_to=relative_base) if conda_value else None
    env_value = choose("conda_env", cli=overrides.get("conda_env", _UNSET),
                       env="BENCH_CONDA_ENV", config=cfg, section="tools", default=None)

    host = str(choose("host", cli=overrides.get("host", _UNSET), env="BENCH_HOST",
                      config=cfg, section="runtime", default="127.0.0.1"))
    port = int(choose("port", cli=overrides.get("port", _UNSET), env="BENCH_PORT",
                      config=cfg, section="runtime", default=8765))
    gateway_host = str(choose("gateway_host", env="BENCH_GATEWAY_HOST", config=cfg,
                              section="runtime", default="127.0.0.1"))
    gateway_port = int(choose("gateway_port", env="BENCH_GATEWAY_PORT", config=cfg,
                              section="runtime", default=18991))
    if not (1 <= port <= 65535 and 1 <= gateway_port <= 65535):
        raise ValueError("service ports must be between 1 and 65535")
    try:
        gateway_address=ipaddress.ip_address(gateway_host)
        if gateway_address.version!=4 or not gateway_address.is_loopback:
            raise ValueError("model gateway host must be a loopback address")
    except ValueError as exc:
        if "must be a loopback" in str(exc):
            raise
        raise ValueError("model gateway host must be an IPv4 or IPv6 loopback address") from exc
    return Settings(cfg_path, cfg, benchmark, data, cache, work, python, prefix,
                    conda, str(env_value) if env_value else None, host, port,
                    gateway_host, gateway_port)


SETTINGS = load_settings()
