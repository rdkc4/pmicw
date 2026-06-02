import pandas as pd

def enrich_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()

    result["segment"]       = result["metric"].map(get_segment)
    result["unit"]          = result["metric"].map(get_units)
    result["direction"]     = result["metric"].map(get_direction)
    result["display_order"] = result["metric"].map(get_display_order)

    return result

def get_segment(metric: str) -> str:
    return str(METRIC_REGISTRY.get(metric, {}).get("segment", "other"))

def get_units(metric: str) -> str:
    return str(METRIC_REGISTRY.get(metric, {}).get("unit", ""))

def get_direction(metric: str) -> bool:
    return bool(METRIC_REGISTRY.get(metric, {}).get("direction", False))

def get_display_order(metric: str) -> int:
    return int(str(METRIC_REGISTRY.get(metric, {}).get("display_order", 9999)))

SEGMENT_ORDER = ["workload_info", "wall_time", "cpu", "gpu", "memory", "system", "startup", "system_info", "other"]

METRIC_REGISTRY: dict[str, dict[str, object]] = {
   
    # Wall Time Metrics
    "wall_time_total_ms":  {"segment": "wall_time", "higher_is_better": False, "noise_metric": False, "display_order": 1, "unit": "ms"},
    "wall_time_ms_mean":   {"segment": "wall_time", "higher_is_better": False, "noise_metric": False, "display_order": 2, "unit": "ms"},
    "wall_time_ms_median": {"segment": "wall_time", "higher_is_better": False, "noise_metric": False, "display_order": 3, "unit": "ms"},
    "wall_time_ms_stddev": {"segment": "wall_time", "higher_is_better": False, "noise_metric": True,  "display_order": 4, "unit": "ms"},
    "wall_time_ms_min":    {"segment": "wall_time", "higher_is_better": False, "noise_metric": False, "display_order": 5, "unit": "ms"},
    "wall_time_ms_max":    {"segment": "wall_time", "higher_is_better": False, "noise_metric": False, "display_order": 6, "unit": "ms"},
    
    # CPU METRICS

    # IPC Metrics
    "total_instructions": {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 1, "unit": "instructions"},
    "total_cycles":       {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 2, "unit": "cycles"},
    "ipc_mean":           {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 3, "unit": "instructions"},
    "ipc_median":         {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 4, "unit": "instructions"},
    "ipc_stddev":         {"segment": "cpu", "higher_is_better": True,  "noise_metric": True,  "display_order": 5, "unit": "instructions"},
    "ipc_min":            {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 6, "unit": "instructions"},
    "ipc_max":            {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 7, "unit": "instructions"},

    # Task Clock Metrics
    "task_clock_total_ms":  {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 8,  "unit": "ms"},
    "task_clock_ms_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 9,  "unit": "ms"},
    "task_clock_ms_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 10, "unit": "ms"},
    "task_clock_ms_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 11, "unit": "ms"},
    "task_clock_ms_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 12, "unit": "ms"},
    "task_clock_ms_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 13, "unit": "ms"},

    # L1 Cache Metrics
    "l1d_total_accesses":       {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 14, "unit": "accesses"},
    "l1d_total_misses":         {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 15, "unit": "misses"},
    "l1i_total_accesses":       {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 16, "unit": "accesses"},
    "l1i_total_misses":         {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 17, "unit": "misses"},
    "l1d_miss_rate_pct_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 18, "unit": "%"},
    "l1d_miss_rate_pct_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 19, "unit": "%"},
    "l1d_miss_rate_pct_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 20, "unit": "%"},
    "l1d_miss_rate_pct_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 21, "unit": "%"},
    "l1d_miss_rate_pct_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 22, "unit": "%"},
    "l1i_miss_rate_pct_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 23, "unit": "%"},
    "l1i_miss_rate_pct_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 24, "unit": "%"},
    "l1i_miss_rate_pct_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 25, "unit": "%"},
    "l1i_miss_rate_pct_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 26, "unit": "%"},
    "l1i_miss_rate_pct_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 27, "unit": "%"},

    # L2 Cache Metrics
    "l2_total_accesses":       {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 28, "unit": "accesses"},
    "l2_total_misses":         {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 29, "unit": "misses"},
    "l2_miss_rate_pct_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 30, "unit": "%"},
    "l2_miss_rate_pct_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 31, "unit": "%"},
    "l2_miss_rate_pct_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 32, "unit": "%"},
    "l2_miss_rate_pct_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 33, "unit": "%"},
    "l2_miss_rate_pct_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 34, "unit": "%"},

    # LLC Cache Metrics
    "llc_total_accesses":       {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 35, "unit": "accesses"},
    "llc_total_misses":         {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 36, "unit": "misses"},
    "llc_miss_rate_pct_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 37, "unit": "%"},
    "llc_miss_rate_pct_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 38, "unit": "%"},
    "llc_miss_rate_pct_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 39, "unit": "%"},
    "llc_miss_rate_pct_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 40, "unit": "%"},
    "llc_miss_rate_pct_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 41, "unit": "%"},

    # Branch Prediction Metrics
    "total_branches":              {"segment": "cpu", "higher_is_better": True,  "noise_metric": False, "display_order": 42, "unit": "branches"},
    "total_branch_misses":         {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 43, "unit": "misses"},
    "branch_miss_rate_pct_mean":   {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 44, "unit": "%"},
    "branch_miss_rate_pct_median": {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 45, "unit": "%"},
    "branch_miss_rate_pct_stddev": {"segment": "cpu", "higher_is_better": False, "noise_metric": True,  "display_order": 46, "unit": "%"},
    "branch_miss_rate_pct_min":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 47, "unit": "%"},
    "branch_miss_rate_pct_max":    {"segment": "cpu", "higher_is_better": False, "noise_metric": False, "display_order": 48, "unit": "%"},

    # GPU Metrics

    # GPU Activity Metrics
    "gpu_activity_pct_mean":   {"segment": "gpu", "higher_is_better": True,  "noise_metric": False, "display_order": 1, "unit": "%"},
    "gpu_activity_pct_median": {"segment": "gpu", "higher_is_better": True,  "noise_metric": False, "display_order": 2, "unit": "%"},
    "gpu_activity_pct_stddev": {"segment": "gpu", "higher_is_better": True,  "noise_metric": True,  "display_order": 3, "unit": "%"},
    "gpu_activity_pct_min":    {"segment": "gpu", "higher_is_better": True,  "noise_metric": False, "display_order": 4, "unit": "%"},
    "gpu_activity_pct_max":    {"segment": "gpu", "higher_is_better": True,  "noise_metric": False, "display_order": 5, "unit": "%"},

    # GPU VRAM Usage Metrics
    "gpu_vram_pct_mean":       {"segment": "gpu", "higher_is_better": False, "noise_metric": True,  "display_order": 6,  "unit": "%"},
    "gpu_vram_pct_median":     {"segment": "gpu", "higher_is_better": False, "noise_metric": True,  "display_order": 7,  "unit": "%"},
    "gpu_vram_pct_stddev":     {"segment": "gpu", "higher_is_better": False, "noise_metric": True,  "display_order": 8,  "unit": "%"},
    "gpu_vram_pct_min":        {"segment": "gpu", "higher_is_better": False, "noise_metric": True,  "display_order": 9,  "unit": "%"},
    "gpu_vram_pct_max":        {"segment": "gpu", "higher_is_better": False, "noise_metric": True,  "display_order": 10, "unit": "%"},

    # Memory Metrics

    # Resident Memory Metrics
    "rss_mb_mean":   {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 1, "unit": "MB"},
    "rss_mb_median": {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 2, "unit": "MB"},
    "rss_mb_stddev": {"segment": "memory", "higher_is_better": False, "noise_metric": True,  "display_order": 3, "unit": "MB"},
    "rss_mb_min":    {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 4, "unit": "MB"},
    "rss_mb_max":    {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 5, "unit": "MB"},

    # Virtual Memory Metrics
    "vms_mb_mean":   {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 6,  "unit": "MB"},
    "vms_mb_median": {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 7,  "unit": "MB"},
    "vms_mb_stddev": {"segment": "memory", "higher_is_better": False, "noise_metric": True,  "display_order": 8,  "unit": "MB"},
    "vms_mb_min":    {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 9,  "unit": "MB"},
    "vms_mb_max":    {"segment": "memory", "higher_is_better": False, "noise_metric": False, "display_order": 10, "unit": "MB"},

    # System Metrics
    "total_context_switches": {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 1,  "unit": "switches"},
    "total_page_faults":      {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 2,  "unit": "faults"},
    "total_minor_faults":     {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 3,  "unit": "faults"},
    "total_major_faults":     {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 4,  "unit": "faults"},
    "context_switch_mean":    {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 5,  "unit": "switches"},
    "context_switch_median":  {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 6,  "unit": "switches"},
    "context_switch_stddev":  {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 7,  "unit": "switches"},
    "context_switch_min":     {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 8,  "unit": "switches"},
    "context_switch_max":     {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 9,  "unit": "switches"},
    "page_fault_mean":        {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 10, "unit": "faults"},
    "page_fault_median":      {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 11, "unit": "faults"},
    "page_fault_stddev":      {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 12, "unit": "faults"},
    "page_fault_min":         {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 13, "unit": "faults"},
    "page_fault_max":         {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 14, "unit": "faults"},
    "minor_fault_mean":       {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 15, "unit": "faults"},
    "minor_fault_median":     {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 16, "unit": "faults"},
    "minor_fault_stddev":     {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 17, "unit": "faults"},
    "minor_fault_min":        {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 18, "unit": "faults"},
    "minor_fault_max":        {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 19, "unit": "faults"},
    "major_fault_mean":       {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 20, "unit": "faults"},
    "major_fault_median":     {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 21, "unit": "faults"},
    "major_fault_stddev":     {"segment": "system", "higher_is_better": False, "noise_metric": True,  "display_order": 22, "unit": "faults"},
    "major_fault_min":        {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 23, "unit": "faults"},
    "major_fault_max":        {"segment": "system", "higher_is_better": False, "noise_metric": False, "display_order": 24, "unit": "faults"},

    # Startup Metrics
    "linker_total_cycles":    {"segment": "startup", "higher_is_better": False, "noise_metric": False, "display_order": 1, "unit": "cycles"},
    "startup_time_ms_mean":   {"segment": "startup", "higher_is_better": False, "noise_metric": False, "display_order": 2, "unit": "ms"},
    "startup_time_ms_median": {"segment": "startup", "higher_is_better": False, "noise_metric": False, "display_order": 3, "unit": "ms"},
    "startup_time_ms_stddev": {"segment": "startup", "higher_is_better": False, "noise_metric": True,  "display_order": 4, "unit": "ms"},
    "startup_time_ms_min":    {"segment": "startup", "higher_is_better": False, "noise_metric": False, "display_order": 5, "unit": "ms"},
    "startup_time_ms_max":    {"segment": "startup", "higher_is_better": False, "noise_metric": False, "display_order": 6, "unit": "ms"},

    # System Info
    "cpu_frequency":      {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 1,  "unit": "MHz"},
    "cpu_physical_cores": {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 2,  "unit": "cores"},
    "cpu_logical_cores":  {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 3,  "unit": "cores"},
    "gpu_vram_total_mb":  {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 4,  "unit": "MB"},
    "gpu_vram_used_mb":   {"segment": "system_info", "higher_is_better": False, "noise_metric": False, "display_order": 5,  "unit": "MB"},
    "mem_total_mb":       {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 6,  "unit": "MB"},
    "mem_available_mb":   {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 7,  "unit": "MB"},
    "mem_free_mb":        {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 8,  "unit": "MB"},
    "mem_used_mb":        {"segment": "system_info", "higher_is_better": False, "noise_metric": False, "display_order": 9,  "unit": "MB"},
    "swp_total_mb":       {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 10, "unit": "MB"},
    "swp_free_mb":        {"segment": "system_info", "higher_is_better": True,  "noise_metric": False, "display_order": 11, "unit": "MB"},
    "swp_used_mb":        {"segment": "system_info", "higher_is_better": False, "noise_metric": False, "display_order": 12, "unit": "MB"},

    # Workload Info
    "workload_iterations":        {"segment": "workload_info", "higher_is_better": True, "noise_metric": False, "display_order": 1, "unit": "iterations"},
    "workload_warmup_iterations": {"segment": "workload_info", "higher_is_better": True, "noise_metric": False, "display_order": 2, "unit": "iterations"}
}