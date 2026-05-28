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
from dataclasses import dataclass
import subprocess
import threading
import time
from typing import Callable

from cli_parser import parse_args
from metric_computer import compute_metrics
from metric_monitor import monitor_amd_gpu, monitor_memory, start_monitor
from record_parser import parse_perf_output

@dataclass
class WorkloadRecords:
    wall_times:       list[float]
    memory_records:   list[dict[str, float]]
    gpu_records:      list[dict[str, float]]
    perf_records:     dict[str, list[dict[str, float]]]

@dataclass
class WorkloadMonitors:
    activity_event: threading.Event
    shutdown_event: threading.Event
    daemon_threads: list[threading.Thread]

@dataclass
class WorkloadContext:
    iterations:        int
    warmup_iterations: int
    monitor_interval:  float
    selected_metrics:  list[str]
    command:           list[str]
    records:           WorkloadRecords
    monitors:          WorkloadMonitors

def run_workload(ctx: WorkloadContext) -> None:
    perf_event_groups = set_perf_events("cpu" in ctx.selected_metrics)

    activity_event = threading.Event()
    shutdown_event = threading.Event()
    daemon_threads = []

    if "memory" in ctx.selected_metrics:
        daemon_threads.append(
            start_monitor(
                monitor_memory, 
                activity_event, 
                shutdown_event, 
                ctx.monitor_interval, 
                ctx.records.memory_records
            )
        )

    if "gpu" in ctx.selected_metrics:
        daemon_threads.append(
            start_monitor(
                monitor_amd_gpu, 
                activity_event, 
                shutdown_event, 
                ctx.monitor_interval, 
                ctx.records.gpu_records
            )
        )

    try:
        warmup_workload(ctx.command)

        if perf_event_groups:
            for event_group_k, event_group in perf_event_groups.items():
                command = ["perf", "stat", "-j", "-e", f"{{{",".join(event_group)}}}"] + ctx.command

                wall_times, records = execute_workload(
                    command         = command, 
                    iterations      = ctx.iterations, 
                    activity_event  = activity_event, 
                    parser          = parse_perf_output
                )

                ctx.records.wall_times += wall_times
                ctx.records.perf_records[event_group_k] = records

        else:
            wall_times, _ = execute_workload(
                command        = ctx.command,
                iterations     = ctx.iterations,
                activity_event = activity_event         
            )

    finally:
        shutdown_event.set()
        for daemon in daemon_threads:
            daemon.join()

    metrics = compute_metrics(
        ctx.selected_metrics, 
        ctx.records.wall_times, 
        ctx.records.perf_records, 
        ctx.records.memory_records, 
        ctx.records.gpu_records
    )

    print(metrics)

def warmup_workload(command: list[str], warmup_iterations: int = 0) -> None:
    for _ in range(warmup_iterations):
        subprocess.run(command)

def execute_workload(
    command:        list[str],
    iterations:     int,
    activity_event: threading.Event,
    parser:         Callable[[str], dict[str, float]] | None = None
) -> tuple[list[float], list[dict[str, float]]]:
    
    wall_times: list[float]            = []
    records:    list[dict[str, float]] = []

    for _ in range(iterations):
        activity_event.set()
        start = time.perf_counter()

        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        activity_event.clear()
        wall_times.append((time.perf_counter() - start) * 1000)

        if parser:
            records.append(parser(proc.stderr))

    return wall_times, records
    

def set_perf_events(cpu_selected: bool) -> dict[str, list[str]]:
    if cpu_selected:
        perf_event_groups = {
            "execution_core": [
                "instructions",
                "cycles",
                "branches",
                "branch-misses",
                "task-clock",
                "context-switches",
                "page-faults",
                "minor-faults",
                "major-faults"
            ],
            "private_caches": [
                "L1-dcache-loads",
                "L1-dcache-misses",
                "l2_cache_req_stat.all",
                "l2_cache_req_stat.ic_dc_miss_in_l2"
            ],
            "shared_caches": [
                "cache-references",
                "cache-misses"
            ]
        }
        return perf_event_groups

    return {}

def setup_workload_context(args: argparse.Namespace):
    records = WorkloadRecords(
        wall_times = [],
        memory_records = [],
        gpu_records = [],
        perf_records = {
            "execution_core": [],
            "private_caches": [],
            "shared_caches":  []
        }
    )

    monitors = WorkloadMonitors(
        activity_event = threading.Event(),
        shutdown_event = threading.Event(),
        daemon_threads = []
    )

    return WorkloadContext(
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        monitor_interval  = 0.1,
        selected_metrics  = args.metric,
        command           = [args.workload] + (args.arguments or []),
        records           = records,
        monitors          = monitors
    )

def main():
    args = parse_args()
    ctx = setup_workload_context(args)
    run_workload(ctx)

if __name__ == "__main__":
    main()