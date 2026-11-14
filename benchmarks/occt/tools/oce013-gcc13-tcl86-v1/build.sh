#!/usr/bin/env bash
set -euo pipefail
source_dir=$(realpath "$1")
build_dir=$(realpath -m "$2")
work="$build_dir/oce-compat"
mkdir -p "$work/source" "$work/include"
cp -a "$source_dir/." "$work/source/"
chmod -R u+w "$work/source"
printf '#include <locale.h>\n' > "$work/include/xlocale.h"
sed -i 's/\<fsqrt\>/oce_local_fsqrt/g' "$work/source/src/BOPTools/BOPTools_AlgoTools.cxx"
cmake -S "$work/source" -B "$work/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
 -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DOCE_DRAW=ON \
 -DOCE_WITH_FREEIMAGE=OFF -DOCE_WITH_GL2PS=OFF \
 "-DCMAKE_CXX_FLAGS=-I$work/include -Wno-narrowing -fno-delete-null-pointer-checks"
cmake --build "$work/build" --target DRAWEXE TKTopTest --parallel "${BENCH_COMPILER_JOBS:-2}"
mkdir -p "$build_dir/lin64/gcc/bin" "$build_dir/lin64/gcc/lib"
ln -sfn "$work/build/adm/cmake/DRAWEXE/DRAWEXE" "$build_dir/lin64/gcc/bin/DRAWEXE"
while IFS= read -r -d '' lib; do
 ln -sfn "$lib" "$build_dir/lin64/gcc/lib/$(basename "$lib")"
done < <(find "$work/build" -name '*.so*' -print0)