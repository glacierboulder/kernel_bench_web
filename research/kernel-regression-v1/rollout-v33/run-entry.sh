#!/usr/bin/env bash
set -eu
root=$PWD
here="$root/research/kernel-regression-v1/rollout-v33"
dir="$root/formal"
source_id=occt801-b8f597c67781-coons
mkdir -p "$dir"
export BENCH_DATA_DIR="$dir/data" BENCH_WORK_DIR="$dir/work" BENCH_CACHE_DIR="$root/cache"
export BENCH_CONFIG="$dir/settings.json" BENCHMARK_ROOT="$root/benchmarks/occt"
printf '{"tools":{"bubblewrap":"%s"}}\n' "$here/bwrap-gcc13" > "$BENCH_CONFIG"
export BENCH_PYTHON_PREFIX=${BENCH_PYTHON_PREFIX:?}
export BENCH_PYTHON="$BENCH_PYTHON_PREFIX/bin/python"
export BENCH_COMPILER_JOBS=2 PYTHONDONTWRITEBYTECODE=1
"$BENCH_PYTHON" -B -m backend.source_cache "$source_id" \
  --from-dir /home/lzy/cad-bench-experiment/rollout11.YaEfGahr/fillet-source >"$dir/verified-source.json"
rc=0
"$BENCH_PYTHON" -B -m backend.reevaluate --source-id "$source_id" \
  --suite-id occt-github-1550-tangents-version-regression --suite-version 1 \
  --patch research/kernel-regression-v1/rollout-v21/neutral.diff >"$dir/cli.json" 2>"$dir/cli.stderr" || rc=$?
"$BENCH_PYTHON" -B research/kernel-regression-v1/rollout-v22/collect.py "$dir" "$root/receipts"
cp "$dir/verified-source.json" "$root/receipts/verified-source.json"
evaluation=("$dir"/data/reevaluations/*/evaluation-workspace)
for file in gh1550-tangents.csv gh1550-build-sha256.txt gh1550-build-commands.txt; do
    if [[ -f "${evaluation[0]}/$file" ]]; then cp "${evaluation[0]}/$file" "$root/receipts/$file"; fi
done
( cd "${evaluation[0]}"; sha256sum gh1550-tangents.csv gh1550-build-sha256.txt gh1550-build-commands.txt ) \
  > "$root/receipts/run-artifact-sha256.txt"
exit "$rc"
