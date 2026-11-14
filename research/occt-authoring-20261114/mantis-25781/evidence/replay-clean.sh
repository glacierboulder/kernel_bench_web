set -eu
cd /root/oce24161
p=/mnt/c/occt-cad-6acadf32/learning/submit-24161/reference.patch
patch -R --dry-run -p1 < "$p"
patch -R -p1 < "$p"
trap 'patch -p1 < "$p"; cmake --build build --target DRAWEXE TKTopTest -j 10 >/tmp/25781-restore-build.log 2>&1' EXIT
cmake --build build --target DRAWEXE TKTopTest -j 10 >/tmp/25781-baseline-build.log 2>&1
sha256sum build/adm/cmake/DRAWEXE/DRAWEXE $(find build -type f -name 'libTKGeomAlgo.so*') > /mnt/c/occt-cad-6acadf32/learning/batch-20261113/25781/B-build-sha256.txt
bash /mnt/c/occt-cad-6acadf32/learning/batch-20261113/25781/repair-all.sh