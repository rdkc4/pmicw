## Benchmark Server Setup

This document explains how to use the benchmark_setup.sh script to prepare your Linux server for consistent benchmark measurements.

### Purpose

Benchmark results can vary due to CPU frequency scaling, turbo boost, memory management, and caching.

The `benchmark_setup.sh` script ensures repeatable and controlled conditions by:
 - Locking CPU frequency at maximum (performance governor)
 - Disabling Turbo Boost
 - Controlling Transparent Huge Pages (THP) behavior (madvise)
 - Cleaning memory caches before benchmarking

How:
 - CPU Governor => performance: Locks CPU at maximum frequency, eliminating variability caused by dynamic frequency scaling. Ensures repeatable benchmark timings.
 - Turbo Boost => disabled: Turbo Boost allows cores to temporarily exceed base frequency depending on thermal/power headroom. Disabling it prevents unpredictable CPU spikes and stabilizes performance.
 - THP => madvise: Only uses huge pages when requested by the application. This reduces variability from automatic huge page allocation and keeps memory performance more consistent without fully disabling huge pages.
 - THP Defrag => madvise: Only defragments huge pages when explicitly requested. Reduces unpredictable memory compaction during benchmarks and improves reproducibility.
 - Cache Cleaning => Frees cached memory and filesystem metadata to minimize memory-related variability. Ensures a “cold start” for benchmarks and more consistent results across runs.

### Requirements

 - Linux system
 - Root access (for apply/reset operations)
 - Bash
 - Optional: `numactl`

### Overview

 - `--info-only` - display system information
 - `--check` - validate current system settings
 - `--apply` - configure system for benchmarking
 - `--reset` - restore default system settings

### Usage

```bash
# Display system info
./benchmark_setup.sh --info-only

# Check if the server is ready for benchmarking
./benchmark_setup.sh --check

# Apply benchmark-ready configuration
sudo ./benchmark_setup.sh --apply

# Reset server to normal state
sudo ./benchmark_setup.sh --reset
```

### Instructions

1) Prepare For Benchmark
```bash
# CPU Governor => performance
# Turbo boost => disabled
# THP => madvise
# Drop caches
sudo ./benchmark_setup.sh --apply
```

2) Check Current Settings
```bash
# [ OK ] => ready for benchmarking
# [ WARN ] => indicates a mismatch
./benchmark_setup.sh --check
```

3) Display System Info
```bash
# Display:
# - OS & Kernel info
# - CPU info
# - NUMA Topology
# - Current CPU governor, Turbo, THP, THP Defrag 
./benchmark_setup.sh --info-only
```

4) Running The Workload
```bash
numactl --cpunodebind=0 --membind=0 ./workload
```

5) Resetting System After Benchmark
```bash
sudo ./benchmark_setup.sh --reset
```

### Permissions

|      Flag     | Requires sudo | Why                                       |
|---------------|---------------|-------------------------------------------|
| `--info-only` | No            | Read-only system information              |
| `--check`     | No            | Reads `/sys` and `/proc` only             |
| `--apply`     | Yes           | Modifies CPU governor, THP, turbo, caches |
| `--reset`     | Yes           | Restores system-wide kernel settings      |