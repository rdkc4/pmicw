#!/usr/bin/env bash
set -euo pipefail

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root" >&2
        exit 1
    fi
}

get_governor_status() {
    if [[ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
        cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    else
        echo "N/A"
    fi
}

get_thp_enabled_status() {
    if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
        cat /sys/kernel/mm/transparent_hugepage/enabled | grep -o "\[.*\]" | tr -d '[]'
    else
        echo "N/A"
    fi
}

get_thp_defrag_status() {
    if [[ -f /sys/kernel/mm/transparent_hugepage/defrag ]]; then
        cat /sys/kernel/mm/transparent_hugepage/defrag | grep -o "\[.*\]" | tr -d '[]'
    else
        echo "N/A"
    fi
}

get_turbo_status() {
    # Intel Check
    if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
        local val=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo)
        [[ "$val" -eq 1 ]] && echo "Disabled (Intel)" || echo "Enabled (Intel)"
    # AMD Check
    elif [[ -f /sys/devices/system/cpu/amd_pstate/no_turbo ]]; then
         local val=$(cat /sys/devices/system/cpu/amd_pstate/no_turbo)
         [[ "$val" -eq 1 ]] && echo "Disabled (AMD)" || echo "Enabled (AMD)"
    elif [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
        local val=$(cat /sys/devices/system/cpu/cpufreq/boost)
        [[ "$val" -eq 0 ]] && echo "Disabled (Global)" || echo "Enabled (Global)"
    else
        echo "N/A/Unknown"
    fi
}

info() {
    echo "=== OS & Kernel ==="
    uname -a
    echo
    
    echo "=== CPU ==="
    lscpu
    echo

    echo "=== NUMA ==="
    if command -v numactl &>/dev/null; then
        numactl --hardware
    else
        echo "numactl not installed"
    fi
    echo

    echo "=== MEMORY ==="
    free -h
    echo

    echo "=== CURRENT SETTINGS ==="
    echo "CPU Governor:    $(get_governor_status)"
    echo "Turbo Boost:     $(get_turbo_status)"
    echo "THP Status:      $(get_thp_enabled_status)"
    echo "THP Defrag:      $(get_thp_defrag_status)"
}

check() {
    echo "=== BENCHMARK READYNESS CHECK ==="
    
    local gov=$(get_governor_status)
    local turbo=$(get_turbo_status)
    local thp=$(get_thp_enabled_status)
    local thp_defrag=$(get_thp_defrag_status)
    
    if [[ "$gov" == "performance" ]]; then
        echo "[ OK ] Governor is set to 'performance'"
    else
        echo "[WARN] Governor is '$gov', should be 'performance'"
    fi

    if [[ "$turbo" =~ "Disabled" ]]; then
        echo "[ OK ] Turbo Boost is Disabled"
    else
        echo "[WARN] Turbo Boost is Enabled/Unknown"
    fi

    if [[ "$thp" == "madvise" ]]; then
        echo "[ OK ] THP is set to 'madvise'"
    else
        echo "[WARN] THP is '$thp', should be 'madvise'"
    fi

    if [[ "$thp_defrag" == "madvise" ]]; then
        echo "[ OK ] THP Defrag is set to 'madvise'"
    else
        echo "[WARN] THP Defrag is '$thp_defrag', should be 'madvise'"
    fi
}

apply() {
    check_root
    echo "=== CONFIGURING SERVER FOR BENCHMARKING ==="
    
    # Set CPU governor to performance:
    # - Locks CPU at maximum frequency.
    # - Eliminates variability caused by frequency scaling.
    # - Result: repeatable benchmark timings.
    if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then
        echo "Setting CPU governor to 'performance'..."
        echo "performance" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    fi
    
    # Disable turbo boost (Intel/AMD):
    # - Turbo Boost allows cores to temporarily exceed base frequency if power/thermal headroom allows.
    # - Disabling it prevents unpredictable frequency spikes during benchmarks.
    # - Result: more consistent CPU performance.
    if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
        echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
        echo "Intel Turbo disabled."
    fi
    if [[ -f /sys/devices/system/cpu/amd_pstate/no_turbo ]]; then
        echo 1 > /sys/devices/system/cpu/amd_pstate/no_turbo
        echo "AMD Turbo disabled."
    fi
    if [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/boost
        echo "Global CPU Boost disabled."
    fi
    
    # Set THP enabled to madvise:
    # - Only uses huge pages if explicitly requested by an application, more controlled memory behavior.
    # - Reduces variability from automatic huge page allocation.
    # - Keeps memory performance more consistent without fully disabling huge pages.
    if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
        echo "madvise" > /sys/kernel/mm/transparent_hugepage/enabled
        echo "THP set to 'madvise'."
    fi

    # Set THP defrag to madvise:
    # - Only defrags huge pages if explicitly requested, more controlled memory behavior.
    # - Reduces variability from automatic huge page defragmentation.
    # - Keeps memory performance more consistent without fully disabling defrag.
    if [[ -f /sys/kernel/mm/transparent_hugepage/defrag ]]; then
        echo "madvise" > /sys/kernel/mm/transparent_hugepage/defrag
        echo "THP defrag set to 'madvise'."
    fi
    
    # Drop caches:
    # - Frees pagecache, dentries, and inodes to minimize memory-related variability.
    # - Ensures benchmarks start with a clean slate in terms of cached data.
    # - Result: more consistent memory performance across runs.
    if [[ -f /proc/sys/vm/drop_caches ]]; then
        echo "Dropping caches..."
        sync && echo 3 > /proc/sys/vm/drop_caches
    fi

    echo   
    echo "Configuration applied successfully. Run your benchmark using:"
    echo "numactl --cpunodebind=0 --membind=0 -- ./benchmark"
}

reset() {
    check_root
    echo "=== RESTORING SETTINGS ==="
    
    # Revert to standard governor (tries schedutil, ondemand, then powersave fallback)
    if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then
        echo "Restoring CPU governor..."
        for gov in schedutil ondemand powersave; do
            if grep -q "$gov" /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null; then
                echo "$gov" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
                break
            fi
        done
    fi
    
    # Enable Turbo Boost
    if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
        echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
    fi
    if [[ -f /sys/devices/system/cpu/amd_pstate/no_turbo ]]; then
        echo 0 > /sys/devices/system/cpu/amd_pstate/no_turbo
    fi
    if [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
        echo 1 > /sys/devices/system/cpu/cpufreq/boost
    fi
    
    # Revert THP to always
    if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
        echo "always" > /sys/kernel/mm/transparent_hugepage/enabled
    fi

    # Revert THP defrag to always
    if [[ -f /sys/kernel/mm/transparent_hugepage/defrag ]]; then
        echo "always" > /sys/kernel/mm/transparent_hugepage/defrag
    fi

    echo "System restored to normal state."
}

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {--info-only|--check|--apply|--reset}"
    exit 1
fi

# Parse flags
case "$1" in
    --info-only)
        info
        ;;
    --check)
        check
        ;;
    --apply)
        apply
        ;;
    --reset)
        reset
        ;;
    *)
        echo "Usage: $0 {--info-only|--check|--apply|--reset}"
        exit 1
        ;;
esac

# Running the benchmark: 
# $ numactl --cpunodebind=0 --membind=0 -- ./benchmark