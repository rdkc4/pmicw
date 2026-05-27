import json

def parse_perf_output(perf_output: str) -> dict[str, float]:
    perf_json_records = []
    for line in perf_output.splitlines():
        try:
            perf_json_records.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    return parse_perf_json_records(perf_json_records)

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