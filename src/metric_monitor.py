import subprocess
import threading
import time
from typing import Callable
import psutil

from metrics_config import SegmentConfig
from record_parser import parse_rocm_smi_output
from record_types import Record, RecordList

def spawn_monitor_daemon(
    target:  Callable,
    args:    tuple,
    daemons: list[threading.Thread]
) -> None:
    daemon = threading.Thread(
        target = target,
        args   = args,
        daemon = True
    )

    daemons.append(daemon)
    daemon.start()

def monitor_process_threads(
    activity_event: threading.Event,
    shutdown_event: threading.Event,
    interval:       float,
    active_pid_ref: list[int],
    thread_records: RecordList,
    segment_config: SegmentConfig
) -> None:

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
                    root_proc = psutil.Process(active_pid)

                    children = root_proc.children(recursive = True)
                    target_proc = children[0] if children else root_proc

                    record = sample_values(target_proc.as_dict(), events)

                    if record:
                        thread_records.append(record)

            except:
                pass

            time.sleep(interval)

def monitor_process_memory(
    activity_event: threading.Event,
    shutdown_event: threading.Event,
    interval:       float,
    active_pid_ref: list[int],
    memory_records: RecordList,
    segment_config: SegmentConfig
) -> None:
    
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
                    root_proc   = psutil.Process(active_pid)
                    children    = root_proc.children(recursive = True)
                    target_proc = children[0] if children else root_proc
                    
                    memory = target_proc.memory_full_info()
                    record = sample_values(memory._asdict(), events)
                    if record:
                        memory_records.append(record)
                    
            except:
                pass

            time.sleep(interval)

def monitor_amd_gpu(
    activity_event: threading.Event, 
    shutdown_event: threading.Event, 
    interval:       float, 
    gpu_records:    RecordList,
    segment_config: SegmentConfig,
    device_index:   int = 0
) -> None:
    
    events = segment_config.read_keys()
    if not events:
        return

    if not gpu_exists(device_index):
        return

    command = [
        "rocm-smi", 
        "--showuse", "--showmemuse", 
        f"--device={device_index}", 
        "--json"
    ]

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

                record = sample_values(parse_rocm_smi_output(rocm_smi_result.stdout.strip(), device_index), events)
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
                record[metric] = float(records[metric])
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
            print(f"Invalid GPU device index {device_index}. Total available devices: {total_devices}")
            return False
            
    except Exception as e:
        print(f"Warning: amdsmi initialization failed during validation: {e}")
        return False

    finally:
        try:
            amdsmi.amdsmi_shut_down()
        except:
            return False
    
    return True