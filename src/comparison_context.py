from dataclasses import dataclass
from enum import StrEnum

from metrics_config import Direction, ProfilerConfig

class MetricStatus(StrEnum):
    NOISE       = "noise"
    IMPROVEMENT = "improvement"
    REGRESSION  = "regression"
    INTERESTING = "interesting"
    IRRELEVANT  = "irrelevant"
    INVALID     = "invalid"

@dataclass
class ComparisonConfig:
    direction:                 Direction = Direction.NEUTRAL
    noise_floor_pct:           float     = 0.0
    improvement_threshold_pct: float     = 0.0
    regression_threshold_pct:  float     = 0.0


def build_comparison_map(cfg: ProfilerConfig) -> dict[str, ComparisonConfig]:
    comparison_map = {}

    for segment in cfg.segments.values():
        for metric in segment.metrics:
            config_instance = ComparisonConfig(
                direction                 = metric.direction,
                noise_floor_pct           = metric.noise_floor_pct,
                improvement_threshold_pct = metric.improvement_threshold_pct,
                regression_threshold_pct  = metric.regression_threshold_pct
            )
            
            comparison_map[metric.name] = config_instance
            
            for structural_field in metric.output_fields():
                comparison_map[structural_field] = config_instance

    return comparison_map