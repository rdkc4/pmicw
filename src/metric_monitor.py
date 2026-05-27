import subprocess
import threading
import time
import psutil
import amdsmi

from record_parser import parse_rocm_smi_output

def monitor_memory(
    activity_event: threading.Event, 
    shutdown_event: threading.Event, 
    interval:       float, 
    memory_records: list[dict[str, float]]
):
    while not shutdown_event.is_set():
        activity_event.wait()
        if shutdown_event.is_set():
            break
        
        mem = psutil.virtual_memory()
        swp = psutil.swap_memory()

        memory_records.append({
            "mem_pct": mem.percent,
            "swp_pct": swp.percent
        })

        time.sleep(interval)

def monitor_amd_gpu(
    activity_event: threading.Event, 
    shutdown_event: threading.Event, 
    interval:       float, 
    gpu_records:    list[dict[str, float]],
    device_index:   int = 0
):
    try:
        amdsmi.amdsmi_init()
        processor_handles = amdsmi.amdsmi_get_processor_handles()
        total_devices = len(processor_handles)
        
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
            rocm_smi_result = subprocess.run(command, capture_output=True, text=True, check=True)
            record = parse_rocm_smi_output(rocm_smi_result.stdout.strip(), device_index)
            gpu_records.append(record)

        except:
            pass

        time.sleep(interval)