from measurement import (
    BranchPredictionMetric, 
    IPCMetric, 
    L1CacheMetric, 
    L2CacheMetric,
    LLCacheMetric,
    MetricStats,
    SystemMetric, 
    WallTimeMetric
)
from statistics import mean, median, stdev
from collections import defaultdict

def compute_wall_time_metric(wall_times: list[float]) -> WallTimeMetric:
    return WallTimeMetric(
        total_ms        = sum(wall_times),
        wall_time_stats = compute_stats_metrics(wall_times)
    )

def compute_core_cpu_metrics(core_records: list[dict[str, float]]) -> tuple[IPCMetric, BranchPredictionMetric]:
    ipc_metrics               = compute_ipc_metrics(core_records)
    branch_prediction_metrics = compute_branch_prediction_metrics(core_records)
    
    return ipc_metrics, branch_prediction_metrics

def compute_ipc_metrics(core_records: list[dict[str, float]]) -> IPCMetric:
    total_instructions, total_cycles, ipc_stats = compute_ratio_metrics(core_records, "instructions", "cycles")

    return IPCMetric(
        total_instructions = int(total_instructions),
        total_cycles       = int(total_cycles),
        total_ipc          = (total_instructions / total_cycles) if total_cycles > 0 else 0.0,
        ipc_stats          = ipc_stats
    )

def compute_branch_prediction_metrics(core_records: list[dict[str, float]]) -> BranchPredictionMetric:
    total_branch_misses, total_branches, branch_miss_rate_stats = compute_ratio_metrics(core_records, "branch-misses", "branches")

    return BranchPredictionMetric(
        total_branches          = int(total_branches),
        total_branch_misses     = int(total_branch_misses),
        total_branch_miss_rate  = (total_branch_misses / total_branches) if total_branches > 0 else 0.0,
        branch_miss_rate_stats  = branch_miss_rate_stats
    )

def compute_l1_cache_metrics(l1_records: list[dict[str, float]]) -> L1CacheMetric:
    total_l1_misses, total_l1_accesses, l1_miss_rate_stats = compute_ratio_metrics(l1_records, "L1-dcache-load-misses", "L1-dcache-loads")

    return L1CacheMetric(
        total_accesses     = int(total_l1_accesses),
        total_misses       = int(total_l1_misses),
        total_miss_rate    = (total_l1_misses / total_l1_accesses) if total_l1_accesses > 0 else 0.0,
        l1_miss_rate_stats = l1_miss_rate_stats
    )

def compute_l2_cache_metrics(l2_records: list[dict[str, float]]) -> L2CacheMetric:
    total_l2_misses, total_l2_accesses, l2_miss_rate_stats = compute_ratio_metrics(l2_records, "l2_cache_req_stat.ic_dc_miss_in_l2", "l2_cache_req_stat.all")

    return L2CacheMetric(
        total_accesses     = int(total_l2_accesses),
        total_misses       = int(total_l2_misses),
        total_miss_rate    = (total_l2_misses / total_l2_accesses) if total_l2_accesses > 0 else 0.0,
        l2_miss_rate_stats = l2_miss_rate_stats
    )

def compute_llc_cache_metrics(llc_records: list[dict[str, float]]) -> LLCacheMetric:
    total_llc_misses, total_llc_accesses, llc_miss_rate_stats = compute_ratio_metrics(llc_records, "cache-misses", "cache-references")

    return LLCacheMetric(
        total_accesses      = int(total_llc_accesses),
        total_misses        = int(total_llc_misses),
        total_miss_rate     = (total_llc_misses / total_llc_accesses) if total_llc_accesses > 0 else 0.0,
        llc_miss_rate_stats = llc_miss_rate_stats
    )

def compute_system_metrics(system_records: list[dict[str, float]]) -> SystemMetric:
    counters = defaultdict(list)

    for record in system_records:
        for key, value in record.items():
            if value is not None:
                counters[key].append(value)

    return SystemMetric(
        total_context_switches = int(sum(counters["context-switches"])),
        total_page_faults      = int(sum(counters["page-faults"])),
        total_minor_faults     = int(sum(counters["minor-faults"])),
        total_major_faults     = int(sum(counters["major-faults"])),

        context_switches_stats = compute_stats_metrics(counters["context-switches"]),
        page_faults_stats      = compute_stats_metrics(counters["page-faults"]),
        minor_faults_stats     = compute_stats_metrics(counters["minor-faults"]),
        major_faults_stats     = compute_stats_metrics(counters["major-faults"]),
    )
    
def compute_stats_metrics(metrics: list[float]) -> MetricStats:
    return MetricStats(
        mean_value   = mean(metrics)   if metrics          else 0.0,
        median_value = median(metrics) if metrics          else 0.0,
        stddev_value = stdev(metrics)  if len(metrics) > 1 else 0.0,
        min_value    = min(metrics)    if metrics          else 0.0,
        max_value    = max(metrics)    if metrics          else 0.0,
    )

def compute_ratio_metrics(records: list[dict[str, float]], numerator_key: str, denominator_key: str) -> tuple[float, float, MetricStats]:
    ratio_values      = []
    total_numerator   = 0
    total_denominator = 0

    for record in records:
        numerator = record.get(numerator_key)
        denominator = record.get(denominator_key)

        if numerator is not None and denominator is not None and denominator > 0:
            ratio_values.append(numerator / denominator)
            total_numerator += numerator
            total_denominator += denominator

    return total_numerator, total_denominator, compute_stats_metrics(ratio_values)