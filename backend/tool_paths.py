"""Resolve configured executable names without embedding host-specific paths."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .sandbox import TOOLCHAIN_ROOT
from .settings import SETTINGS


def executable(name: str, *, env_name: str, config_name: str, default: str | None = None) -> str:
    value=os.environ.get(env_name) or SETTINGS.config.get("tools",{}).get(config_name) or default
    if not value:
        raise RuntimeError(f"{name} is not configured")
    if os.sep in str(value):
        candidate=Path(str(value)).expanduser()
        if not candidate.is_absolute():candidate=SETTINGS.config_file.parent/candidate
        candidate=candidate.resolve()
    else:
        found=shutil.which(str(value))
        if not found:raise RuntimeError(f"configured {name} is unavailable")
        candidate=Path(found).resolve()
    if not candidate.is_file() or not os.access(candidate,os.X_OK):
        raise RuntimeError(f"configured {name} is not an executable file")
    allowed=(Path("/usr").resolve(),TOOLCHAIN_ROOT.resolve())
    if not any(candidate.is_relative_to(root) for root in allowed):
        raise RuntimeError(f"configured {name} must be under /usr or the configured conda/toolchain root")
    return str(candidate)
