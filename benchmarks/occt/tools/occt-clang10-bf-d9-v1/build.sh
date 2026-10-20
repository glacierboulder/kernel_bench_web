#!/usr/bin/env bash
set -euo pipefail

repo_path="${1:-repo}"
build_path="${2:-build}"
cmake_bin="${BENCH_CMAKE:-cmake}"
cc="${BENCH_CC:-clang-10}"
cxx="${BENCH_CXX:-clang++-10}"
jobs="${BENCH_COMPILER_JOBS:-2}"
[[ -n "${CONDA_PREFIX:-}" && -d "${CONDA_PREFIX}/conda-meta" ]] || { echo 'run inside a verified conda environment' >&2; exit 2; }
[[ "$jobs" =~ ^[1-2]$ ]] || { echo 'BENCH_COMPILER_JOBS must be 1 or 2' >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
overlay="$script_dir/overlay"
# freeze copies this entrypoint to snapshot/tools/build.sh while it places
# evaluator assets under snapshot/supervisor/evaluator_assets. Resolve that
# frozen layout without requiring the full staging bundle to be present.
if [[ ! -f "$overlay/xlocale.h" ]]; then
  overlay="$script_dir/../supervisor/evaluator_assets/occt-bf-group-d9d310-21494-29807-31835/toolchain_overlay"
fi
header="$overlay/xlocale.h"
expected_sha='0cfbf755395add5d865f01722849120cbd0dccb0774755f2af369950dbcb779f'
[[ -d "$overlay" && -f "$header" ]] || { echo 'locked xlocale overlay is missing' >&2; exit 2; }
actual_sha="$(sha256sum "$header" | cut -d ' ' -f 1)"
[[ "$actual_sha" == "$expected_sha" ]] || { echo 'locked xlocale overlay SHA mismatch' >&2; exit 2; }

prefix="${CONDA_PREFIX:?verified Conda prefix is not set}"
cmake_args=(
  -S "$repo_path" -B "$build_path" -G 'Unix Makefiles'
  -DCMAKE_BUILD_TYPE=Release
  '-DCMAKE_C_FLAGS_RELEASE=-O0 -DNDEBUG'
  '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG'
  "-DCMAKE_C_COMPILER=$cc" "-DCMAKE_CXX_COMPILER=$cxx"
  -DBUILD_LIBRARY_TYPE=Shared
  '-DBUILD_ADDITIONAL_TOOLKITS=DRAWEXE;TKTopTest'
  -DBUILD_MODULE_ApplicationFramework=OFF
  -DBUILD_MODULE_DataExchange=OFF
  -DBUILD_MODULE_Draw=OFF
  -DBUILD_MODULE_FoundationClasses=OFF
  -DBUILD_MODULE_ModelingAlgorithms=OFF
  -DBUILD_MODULE_ModelingData=OFF
  -DBUILD_MODULE_Visualization=ON
  -DBUILD_DOC_Overview=OFF -DINSTALL_SAMPLES=OFF -DINSTALL_TEST_CASES=OFF
  -DUSE_TK=ON -DUSE_FREETYPE=ON
  "-DCMAKE_CXX_FLAGS=-I$overlay"
  "-D3RDPARTY_TCL_DIR=${BENCH_TCL_DIR:-$prefix}"
  "-D3RDPARTY_TCL_INCLUDE_DIR=${BENCH_TCL_INCLUDE_DIR:-$prefix/include}"
  "-D3RDPARTY_TCL_LIBRARY=${BENCH_TCL_LIBRARY:-$prefix/lib/libtcl8.6.so}"
  "-D3RDPARTY_TCL_LIBRARY_DIR=${BENCH_TCL_LIBRARY_DIR:-$prefix/lib}"
  "-D3RDPARTY_TK_DIR=${BENCH_TK_DIR:-$prefix}"
  "-D3RDPARTY_TK_INCLUDE_DIR=${BENCH_TK_INCLUDE_DIR:-$prefix/include}"
  "-D3RDPARTY_TK_LIBRARY=${BENCH_TK_LIBRARY:-$prefix/lib/libtk8.6.so}"
  "-D3RDPARTY_TK_LIBRARY_DIR=${BENCH_TK_LIBRARY_DIR:-$prefix/lib}"
  "-D3RDPARTY_FREETYPE_INCLUDE_DIR_ft2build=${BENCH_FREETYPE_INCLUDE_FT2BUILD:-/usr/include/freetype2}"
  "-D3RDPARTY_FREETYPE_INCLUDE_DIR_freetype2=${BENCH_FREETYPE_INCLUDE_FREETYPE2:-/usr/include/freetype2}"
  "-D3RDPARTY_FREETYPE_LIBRARY=${BENCH_FREETYPE_LIBRARY:-/usr/lib/x86_64-linux-gnu/libfreetype.so}"
  "-D3RDPARTY_FREETYPE_LIBRARY_DIR=${BENCH_FREETYPE_LIBRARY_DIR:-/usr/lib/x86_64-linux-gnu}"
)

"$cmake_bin" "${cmake_args[@]}"
"$cmake_bin" --build "$build_path" --target DRAWEXE TKTopTest --parallel "$jobs"
