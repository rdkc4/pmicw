import json

from record_types import Record
from typing import TypeAlias

PerfRecord:     TypeAlias = Record
BpftraceRecord: TypeAlias = Record
ROCMSMIRecord:  TypeAlias = dict

def parse_perf_output(perf_output: str) -> PerfRecord:
    """
    Parses the output produced by perf (and optionally LD)

    Splits the output into perf records and ld records\n
    pid is required to capture ld cycles of the process
    """
    perf_json_records = []

    for line in perf_output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("{"):
            try:
                perf_json_records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return parse_perf_json_records(perf_json_records)

def parse_perf_json_records(perf_json_records: list[dict]) -> PerfRecord:
    """
    Extracts event name and counter value from the perf json records
    """
    metrics: PerfRecord = {}

    for record in perf_json_records:
        event = record.get("event")
        value = record.get("counter-value")

        if event and value:
            try:
                metrics[event] = float(value)
            except ValueError:
                continue

    return metrics

def parse_bpftrace_output(bpftrace_output: str) -> BpftraceRecord:
    record = {}
    try:
        raw = dict(json.loads(bpftrace_output))
        for metric_name, metric_value in raw.items():
            record[metric_name] = metric_value

    except json.JSONDecodeError:
        pass

    return record

def parse_rocm_smi_output(rocm_smi_output: str, device_index: int) -> ROCMSMIRecord:
    """
    Parses rocm-smi output for a specific device
    """
    json_start = rocm_smi_output.find("{")

    if(json_start != -1):
        rocm_smi_output = rocm_smi_output[json_start:]
        data = {}
        try:
            data = json.loads(rocm_smi_output)

        except json.JSONDecodeError:
            pass

        gpu_data = data.get(f"card{device_index}", {})
        return gpu_data
    
    return {}