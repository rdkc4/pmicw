#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="${1:?usage: host_pre.sh <state_file>}"

# Capture original state
{
    echo "ORIGINAL_GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true)"
    echo "ORIGINAL_INTEL_TURBO=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true)"
    echo "ORIGINAL_AMD_BOOST=$(cat /sys/devices/system/cpu/cpufreq/boost 2>/dev/null || true)"
    echo "ORIGINAL_THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null | grep -o '\[.*\]' | tr -d '[]' || true)"
    echo "ORIGINAL_THP_DEFRAG=$(cat /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null | grep -o '\[.*\]' | tr -d '[]' || true)"
} > "$STATE_FILE"

# Set CPU governor to performance
if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$gov" || true
    done
else
    echo "Warning: CPU frequency scaling not supported. Skipping governor change."
fi

# Disable turbo boost (Intel/AMD)
if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
    echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo || true
elif [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
    echo 0 > /sys/devices/system/cpu/cpufreq/boost || true
else
    echo "Warning: Turbo boost control not found. Skipping."
fi

# Set THP to madvise
if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
    echo madvise > /sys/kernel/mm/transparent_hugepage/enabled || true
else
    echo "Warning: THP control not found. Skipping."
fi


if [[ -f /sys/kernel/mm/transparent_hugepage/defrag ]]; then
    echo madvise > /sys/kernel/mm/transparent_hugepage/defrag || true
else
    echo "Warning: THP defrag control not found. Skipping."
fi

# Drop caches
sync
if [[ -f /proc/sys/vm/drop_caches ]]; then
    echo 3 > /proc/sys/vm/drop_caches || true
else
    echo "Warning: /proc/sys/vm/drop_caches not found. Skipping cache drop."
fi

echo "[host_pre] done"