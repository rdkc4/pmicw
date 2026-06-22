#!/usr/bin/env bash
set -euo pipefail

show_help() {
    echo "Usage: $0 [options] <workload> [workload-args...]"
    echo ""
    echo "[options]:"
    echo "  -m,    --metric <m>                     Gathered metrics (cpu,gpu,memory,thread)"
    echo "  -it,   --iteration <n>                  Number of iterations for workload to run"
    echo "  -wit,  --warmup-iteration               Number of warmup iterations for workload to run"
    echo "  -ct,   --compute-thresholds <n>         Compute thresholds based on workload, using 'n' as z-score"
    echo "  -cmp,  --compare <n>                    Compare with last 'n' runs"
    echo "  -cmp2, --compare-two <a> <b>            Compare two explicit run IDs"
    echo "  -cmpw, --compare-with <id>              Compare current run against a specific baseline ID"
    echo "  -uct,  --use-computed-thresholds <path> Use computed thresholds in comparisons, path optional"
    echo "  -rfmt, --report-format <f>              Format for analysis output (csv,json,md)"
    echo "  -vfmt, --visual-format <v>              Visualization type (table,chart,graph)"
    echo ""
    exit 0
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
fi

RUN_ID=$(date +%Y%m%d_%H%M%S)
POSTURE_FILE="host_posture_${RUN_ID}.log"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PRE="$SCRIPT_DIR/scripts/host_pre.sh"
POST="$SCRIPT_DIR/scripts/host_post.sh"

RUNNER="$SCRIPT_DIR/src/workload_runner.py"
COMPARISON="$SCRIPT_DIR/src/comparison_tool.py"

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

echo "[bench] Warming bpftrace into memory..."
sudo bpftrace -e 'BEGIN { exit(); }' >/dev/null 2>&1

RUNNER_COMMAND=("$RUNNER")
COMPARISON_COMMAND=("$COMPARISON")

while [[ $# -gt 0 ]]; do
    case "$1" in
        -cmp|--compare)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                echo "Error: Option $1 requires a positive integer value." >&2
                show_help
            fi
            COMPARISON_COMMAND+=("$1" "$2")
            shift 2
            ;;
        -cmp2|--compare-two)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]] || [[ -z "${3:-}" ]] || [[ "$3" =~ ^- ]]; then
                echo "Error: Option $1 requires two explicit run ID strings." >&2
                show_help
            fi
            COMPARISON_COMMAND+=("$1" "$2" "$3")
            shift 3
            ;;
        -cmpw|--compare-with)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                echo "Error: Option $1 requires a target run ID string." >&2
                show_help
            fi
            COMPARISON_COMMAND+=("$1" "$2")
            shift 2
            ;;
        -uct|--use-computed-thresholds)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                COMPARISON_COMMAND+=("$1")
                shift 1
            fi
            COMPARISON_COMMAND+=("$1" "$2")
            shift 2
            ;;
        -rfmt|--report-format)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                echo "Error: Option $1 requires a format string (csv,json,md)." >&2
                show_help
            fi
            COMPARISON_COMMAND+=("$1" "$2")
            shift 2
            ;;
        -vfmt|--visual-format)
            if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                echo "Error: Option $1 requires a visualization type (table,chart,graph)." >&2
                show_help
            fi
            COMPARISON_COMMAND+=("$1" "$2")
            shift 2
            ;;
        *)
            RUNNER_COMMAND+=("$1")
            shift
            ;;
    esac
done

if command -v numactl &>/dev/null; then
    RESULT=$(numactl --cpunodebind=0 --membind=0 ${RUNNER_COMMAND[@]})
else
    RESULT=$("${RUNNER_COMMAND[@]}")
fi

JSON_RESULT=$(echo "$RESULT" | grep -o '{.*}' || true)

if [[ -z "$JSON_RESULT" ]]; then
    echo "ERROR: No JSON object found in the command output!" >&2
    exit 1
fi

RUN_ID=$(echo "$JSON_RESULT" | jq -r '.run_id // empty' 2>/dev/null)
WORKLOAD=$(echo "$JSON_RESULT" | jq -r '.workload_name // empty' 2>/dev/null)
CSV_PATH=$(echo "$JSON_RESULT" | jq -r '.csv_path // empty' 2>/dev/null)


if [[ -z "$RUN_ID" ]] || [[ -z "$WORKLOAD" ]] || [[ -z "$CSV_PATH" ]]; then
    echo "ERROR: Required keys missing or empty!" >&2
    echo "Extracted Run ID: '$RUN_ID'" >&2
    echo "Extracted Workload Name: '$WORKLOAD'" >&2
    echo "Extracted CSV Path: '$CSV_PATH'" >&2
    exit 1
fi

if [[ ${#COMPARISON_COMMAND[@]} -gt 1 ]]; then
    COMPARISON_COMMAND+=("-rid" "$RUN_ID" "-wn" "$WORKLOAD" "-p" "$CSV_PATH")
    "${COMPARISON_COMMAND[@]}"
fi

log_host_posture "DURING"

# post restore handled by trap
echo "[bench] finished"