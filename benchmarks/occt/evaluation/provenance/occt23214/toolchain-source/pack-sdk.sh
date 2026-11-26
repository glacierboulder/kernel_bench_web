#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
stage=$(realpath -m "$1")
debs=$(realpath "$2")
headers=$(realpath "$3")
wok=$(realpath "$4")
archive=$(realpath -m "$5")
mkdir -p "$stage"/{debs,headers,templates}
cp "$here"/{configure.sh,finalize_headers.py,generate.tcl,wok_extract.cxx,build_native.py,legacy-host-config.py} "$stage/"
cp "$debs"/*.deb "$stage/debs/"
cp "$wok"/src/CPPExt/CPPExt_{Standard,Template,TemplateCSFDB,TemplateOBJS,TemplateOBJY}.edl "$stage/templates/"
g++ -MM -std=gnu++98 -DHAVE_IOSTREAM -DHAVE_LIMITS_H -DHAVE_IOMANIP -DHAVE_SYS_STAT_H -DHAVE_FSTREAM -DLIN -DLININTEL -DCSFDB \
    -include iomanip -I/usr/include/tcl -I"$debs/extracted/usr/include/opencascade/arch-6.3.0" -I"$headers" "$here/wok_extract.cxx" |
  tr ' ' '\n' | while IFS= read -r dep; do
    if [[ $dep == "$headers/"* && -f $dep ]]; then cp "$dep" "$stage/headers/"; fi
  done
cp "$here/SDK-SOURCES.md" "$stage/"
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cJf "$archive" -C "$stage" .
