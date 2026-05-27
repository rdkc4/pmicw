import argparse
import json
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
    wall_times:     list[float]            = []
    memory_records: list[dict[str, float]] = []
    gpu_records:    list[dict[str, float]] = []
    perf_records:   dict[str, list[dict[str, float]]] = {
        "execution_core": [],
        "private_caches": [],
        "shared_caches":  []
    }

    perf_event_sets = {
        "execution_core": "'{instructions,cycles,branches,branch-misses,context-switches,page-faults,minor-faults,major-faults}'", 
        "private_caches": "'{L1-dcache-loads,L1-dcache-load-misses,l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_miss_in_l2}'", 
        "shared_caches":  "'{cache-references,cache-misses}'"
    }

    activity_event = threading.Event()
    shutdown_event = threading.Event()

    mem_thread = threading.Thread(
        target = monitor_memory,
        args   = (activity_event, shutdown_event, 0.1, memory_records),
        daemon = True
    )
    gpu_thread = threading.Thread(
        target = monitor_amd_gpu,
        args   = (activity_event, shutdown_event, 0.1, gpu_records),
        daemon = True
    )

    mem_thread.start()
    gpu_thread.start()

    try:
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

    finally:
        shutdown_event.set()
        mem_thread.join()
        gpu_thread.join()

    wall_time_metric                                    = compute_wall_time_metric(wall_times)
    ipc_metric, branch_prediction_metric, system_metric = compute_execution_core_metrics(perf_records["execution_core"])
    l1_cache_metric, l2_cache_metric                    = compute_private_cache_metrics(perf_records["private_caches"])
    llc_cache_metric                                    = compute_shared_cache_metrics(perf_records["shared_caches"])
    memory_metrics                                      = compute_memory_metrics(memory_records)
    gpu_metrics                                         = compute_gpu_metrics(gpu_records)

    print(wall_time_metric)
    print(ipc_metric)
    print(branch_prediction_metric)
    print(l1_cache_metric)
    print(l2_cache_metric)
    print(llc_cache_metric)
    print(system_metric)
    print(memory_metrics)
    print(gpu_metrics)

def main():
    args = parse_args()
    run_workload(args)

if __name__ == "__main__":
    main()