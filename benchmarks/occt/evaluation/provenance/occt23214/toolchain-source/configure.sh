#!/usr/bin/env bash
# Build an unchanged, locked CDL-era kernel. The SDK holds generator inputs only.
set -euo pipefail
sdk=$(cd "$(dirname "$0")" && pwd)
source_root=$(realpath "$1")
build=$(realpath -m "$2")
mkdir -p "$build"
cd "$build"
mkdir -p wok cdlin gen inc obj include/opencascade lin64/gcc/lib
for package in "$sdk"/debs/*.deb; do dpkg-deb -x "$package" wok; done
export WOK_RELEASE="$build/wok/usr"
export WOK_TEMPLATES="$sdk/templates"
export WOK_EXTRACT_PLUGIN="$build/directwok.so"
cxx=${BENCH_CXX:-g++}
"$cxx" -std=gnu++98 -fPIC -shared -w -DHAVE_IOSTREAM -DHAVE_LIMITS_H -DHAVE_IOMANIP \
  -DHAVE_SYS_STAT_H -DHAVE_FSTREAM -DLIN -DLININTEL -DCSFDB -include iomanip \
  -I/usr/include/tcl -I"$WOK_RELEASE/include/opencascade/arch-6.3.0" -I"$sdk/headers" \
  "$sdk/wok_extract.cxx" -L"$WOK_RELEASE/lib" -Wl,-rpath-link,"$WOK_RELEASE/lib" \
  -l:libTKWOK-6.3.0.so -l:libTKernel-6.3.0.so -l:libTKCPPExt-6.3.0.so -o "$WOK_EXTRACT_PLUGIN"
find "$source_root/src" -type f -name '*.cdl' -exec ln -sft cdlin -- {} +
find "$source_root/src" -type f \( -name '*.h' -o -name '*.hxx' -o -name '*.lxx' -o -name '*.gxx' -o -name '*.pxx' \) -exec ln -sft inc -- {} +
ln -sf /usr/include/locale.h inc/xlocale.h
LD_LIBRARY_PATH="$WOK_RELEASE/lib" TCL_LIBRARY="$WOK_RELEASE/share/tcltk/tcl8.5" \
  "$WOK_RELEASE/bin/tclsh8.5" "$sdk/generate.tcl" "$source_root/src" "$build/cdlin" "$build/gen" \
  TKernel TKMath TKG2d TKG3d TKGeomBase TKBRep TKGeomAlgo TKTopAlgo TKPrim TKBO > generation.log 2>&1
if grep -q '^Error   :' generation.log; then tail -50 generation.log >&2; exit 1; fi
python3 "$sdk/finalize_headers.py" "$source_root/src" "$build"
python3 "$sdk/build_native.py" "$source_root/src" "$build"
python3 "$sdk/legacy-host-config.py" "$build" "$source_root/src"
# Preserve the same handwritten-before-generated include order in public consumers.
find "$build/gen" -type f ! -name '*.cxx' -exec ln -sft include/opencascade -- {} +
find "$build/inc" -type l -exec ln -sft include/opencascade -- {} +
