#!/usr/bin/env bash
set -euo pipefail
public=$(cd "$(dirname "$0")" && pwd)
build=$(realpath "${1:?built kernel directory}")
"${BENCH_CXX:-g++}" -std=c++17 -I"$build/include/opencascade" "$public/reproduce.cxx" \
  -L"$build/lin64/gcc/lib" -lTKBO -o "$build/public-reproduce"
"$build/public-reproduce"
