set -eu
base=/mnt/c/occt-cad-6acadf32/learning/batch-20261113/25781
for role in B F; do
 if [ "$role" = B ]; then
  cd /root/oce24161
  exe="$PWD/build/adm/cmake/DRAWEXE/DRAWEXE"
  source_root="$PWD"
 else
  cd /root/occt25242-later-f
  exe="$PWD/build/lin64/gcc/bin/DRAWEXE"
  source_root="$PWD/src"
 fi
 export LD_LIBRARY_PATH="$(find "$PWD/build" -name '*.so' -printf '%h\n' | sort -u | paste -sd:)"
 export CASROOT="$source_root" DRAWHOME="$source_root/src/DrawResources" CSF_DrawPluginDefaults="$source_root/src/DrawResources"
 for name in original shift rotate regression; do
  printf 'if {[catch {source {%s/repair-%s.tcl}} msg]} {puts stderr "RUN_ERROR: $msg";exit 1}\nexit 0\n' "$base" "$name" >"$base/repair-entry.tcl"
  rc=0
  timeout 15 "$exe" -b -f "$base/repair-entry.tcl" >"$base/repair-$role-$name.txt" 2>&1 || rc=$?
  printf '%s %s %s\n' "$role" "$name" "$rc"
  grep -E 'CASE_PASS|RUN_ERROR|Mass|SOLID|valid' "$base/repair-$role-$name.txt" || true
 done
done
