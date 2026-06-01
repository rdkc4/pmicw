#!/usr/bin/env python3
"""
Orchestration and Workload Execution Engine.

This module coordinates the active profiling lifecycle. It parses user requests,
spawns asynchronous background resource samplers, executes target workloads under
hardware counters, and routes collected payloads to the aggregation layer.

Asynchronous Thread Coordination Model:
    [Main Thread]                   [Background Threads]
          |                                  |
          |--> gpu_thread.start() ---------->| (Idle / Event Blocked)
          |                                  |
       |->| Loop: Iteration                  |
       |  |--> activity_event.set() -------->| (Wake up & sample hardware)
       |  |--> subprocess.Popen(workload)    | (Active Execution)
       |  |--> sample rss and vms            |
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
    $ ./workload_runner.py workload [workload-options] [options]
"""
import argparse
from dataclasses import dataclass
import subprocess
import threading
import time
import os

import psutil

from cli_parser import parse_args
from measurement import Measurement, Metadata, Metrics, Workload
from metric_computer import compute_metrics
from metric_monitor import monitor_amd_gpu, monitor_process_memory
from record_parser import parse_cpu_prof_output
from csv_writer import write

@dataclass
class WorkloadRecords:
    wall_times:     list[float]
    memory_records: list[dict[str, float]]
    gpu_records:    list[dict[str, float]]
    perf_records:   dict[str, list[dict[str, float]]]
    link_records:   list[dict[str, float]]

@dataclass
class WorkloadMonitors:
    interval:       float
    activity_event: threading.Event
    shutdown_event: threading.Event
    daemon_threads: list[threading.Thread]

@dataclass
class WorkloadContext:
    iterations:        int
    warmup_iterations: int
    selected_metrics:  list[str]
    command:           list[str]
    env:               dict[str, str]
    records:           WorkloadRecords
    monitors:          WorkloadMonitors

@dataclass
class PerfGroupConfig:
    name:   str
    events: list[str]
    env:    dict[str, str] | None

def run_workload(ctx: WorkloadContext) -> Metrics:
    perf_event_groups = set_perf_events("cpu" in ctx.selected_metrics, ctx.env)

    if "gpu" in ctx.selected_metrics:
        daemon = threading.Thread(
            target = monitor_amd_gpu,
            args   = (ctx.monitors.activity_event, ctx.monitors.shutdown_event, ctx.monitors.interval, ctx.records.gpu_records),
            daemon =True
        )
        ctx.monitors.daemon_threads.append(daemon)
        daemon.start()

    try:
        warmup_workload(ctx.command)

        if perf_event_groups:
            for event_group in perf_event_groups:
                command = ["perf", "stat", "-j", "-e", f"{{{",".join(event_group.events)}}}"] + ctx.command

                wall_times, perf_records, memory_records, link_records = execute_workload(
                    command         = command,
                    ctx             = ctx,
                    cpu_selected    = "cpu" in ctx.selected_metrics,
                    memory_selected = "memory" in ctx.selected_metrics,
                    env             = event_group.env
                )

                ctx.records.wall_times                    += wall_times
                ctx.records.memory_records                += memory_records
                ctx.records.perf_records[event_group.name] = perf_records
                if link_records:
                    ctx.records.link_records              += link_records

        else:
            wall_times, _, memory_records, _ = execute_workload(
                command         = ctx.command,
                ctx             = ctx,
                cpu_selected    = "cpu" in ctx.selected_metrics,
                memory_selected = "memory" in ctx.selected_metrics  
            )

            ctx.records.wall_times      = wall_times
            ctx.records.memory_records += memory_records

    finally:
        ctx.monitors.shutdown_event.set()
        for daemon in ctx.monitors.daemon_threads:
            daemon.join()

    metrics = compute_metrics(
        ctx.selected_metrics, 
        ctx.records.wall_times, 
        ctx.records.perf_records, 
        ctx.records.memory_records, 
        ctx.records.gpu_records,
        ctx.records.link_records
    )

    return metrics

