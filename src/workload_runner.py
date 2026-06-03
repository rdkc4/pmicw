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
          |--> mem_thread.start() ---------->|
          |--> thr_thread.start() ---------->|
          |                                  |
       |->| Loop: Iteration                  |
       |  |--> activity_event.set() -------->| (Wake up & sample hardware)
       |  |--> subprocess.Popen(workload)    | (Active Execution)
       |  |                                  |
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
    $ ./workload_runner.py [options] <workload> [workload-args...]
"""
import argparse
from dataclasses import dataclass
import subprocess
import sys
import threading
import time
import os

from cli_parser import parse_args
from measurement import Measurement, Metadata, Metrics, Workload
from metric_computer import compute_metrics
from metric_monitor import monitor_amd_gpu, monitor_process_memory, monitor_process_threads, spawn_monitor_daemon
from record_parser import parse_cpu_prof_output
from csv_writer import write
from record_types import RecordList
from workload_context import WorkloadContext, WorkloadMetricSelection, WorkloadMonitors
from typing import TypeAlias

WorkloadMetrics: TypeAlias = tuple[RecordList, RecordList, RecordList, RecordList, RecordList]

@dataclass
class PerfGroupConfig:
    name:   str
    events: list[str]
    env:    dict[str, str] | None

def run_workload(ctx: WorkloadContext) -> Metrics:
    perf_event_groups = set_perf_events(ctx.selected_metrics.cpu, ctx.env)

    if ctx.selected_metrics.gpu:
        spawn_monitor_daemon(
            target  = monitor_amd_gpu,
            args    = (
                ctx.monitors.activity_event, 
                ctx.monitors.shutdown_event, 
                ctx.monitors.interval, 
                ctx.records['gpu']
            ),
            daemons = ctx.monitors.daemon_threads
        )

    if ctx.selected_metrics.memory:
        spawn_monitor_daemon(
            target  = monitor_process_memory,
            args    = (
                ctx.monitors.activity_event, 
                ctx.monitors.shutdown_event, 
                ctx.monitors.interval, 
                ctx.monitors.active_pid, 
                ctx.records['memory']
            ),
            daemons = ctx.monitors.daemon_threads
        )

    if ctx.selected_metrics.thread:
        spawn_monitor_daemon(
            target  = monitor_process_threads,
            args    = (
                ctx.monitors.activity_event, 
                ctx.monitors.shutdown_event, 
                ctx.monitors.interval, 
                ctx.monitors.active_pid, 
                ctx.records['thread']
            ),
            daemons = ctx.monitors.daemon_threads
        )

    try:
        warmup_workload(ctx.command)

        if perf_event_groups:
            for event_group in perf_event_groups:
                command = ["perf", "stat", "-j", "-e", f"{{{",".join(event_group.events)}}}"] + ctx.command

                wall_times, perf_records, memory_records, link_records, thread_records = execute_workload(
                    command = command,
                    ctx     = ctx,
                    env     = event_group.env
                )

                ctx.records['wall-time'] += wall_times
                ctx.records['memory']    += memory_records
                ctx.records['perf']      += perf_records
                ctx.records['thread']    += thread_records
                ctx.records['ld']        += link_records

        else:
            wall_times, _, memory_records, _, thread_records = execute_workload(
                command = ctx.command,
                ctx     = ctx
            )

            ctx.records['wall-time']  = wall_times
            ctx.records['memory']    += memory_records
            ctx.records['thread']    += thread_records

    finally:
        ctx.monitors.shutdown_event.set()
        for daemon in ctx.monitors.daemon_threads:
            daemon.join()

    return compute_metrics(ctx.selected_metrics, ctx.records)

def warmup_workload(command: list[str], warmup_iterations: int = 0) -> None:
    for _ in range(warmup_iterations):
        subprocess.run(command)

def execute_workload(
    command: list[str],
    ctx:     WorkloadContext,
    env:     dict[str, str] | None = None
) -> WorkloadMetrics:
    
    wall_times:     RecordList = []
    perf_records:   RecordList = []
    memory_records: RecordList = []
    link_records:   RecordList = []
    thread_records: RecordList = []

    for _ in range(ctx.iterations):
        start = time.perf_counter()

        proc = subprocess.Popen(
            command,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text   = True,
            env    = env
        )

        ctx.monitors.active_pid[0] = proc.pid
        ctx.monitors.activity_event.set()

        _, stderr = proc.communicate()

        if proc.returncode != 0:
            ctx.monitors.activity_event.clear()
            raise RuntimeError(
                f"Workload '{" ".join(command)}' failed with exit code {proc.returncode}.\n"
            )

        ctx.monitors.activity_event.clear()
        ctx.monitors.active_pid[0] = -1
        wall_times.append({'execution_time': (time.perf_counter() - start) * 1000})
        
        if ctx.selected_metrics.cpu:
            perf_record, link_record = parse_cpu_prof_output(stderr, proc.pid)
            perf_records.append(perf_record)
            link_records.append(link_record)

    return wall_times, perf_records, memory_records, link_records, thread_records
    

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

    metrics = WorkloadMetricSelection(
        wall_time = True,
        cpu       = 'cpu'    in args.metric,
        gpu       = 'gpu'    in args.metric,
        memory    = 'memory' in args.metric,
        thread    = 'thread' in args.metric
    )

    monitors = WorkloadMonitors(
        active_pid     = [-1],
        interval       = 0.1,
        activity_event = threading.Event(),
        shutdown_event = threading.Event(),
        daemon_threads = []
    )

    return WorkloadContext(
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        selected_metrics  = metrics,
        command           = [args.workload] + (args.workload_args or []),
        env               = env,
        records           = {
            'wall-time': [],
            'perf':      [],
            'ld':        [],
            'gpu':       [],
            'memory':    [],
            'thread':    []
        },
        monitors          = monitors
    )

def assemble_workload(args: argparse.Namespace) -> Workload:
    return Workload(
        name              = args.workload,
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        arguments         = args.workload_args or []
    )

def assemble_measurement(workload: Workload, metrics: Metrics) -> Measurement:
    return Measurement(
        metadata = Metadata(),
        workload = workload,
        metrics  = metrics
    )

def main():
    args     = parse_args()
    ctx      = setup_workload_context(args)
    workload = assemble_workload(args)

    try:
        metrics = run_workload(ctx)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    measurement = assemble_measurement(workload, metrics)
    write(measurement)

if __name__ == "__main__":
    main()