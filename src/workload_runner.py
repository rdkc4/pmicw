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
import subprocess
import sys
import threading
import time
import os

from cli_parser import parse_runner_args
from measurement import Measurement, Metadata, Metrics, Workload
from metric_computer import compute_records
from metric_monitor import start_monitoring
from metrics_config import PerfGroupConfig, ProfilerConfig, Segments, load_config
from record_parser import parse_cpu_prof_output
from csv_writer import write
from workload_context import WorkloadContext, WorkloadMetricSelection, WorkloadMonitors

def run_workload(ctx: WorkloadContext, cfg: ProfilerConfig) -> dict[str, Metrics]:
    perf_event_groups = get_perf_groups(cfg, ctx.selected_metrics.cpu, ctx.env)
    
    start_monitoring(ctx, cfg)
    try:
        warmup_workload(ctx.command, ctx.warmup_iterations)

        if perf_event_groups:
            for event_group in perf_event_groups:
                command = ["perf", "stat", "-j", "-e", f"{{{",".join(event_group.events)}}}"] + ctx.command
                execute_workload(command, ctx, event_group.env)

        else:
            execute_workload(ctx.command, ctx)

    finally:
        ctx.monitors.shutdown_event.set()
        for daemon in ctx.monitors.daemon_threads:
            daemon.join()

    return compute_records(cfg, ctx.records)

def warmup_workload(command: list[str], warmup_iterations: int = 0) -> None:
    for _ in range(warmup_iterations):
        subprocess.run(command)

def execute_workload(
    command: list[str],
    ctx:     WorkloadContext,
    env:     dict[str, str] | None = None
) -> None:
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
        ctx.records[Segments.WALL_TIME].append({'execution_time': (time.perf_counter() - start) * 1000})
        
        if ctx.selected_metrics.cpu:
            perf_record, link_record = parse_cpu_prof_output(stderr, proc.pid)
            ctx.records[Segments.PERF].append(perf_record)
            ctx.records[Segments.LD].append(link_record)

    
def get_perf_groups(cfg: ProfilerConfig, cpu_selected: bool, base_env: dict[str, str]) -> list[PerfGroupConfig]:
    if not cpu_selected or Segments.CPU not in cfg.segments:
        return []
    
    active_groups = []
    cpu_segment   = cfg.segments[Segments.CPU]

    for group in cpu_segment.perf_groups:
        group_env = None
        if group.use_ld_env:
            group_env = base_env.copy()
            group_env["LD_DEBUG"] = "statistics"
            group_env["LD_BIND_NOW"] = "1"
        
        active_groups.append(
            PerfGroupConfig(
                name   = group.name,
                events = group.events,
                env    = group_env
            )
        )

    return active_groups

def setup_workload_context(args: argparse.Namespace, cfg: ProfilerConfig):
    env = os.environ.copy()

    metrics = WorkloadMetricSelection(
        wall_time = True,
        cpu       = Segments.CPU    in args.metric,
        gpu       = Segments.GPU    in args.metric,
        memory    = Segments.MEMORY in args.metric,
        thread    = Segments.THREAD in args.metric
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
        records           = {segment: [] for segment in Segments},
        monitors          = monitors
    )

def assemble_workload(args: argparse.Namespace) -> Workload:
    return Workload(
        name              = args.workload.split('/')[-1],
        iterations        = args.iteration,
        warmup_iterations = args.warmup_iteration,
        arguments         = args.workload_args or []
    )

def assemble_measurement(workload: Workload, metrics: dict[str, Metrics], cfg: ProfilerConfig) -> Measurement:
    return Measurement(
        metadata = Metadata(),
        workload = workload,
        metrics  = metrics,
        cfg      = cfg
    )

def main():
    args     = parse_runner_args()
    cfg      = load_config("config/metrics_config.yaml")
    ctx      = setup_workload_context(args, cfg)
    workload = assemble_workload(args)

    try:
        metrics = run_workload(ctx, cfg)

    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    measurement = assemble_measurement(workload, metrics, cfg)
    write(measurement)

if __name__ == "__main__":
    main()