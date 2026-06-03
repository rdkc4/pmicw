from measurement import (
    BranchPredictionMetric,
    CPUMetric,
    GPUMetric, 
    IPCMetric, 
    L1CacheMetric, 
    L2CacheMetric,
    LLCacheMetric,
    MemoryMetric,
    MetricStats,
    Metrics,
    StartupMetric,
    TaskClockMetric,
    ThreadMetric, 
    WallTimeMetric
)
from itertools import chain
from statistics import mean, median, stdev
from collections import defaultdict
from workload_context import WorkloadMetricSelection

Record      = dict[str, float]
RecordList  = list[Record]
RecordGroup = dict[str, RecordList]
FlatRecords = dict[str, list[float]]

def compute_metrics(selected_metrics: WorkloadMetricSelection, record_groups: RecordGroup) -> Metrics:
    flat_metrics       = extract_metrics_from_groups(record_groups)
    wall_time_metrics  = compute_wall_time_metric(flat_metrics)
    mean_wall_time_ms  = wall_time_metrics.wall_time_stats_ms.mean_value
    mean_task_clock_ms = 0

    cpu_metrics = gpu_metrics = memory_metrics = startup_metrics = thread_metrics = None

    if selected_metrics.cpu:
        ipc             = compute_ipc_metrics(flat_metrics)
        task_clock      = compute_task_clock_metrics(flat_metrics)
        branch          = compute_branch_prediction_metrics(flat_metrics)
        l1              = compute_l1_cache_metrics(flat_metrics)
        l2              = compute_l2_cache_metrics(flat_metrics)
        llc             = compute_llc_cache_metrics(flat_metrics)
        startup_metrics = compute_startup_metrics(flat_metrics, mean_wall_time_ms)

        mean_task_clock_ms = task_clock.task_clock_stats_ms.mean_value

        cpu_metrics = CPUMetric(
            ipc               = ipc,
            task_clock        = task_clock,
            l1_cache          = l1,
            l2_cache          = l2,
            llc_cache         = llc,
            branch_prediction = branch
        )

    if selected_metrics.memory:
        memory_metrics = compute_memory_metrics(flat_metrics)

    if selected_metrics.gpu:
        gpu_metrics    = compute_gpu_metrics(flat_metrics)

    if selected_metrics.thread:
        thread_metrics = compute_thread_metrics(flat_metrics, mean_wall_time_ms, mean_task_clock_ms)

    return Metrics(
        wall_time = wall_time_metrics,
        cpu       = cpu_metrics,
        gpu       = gpu_metrics,
        memory    = memory_metrics,
        startup   = startup_metrics,
        thread    = thread_metrics
    )

def compute_wall_time_metric(records: FlatRecords) -> WallTimeMetric:
    return WallTimeMetric(
        wall_time_total_ms = sum(records['execution_time']),
        wall_time_stats_ms = compute_stats_metrics(records['execution_time'])
    )

def compute_ipc_metrics(records: FlatRecords) -> IPCMetric:
    total_instructions, total_cycles, ipc_stats = compute_ratio_metrics(records, "instructions", "cycles")

    return IPCMetric(
        total_instructions = int(total_instructions),
        total_cycles       = int(total_cycles),
        ipc_stats          = ipc_stats
    )

def compute_task_clock_metrics(records: FlatRecords) -> TaskClockMetric:
    task_clock_values = records.get('task-clock', [])
    task_clock_values = [value / 1000000 for value in task_clock_values]

    return TaskClockMetric(
        task_clock_total_ms = sum(task_clock_values),
        task_clock_stats_ms = compute_stats_metrics(task_clock_values)
    )


def compute_branch_prediction_metrics(records: FlatRecords) -> BranchPredictionMetric:
    total_branch_miss, total_branch, branch_miss_rate_stats = compute_ratio_metrics(records, "branch-misses", "branches")

    return BranchPredictionMetric(
        total_branches             = int(total_branch),
        total_branch_misses        = int(total_branch_miss),
        branch_miss_rate_stats_pct = branch_miss_rate_stats
    )

def compute_l1_cache_metrics(records: FlatRecords) -> L1CacheMetric:
    total_l1d_miss, total_l1d_access, l1d_miss_rate_stats = compute_ratio_metrics(records, "L1-dcache-load-misses", "L1-dcache-loads")
    total_l1i_miss, total_l1i_access, l1i_miss_rate_stats = compute_ratio_metrics(records, "L1-icache-load-misses", "L1-icache-loads")
    
    return L1CacheMetric(
        l1d_total_accesses      = int(total_l1d_access),
        l1d_total_misses        = int(total_l1d_miss),
        l1i_total_accesses      = int(total_l1i_access),
        l1i_total_misses        = int(total_l1i_miss),
        l1d_miss_rate_stats_pct = l1d_miss_rate_stats,
        l1i_miss_rate_stats_pct = l1i_miss_rate_stats
    )

