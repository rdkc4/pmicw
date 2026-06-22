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
from dataclasses import asdict, dataclass
import json
import signal
import subprocess
import sys
import threading
import time
import os
import psutil

from cli_parser import parse_runner_args
from command_config import CommandConfig, load_command_config
from measurement import Measurement, Metadata, Metrics, Workload
from metric_computer import compute_records
from metric_monitor import start_monitoring
from metric_config import ProfilerConfig, Segments, load_config
from record_parser import parse_perf_output
from csv_writer import write
from threshold_config_generator import compute_thresholds
from workload_context import WorkloadContext, WorkloadMetricSelection, WorkloadMonitors

@dataclass
class RunnerResult:
    """
    Result of workload execution containing:\n
    id of the executed run, name of the executed workload, and csv path to its storage

    This format is required by run.sh script, these results are passed to comparison tool
    """
    run_id:        str
    workload_name: str
    csv_path:      str

    def to_json(self):
        return json.dumps(asdict(self))

def run_workload(ctx: WorkloadContext, cfg: ProfilerConfig, cmd_cfg: CommandConfig) -> dict[str, Metrics]:
    """
    Entry point for workload execution

    ctx: context of the workload\n
    cfg: metric configuration

    Spawns daemon monitor threads and executes workload\n
    If perf event groups are defined, each group will run for number of iterations set by CLI

    Returns dict that maps segment name to its metrics
    """

    start_monitoring(ctx, cfg, cmd_cfg)
    try:
        wrapper  = cmd_cfg.bash_wrapper.base_command if ctx.selected_metrics.startup else []
        wrapper += ctx.command

        # preventing cold runs to affect statistics (optional)
        warmup_workload(ctx.command, ctx.warmup_iterations)
        if ctx.selected_metrics.cpu:
            for event_group in cfg.segments[Segments.CPU].perf_groups:
                command = list(cmd_cfg.perf.base_command) + [f"{{{",".join(event_group.events)}}}"] + wrapper
                execute_workload(command, ctx)

        else:
            execute_workload(wrapper, ctx)

    finally:
        ctx.monitors.shutdown_event.set()
        ctx.monitors.activity_event.set()
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
    """
    Executes the workload command

    Measures the wall time\n
    Notifies monitors when to start/stop\n
    Parses perf records if defined
    """
    for _ in range(ctx.iterations):
        ctx.monitors.activity_event.clear()
        try:
            proc = subprocess.Popen(
                command,
                stdout = subprocess.DEVNULL,
                stderr = subprocess.PIPE,
                text   = True,
                env    = env
            )
        except Exception as e:
            print(f"Failed to start process: {e}", file = sys.stderr)
            continue
        
        if ctx.selected_metrics.cpu:
            try:
                perf_process = psutil.Process(proc.pid)
                children     = []
                deadline     = time.time() + 5.0

                while time.time() < deadline:
                    try:
                        children = perf_process.children()
                        if children:
                            break

                    except psutil.NoSuchProcess:
                        break

                    time.sleep(0.01)

                target_pid = children[0].pid if children else proc.pid

            except psutil.NoSuchProcess:
                target_pid = proc.pid
        else:
            target_pid = proc.pid

        ctx.monitors.active_pid[0] = target_pid
        ctx.monitors.activity_event.set()

        if ctx.selected_metrics.startup:
            # giving some time for bpfscript to compile
            time.sleep(2)
            start = time.perf_counter()
            
            # Send SIGCONT to wake up the suspended shell, letting it fall through to 'exec'
            try:
                os.kill(target_pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
        
        else:
            start = time.perf_counter()

        _, stderr = proc.communicate()
        
        ctx.monitors.activity_event.clear()
        ctx.monitors.active_pid[0] = -1

        if proc.returncode != 0:
            print(f"Warning: workload '{" ".join(ctx.command)}' failed with exit code {proc.returncode}.\n", file = sys.stderr)
            continue

        ctx.records[Segments.WALL_TIME].append({'execution_time': (time.perf_counter() - start) * 1000})
        
        if ctx.selected_metrics.cpu:
            perf_record = parse_perf_output(stderr)
            ctx.records[Segments.PERF].append(perf_record)

def setup_workload_context(args: argparse.Namespace):
    """
    Defines selected metrics\n
    Defines monitor data\n
    Loads workload context from CLI
    """
    env = os.environ.copy()

    metrics = WorkloadMetricSelection(
        wall_time = True,
        cpu       = Segments.CPU     in args.metric,
        gpu       = Segments.GPU     in args.metric,
        memory    = Segments.MEMORY  in args.metric,
        thread    = Segments.THREAD  in args.metric,
        startup   = Segments.STARTUP in args.metric
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
        name              = args.workload.split('/')[-1], # workload name is the file name, previous path is ignored
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
    cfg      = load_config("config/metric_config.yaml")
    cmd_cfg  = load_command_config("config/command_config.yaml")
    ctx      = setup_workload_context(args)
    workload = assemble_workload(args)

    try:
        metrics = run_workload(ctx, cfg, cmd_cfg)

    except RuntimeError as e:
        print(f"Error: {e}", file = sys.stderr)
        sys.exit(1)

    measurement = assemble_measurement(workload, metrics, cfg)
    path = write(measurement)

    if not path:
        sys.exit(1)

    compute_thresholds(args, "config/comparison_threshold_config.yaml", measurement)
        
    result = RunnerResult(str(measurement.metadata.run_id), measurement.workload.name, str(path))
    print(result.to_json(), file = sys.stdout)

if __name__ == "__main__":
    main()