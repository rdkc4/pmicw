from dataclasses import dataclass
import subprocess
import sys
import threading
import time
from typing import Callable
import psutil

from command_config import BPFTraceStartupCommandConfig, CommandConfig, RocmSMICommandConfig
from metric_config import ProfilerConfig, SegmentConfig, Segments
from record_parser import parse_bpftrace_output, parse_rocm_smi_output
from record_types import Record, RecordList
from workload_context import WorkloadContext

@dataclass
class MonitorSpecification:
    """
    Specifies the target of the monitor,
    and if monitor requires a process id to sample data
    """
    target:       Callable
    req_cfg:      bool
    req_pid:      bool
    req_interval: bool

def get_monitors() -> dict[Segments, MonitorSpecification]:
    return {
        Segments.THREAD:  MonitorSpecification(target = monitor_process_threads, req_cfg = True,  req_pid = True,  req_interval = True),
        Segments.MEMORY:  MonitorSpecification(target = monitor_process_memory,  req_cfg = True,  req_pid = True,  req_interval = True),
        Segments.GPU:     MonitorSpecification(target = monitor_amd_gpu,         req_cfg = True,  req_pid = False, req_interval = True),
        Segments.STARTUP: MonitorSpecification(target = monitor_process_startup, req_cfg = False, req_pid = True,  req_interval = False)
    }

def start_monitoring(ctx: WorkloadContext, cfg: ProfilerConfig, cmd_cfg: CommandConfig) -> None:
    """
    Entry point for monitoring

    ctx:     context of the workload\n
    cfg:     metric configuration
    cmd_cfg: command configuration (for rocm-smi)

    Starts monitors of the selected segments (memory, thread, gpu)
    """
    monitors = get_monitors()

    for segment, monitor in monitors.items():
        if not getattr(ctx.selected_metrics, segment):
            continue

        cfg_segment = cfg.segments.get(segment)
        if cfg_segment is None:
            print(f"Segment '{segment}' not found in config", file = sys.stderr)
            continue

        # orchestration events
        args: list = [ctx.monitors.activity_event, ctx.monitors.shutdown_event]

        # records
        args.append(ctx.records[segment])


        # requires configuration
        if monitor.req_cfg:
            args.append(cfg_segment)

        # requires interval
        if monitor.req_interval:
            args.append(ctx.monitors.interval)

        # commands
        if segment == Segments.GPU:
            args.append(cmd_cfg.rocm_smi)

        if segment == Segments.STARTUP:
            args.append(cmd_cfg.bpftrace_startup)

        # required process id
        if monitor.req_pid:
            args.append(ctx.monitors.active_pid)

        spawn_monitor_daemon(
            target  = monitor.target,
            args    = tuple(args),
            daemons = ctx.monitors.daemon_threads,
        )

def spawn_monitor_daemon(
    target:  Callable,
    args:    tuple,
    daemons: list[threading.Thread]
) -> None:
    """
    Spawns monitor daemon thread

    target: monitoring target\n
    args: arguments for the target\n
    daemons: reference to a list of all daemons
    """
    daemon = threading.Thread(
        target = target,
        args   = args,
        daemon = True
    )

    daemons.append(daemon)
    daemon.start()

def monitor_process_startup(
    activity_event:  threading.Event,
    shutdown_event:  threading.Event,
    startup_records: RecordList,
    cmd:             BPFTraceStartupCommandConfig,
    active_pid_ref:  list[int]
) -> None:
    """
    Monitors startup cleanly across an infinite number of iterations
    without busy-spinning or state-locking.
    """
    while not shutdown_event.is_set():
        activity_event.wait()

        if shutdown_event.is_set():
            break

        try:
            active_pid = active_pid_ref[0]
            if active_pid > 0:
                command = cmd.base_command + [cmd.pid_flag, str(active_pid), cmd.script]

                proc = subprocess.Popen(
                    command,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE,
                    text   = True
                )

                stdout, _ = proc.communicate()
                
                record = parse_bpftrace_output(stdout.strip())
                if record:
                    startup_records.append(record)

        except Exception as e:
            print(f"Monitor startup error: {e}", file = sys.stderr)
        
        while activity_event.is_set() and not shutdown_event.is_set():
            time.sleep(0.01)

    return

