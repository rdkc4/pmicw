import json
import re

def parse_cpu_prof_output(perf_output: str, pid: int) -> tuple[dict[str, float], dict[str, float]]:
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
    total_cycles        = parsed_perf.get("cycles", 0.0)

    if dynamic_link_cycles and total_cycles > 0:
        return parsed_perf, {"cycles": total_cycles, "ld": dynamic_link_cycles}

    return parsed_perf, {}

def parse_perf_json_records(perf_json_records: list[dict]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    for record in perf_json_records:
        event = record.get("event")
        value = record.get("counter-value")

        if event and value:
            try:
                metrics[event] = float(value)
            except ValueError:
                continue

    return metrics

def parse_ld_records(ld_records: list[str]) -> float | None:
    pattern = re.compile(r"total startup time in dynamic loader:\s*(\d+)\s*cycles")

    for record in reversed(ld_records):
        match = pattern.search(record)
        if match:
            return float(match.group(1))
    return None

def parse_rocm_smi_output(rocm_smi_output: str, device_index: int) -> dict[str, float]:
    json_start = rocm_smi_output.find("{")
    if(json_start != -1):
        rocm_smi_output = rocm_smi_output[json_start:]
        data            = json.loads(rocm_smi_output)
        gpu_data        = data.get(f"card{device_index}", {})

        return parse_rocm_smi_json_record(gpu_data)

    return {
        "gfx_activity_pct": 0.0,
        "vram_pct":         0.0
    }

def parse_rocm_smi_json_record(rocm_smi_record: dict) -> dict[str, float]:
    return {
        "gfx_activity_pct": float(rocm_smi_record.get("GPU use (%)", "0")),
        "vram_pct":         float(rocm_smi_record.get("GPU Memory Allocated (VRAM%)", "0"))
    }