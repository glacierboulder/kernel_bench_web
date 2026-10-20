#!/bin/bash
set -euo pipefail
args=()
for arg in "$@"; do
  if [[ "$arg" == "--unshare-all" ]]; then
    args+=(--unshare-user --unshare-ipc --unshare-pid --unshare-uts --unshare-cgroup)
  else
    args+=("$arg")
  fi
done
exec /usr/bin/bwrap "${args[@]}"