def monitor_process_threads(
    activity_event: threading.Event,
    shutdown_event: threading.Event,
    thread_records: RecordList,
    segment_config: SegmentConfig,
    interval:       float,
    active_pid_ref: list[int],
) -> None:
    """
    Monitors threads of the process

    Starts sampling when activity_event is set\n
    Stops sampling when activity_event is cleared\n
    Stops monitoring when shutdown_event is set

    Events that are monitored are captured from segment configuration\n
    Requires reference to a process id to sample its data

    Note: can sample only fields defined by psutil.Process
    """
    events = segment_config.read_keys_for_target(psutil.Process)
    if not events:
        return
    
    while not shutdown_event.is_set():
        activity_event.wait()

        if shutdown_event.is_set():
            break

        while activity_event.is_set() and not shutdown_event.is_set():
            try:
                active_pid = active_pid_ref[0]
                if active_pid > 0:
                    proc   = psutil.Process(active_pid)

                    record = sample_values(proc.as_dict(), events)
                    if record:
                        thread_records.append(record)

            except:
                pass

            time.sleep(interval)

def monitor_process_memory(
    activity_event: threading.Event,
    shutdown_event: threading.Event,
    memory_records: RecordList,
    segment_config: SegmentConfig,
    interval:       float,
    active_pid_ref: list[int]
) -> None:
    """
    Monitors memory of the process

    Starts sampling when activity_event is set\n
    Stops sampling when activity_event is cleared\n
    Stops monitoring when shutdown_event is set

    Events that are monitored are captured from segment configuration\n
    Requires reference to a process id to sample its data

    Note: can sample only fields defined by psutil._ntp.pfullmem
    """
    
    events = segment_config.read_keys_for_target(psutil._ntp.pfullmem)
    if not events:
        return

    while not shutdown_event.is_set():
        activity_event.wait()

        if shutdown_event.is_set():
            break

        while activity_event.is_set() and not shutdown_event.is_set():
            try:
                active_pid = active_pid_ref[0]
                if active_pid > 0:
                    proc   = psutil.Process(active_pid)
                    memory = proc.memory_full_info()

                    record = sample_values(memory._asdict(), events)
                    if record:
                        memory_records.append(record)
                    
            except:
                pass

            time.sleep(interval)

def monitor_amd_gpu(
    activity_event: threading.Event, 
    shutdown_event: threading.Event, 
    gpu_records:    RecordList,
    segment_config: SegmentConfig,
    interval:       float, 
    cfg:            RocmSMICommandConfig
) -> None:
    """
    Monitors gpu during the execution of the process

    Starts sampling when activity_event is set\n
    Stops sampling when activity_event is cleared\n
    Stops monitoring when shutdown_event is set

    Events that are monitored are captured from segment configuration\n

    Note: can sample only fields available from rocm-smi
    """
    
    events = segment_config.read_keys()
    if not events:
        return

    if not gpu_exists(cfg.device_index):
        return

    command = list(cfg.base_command) + [f"{cfg.device_flag}{cfg.device_index}"]

    while not shutdown_event.is_set():
        activity_event.wait()
        if shutdown_event.is_set():
            break

        while activity_event.is_set() and not shutdown_event.is_set():
            try:
                rocm_smi_result = subprocess.run(
                    command, 
                    capture_output = True, 
                    text           = True, 
                    check          = True
                )

                record = sample_values(parse_rocm_smi_output(rocm_smi_result.stdout.strip(), cfg.device_index), events)
                if record:
                    gpu_records.append(record)

            except:
                pass

            time.sleep(interval)

def sample_values(records: dict, metrics: list[str]) -> Record:
    record = {}

    for metric in metrics:
        if records.get(metric, None) != None:
            try:
                value = float(records[metric])
                if value > 0:
                    record[metric] = value

            except:
                pass

    return record

def gpu_exists(device_index: int) -> bool:
    try:
        import amdsmi
        amdsmi.amdsmi_init()
        processor_handles = amdsmi.amdsmi_get_processor_handles()
        total_devices     = len(processor_handles)
        
        if device_index >= total_devices:
            print(f"Invalid GPU device index {device_index}. Total available devices: {total_devices}", file = sys.stderr)
            return False
            
    except Exception as e:
        print(f"Warning: amdsmi initialization failed during validation: {e}", file = sys.stderr)
        return False

    finally:
        try:
            amdsmi.amdsmi_shut_down() # type: ignore
        except:
            return False
    
    return True