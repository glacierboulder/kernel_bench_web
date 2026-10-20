#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo 'usage: build.sh <configured-build-dir>' >&2; exit 2; fi
jobs="${BENCH_COMPILER_JOBS:-2}"
[[ "$jobs" =~ ^[1-2]$ ]] || { echo 'BENCH_COMPILER_JOBS must be 1 or 2' >&2; exit 2; }
exec cmake --build "$1" --target DRAWEXE TKTopTest --parallel "$jobs"
