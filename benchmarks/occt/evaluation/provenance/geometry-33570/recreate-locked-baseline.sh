#!/usr/bin/env bash
set -euo pipefail
origin=$1
dest=$2
asset_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
base=b8f597c677811d1f9f4d8a97f5ae2825c0353a42
expected=381c5ec350fde3b9808475d8070bf00eda0260c9
git clone --no-checkout --local "$origin" "$dest"
git -C "$dest" checkout --detach "$base"
git -C "$dest" apply -R "$asset_dir/reference.patch"
export GIT_AUTHOR_DATE=2026-11-15T00:00:00Z GIT_COMMITTER_DATE=2026-11-15T00:00:00Z
git -C "$dest" -c user.name='OCCT Benchmark Authoring' -c user.email='benchmark@example.invalid' \
  -c commit.gpgsign=false commit -qam 'Derive OCCT 33570 baseline by reverting the sphere projection condition'
actual=$(git -C "$dest" rev-parse HEAD)
if [[ "$actual" != "$expected" ]]; then
  printf 'Derived commit mismatch: expected %s, got %s\n' "$expected" "$actual" >&2
  exit 1
fi
printf '%s\n' "$actual"