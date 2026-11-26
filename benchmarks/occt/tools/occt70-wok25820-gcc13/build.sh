#!/usr/bin/env bash
set -euo pipefail
source_root=$(realpath "${1:?OCCT source directory}")
build=$(realpath -m "${2:?empty build directory}")
tools=$(cd "$(dirname "$0")" && pwd)
if [[ -n ${3:-} ]]; then
  public=$(realpath "$3")
else
  public=$tools
  for folder in "$tools/../visible/issue_25820" "$tools/../issues/occt-25820/1/public"; do
    [[ ! -f "$folder/cdl-toolchain.tar.xz" ]] || public=$folder
  done
fi
mkdir -p "$build/sdk"
tar -xJf "$public/cdl-toolchain.tar.xz" -C "$build/sdk"
bash "$build/sdk/configure.sh" "$source_root" "$build"
ninja -C "$build" -j"${BENCH_COMPILER_JOBS:-2}" lin64/gcc/lib/libTKBO.a
