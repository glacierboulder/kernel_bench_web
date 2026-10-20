#!/usr/bin/env bash
set -euo pipefail

source_arg="${1:-repo}"
build_arg="${2:-build}"
source_path="$(cd "$source_arg" && pwd -P)"
mkdir -p "$build_arg"
build_path="$(cd "$build_arg" && pwd -P)"
cmake_bin="${BENCH_CMAKE:-cmake}"
cc="${BENCH_CC:-clang-10}"
cxx="${BENCH_CXX:-clang++-10}"
jobs="${BENCH_COMPILER_JOBS:-2}"
toolchain_name="${BENCH_TOOLCHAIN_NAME:-clang}"

if [[ ! "$jobs" =~ ^[1-2]$ ]]; then
  echo "BENCH_COMPILER_JOBS must be 1 or 2" >&2
  exit 2
fi
if [[ "$build_path" == "$source_path" || "$build_path" == "$source_path"/* ]]; then
  echo "build directory must be outside the locked source tree" >&2
  exit 2
fi

version_header=""
for candidate in \
  "$source_path/src/Standard/Standard_Version.hxx" \
  "$source_path/Standard/Standard_Version.hxx" \
  "$source_path/inc/Standard_Version.hxx"; do
  if [[ -f "$candidate" ]]; then version_header="$candidate"; break; fi
done
if [[ -z "$version_header" ]]; then
  echo "cannot identify OCCT version: Standard_Version.hxx is missing" >&2
  exit 2
fi
version_major="$(sed -nE 's/^[[:space:]]*#define[[:space:]]+OCC_VERSION_MAJOR[[:space:]]+([0-9]+).*/\1/p' "$version_header" | head -n1)"
version_minor="$(sed -nE 's/^[[:space:]]*#define[[:space:]]+OCC_VERSION_MINOR[[:space:]]+([0-9]+).*/\1/p' "$version_header" | head -n1)"
if [[ -z "$version_major" || -z "$version_minor" ]]; then
  echo "cannot parse OCCT version from $version_header" >&2
  exit 2
fi

cmake_args=(
  -S "$source_path" -B "$build_path"
  -DCMAKE_BUILD_TYPE=Release
  '-DCMAKE_C_FLAGS_RELEASE=-O3 -DNDEBUG'
  '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG'
  "-DCMAKE_C_COMPILER=$cc"
  "-DCMAKE_CXX_COMPILER=$cxx"
)
locale_header="$source_path/src/Standard/Standard_CLocaleSentry.hxx"
if [[ "${OSTYPE:-}" == linux* && -f "$locale_header" ]] && grep -q '#include <xlocale.h>' "$locale_header"; then
  if ! "$cxx" -E -x c++ - >/dev/null 2>&1 <<< '#include <xlocale.h>'; then
    mkdir -p "$build_path/compat-include"
    printf '#pragma once\n#include <locale.h>\n' > "$build_path/compat-include/xlocale.h"
    cmake_args+=("-DCMAKE_CXX_FLAGS=-I$build_path/compat-include")
  fi
fi
if [[ "$version_major" == 6 && ( "$version_minor" == 8 || "$version_minor" == 9 ) ]]; then
  cmake_args+=("-DBUILD_TOOLKITS=TKTopTest;DRAWEXE" "-DINSTALL_DIR=$build_path/install")
elif [[ "$version_major" == 7 || "$version_major" == 8 ]]; then
  cmake_args+=(
    -DBUILD_LIBRARY_TYPE=Shared
    '-DBUILD_ADDITIONAL_TOOLKITS=TKTopTest;DRAWEXE'
    -DBUILD_MODULE_ApplicationFramework=OFF
    -DBUILD_MODULE_DataExchange=OFF
    -DBUILD_MODULE_Draw=OFF
    -DBUILD_MODULE_FoundationClasses=OFF
    -DBUILD_MODULE_ModelingAlgorithms=OFF
    -DBUILD_MODULE_ModelingData=OFF
    -DBUILD_MODULE_Visualization=OFF
    -DUSE_FREETYPE=OFF
    -DUSE_TK=OFF
  )
else
  echo "unsupported OCCT version $version_major.$version_minor; expected 6.8, 6.9, 7.x, or 8.x" >&2
  exit 2
fi

for pair in \
  "3RDPARTY_TCL_DIR:${BENCH_TCL_DIR:-}" \
  "3RDPARTY_TCL_INCLUDE_DIR:${BENCH_TCL_INCLUDE_DIR:-}" \
  "3RDPARTY_TCL_LIBRARY:${BENCH_TCL_LIBRARY:-}" \
  "3RDPARTY_TCL_LIBRARY_DIR:${BENCH_TCL_LIBRARY_DIR:-}"; do
  name="${pair%%:*}"
  value="${pair#*:}"
  if [[ -n "$value" ]]; then cmake_args+=("-D${name}=${value}"); fi
done

echo "Configuring OCCT $version_major.$version_minor with at most $jobs compiler jobs"
"$cmake_bin" "${cmake_args[@]}"
"$cmake_bin" --build "$build_path" --target DRAWEXE TKTopTest --parallel "$jobs"

# OCCT 6.8/6.9 place products under out/{bin,lib}; the evaluator toolchain
# contract uses lin64/<compiler>/{bin,lib}. Keep compatibility links in build.
if [[ -d "$build_path/out/bin" || -d "$build_path/out/lib" || -d "$build_path/lin64/gcc/bin" ]]; then
  alias_dir="$build_path/lin64/$toolchain_name"
  mkdir -p "$alias_dir"
  for kind in bin lib; do
    target="$build_path/out/$kind"
    if [[ ! -d "$target" ]]; then target="$build_path/lin64/gcc/$kind"; fi
    link="$alias_dir/$kind"
    if [[ -d "$target" && ! -e "$link" ]]; then
      ln -s "$target" "$link"
    fi
  done
fi

# Legacy headers live in source/inc rather than build/include/opencascade.
# The alias is confined to the disposable build tree and never edits source.
header_path="$source_path/inc"
if [[ -d "$build_path/inc" ]]; then header_path="$build_path/inc"; fi
if [[ ! -e "$build_path/include/opencascade" && -d "$header_path" ]]; then
  mkdir -p "$build_path/include"
  ln -s "$header_path" "$build_path/include/opencascade"
fi
