from measurement import Metrics
from itertools import chain
from statistics import mean, median, stdev
from collections import OrderedDict, defaultdict
from metrics_config import (
    STATS_SUFFIX,
    DerivedMetric, 
    ProfilerConfig, 
    RatioMetric, 
    SegmentConfig, 
    StatsMetric, 
    SumMetric, 
    total_key
)
from record_types import FlatRecords, Record, RecordGroup, RecordList

def compute_records(cfg: ProfilerConfig, record_groups: RecordGroup) -> dict[str, Metrics]:
    """
    Entry point for record computation

    cfg: metric configuration\n
    record_groups: grouped records (perf, gpu, memory, thread, ld)
    """
    flat_metrics = extract_metrics_from_groups(record_groups)
    return compute_metrics(cfg, flat_metrics)

def extract_metrics_from_groups(groups: RecordGroup) -> FlatRecords:
    """
    Flattens metrics so that metric name and all its values are grouped together
    """
    extracted_metrics = defaultdict(list)
    
    for item in chain.from_iterable(groups.values()):
        for metric_name, value in item.items():
            if value is not None:
                extracted_metrics[metric_name.split(':')[0]].append(value)
    
    return dict(extracted_metrics)

EVAL_BUILTINS: dict = {
    "__builtins__": {},
    "abs":          abs,
    "round":        round,
    "min":          min,
    "max":          max,
    "sum":          sum
}

def compute_metrics(cfg: ProfilerConfig, flat_records: FlatRecords) -> dict[str, Metrics]:
    """
    Entry point for metric computation

    Returns metrics grouped by segments from the metric configuration
    """
    global_calculation_space: dict[str, float]   = {}
    structured_metrics:       dict[str, Metrics] = OrderedDict()

    for seg in cfg.segments.values():
        segment_record: Record = {}
        compute_segment(seg, flat_records, global_calculation_space, segment_record)
        structured_metrics[seg.name] = Metrics(segment_record)

    return structured_metrics

def compute_segment(
    segment:        SegmentConfig, 
    flat_records:   FlatRecords, 
    global_record:  Record, 
    segment_record: Record
) -> None:
    """
    Evaluates each metric inside of a segment

    Type of evaluation depends on the type of the metric\n
    Derived metrics must be evaluated last
    """
    for metric in segment.metrics:
        if isinstance(metric, RatioMetric):
            apply_ratio(metric, flat_records, global_record, segment_record)

        elif isinstance(metric, StatsMetric):
            apply_stats(metric, flat_records, global_record, segment_record)

        elif isinstance(metric, SumMetric):
            apply_sum(metric, flat_records, global_record, segment_record)

    for metric in segment.metrics:
        if isinstance(metric, DerivedMetric):
            apply_derived(metric, global_record, segment_record)


def apply_ratio(metric: RatioMetric, flat_records: FlatRecords, global_record: Record, segment_record: Record) -> None:
    """
    Applies ratio to metrics

    Numerator and Denominator metrics are defined in metric configuration\n
    Ratio is calculated as numerator / denominator\n
    Additional option is defining `totals` list in metric configuration\n
    If numerator and/or denominator are listed in totals their aggregated values will be captured too\n
    Applies scaling
    """
    numerators   = flat_records.get(metric.numerator,   [])
    denominators = flat_records.get(metric.denominator, [])

    ratios:            list[float] = []
    total_numerator:   float       = 0.0
    total_denominator: float       = 0.0

    if len(numerators) == len(denominators):
        for num, den in zip(numerators, denominators):
            if den != 0:
                ratios.append(num / den)
                total_numerator   += num
                total_denominator += den

    if "numerator" in metric.totals:
        key = total_key(metric.numerator)
        global_record[key] = segment_record[key] = total_numerator * metric.scale

    if "denominator" in metric.totals:
        key = total_key(metric.denominator)
        global_record[key] = segment_record[key] = total_denominator * metric.scale

    ratio_stats = compute_stats(ratios)
    ratio_stats = tuple(val * metric.scale for val in ratio_stats)

    for field, value in zip((f"{metric.name}_{suffix}" for suffix in STATS_SUFFIX), ratio_stats):
        global_record[field] = segment_record[field] = value


def apply_stats(metric: StatsMetric, flat_records: FlatRecords, global_record: Record, segment_record: Record) -> None:
    """
    Applies stats to metrics

    Evaluated mean, median, stddev, min, and max values of the metric\n
    Additional option is `total` in configuration\n
    If total is set to true aggregated values of metric will be stored too\n
    Applies scaling
    """
    values = flat_records.get(metric.key, [])

    if metric.scale != 1:
        values = [val * metric.scale for val in values]

    if metric.total:
        key = f"{metric.name}_total"
        global_record[key] = segment_record[key] = sum(values)

    for field, value in zip((f"{metric.name}_{suffix}" for suffix in STATS_SUFFIX), compute_stats(values)):
        global_record[field] = segment_record[field] = value


def apply_sum(metric: SumMetric, flat_records: FlatRecords, global_record: Record, segment_record: Record) -> None:
    """
    Applies sum to a metric

    Applies scaling
    """
    values = flat_records.get(metric.key, [])
    
    if metric.scale != 1:
        values = [val * metric.scale for val in values]

    key = f"{metric.name}_total"
    global_record[key] = segment_record[key] = sum(values)


def apply_derived(metric: DerivedMetric, global_record: Record, segment_record: Record) -> None:
    """
    Evaluates the derived metric based on the `formula` defined in metric configuration

    Applies scaling
    """
    env = dict(EVAL_BUILTINS)
    env.update(global_record)

    try:
        result = eval(metric.formula, env)
        
    except ZeroDivisionError:
        result = 0.0

    except Exception as e:
        raise RuntimeError(
            f"Derived metric '{metric.name}' failed during evaluation: {e}\n"
            f"Formula: {metric.formula}"
        ) from e

    global_record[metric.name] = segment_record[metric.name] = float(result) * metric.scale

def compute_stats(values: list[float]) -> tuple[float, float, float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    return (
        mean(values),
        median(values),
        stdev(values) if len(values) > 1 else 0.0,
        min(values),
        max(values),
    )