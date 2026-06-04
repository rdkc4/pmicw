import json
import re

from record_types import Record
from typing import TypeAlias

PerfRecord:    TypeAlias = Record
LDRecord:      TypeAlias = Record
ROCMSMIRecord: TypeAlias = dict

def parse_cpu_prof_output(perf_output: str, pid: int) -> tuple[PerfRecord, LDRecord]:
    perf_json_records = []
    ld_records        = []

    for line in perf_output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("{"):
            try:
                perf_json_records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        elif line.startswith(str(pid)):
            ld_records.append(line)

    parsed_perf         = parse_perf_json_records(perf_json_records)
    dynamic_link_cycles = parse_ld_records(ld_records)

    return parsed_perf, dynamic_link_cycles

def parse_perf_json_records(perf_json_records: list[dict]) -> PerfRecord:
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

def parse_ld_records(ld_records: list[str]) -> LDRecord:
    pattern = re.compile(r"total startup time in dynamic loader:\s*(\d+)\s*cycles")

    for record in reversed(ld_records):
        match = pattern.search(record)
        if match:
            return {'ld': float(match.group(1))}
    return {}

def parse_rocm_smi_output(rocm_smi_output: str, device_index: int) -> ROCMSMIRecord:
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