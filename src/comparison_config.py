from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import yaml

SUFFIXES = ["_total", "_mean", "_median", "_stddev", "_min", "_max"]

class Direction(StrEnum):
    HIGHER_BETTER = "higher_better"
    LOWER_BETTER  = "lower_better"
    NEUTRAL       = "neutral"

@dataclass(frozen = True)
class ThresholdConfig:
    direction:                 Direction = Direction.NEUTRAL
    noise_floor_pct:           float     = 0.0
    improvement_threshold_pct: float     = 0.0
    regression_threshold_pct:  float     = 0.0

def load_thresholds_config(yaml_path: Path | str) -> dict[str, ThresholdConfig]:
    with open(yaml_path, "r", encoding = "utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    extended_map: dict[str, ThresholdConfig] = {}
    raw_thresholds                           = raw_data.get("thresholds", {})

    for base_metric_name, raw_cfg in raw_thresholds.items():
        raw_direction  = raw_cfg.get("direction", "neutral")
        
        try:
            direction = Direction(raw_direction)
        except:
            direction = Direction.NEUTRAL

        config_instance = ThresholdConfig(
            direction                 = direction,
            noise_floor_pct           = float(raw_cfg.get("noise_floor_pct", 0.0)),
            improvement_threshold_pct = float(raw_cfg.get("improvement_threshold_pct", 0.0)),
            regression_threshold_pct  = float(raw_cfg.get("regression_threshold_pct", 0.0))
        )

        extended_map[base_metric_name] = config_instance

        for suffix in SUFFIXES:
            suffixed_key               = f"{base_metric_name}{suffix}"
            extended_map[suffixed_key] = config_instance

    return extended_map