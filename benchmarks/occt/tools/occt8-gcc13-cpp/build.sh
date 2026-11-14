#!/usr/bin/env bash
set -euo pipefail
source_dir="$(realpath "${1:-repo}")"
build_dir="$(realpath -m "${2:-build}")"
case "$build_dir/" in "$source_dir/"*) echo "Build directory must be outside source" >&2; exit 2;; esac
jobs="${BENCH_COMPILER_JOBS:-2}"
[[ "$jobs" =~ ^[12]$ ]] || exit 2
cmake_bin="${BENCH_CMAKE:-cmake}"
"$cmake_bin" -S "$source_dir" -B "$build_dir" -DCMAKE_BUILD_TYPE=Release \
  "-DCMAKE_C_COMPILER=${BENCH_CC:-gcc}" "-DCMAKE_CXX_COMPILER=${BENCH_CXX:-g++}" \
  '-DBUILD_ADDITIONAL_TOOLKITS=TKFillet;TKPrim' -DUSE_TBB=OFF \
  -DBUILD_MODULE_FoundationClasses=OFF -DBUILD_MODULE_ModelingData=OFF \
  -DBUILD_MODULE_ModelingAlgorithms=OFF -DBUILD_MODULE_Visualization=OFF \
  -DBUILD_MODULE_ApplicationFramework=OFF -DBUILD_MODULE_DataExchange=OFF -DBUILD_MODULE_Draw=OFF
"$cmake_bin" --build "$build_dir" --target TKFillet TKPrim --parallel "$jobs"
