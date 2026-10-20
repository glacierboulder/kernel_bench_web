"""Resolve the configured Python/conda runtime before starting the service."""
from __future__ import annotations

import shutil
import subprocess
import sys

from .settings import SETTINGS


def main() -> int:
    service_args=sys.argv[1:]
    if SETTINGS.conda_env:
        conda=str(SETTINGS.conda) if SETTINGS.conda else shutil.which("conda")
        if not conda:
            raise RuntimeError("a conda environment is configured but the conda executable is unavailable")
        command=[conda,"run","--no-capture-output","-n",SETTINGS.conda_env,
                 "python","-m","backend.serve",*service_args]
    else:
        command=[str(SETTINGS.python),"-m","backend.serve",*service_args]
    return subprocess.call(command)


if __name__=="__main__":
    raise SystemExit(main())
