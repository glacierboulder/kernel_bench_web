#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec "${BENCH_PYTHON:-python}" -m backend.launch "$@"
