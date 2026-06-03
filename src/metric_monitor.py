import subprocess
import threading
import time
from typing import Callable
import psutil

from record_parser import parse_rocm_smi_output

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
    thread_records: list[dict[str, float]]
) -> None:

    while not shutdown_event.is_set():
        activity_event.wait()

        if shutdown_event.is_set():
            break

        while activity_event.is_set():
            try:
                active_pid = active_pid_ref[0]
                if active_pid > 0:
                    root_proc = psutil.Process(active_pid)

                    children = root_proc.children(recursive=True)
                    target_proc = children[0] if children else root_proc

                    threads = target_proc.num_threads()
                    thread_records.append({'threads': float(threads)})
                    
                    time.sleep(interval)
            except:
                pass


def monitor_process_memory(
    activity_event: threading.Event,
    shutdown_event: threading.Event,
    interval:       float,
    active_pid_ref: list[int],
    memory_records: list[dict[str, float]]
) -> None:

    while not shutdown_event.is_set():
        activity_event.wait()

        if shutdown_event.is_set():
            break

        while activity_event.is_set():
            try:
                active_pid = active_pid_ref[0]
                if active_pid > 0:
                    root_proc   = psutil.Process(active_pid)
                    children    = root_proc.children(recursive = True)
                    target_proc = children[0] if children else root_proc
                    memory      = target_proc.memory_info()

                    memory_records.append({
                        "rss_mb": memory.rss / (1024 ** 2),
                        "vms_mb": memory.vms / (1024 ** 2)
                    })
                    
                    time.sleep(interval)
            except:
                pass

def monitor_amd_gpu(
    activity_event: threading.Event, 
    shutdown_event: threading.Event, 
    interval:       float, 
    gpu_records:    list[dict[str, float]],
    device_index:   int = 0
):
    try:
        import amdsmi
        amdsmi.amdsmi_init()
        processor_handles = amdsmi.amdsmi_get_processor_handles()
        total_devices     = len(processor_handles)
        
        if device_index >= total_devices:
            print(f"Invalid GPU device index {device_index}. Total available devices: {total_devices}")
            return
            
    except Exception as e:
        print(f"Warning: amdsmi initialization failed during validation: {e}")
        return
    finally:
        try:
            amdsmi.amdsmi_shut_down()
        except:
            pass

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

        try:
            rocm_smi_result = subprocess.run(
                command, 
                capture_output = True, 
                text           = True, 
                check          = True
            )

            record = parse_rocm_smi_output(rocm_smi_result.stdout.strip(), device_index)
            gpu_records.append(record)

        except:
            pass

        time.sleep(interval)