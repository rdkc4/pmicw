#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="${1:?usage: host_pre.sh <state_file>}"

echo "[host_post] restoring system state"

if [[ ! -f "$STATE_FILE" ]]; then
    echo "[host_post] no state file found, skipping restore"
    exit 0
fi

# shellcheck disable=SC1090
source "$STATE_FILE"

# Restore CPU governor
if [[ -n "${ORIGINAL_GOVERNOR:-}" ]]; then
    for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo "$ORIGINAL_GOVERNOR" > "$g" || true
    done
fi

# Restore turbo state
if [[ -n "${ORIGINAL_INTEL_TURBO:-}" ]]; then
    echo "$ORIGINAL_INTEL_TURBO" > /sys/devices/system/cpu/intel_pstate/no_turbo || true
elif [[ -n "${ORIGINAL_AMD_BOOST:-}" ]]; then
    echo "$ORIGINAL_AMD_BOOST" > /sys/devices/system/cpu/cpufreq/boost || true
fi

# Restore THP
if [[ -n "${ORIGINAL_THP:-}" ]]; then
    echo "$ORIGINAL_THP" > /sys/kernel/mm/transparent_hugepage/enabled || true
fi

if [[ -n "${ORIGINAL_THP_DEFRAG:-}" ]]; then
    echo "$ORIGINAL_THP_DEFRAG" > /sys/kernel/mm/transparent_hugepage/defrag || true
fi

echo "[host_post] done"