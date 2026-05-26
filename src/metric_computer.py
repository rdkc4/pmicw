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
    ipc_values         = []
    total_instructions = 0
    total_cycles       = 0

    for record in core_records:
        instructions = record.get("instructions")
        cycles       = record.get("cycles")

        if instructions is not None and cycles is not None and cycles > 0:
            ipc_values.append(instructions / cycles)
            total_instructions += instructions
            total_cycles       += cycles

    return IPCMetric(
        total_instructions = int(total_instructions),
        total_cycles       = int(total_cycles),
        total_ipc          = (total_instructions / total_cycles) if total_cycles > 0 else 0.0,
        ipc_stats          = compute_stats_metrics(ipc_values)
    )

def compute_branch_prediction_metrics(core_records: list[dict[str, float]]) -> BranchPredictionMetric:
    branch_prediction_values = []
    total_branches           = 0
    total_branch_misses      = 0

    for record in core_records:
        branches      = record.get("branches")
        branch_misses = record.get("branch-misses")

        if branches is not None and branch_misses is not None and branches > 0:
            branch_prediction_values.append(branch_misses / branches)
            total_branches      += branches
            total_branch_misses += branch_misses

    return BranchPredictionMetric(
        total_branches          = int(total_branches),
        total_branch_misses     = int(total_branch_misses),
        total_branch_miss_rate  = (total_branch_misses / total_branches) if total_branches > 0 else 0.0,
        branch_miss_rate_stats  = compute_stats_metrics(branch_prediction_values)
    )

def compute_l1_cache_metrics(l1_records: list[dict[str, float]]) -> L1CacheMetric:
    l1_cache_miss_rates  = []
    total_l1_loads       = 0
    total_l1_load_misses = 0

    for record in l1_records:
        l1_loads = record.get("L1-dcache-loads")
        l1_load_misses = record.get("L1-dcache-load-misses")

        if l1_loads is not None and l1_load_misses is not None and l1_loads > 0:
            l1_cache_miss_rates.append(l1_load_misses / l1_loads)
            total_l1_loads       += l1_loads
            total_l1_load_misses += l1_load_misses

    return L1CacheMetric(
        total_accesses     = int(total_l1_loads),
        total_misses       = int(total_l1_load_misses),
        total_miss_rate    = (total_l1_load_misses / total_l1_loads) if total_l1_loads > 0 else 0.0,
        l1_miss_rate_stats = compute_stats_metrics(l1_cache_miss_rates)
    )

def compute_l2_cache_metrics(l2_records: list[dict[str, float]]) -> L2CacheMetric:
    l2_cache_miss_rates = []
    total_l2_accesses   = 0
    total_l2_misses     = 0

    for record in l2_records:
        l2_accesses = record.get("l2_cache_req_stat.all")
        l2_misses   = record.get("l2_cache_req_stat.ic_dc_miss_in_l2")

        if l2_accesses is not None and l2_misses is not None and l2_accesses > 0:
            l2_cache_miss_rates.append(l2_misses / l2_accesses)
            total_l2_accesses += l2_accesses
            total_l2_misses   += l2_misses

    return L2CacheMetric(
        total_accesses     = int(total_l2_accesses),
        total_misses       = int(total_l2_misses),
        total_miss_rate    = (total_l2_misses / total_l2_accesses) if total_l2_accesses > 0 else 0.0,
        l2_miss_rate_stats = compute_stats_metrics(l2_cache_miss_rates)
    )

def compute_llc_cache_metrics(llc_records: list[dict[str, float]]) -> LLCacheMetric:
    llc_cache_miss_rates = []
    total_llc_accesses   = 0
    total_llc_misses     = 0

    for record in llc_records:
        llc_accesses = record.get("cache-references")
        llc_misses   = record.get("cache-misses")

        if llc_accesses is not None and llc_misses is not None and llc_accesses > 0:
            llc_cache_miss_rates.append(llc_misses / llc_accesses)
            total_llc_accesses += llc_accesses
            total_llc_misses   += llc_misses

    return LLCacheMetric(
        total_accesses      = int(total_llc_accesses),
        total_misses        = int(total_llc_misses),
        total_miss_rate     = (total_llc_misses / total_llc_accesses) if total_llc_accesses > 0 else 0.0,
        llc_miss_rate_stats = compute_stats_metrics(llc_cache_miss_rates)
    )

def compute_system_metrics(system_records: list[dict[str, float]]) -> SystemMetric:
    context_switches_values = []
    page_faults_values      = []
    minor_faults_values     = []
    major_faults_values     = []
    total_context_switches  = 0
    total_page_faults       = 0
    total_minor_faults      = 0
    total_major_faults      = 0

    for record in system_records:
        context_switches = record.get("context-switches")
        page_faults      = record.get("page-faults")
        minor_faults     = record.get("minor-faults")
        major_faults     = record.get("major-faults")

        if context_switches is not None:
            context_switches_values.append(context_switches)
            total_context_switches += context_switches

        if page_faults is not None:
            page_faults_values.append(page_faults)
            total_page_faults += page_faults

        if minor_faults is not None:
            minor_faults_values.append(minor_faults)
            total_minor_faults += minor_faults

        if major_faults is not None:
            major_faults_values.append(major_faults)
            total_major_faults += major_faults

    return SystemMetric(
        total_context_switches = int(total_context_switches),
        total_page_faults      = int(total_page_faults),
        total_minor_faults     = int(total_minor_faults),
        total_major_faults     = int(total_major_faults),
        context_switches_stats = compute_stats_metrics(context_switches_values),
        page_faults_stats      = compute_stats_metrics(page_faults_values),
        minor_faults_stats     = compute_stats_metrics(minor_faults_values),
        major_faults_stats     = compute_stats_metrics(major_faults_values)
    )
    
def compute_stats_metrics(metrics: list[float]) -> MetricStats:
    return MetricStats(
        mean_value   = mean(metrics)   if metrics          else 0.0,
        median_value = median(metrics) if metrics          else 0.0,
        stddev_value = stdev(metrics)  if len(metrics) > 1 else 0.0,
        min_value    = min(metrics)    if metrics          else 0.0,
        max_value    = max(metrics)    if metrics          else 0.0,
    )