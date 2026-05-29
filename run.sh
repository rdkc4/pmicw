#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <workload-runner-path> workload [workload-options] [options]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRE="$SCRIPT_DIR/scripts/host_pre.sh"
POST="$SCRIPT_DIR/scripts/host_post.sh"

STATE_FILE="./bench_state_$$.env"

echo "[bench] state file: $STATE_FILE"

cleanup() {
    sudo bash "$POST" "$STATE_FILE" || true
    rm -f "$STATE_FILE"
}

trap cleanup EXIT

ORIG_USER="${SUDO_USER:-$USER}"
ORIG_HOME=$(eval echo "~$ORIG_USER")

echo "[bench] starting pipeline"

# pre-conditioning (root)
sudo bash "$PRE" "$STATE_FILE"

# run workload
RUNNER="$1"
WORKLOAD="$2"
shift 2

COMMAND=("$RUNNER" "$WORKLOAD" "$@")

if command -v numactl &>/dev/null; then
    numactl --cpunodebind=0 --membind=0 "${COMMAND[@]}"
else
    "${COMMAND[@]}"
fi

# post restore handled by trap
echo "[bench] finished"