def compute_l2_cache_metrics(records: FlatRecords) -> L2CacheMetric:
    total_l2_miss, total_l2_access, l2_miss_rate_stats = compute_ratio_metrics(records, "l2_cache_req_stat.ic_dc_miss_in_l2", "l2_cache_req_stat.all")

    return L2CacheMetric(
        l2_total_accesses      = int(total_l2_access),
        l2_total_misses        = int(total_l2_miss),
        l2_miss_rate_stats_pct = l2_miss_rate_stats
    )

def compute_llc_cache_metrics(records: FlatRecords) -> LLCacheMetric:
    total_llc_miss, total_llc_access, llc_miss_rate_stats = compute_ratio_metrics(records, "cache-misses", "cache-references")

    return LLCacheMetric(
        llc_total_accesses      = int(total_llc_access),
        llc_total_misses        = int(total_llc_miss),
        llc_miss_rate_stats_pct = llc_miss_rate_stats
    )
    
def compute_memory_metrics(records: FlatRecords) -> MemoryMetric:
    rss          = records.get('rss_mb',       [])
    vms          = records.get('vms_mb',       [])
    page_faults  = records.get('page-faults',  [])
    minor_faults = records.get('minor-faults', [])
    major_faults = records.get('major-faults', [])

    return MemoryMetric(
        total_page_faults  = int(sum(page_faults)), 
        total_minor_faults = int(sum(minor_faults)), 
        total_major_faults = int(sum(major_faults)),
        rss_stats_mb       = compute_stats_metrics(rss),
        vms_stats_mb       = compute_stats_metrics(vms),
        page_faults_stats  = compute_stats_metrics(page_faults),
        minor_faults_stats = compute_stats_metrics(minor_faults),
        major_faults_stats = compute_stats_metrics(major_faults)
    )

def compute_gpu_metrics(records: FlatRecords) -> GPUMetric:
    activity = records.get('gfx_activity_pct', [])
    vram     = records.get('vram_pct',         [])

    return GPUMetric(
        activity_stats_pct = compute_stats_metrics(activity),
        vram_stats_pct     = compute_stats_metrics(vram)
    )

def compute_startup_metrics(records: FlatRecords, mean_wall_time: float) -> StartupMetric:
    link_cycles, _, cycle_ratio = compute_ratio_metrics(records, "ld", "cycles")

    return StartupMetric(
        linker_total_cycles   = int(link_cycles),
        startup_time_stats_ms = MetricStats(
            mean_value        = cycle_ratio.mean_value   * mean_wall_time,
            median_value      = cycle_ratio.median_value * mean_wall_time,
            stddev_value      = cycle_ratio.stddev_value * mean_wall_time,
            min_value         = cycle_ratio.min_value    * mean_wall_time,
            max_value         = cycle_ratio.max_value    * mean_wall_time
        )
    )

def compute_thread_metrics(records: FlatRecords, mean_wall_time: float, mean_task_clock: float) -> ThreadMetric:
    thread_counts              = records.get('threads',          [])
    context_switches           = records.get('context-switches', [])
    thread_util_scale_factor   = mean_task_clock / mean_wall_time if mean_wall_time else 0
    thread_utilization_records = [thread_util_scale_factor / count * 100 for count in thread_counts]

    return ThreadMetric(
        total_context_switches       = int(sum(context_switches)),
        context_switches_stats       = compute_stats_metrics(context_switches),
        thread_count_stats           = compute_stats_metrics(thread_counts),
        thread_utilization_stats_pct = compute_stats_metrics(thread_utilization_records)
    )

def compute_stats_metrics(metrics: list[float]) -> MetricStats:
    return MetricStats(
        mean_value   = mean(metrics)   if metrics          else 0.0,
        median_value = median(metrics) if metrics          else 0.0,
        stddev_value = stdev(metrics)  if len(metrics) > 1 else 0.0,
        min_value    = min(metrics)    if metrics          else 0.0,
        max_value    = max(metrics)    if metrics          else 0.0,
    )

def compute_ratio_metrics(records: FlatRecords, numerator_key: str, denominator_key: str) -> tuple[float, float, MetricStats]:
    ratio_values      = []
    total_numerator   = 0
    total_denominator = 0

    numerators   = records.get(numerator_key,   [])
    denominators = records.get(denominator_key, [])

    if len(numerators) == len(denominators):
        for (num, den) in zip(numerators, denominators):
            if den != 0:
                ratio_values.append(num / den)
                total_numerator   += num
                total_denominator += den

    return total_numerator, total_denominator, compute_stats_metrics(ratio_values)

def extract_metrics_from_groups(groups: dict[str, RecordList]) -> dict[str, list[float]]:
    extracted_metrics = defaultdict(list)
    
    for item in chain.from_iterable(groups.values()):
        for metric_name, value in item.items():
            if value is not None:
                extracted_metrics[metric_name.split(':')[0]].append(value)
    
    return dict(extracted_metrics)