import threading
import time
import amdsmi
import psutil

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
        if device_index >= len(processor_handles):
            print(f"Invalid GPU device index {device_index}. Available devices: {len(processor_handles)}")
            return

        gpu_handle = processor_handles[device_index]

        while not shutdown_event.is_set():
            activity_event.wait()
            if shutdown_event.is_set():
                break

            try:
                vram = amdsmi.amdsmi_get_gpu_vram_usage(gpu_handle)

                vram_used  = vram.get('vram_used', 0.0)
                vram_total = vram.get('vram_total', 0.0)
            except:
                vram_used  = 0
                vram_total = 0
            
            try:
                util     = amdsmi.amdsmi_get_gpu_metrics_info(gpu_handle)
                activity = util.get('average_gfx_activity', 0.0)
            except:
                activity = 0

            gpu_records.append({
                "gfx_activity_pct": activity,
                "vram_pct":         vram_used / vram_total * 100 if vram_total > 0 else 0.0
            })

            time.sleep(interval)

    except Exception as e:
        print(f"Failed to initialize AMD SMI monitoring: {e}")

    finally:
        try:
            amdsmi.amdsmi_shut_down()
        except:
            pass