#!/usr/bin/env bash
set -euo pipefail

RUN_ID=$(date +%Y%m%d_%H%M%S)
POSTURE_FILE="host_posture_${RUN_ID}.log"
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

echo "=================================================="  > "$POSTURE_FILE"
echo " HOST POSTURE"                                      >> "$POSTURE_FILE"
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

echo "[host_pre] done"