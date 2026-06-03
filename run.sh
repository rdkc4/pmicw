#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <workload-runner-path> [options] <workload> [workload-args...]"
    exit 1
fi

RUN_ID=$(date +%Y%m%d_%H%M%S)
POSTURE_FILE="host_posture_${RUN_ID}.log"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRE="$SCRIPT_DIR/scripts/host_pre.sh"
POST="$SCRIPT_DIR/scripts/host_post.sh"

STATE_FILE="./bench_state_$$.env"

echo "[bench] state file: $STATE_FILE"

log_host_posture() {
    local phase="$1"

    touch $POSTURE_FILE

    echo "==================================================" >> "$POSTURE_FILE"
    echo " HOST POSTURE ($phase BENCHMARKING)"                >> "$POSTURE_FILE"
    echo "==================================================" >> "$POSTURE_FILE"

    {
        echo "--- OS & Kernel ---"
        uname -a
        
        echo "--- CPU ---"
        lscpu

        echo "--- NUMA ---"
        if command -v numactl &>/dev/null; then
            numactl --hardware
        else
            echo "numactl not installed"
        fi

        echo "--- CPU Governor ---"
        if [[ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
            cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
        else
            echo "CPU frequency scaling not supported."
        fi

        echo "--- Turbo State ---"
        if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
            cat /sys/devices/system/cpu/intel_pstate/no_turbo
        elif [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
            cat /sys/devices/system/cpu/cpufreq/boost
        else
            echo "Turbo boost control not found."
        fi

        echo "--- THP ---"
        if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
            cat /sys/kernel/mm/transparent_hugepage/enabled
        else
            echo "THP enabled control not found."
        fi

        if [[ -f /sys/kernel/mm/transparent_hugepage/defrag ]]; then
            cat /sys/kernel/mm/transparent_hugepage/defrag
        else
            echo "THP defrag control not found."
        fi

        echo "--- Memory ---"
        free -h

    } >> "$POSTURE_FILE"
}

cleanup() {
    sudo bash "$POST" "$STATE_FILE" || true
    rm -f "$STATE_FILE"
    log_host_posture "AFTER"
}

trap cleanup EXIT

ORIG_USER="${SUDO_USER:-$USER}"
ORIG_HOME=$(eval echo "~$ORIG_USER")

echo "[bench] starting pipeline"

log_host_posture "BEFORE"

# pre-conditioning (root)
sudo bash "$PRE" "$STATE_FILE"

# run workload
RUNNER="$1"
shift

COMMAND=("$RUNNER" "$@")

if command -v numactl &>/dev/null; then
    numactl --cpunodebind=0 --membind=0 "${COMMAND[@]}"
else
    "${COMMAND[@]}"
fi

log_host_posture "DURING"

# post restore handled by trap
echo "[bench] finished"