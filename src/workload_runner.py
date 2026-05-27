"""
Orchestration and Workload Execution Engine.

This module coordinates the active profiling lifecycle. It parses user requests,
spawns asynchronous background resource samplers, executes target workloads under
hardware counters, and routes collected payloads to the aggregation layer.

Asynchronous Thread Coordination Model:
    [Main Thread]                   [Background Threads]
          |                                  |
          |--> mem_thread.start() ---------->| (Idle / Event Blocked)
          |--> gpu_thread.start() ---------->| (Idle / Event Blocked)
          |                                  |
       |->| Loop: Iteration                  |
       |  |--> activity_event.set() -------->| (Wake up & sample hardware)
       |  |--> subprocess.run(workload)      | (Active Execution)
       |  |--> activity_event.clear() ------>| (Pause sampling)
       |--|
          |
          |--> shutdown_event.set() -------->| (Break loop & terminate)
          |--> Join Threads <----------------|

Error Isolation & Resource Guarantees:
    - Daemon threads are safely captured in a lifecycle registration list.
    - A blanket `finally` context guarantees background samplers are signaled 
      to spin down and cleanly joined, eliminating runaway background processes.

Usage:
    $ python3 ./workload_runner.py workload [workload-options] [options]
"""
import argparse
import subprocess
import threading
import time

from cli_parser import parse_args
from metric_computer import (
    compute_gpu_metrics,
    compute_memory_metrics,
    compute_wall_time_metric,
    compute_execution_core_metrics,
    compute_private_cache_metrics,
    compute_shared_cache_metrics
)
from metric_monitor import monitor_amd_gpu, monitor_memory
from record_parser import parse_perf_output

def run_workload(args: argparse.Namespace) -> None:
    selected_metrics: list[str]              = args.metric
    wall_times:       list[float]            = []
    memory_records:   list[dict[str, float]] = []
    gpu_records:      list[dict[str, float]] = []

    perf_records:     dict[str, list[dict[str, float]]] = {
        "execution_core": [],
        "private_caches": [],
        "shared_caches":  []
    }

    perf_event_sets: dict[str, str] = {}

    if "cpu" in selected_metrics:
        perf_event_sets["execution_core"] = "'{instructions,cycles,branches,branch-misses,context-switches,page-faults,minor-faults,major-faults}'"
        perf_event_sets["private_caches"] = "'{L1-dcache-loads,L1-dcache-load-misses,l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_miss_in_l2}'"
        perf_event_sets["shared_caches"]  = "'{cache-references,cache-misses}'"

    activity_event = threading.Event()
    shutdown_event = threading.Event()
    daemon_threads = []

    if "memory" in selected_metrics:
        mem_thread = threading.Thread(
            target = monitor_memory,
            args   = (activity_event, shutdown_event, 0.1, memory_records),
            daemon = True
        )
        mem_thread.start()
        daemon_threads.append(mem_thread)

    if "gpu" in selected_metrics:
        gpu_thread = threading.Thread(
            target = monitor_amd_gpu,
            args   = (activity_event, shutdown_event, 0.1, gpu_records),
            daemon = True
        )
        gpu_thread.start()
        daemon_threads.append(gpu_thread)

    try:
        if(perf_event_sets):
            for event_set_k, event_set in perf_event_sets.items():
                command = [
                    "perf", "stat",
                    "-j",
                    "-e", event_set,
                    args.workload
                ] + (args.arguments or [])

                for _ in range(args.iteration):
                    activity_event.set()
                    start = time.perf_counter()
                    
                    proc = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    activity_event.clear()
                    duration_ms = (time.perf_counter() - start) * 1000
                    wall_times.append(duration_ms)

                    perf_records[event_set_k].append(parse_perf_output(proc.stderr))

        else:
            command = [args.workload] + (args.arguments or [])
            for _ in range(args.iteration):
                activity_event.set()
                start = time.perf_counter()
                
                proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                activity_event.clear()
                duration_ms = (time.perf_counter() - start) * 1000
                wall_times.append(duration_ms)

    finally:
        shutdown_event.set()
        for daemon in daemon_threads:
            daemon.join()

    wall_time_metric = compute_wall_time_metric(wall_times)
    print(wall_time_metric)

    if "cpu" in selected_metrics:
        ipc_metric, branch_prediction_metric, system_metric = compute_execution_core_metrics(perf_records["execution_core"])
        l1_cache_metric, l2_cache_metric                    = compute_private_cache_metrics(perf_records["private_caches"])
        llc_cache_metric                                    = compute_shared_cache_metrics(perf_records["shared_caches"])

        print(ipc_metric)
        print(branch_prediction_metric)
        print(l1_cache_metric)
        print(l2_cache_metric)
        print(llc_cache_metric)
        print(system_metric)

    if "memory" in selected_metrics:
        memory_metrics = compute_memory_metrics(memory_records)
        print(memory_metrics)
    
    if "gpu" in selected_metrics:
        gpu_metrics = compute_gpu_metrics(gpu_records)
        print(gpu_metrics)

def main():
    args = parse_args()
    run_workload(args)

if __name__ == "__main__":
    main()