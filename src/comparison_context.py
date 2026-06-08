from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from metrics_config import ProfilerConfig

class MetricStatus(StrEnum):
    NOISE       = "noise"
    IMPROVEMENT = "improvement"
    REGRESSION  = "regression"
    INTERESTING = "interesting"
    IRRELEVANT  = "irrelevant"
    INVALID     = "invalid"

class CSVMetadataCols(StrEnum):
    RUN_ID        = "run_id"
    TIMESTAMP     = "timestamp"
    WORKLOAD_NAME = "workload_name"
    WORKLOAD_ARGS = "workload_arguments"

class ComparisonCols(StrEnum):
    # metadata
    BASELINE_RUN_ID  = "baseline_run_id"
    CONTENDER_RUN_ID = "contender_run_id"
    BASELINE_ARGS    = "baseline_args"
    CONTENDER_ARGS   = "contender_args"
    WORKLOAD_NAME    = "workload_name"
    TIMESTAMP        = "timestamp"
    CFG              = "comparison_cfg"

    # data
    COMPARISON       = "comparison"
    METRIC           = "metric"
    BASELINE_VAL     = "baseline_val"
    CONTENDER_VAL    = "contender_val"
    DELTA_ABS        = "delta_abs"
    DELTA_PCT        = "delta_pct"
    UNIT             = "unit"
    STATUS           = "status"

def build_segment_map(cfg: ProfilerConfig) -> dict[str, set[str]]:
    segment_map = defaultdict(set)

    for segment in cfg.segments.values():
        for metric in segment.metrics:
            segment_map[segment.name].add(metric.name)
            
            for structural_field in metric.output_fields():
                segment_map[segment.name].add(structural_field)

    return dict(segment_map)