def warmup_workload(command: list[str], warmup_iterations: int = 0) -> None:
    for _ in range(warmup_iterations):
        subprocess.run(command)

def execute_workload(
    command:         list[str],
    ctx:             WorkloadContext,
    cpu_selected:    bool,
    memory_selected: bool,
    env:             dict[str, str] | None = None
) -> tuple[list[float], list[dict[str, float]], list[dict[str, float]], list[dict[str, float]]]:
    
    wall_times:     list[float]            = []
    perf_records:   list[dict[str, float]] = []
    memory_records: list[dict[str, float]] = []
    link_records:   list[dict[str, float]] = []

    for _ in range(ctx.iterations):
        ctx.monitors.activity_event.set()
        start = time.perf_counter()

        proc = subprocess.Popen(
            command,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text   = True,
            env    = env
        )

        parent_process     = psutil.Process(proc.pid)
        children_processes = parent_process.children(recursive = True)
        program_process    = children_processes[0] if cpu_selected and len(children_processes) > 0 else parent_process

        if memory_selected:
            memory_samples  = monitor_process_memory(proc, program_process, ctx.monitors.interval)
            memory_records += memory_samples

        _, stderr = proc.communicate()

        ctx.monitors.activity_event.clear()
        wall_times.append((time.perf_counter() - start) * 1000)
        
        if cpu_selected:
            perf_record, link_record = parse_cpu_prof_output(stderr, proc.pid)
            perf_records.append(perf_record)
            link_records.append(link_record)

    return wall_times, perf_records, memory_records, link_records
    

def set_perf_events(cpu_selected: bool, env: dict[str,str] | None = None) -> list[PerfGroupConfig]:
    if cpu_selected:
        perf_event_groups = [
            PerfGroupConfig(
                name   = "execution_core",
                events = [
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
                env    = env
            ),
            PerfGroupConfig(
                name   = "l1_caches",
                events = [
                    "L1-dcache-loads",
                    "L1-dcache-load-misses",
                    "L1-icache-loads",
                    "L1-icache-load-misses"
                ],
                env    = None
            ),
            PerfGroupConfig(
                name   = "l2_llc_caches",
                events = [
                    "l2_cache_req_stat.all",
                    "l2_cache_req_stat.ic_dc_miss_in_l2",
                    "cache-references",
                    "cache-misses"
                ],
                env    = None
            )
        ]
        return perf_event_groups

    return []

def setup_workload_context(args: argparse.Namespace):
    env = os.environ.copy()
    env["LD_DEBUG"]    = "statistics"
    env["LD_BIND_NOW"] = "1"

    records = WorkloadRecords(
        wall_times     = [],
        memory_records = [],
        gpu_records    = [],
        perf_records   = {
            "execution_core": [],
            "l1_caches":      [],
            "l2_llc_caches":  []
        },
        link_records   = []
    )

    monitors = WorkloadMonitors(
        interval       = 0.1,
        activity_event = threading.Event(),
        shutdown_event = threading.Event(),
        daemon_threads = []
    )

    return WorkloadContext(
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        selected_metrics  = args.metric,
        command           = [args.workload] + (args.arguments or []),
        env               = env,
        records           = records,
        monitors          = monitors
    )

def assemble_workload(args: argparse.Namespace) -> Workload:
    return Workload(
        name              = args.workload,
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        arguments         = args.arguments
    )

def assemble_measurement(workload: Workload, metrics: Metrics) -> Measurement:
    return Measurement(
        metadata  = Metadata(),
        workload = workload,
        metrics  = metrics
    )

def main():
    args        = parse_args()
    ctx         = setup_workload_context(args)
    workload    = assemble_workload(args)
    metrics     = run_workload(ctx)
    measurement = assemble_measurement(workload, metrics)
    write(measurement)

if __name__ == "__main__":
    main()