#!/usr/bin/env bash
set -euo pipefail

repo_path="${1:-repo}"
build_path="${2:-build}"
cmake_bin="${BENCH_CMAKE:-cmake}"
cc="${BENCH_CC:-clang-10}"
cxx="${BENCH_CXX:-clang++-10}"
jobs="${BENCH_COMPILER_JOBS:-2}"
if [[ ! "$jobs" =~ ^[1-2]$ ]]; then
  echo "BENCH_COMPILER_JOBS must be 1 or 2" >&2
  exit 2
fi

cmake_args=(
  -S "$repo_path" -B "$build_path"
  -DCMAKE_BUILD_TYPE=Release
  '-DCMAKE_C_FLAGS_RELEASE=-O1 -DNDEBUG'
  '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG'
  "-DCMAKE_C_COMPILER=$cc"
  "-DCMAKE_CXX_COMPILER=$cxx"
  -DBUILD_LIBRARY_TYPE=Shared
  '-DBUILD_ADDITIONAL_TOOLKITS=TKTopTest;DRAWEXE'
  -DBUILD_MODULE_ApplicationFramework=OFF
  -DBUILD_MODULE_DataExchange=OFF
  -DBUILD_MODULE_Draw=OFF
  -DBUILD_MODULE_FoundationClasses=OFF
  -DBUILD_MODULE_ModelingAlgorithms=OFF
  -DBUILD_MODULE_ModelingData=OFF
  -DBUILD_MODULE_Visualization=OFF
  -DUSE_FREETYPE=OFF -DUSE_TK=OFF
)
for pair in \
  "3RDPARTY_TCL_DIR:${BENCH_TCL_DIR:-}" \
  "3RDPARTY_TCL_INCLUDE_DIR:${BENCH_TCL_INCLUDE_DIR:-}" \
  "3RDPARTY_TCL_LIBRARY:${BENCH_TCL_LIBRARY:-}" \
  "3RDPARTY_TCL_LIBRARY_DIR:${BENCH_TCL_LIBRARY_DIR:-}"; do
  name="${pair%%:*}"
  value="${pair#*:}"
  if [[ -n "$value" ]]; then cmake_args+=("-D${name}=${value}"); fi
done

"$cmake_bin" "${cmake_args[@]}"
"$cmake_bin" --build "$build_path" --target DRAWEXE TKTopTest --parallel "$jobs"
